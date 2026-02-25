import { useState, useEffect } from 'react'
import { Home, Search, MapPin, DollarSign, Bed, Bath, Users, Star, User, ExternalLink, Phone, Eye, Calendar, Bookmark, Target, TrendingUp, Clock, CheckCircle, AlertCircle, Sparkles, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import ClientSelector from '../components/ClientSelector'
import { API_BASE_URL } from '../api/config'

function CaseManagerHousing() {
  const apiBase = API_BASE_URL ? API_BASE_URL.replace(/\/$/, '') : ''
  const [selectedClient, setSelectedClient] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalResults, setTotalResults] = useState(0)
  const [dashboardData, setDashboardData] = useState(null)
  const [searchParams, setSearchParams] = useState({
    location: 'Los Angeles, CA',
    maxPrice: '',
    bedrooms: '',
    backgroundFriendly: false,
    clientNeeds: []
  })

  // Case Manager Enhanced Search
  const searchHousingForCaseManager = async (page = 1) => {
    if (!searchParams.location) {
      toast.error('Please enter a location')
      return
    }

    setLoading(true)
    try {
      // Build search query for case manager workflow
      let query = 'apartment rental'
      if (searchParams.backgroundFriendly) {
        query += ' background friendly second chance'
      }
      if (searchParams.bedrooms) {
        query += ` ${searchParams.bedrooms} bedroom`
      }
      
      // Prepare client needs
      const clientNeeds = []
      if (searchParams.backgroundFriendly) clientNeeds.push('background_friendly')
      if (selectedClient?.needs) clientNeeds.push(...selectedClient.needs)
      
      const params = new URLSearchParams({
        query: query,
        location: searchParams.location,
        ...(selectedClient?.id && { client_id: selectedClient.id }),
        ...(searchParams.maxPrice && { client_budget: searchParams.maxPrice }),
        ...(clientNeeds.length > 0 && { client_needs: clientNeeds.join(',') })
      })
      
      const response = await fetch(`${apiBase}/api/housing/case-manager-search?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Case Manager Housing API Response:', data)
        
        if (data.success && data.case_manager_view) {
          setSearchResults(data.results || [])
          setTotalResults(data.summary?.total_results || 0)
          setCurrentPage(page)
          
          toast.success(`Found ${data.results?.length || 0} housing options with case manager tools`)
        } else {
          throw new Error(data.error || 'Case manager search failed')
        }
      } else {
        throw new Error('Case manager search API not available')
      }
    } catch (error) {
      console.error('Case manager search error:', error)
      toast.error('Case manager search failed. Please try again.')
      setSearchResults([])
      setTotalResults(0)
    } finally {
      setLoading(false)
    }
  }

  // Load case manager dashboard
  const loadDashboard = async () => {
    try {
      const params = new URLSearchParams()
      if (selectedClient?.id) {
        params.append('client_id', selectedClient.id)
      }
      
      const response = await fetch(`${apiBase}/api/housing/case-manager-dashboard?${params}`)
      if (response.ok) {
        const data = await response.json()
        setDashboardData(data)
      }
    } catch (error) {
      console.error('Dashboard load error:', error)
    }
  }

  // Handle quick actions
  const handleQuickAction = async (action, result) => {
    switch (action.type) {
      case 'quick_search':
        window.open(action.url, '_blank', 'noopener,noreferrer')
        toast.success(`Opening ${result.site_info.name} search`)
        break
        
      case 'save_client':
        if (selectedClient) {
          // Here you would save to client's housing resources
          toast.success(`Saved to ${selectedClient.first_name}'s housing resources`)
        } else {
          toast.error('Please select a client first')
        }
        break
        
      case 'schedule_followup':
        if (selectedClient) {
          // Here you would create a follow-up reminder
          toast.success(`Follow-up scheduled for ${selectedClient.first_name}`)
        } else {
          toast.error('Please select a client first')
        }
        break
        
      case 'get_contacts':
        if (result.contact_info.has_contact) {
          const contacts = [
            ...result.contact_info.phones.map(p => `Phone: ${p}`),
            ...result.contact_info.emails.map(e => `Email: ${e}`)
          ]
          toast.success(`Contacts found: ${contacts.join(', ')}`)
        } else {
          toast.info('No direct contacts found - visit listing for details')
        }
        break
        
      default:
        window.open(result.url, '_blank', 'noopener,noreferrer')
    }
  }

  // Handle dashboard quick searches
  const handleDashboardQuickSearch = (quickSearch) => {
    setSearchParams(prev => ({
      ...prev,
      location: quickSearch.location || prev.location,
      maxPrice: quickSearch.budget || prev.maxPrice,
      clientNeeds: quickSearch.needs || []
    }))
    
    // Trigger search with new parameters
    setTimeout(() => searchHousingForCaseManager(1), 100)
  }

  // Load dashboard on component mount and when client changes
  useEffect(() => {
    loadDashboard()
  }, [selectedClient])

  // Auto-search when client is selected
  useEffect(() => {
    if (selectedClient) {
      searchHousingForCaseManager(1)
    }
  }, [selectedClient])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-red-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-orange-500 to-amber-500 rounded-xl shadow-lg">
                <Target className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-orange-200 to-amber-200 bg-clip-text text-transparent">
                  Case Manager Housing Tools
                </h1>
                <p className="text-gray-300 text-lg">Enhanced housing search with workflow optimization</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Client Selection - FIXED with proper z-index */}
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20 mb-8 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-3 text-white">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client for Housing Search
            </h2>
            <ClientSelector 
              onClientSelect={setSelectedClient}
              placeholder="Select a client to search housing for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-200">
                      <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
                    </p>
                    <p className="text-xs text-blue-300">
                      Budget: ${selectedClient.budget || 'Not specified'} | 
                      Needs: {selectedClient.needs?.join(', ') || 'None specified'}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="inline-block px-3 py-1 bg-gradient-to-r from-orange-500/20 to-amber-500/20 text-orange-300 text-xs rounded-full border border-orange-500/30">
                      Case Management Mode
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Dashboard Quick Actions */}
          {dashboardData && (
            <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white">Quick Searches</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {dashboardData.quick_searches?.map((quickSearch, index) => (
                  <button
                    key={index}
                    onClick={() => handleDashboardQuickSearch(quickSearch)}
                    className="group p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl hover:border-white/30 transition-all duration-300 text-left hover:scale-105 hover:shadow-xl hover:shadow-emerald-500/20"
                  >
                    <div className="text-sm font-medium text-white group-hover:text-emerald-200 transition-colors">{quickSearch.label}</div>
                    <div className="text-xs text-gray-400 group-hover:text-gray-300 transition-colors mt-2">
                      {quickSearch.budget && `Budget: $${quickSearch.budget}`}
                      {quickSearch.needs && ` • ${quickSearch.needs.join(', ')}`}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search Form */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                <Search className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">Housing Search Criteria</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Location
                </label>
                <div className="relative">
                  <MapPin className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="text"
                    placeholder="City, State or ZIP"
                    value={searchParams.location}
                    onChange={(e) => setSearchParams(prev => ({ ...prev, location: e.target.value }))}
                    className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Client Budget
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    type="number"
                    placeholder="Monthly rent limit"
                    value={searchParams.maxPrice}
                    onChange={(e) => setSearchParams(prev => ({ ...prev, maxPrice: e.target.value }))}
                    className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Bedrooms
                </label>
                <select
                  value={searchParams.bedrooms}
                  onChange={(e) => setSearchParams(prev => ({ ...prev, bedrooms: e.target.value }))}
                  className="w-full px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white transition-all duration-300 hover:bg-white/15"
                >
                  <option value="" className="bg-gray-800 text-white">Any</option>
                  <option value="1" className="bg-gray-800 text-white">1</option>
                  <option value="2" className="bg-gray-800 text-white">2</option>
                  <option value="3" className="bg-gray-800 text-white">3</option>
                  <option value="4+" className="bg-gray-800 text-white">4+</option>
                </select>
              </div>
              
              <div className="flex items-end">
                <label className="flex items-center group cursor-pointer">
                  <input
                    type="checkbox"
                    checked={searchParams.backgroundFriendly}
                    onChange={(e) => setSearchParams(prev => ({ ...prev, backgroundFriendly: e.target.checked }))}
                    className="mr-3 h-5 w-5 text-yellow-500 focus:ring-yellow-400 border-gray-400 rounded bg-white/10"
                  />
                  <span className="text-sm text-gray-300 group-hover:text-white transition-colors">Background-friendly only</span>
                </label>
              </div>
            </div>
            
            <button
              onClick={() => searchHousingForCaseManager(1)}
              disabled={loading}
              className="group w-full md:w-auto px-8 py-4 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-orange-500/25 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center justify-center gap-3"
            >
              <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                <Search className="h-5 w-5" />
              </div>
              {loading ? 'Searching...' : 'Search with Case Manager Tools'}
            </button>
          </div>

          {/* Results */}
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                <div className="relative mx-auto mb-6 w-12 h-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-orange-500/20 border-t-orange-500"></div>
                  <div className="absolute inset-2 animate-spin rounded-full border-2 border-amber-500/20 border-t-amber-500" style={{animationDirection: 'reverse'}}></div>
                </div>
                <p className="text-gray-300 font-medium">Searching with case manager workflow tools...</p>
              </div>
            ) : searchResults.length > 0 ? (
              <>
                {/* Results Header with Case Manager Summary */}
                <div className="bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-xl shadow-purple-500/10 mb-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                        <Target className="h-6 w-6 text-white" />
                      </div>
                      <span className="font-bold text-white text-xl">
                        Case Manager Results: {totalResults} Housing Options Found
                      </span>
                    </div>
                    <div className="text-sm text-gray-300 px-4 py-2 bg-white/10 rounded-full border border-white/20">
                      Enhanced with workflow tools
                    </div>
                  </div>
                  
                  {/* Priority Summary */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="group bg-gradient-to-br from-red-500/20 to-pink-500/20 backdrop-blur-sm p-4 rounded-xl border border-red-500/30 hover:border-red-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                          <AlertCircle size={16} className="text-white" />
                        </div>
                        <span className="text-sm font-medium text-red-300">High Priority</span>
                      </div>
                      <div className="text-2xl font-bold text-red-400">
                        {searchResults.filter(r => r.priority_level === 'high').length}
                      </div>
                    </div>
                    <div className="group bg-gradient-to-br from-yellow-500/20 to-amber-500/20 backdrop-blur-sm p-4 rounded-xl border border-yellow-500/30 hover:border-yellow-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-gradient-to-r from-yellow-500 to-amber-500 rounded-lg">
                          <Clock size={16} className="text-white" />
                        </div>
                        <span className="text-sm font-medium text-yellow-300">Medium Priority</span>
                      </div>
                      <div className="text-2xl font-bold text-yellow-400">
                        {searchResults.filter(r => r.priority_level === 'medium').length}
                      </div>
                    </div>
                    <div className="group bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm p-4 rounded-xl border border-green-500/30 hover:border-green-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                          <CheckCircle size={16} className="text-white" />
                        </div>
                        <span className="text-sm font-medium text-green-300">With Contacts</span>
                      </div>
                      <div className="text-2xl font-bold text-green-400">
                        {searchResults.filter(r => r.contact_info?.has_contact).length}
                      </div>
                    </div>
                    <div className="group bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm p-4 rounded-xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                          <DollarSign size={16} className="text-white" />
                        </div>
                        <span className="text-sm font-medium text-blue-300">Budget Matches</span>
                      </div>
                      <div className="text-2xl font-bold text-blue-400">
                        {searchResults.filter(r => r.match_score >= 40).length}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Property Listings with Case Manager Tools */}
                {searchResults.map((property) => (
                  <div key={property.id} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 hover:border-white/30 transition-all duration-500 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20 border-l-4" 
                       style={{borderLeftColor: property.priority_level === 'high' ? '#ef4444' : property.priority_level === 'medium' ? '#f59e0b' : '#6b7280'}}>
                    <div className="flex flex-col lg:flex-row gap-8">
                      <div className="lg:w-1/4">
                        <div className="relative bg-gradient-to-br from-orange-500/20 to-amber-500/20 backdrop-blur-sm rounded-2xl h-48 flex items-center justify-center overflow-hidden border border-orange-500/30 group-hover:border-orange-400/50 transition-all duration-300">
                          <div className="flex flex-col items-center justify-center p-4">
                            <div className={`w-16 h-8 bg-gradient-to-r from-${property.site_info.color}-500 to-${property.site_info.color}-600 rounded flex items-center justify-center mb-2 shadow-lg`}>
                              <span className="text-white font-bold text-xs">{property.site_info.name}</span>
                            </div>
                            <span className="text-xs text-orange-200 text-center font-medium">{property.site_info.name} Listing</span>
                          </div>
                          
                          {/* Priority Badge */}
                          <div className="absolute top-3 right-3">
                            <span className={`inline-block px-3 py-1 text-white text-xs rounded-full font-medium shadow-lg ${
                              property.priority_level === 'high' ? 'bg-gradient-to-r from-red-500 to-pink-500' : 
                              property.priority_level === 'medium' ? 'bg-gradient-to-r from-yellow-500 to-amber-500' : 'bg-gradient-to-r from-gray-500 to-gray-600'
                            }`}>
                              {property.priority_level.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="lg:w-3/4">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="text-2xl font-bold text-white group-hover:text-orange-200 transition-colors">
                                {property.title}
                              </h3>
                              <span className="text-xs bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 px-3 py-1 rounded-full border border-blue-500/30">
                                Match: {property.match_score}%
                              </span>
                            </div>
                            <p className="text-gray-300 flex items-center gap-2 mb-3">
                              <MapPin size={16} className="text-orange-400" />
                              {property.description?.substring(0, 100)}...
                            </p>
                            
                            {/* Match Reasons */}
                            <div className="flex flex-wrap gap-2 mb-4">
                              {property.match_reasons?.map((reason, index) => (
                                <span key={index} className="text-xs bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 px-3 py-1 rounded-full border border-green-500/30">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="text-right ml-4">
                            <p className="text-3xl font-bold bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
                              {property.pricing_info?.price_display || 'See listing'}
                            </p>
                            {property.contact_info?.has_contact && (
                              <span className="inline-block px-3 py-1 bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 text-sm rounded-full mt-2 border border-green-500/30">
                                Has Contacts
                              </span>
                            )}
                          </div>
                        </div>
                        
                        {/* Case Manager Quick Actions */}
                        <div className="flex flex-wrap gap-2 mb-6">
                          {property.quick_actions?.map((action, index) => (
                            <button
                              key={index}
                              onClick={() => handleQuickAction(action, property)}
                              className="group/btn px-4 py-2 text-xs bg-white/10 backdrop-blur-sm hover:bg-white/20 text-gray-300 hover:text-white rounded-lg transition-all duration-300 flex items-center gap-2 border border-white/20 hover:border-white/30 hover:scale-105"
                            >
                              {action.icon === 'search' && <Search size={12} className="text-emerald-400" />}
                              {action.icon === 'bookmark' && <Bookmark size={12} className="text-blue-400" />}
                              {action.icon === 'calendar' && <Calendar size={12} className="text-purple-400" />}
                              {action.icon === 'phone' && <Phone size={12} className="text-green-400" />}
                              {action.icon === 'user' && <User size={12} className="text-indigo-400" />}
                              {action.icon === 'home' && <Home size={12} className="text-orange-400" />}
                              {action.label}
                            </button>
                          ))}
                        </div>
                        
                        {/* Contact Information */}
                        {property.contact_info?.has_contact && (
                          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm p-4 rounded-xl border border-white/20 mb-6">
                            <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                              <Phone size={16} className="text-green-400" />
                              Contact Information:
                            </h4>
                            <div className="text-sm text-gray-300 space-y-1">
                              {property.contact_info.phones?.map((phone, index) => (
                                <div key={index} className="flex items-center gap-2">
                                  <span className="text-green-400">📞</span> {phone}
                                </div>
                              ))}
                              {property.contact_info.emails?.map((email, index) => (
                                <div key={index} className="flex items-center gap-2">
                                  <span className="text-blue-400">✉️</span> {email}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Main Action Buttons */}
                        <div className="flex gap-4">
                          <button 
                            onClick={() => window.open(property.url, '_blank', 'noopener,noreferrer')}
                            className="group/btn px-8 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25 flex items-center gap-2"
                          >
                            <Eye size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                            View Full Listing
                          </button>
                          {selectedClient && (
                            <button 
                              onClick={() => handleQuickAction({type: 'save_client'}, property)}
                              className="group/btn px-8 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-xl font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300 transform hover:scale-105 flex items-center gap-2"
                            >
                              <Bookmark size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                              Save for {selectedClient.first_name}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </>
            ) : (
              <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                <div className="p-4 bg-gradient-to-r from-orange-500/20 to-amber-500/20 rounded-2xl w-fit mx-auto mb-6">
                  <Target size={48} className="text-orange-400" />
                </div>
                <h3 className="text-xl font-medium mb-3 text-white">No housing options found</h3>
                <p className="text-gray-400 mb-6">Select a client and search to see case manager tools</p>
                <button 
                  onClick={() => searchHousingForCaseManager(1)}
                  className="group px-8 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25"
                >
                  Search with Case Manager Tools
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default CaseManagerHousing
