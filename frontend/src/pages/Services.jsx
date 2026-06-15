import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Briefcase, Search, MapPin, Phone, User, Building2, Heart, Users, Car, Home, GraduationCap, Shield, Sparkles, Zap, TrendingUp, X, Calendar, ClipboardList, Activity, DollarSign, FileText, ShoppingCart, AlertTriangle, RefreshCw, Scale, Baby, Flag } from 'lucide-react'
import ClientSelector from '../components/ClientSelector'
import Pagination from '../components/Pagination'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

function Services() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '')
  const [services, setServices] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeCategory, setActiveCategory] = useState(searchParams.get('category') || 'all')
  const [treatmentFilters, setTreatmentFilters] = useState({
    population: searchParams.get('population') || 'all',
    insuranceType: searchParams.get('insurance_type') || 'all',
  })
  
  // Referral modal state
  const [showReferralModal, setShowReferralModal] = useState(false)
  const [selectedService, setSelectedService] = useState(null)
  const [referralForm, setReferralForm] = useState({
    appointment_time: '',
    doctor_name: '',
    items_to_bring: '',
    notes: '',
  })
  const [referralSaving, setReferralSaving] = useState(false)

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: parseInt(searchParams.get('page')) || 1,
    totalPages: 0,
    totalResults: 0,
    perPage: 10,
    hasNextPage: false,
    hasPrevPage: false
  })

  const serviceCategories = [
    { id: 'all',               name: 'All Resources',                  icon: Building2,     gradient: 'from-slate-400 to-slate-500'    },
    { id: 'housing',           name: 'Housing',                        icon: Home,          gradient: 'from-blue-500 to-blue-600'      },
    { id: 'benefits',          name: 'Benefits',                       icon: DollarSign,    gradient: 'from-emerald-500 to-green-600'  },
    { id: 'medical',           name: 'Medical',                        icon: Activity,      gradient: 'from-rose-500 to-red-600'       },
    { id: 'dental',            name: 'Dental',                         icon: Sparkles,      gradient: 'from-cyan-400 to-sky-500'       },
    { id: 'mental-health',     name: 'Mental Health',                  icon: Heart,         gradient: 'from-violet-500 to-purple-600'  },
    { id: 'sud-recovery',      name: 'SUD / Recovery',                 icon: Shield,        gradient: 'from-blue-600 to-indigo-600'    },
    { id: 'legal-aid',         name: 'Legal Aid',                      icon: Scale,         gradient: 'from-indigo-500 to-indigo-600'  },
    { id: 'food',              name: 'Food',                           icon: ShoppingCart,  gradient: 'from-amber-400 to-orange-500'   },
    { id: 'transportation',    name: 'Transportation',                 icon: Car,           gradient: 'from-yellow-400 to-amber-500'   },
    { id: 'employment',        name: 'Employment',                     icon: Briefcase,     gradient: 'from-sky-500 to-blue-500'       },
    { id: 'documents-id',      name: 'Documents / ID',                 icon: FileText,      gradient: 'from-cyan-500 to-teal-500'      },
    { id: 'crisis',            name: 'Crisis',                         icon: AlertTriangle, gradient: 'from-red-500 to-rose-600'       },
    { id: 'veterans',          name: 'Veterans',                       icon: Flag,          gradient: 'from-blue-700 to-indigo-700'    },
    { id: 'disability-ihss',   name: 'Disability / IHSS',              icon: Users,         gradient: 'from-violet-500 to-purple-500'  },
    { id: 'family-parenting',  name: 'Family / Parenting',             icon: Baby,          gradient: 'from-fuchsia-500 to-pink-500'   },
    { id: 'youth-foster',      name: 'Youth / Foster',                 icon: GraduationCap, gradient: 'from-purple-500 to-violet-500'  },
    { id: 'reentry',           name: 'Reentry',                        icon: RefreshCw,     gradient: 'from-teal-500 to-cyan-500'      },
    { id: 'domestic-violence', name: 'Domestic Violence / Victim Svcs',icon: Heart,         gradient: 'from-rose-500 to-pink-500'      },
  ]

  const searchServices = async (query = '', category = 'all', page = pagination.currentPage) => {
    setLoading(true)
    
    // Scroll to top when changing pages
    if (page !== pagination.currentPage) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    
    try {
      // Let the explicit category filter drive the search scope.
      // Only use the user's actual query text; otherwise send a generic services query.
      const trimmedQuery = query.trim()
      const searchQuery = trimmedQuery || 'services'
      
      const params = new URLSearchParams({
        search: searchQuery || 'social services',
        location: 'Los Angeles, CA',
        category,
        page: String(page),
        per_page: String(pagination.perPage)
      })

      if (category === 'substance-abuse' && treatmentFilters.population !== 'all') {
        params.set('population', treatmentFilters.population)
      }
      if (category === 'substance-abuse' && treatmentFilters.insuranceType !== 'all') {
        params.set('insurance_type', treatmentFilters.insuranceType)
      }
      
      // Update URL parameters for bookmarking
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('search', query)
      newSearchParams.set('category', category)
      newSearchParams.set('page', String(page))
      if (category === 'substance-abuse' && treatmentFilters.population !== 'all') {
        newSearchParams.set('population', treatmentFilters.population)
      } else {
        newSearchParams.delete('population')
      }
      if (category === 'substance-abuse' && treatmentFilters.insuranceType !== 'all') {
        newSearchParams.set('insurance_type', treatmentFilters.insuranceType)
      } else {
        newSearchParams.delete('insurance_type')
      }
      setSearchParams(newSearchParams)
      
      const response = await apiFetch(`/api/services/search?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Paginated Services API Response:', data)
        
        if (data.success && data.pagination) {
          // Update pagination state
          setPagination({
            currentPage: data.pagination.current_page,
            totalPages: data.pagination.total_pages,
            totalResults: data.pagination.total_results,
            perPage: data.pagination.per_page,
            hasNextPage: data.pagination.has_next_page,
            hasPrevPage: data.pagination.has_prev_page
          })
          
          // Transform paginated service results
          const transformedServices = (data.service_providers || []).map((result, index) => ({
            id: `service_${data.pagination.current_page}_${index}`,
            name: result.title,
            address: result.address || result.location || 'Address not shown in current result',
            phone: result.phone || 'Visit website for contact details',
            backgroundFriendly: (result.background_friendly_score || 0) >= 60,
            category: result.service_type || category,
            url: result.url || result.link,
            description: result.description || '',
            source: result.source,
            relevanceReason: result.relevance_reason || '',
            serviceType: result.service_type || 'General Services',
            servesPopulation: result.serves_population || '',
            acceptsMediCal: Boolean(result.accepts_medi_cal),
            acceptsPrivateInsurance: Boolean(result.accepts_private_insurance),
            acceptsMedicare: Boolean(result.accepts_medicare),
          }))
          
          setServices(transformedServices)
          toast.success(`Found ${data.pagination.total_results.toLocaleString()} services (showing page ${page})`)
        } else {
          throw new Error(data.message || 'Search API returned invalid data')
        }
      } else {
        throw new Error('Search API not available')
      }
    } catch (error) {
      console.error('Services search error:', error)
      toast.error('Search failed. Please try again.')
      setServices([])
      setPagination(prev => ({ ...prev, totalResults: 0, totalPages: 0 }))
    } finally {
      setLoading(false)
    }
  }

  // Pagination handlers
  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, currentPage: newPage }))
    searchServices(searchTerm, activeCategory, newPage)
  }

  const handleNewSearch = () => {
    // Reset to page 1 for new searches
    setPagination(prev => ({ ...prev, currentPage: 1 }))
    searchServices(searchTerm, activeCategory, 1)
  }

  const handleCategoryChange = (category) => {
    setActiveCategory(category)
    setPagination(prev => ({ ...prev, currentPage: 1 }))
    searchServices(searchTerm, category, 1)
  }

  const handleTreatmentFilterChange = (field, value) => {
    const nextFilters = { ...treatmentFilters, [field]: value }
    setTreatmentFilters(nextFilters)
  }

  // Load services on component mount
  useEffect(() => {
    if (searchParams.get('search') || searchParams.get('category')) {
      searchServices(searchTerm, activeCategory, pagination.currentPage)
    }
  }, []) // Only run on mount

  const handleSearch = () => {
    handleNewSearch()
  }

  // Always display results returned by the server. Do not re-filter by the same term client-side,
  // as that can hide valid matches from external sources.
  const filteredServices = services

  const openReferralModal = (service) => {
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }
    setSelectedService(service)
    setReferralForm({ appointment_time: '', doctor_name: '', items_to_bring: '', notes: '' })
    setShowReferralModal(true)
  }

  const submitReferral = async () => {
    if (!selectedClient?.client_id || !selectedService) return
    setReferralSaving(true)
    try {
      const response = await apiFetch(`/api/clients/${selectedClient.client_id}/service-referrals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_name: selectedService.name,
          service_type: selectedService.serviceType || selectedService.category,
          provider_name: selectedService.name,
          phone: selectedService.phone,
          address: selectedService.address,
          url: selectedService.url,
          appointment_time: referralForm.appointment_time || null,
          doctor_name: referralForm.doctor_name || null,
          items_to_bring: referralForm.items_to_bring || null,
          notes: referralForm.notes || null,
        }),
      })
      if (!response.ok) throw new Error('Failed to create referral')
      toast.success(`Referral created for ${selectedClient.first_name} ${selectedClient.last_name}`)
      setShowReferralModal(false)
    } catch (error) {
      toast.error(error?.message || 'Failed to create referral')
    } finally {
      setReferralSaving(false)
    }
  }

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-xl shadow-lg">
                <Building2 className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-teal-200 to-cyan-200 bg-clip-text text-transparent">
                  Services Directory
                </h1>
                <p className="text-gray-300 text-lg">Find local services and resources</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
          {/* Client Selection - FIXED with proper z-index */}
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20 mb-8 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-3 text-white">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector 
              onClientSelect={setSelectedClient}
              placeholder="Select a client to find services for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                <p className="text-sm text-blue-200">
                  Finding services for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
                </p>
              </div>
            )}
          </div>

          {/* Category Filter */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white">Service Categories</h3>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
              {serviceCategories.map((category) => (
                <button
                  key={category.id}
                  onClick={() => handleCategoryChange(category.id)}
                  className={`group flex flex-col items-center gap-3 p-4 rounded-xl transition-all duration-200 ${
                    activeCategory === category.id
                      ? 'bg-slate-700/90 border border-teal-400/60 text-white shadow-lg shadow-teal-500/20 scale-[1.03]'
                      : 'bg-slate-800/75 border border-white/[0.09] text-slate-300 hover:text-white hover:bg-slate-700/70 hover:border-white/20 hover:-translate-y-0.5 hover:shadow-md hover:shadow-black/40'
                  }`}
                >
                  <div className={`p-2 rounded-lg bg-gradient-to-br ${category.gradient} transition-all duration-200 ${
                    activeCategory === category.id
                      ? 'opacity-100 shadow-sm'
                      : 'opacity-75 group-hover:opacity-95'
                  }`}>
                    <category.icon size={18} className="text-white" />
                  </div>
                  <span className="text-xs font-semibold text-center leading-tight tracking-wide">{category.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Search */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search services..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={loading}
                className="group px-8 py-4 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-teal-500/25 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2"
              >
                <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                  <Search className="h-4 w-4" />
                </div>
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {activeCategory === 'substance-abuse' && (
              <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-blue-100">
                    Population Type
                  </label>
                  <select
                    value={treatmentFilters.population}
                    onChange={(e) => handleTreatmentFilterChange('population', e.target.value)}
                    className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-white focus:border-teal-500 focus:outline-none"
                  >
                    <option value="all" className="bg-slate-900">All populations</option>
                    <option value="men" className="bg-slate-900">Men</option>
                    <option value="women" className="bg-slate-900">Women</option>
                    <option value="co-ed" className="bg-slate-900">Co-ed</option>
                    <option value="couples" className="bg-slate-900">Couples</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-blue-100">
                    Insurance Type
                  </label>
                  <select
                    value={treatmentFilters.insuranceType}
                    onChange={(e) => handleTreatmentFilterChange('insuranceType', e.target.value)}
                    className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-white focus:border-teal-500 focus:outline-none"
                  >
                    <option value="all" className="bg-slate-900">All insurance</option>
                    <option value="medi-cal" className="bg-slate-900">Medi-Cal</option>
                    <option value="private" className="bg-slate-900">Private insurance</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Services Results */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
            <div className="p-8">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white">
                    Services
                    {pagination.totalResults > 0 && (
                      <span className="text-gray-400 font-normal ml-3 text-lg">
                        ({pagination.totalResults.toLocaleString()} total found)
                      </span>
                    )}
                  </h3>
                </div>
                <div className="flex items-center gap-4">
                  {pagination.totalResults > 0 && (
                    <div className="px-4 py-2 bg-gradient-to-r from-purple-500/20 to-indigo-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30">
                      <span className="text-sm text-purple-200">
                        Page {pagination.currentPage} of {pagination.totalPages.toLocaleString()}
                      </span>
                    </div>
                  )}
                  {activeCategory !== 'all' && (
                    <div className={`px-4 py-2 bg-gradient-to-r ${serviceCategories.find(c => c.id === activeCategory)?.bgGradient} backdrop-blur-sm rounded-xl border ${serviceCategories.find(c => c.id === activeCategory)?.borderColor}`}>
                      <span className="text-sm font-medium text-white">
                        {serviceCategories.find(c => c.id === activeCategory)?.name}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              {loading ? (
                <div className="text-center py-16">
                  <div className="relative mx-auto mb-6 w-12 h-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500/20 border-t-teal-500"></div>
                    <div className="absolute inset-2 animate-spin rounded-full border-2 border-cyan-500/20 border-t-cyan-500" style={{animationDirection: 'reverse'}}></div>
                  </div>
                  <p className="text-gray-300 font-medium">Searching for services...</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {services.map((service, index) => (
                      <div key={service.id || index} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm p-6 border border-white/20 rounded-xl hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-teal-500/20">
                        <div className="flex justify-between items-start mb-4">
                          <h4 className="font-bold text-white text-lg group-hover:text-teal-200 transition-colors">{service.name}</h4>
                          {service.backgroundFriendly && (
                            <span className="px-3 py-1 bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 text-xs font-medium rounded-full border border-green-500/30">
                              Background Friendly
                            </span>
                          )}
                        </div>
                        <div className="space-y-3 text-sm text-gray-300 mb-6">
                          <div className="flex items-center gap-3">
                            <div className="p-1 bg-emerald-500/20 rounded">
                              <Sparkles className="h-4 w-4 text-emerald-400" />
                            </div>
                            <span className="font-medium text-emerald-200">{service.serviceType}</span>
                          </div>
                          {service.source && (
                            <div>
                              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                                service.source === 'Internal Resource Library'
                                  ? 'bg-teal-500/20 border-teal-500/40 text-teal-200'
                                  : service.source === 'Virgil St Resources' || (service.source || '').toLowerCase().startsWith('virgil')
                                  ? 'bg-blue-500/20 border-blue-500/40 text-blue-200'
                                  : 'bg-slate-500/20 border-slate-500/40 text-slate-300'
                              }`}>
                                {service.source === 'Internal Resource Library' ? 'Internal Resource Library'
                                  : (service.source === 'Virgil St Resources' || (service.source || '').toLowerCase().startsWith('virgil')) ? 'Virgil St Resources'
                                  : service.source}
                              </span>
                            </div>
                          )}
                          {(service.servesPopulation || service.acceptsMediCal || service.acceptsPrivateInsurance || service.acceptsMedicare) && (
                            <div className="flex flex-wrap gap-2">
                              {service.servesPopulation ? (
                                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/15 px-2.5 py-1 text-xs font-medium text-cyan-200">
                                  {service.servesPopulation.replace('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())}
                                </span>
                              ) : null}
                              {service.acceptsMediCal ? (
                                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-200">
                                  Medi-Cal
                                </span>
                              ) : null}
                              {service.acceptsPrivateInsurance ? (
                                <span className="rounded-full border border-purple-500/30 bg-purple-500/15 px-2.5 py-1 text-xs font-medium text-purple-200">
                                  Private Insurance
                                </span>
                              ) : null}
                              {service.acceptsMedicare ? (
                                <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2.5 py-1 text-xs font-medium text-amber-200">
                                  Medicare
                                </span>
                              ) : null}
                            </div>
                          )}
                          <div className="flex items-start gap-3">
                            <div className="p-1 bg-teal-500/20 rounded mt-0.5">
                              <MapPin className="h-4 w-4 text-teal-400" />
                            </div>
                            <span className="flex-1">{service.address}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="p-1 bg-blue-500/20 rounded">
                              <Phone className="h-4 w-4 text-blue-400" />
                            </div>
                            <span>{service.phone}</span>
                          </div>
                          {service.url && (
                            <div className="flex items-center gap-3">
                              <div className="p-1 bg-purple-500/20 rounded">
                                <Building2 className="h-4 w-4 text-purple-400" />
                              </div>
                              <a 
                                href={service.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-teal-400 hover:text-teal-300 underline transition-colors"
                              >
                                Visit Website
                              </a>
                            </div>
                          )}
                        </div>

                          {service.relevanceReason && (
                          <div className="mb-6 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-4">
                            <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300 mb-1">
                              Why this matched
                            </p>
                            <p className="text-sm text-cyan-100">{service.relevanceReason}</p>
                          </div>
                        )}
                        
                        <div className="flex gap-3">
                          <button
                            onClick={() => openReferralModal(service)}
                            className="group/btn flex-1 px-4 py-3 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white text-sm rounded-lg font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-teal-500/25"
                          >
                            Refer Client
                          </button>
                          <button 
                            onClick={() => service.url ? window.open(service.url, '_blank') : toast.info('Contact information: ' + service.phone)}
                            className="group/btn px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 text-sm rounded-lg font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300 transform hover:scale-105"
                          >
                            Contact
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Pagination Component */}
                  {!loading && services.length > 0 && (
                    <Pagination
                      currentPage={pagination.currentPage}
                      totalPages={pagination.totalPages}
                      totalResults={pagination.totalResults}
                      perPage={pagination.perPage}
                      onPageChange={handlePageChange}
                      loading={loading}
                      className="mt-8 border-t border-white/10 pt-8"
                    />
                  )}
                </>
              )}

              {!loading && (searchTerm ? filteredServices.length === 0 : services.length === 0) && (
                <div className="text-center py-16">
                  <div className="p-4 bg-gradient-to-r from-gray-500/20 to-gray-600/20 rounded-2xl w-fit mx-auto mb-6">
                    <Search size={48} className="text-gray-400" />
                  </div>
                  <h3 className="text-xl font-medium mb-3 text-white">No services found</h3>
                  <p className="text-gray-400">Try adjusting your search terms or category</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Referral Details Modal */}
      {showReferralModal && selectedService && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowReferralModal(false)} />
          <div className="relative z-10 w-full max-w-lg bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border border-white/20 shadow-2xl shadow-teal-500/20 p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                  <ClipboardList className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">Refer Client</h2>
                  <p className="text-sm text-teal-300">{selectedService.name}</p>
                </div>
              </div>
              <button onClick={() => setShowReferralModal(false)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mb-4 p-3 bg-teal-500/10 border border-teal-500/20 rounded-xl">
              <p className="text-sm text-teal-200">
                Referring <strong className="text-white">{selectedClient?.first_name} {selectedClient?.last_name}</strong> to this service.
                All fields below are optional.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1 flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> Appointment Date/Time
                </label>
                <input
                  type="datetime-local"
                  value={referralForm.appointment_time}
                  onChange={e => setReferralForm(f => ({ ...f, appointment_time: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Doctor / Provider Name</label>
                <input
                  type="text"
                  placeholder="e.g. Dr. Smith"
                  value={referralForm.doctor_name}
                  onChange={e => setReferralForm(f => ({ ...f, doctor_name: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">What Client Needs to Bring</label>
                <input
                  type="text"
                  placeholder="e.g. ID, insurance card, referral letter"
                  value={referralForm.items_to_bring}
                  onChange={e => setReferralForm(f => ({ ...f, items_to_bring: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Notes</label>
                <textarea
                  rows={3}
                  placeholder="Any additional notes for this referral..."
                  value={referralForm.notes}
                  onChange={e => setReferralForm(f => ({ ...f, notes: e.target.value }))}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 resize-none"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowReferralModal(false)}
                className="flex-1 px-4 py-2.5 bg-white/10 border border-white/20 text-gray-300 rounded-xl hover:bg-white/20 hover:text-white transition-all"
              >
                Cancel
              </button>
              <button
                onClick={submitReferral}
                disabled={referralSaving}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all disabled:opacity-50"
              >
                {referralSaving ? 'Saving...' : 'Create Referral'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Services
