import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Briefcase, Search, MapPin, Star, Bookmark, ExternalLink, Clock, DollarSign, User, Zap, TrendingUp, Send, X, Package, ShoppingBag, Truck, UtensilsCrossed, Camera, Building2, Wrench, GraduationCap } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import LocationSelector from '../components/LocationSelector'
import Pagination from '../components/Pagination'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'
import {
  clientLocation,
  fetchClientWithOperationalContext,
  getIntakeContext,
  getNeedKeys,
  getTreatmentPlanContext,
} from '../utils/clientOperationalContext'

const CRAIGSLIST_JOB_REGIONS = [
  { match: ['los angeles', 'hollywood', 'van nuys', 'panorama city', 'north hollywood', 'burbank', 'glendale', 'pasadena', 'santa monica', 'venice', 'culver city', 'inglewood', 'compton', 'downey', 'whittier', 'long beach', 'torrance', 'gardena', 'hawthorne'], base: 'https://losangeles.craigslist.org' },
  { match: ['anaheim', 'santa ana', 'orange'], base: 'https://orangecounty.craigslist.org' },
  { match: ['riverside', 'san bernardino'], base: 'https://inlandempire.craigslist.org' },
  { match: ['lancaster', 'palmdale'], base: 'https://losangeles.craigslist.org' },
]

const JOB_CATEGORY_TILES = [
  { id: 'warehouse', label: 'Warehouse', keywords: 'warehouse', icon: Package, gradient: 'from-emerald-500 to-green-600' },
  { id: 'retail', label: 'Retail', keywords: 'retail sales associate', icon: ShoppingBag, gradient: 'from-pink-500 to-rose-600' },
  { id: 'delivery', label: 'Delivery', keywords: 'delivery driver', icon: Truck, gradient: 'from-amber-500 to-orange-600' },
  { id: 'food-service', label: 'Food Service', keywords: 'food service', icon: UtensilsCrossed, gradient: 'from-cyan-500 to-blue-600' },
  { id: 'photography', label: 'Photography', keywords: 'photographer', icon: Camera, gradient: 'from-violet-500 to-purple-600' },
  { id: 'office', label: 'Office', keywords: 'office assistant', icon: Building2, gradient: 'from-sky-500 to-cyan-600' },
  { id: 'maintenance', label: 'Maintenance', keywords: 'maintenance janitorial', icon: Wrench, gradient: 'from-slate-500 to-slate-700' },
  { id: 'training', label: 'Training / Entry', keywords: 'entry level training', icon: GraduationCap, gradient: 'from-indigo-500 to-blue-600' },
]

function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('jobCategory') || '')
  const [searchForm, setSearchForm] = useState({
    keywords: searchParams.get('keywords') || '',
    location: searchParams.get('location') || 'Los Angeles',
    backgroundFriendly: searchParams.get('backgroundFriendly') === 'true',
    jobType: 'all',
    experienceLevel: 'all',
    searchType: searchParams.get('searchType') || 'general'  // 'general' or 'specific'
  })
  const [savedJobs, setSavedJobs] = useState([])
  const [activeTab, setActiveTab] = useState('search')
  const [linkResources, setLinkResources] = useState(null)
  const [linksLoading, setLinksLoading] = useState(false)
  const [clientResumes, setClientResumes] = useState([])
  const [showApplyModal, setShowApplyModal] = useState(false)
  const [applyingJob, setApplyingJob] = useState(null)
  const [selectedResumeId, setSelectedResumeId] = useState('')
  const [applyLoading, setApplyLoading] = useState(false)
  
  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: parseInt(searchParams.get('page')) || 1,
    totalPages: 0,
    totalResults: 0,
    perPage: 10,
    hasNextPage: false,
    hasPrevPage: false
  })

  useEffect(() => {
    const clientId = searchParams.get('client')
    if (!clientId || selectedClient?.client_id === clientId) return

    fetchClientWithOperationalContext(apiFetch, clientId)
      .then(setSelectedClient)
      .catch((error) => {
        console.error('Failed to load jobs client from URL:', error)
      })
  }, [searchParams, selectedClient?.client_id])

  useEffect(() => {
    if (selectedClient?.client_id) {
      fetchClientResumes(selectedClient.client_id)
      fetchSavedJobs(selectedClient.client_id)
    } else {
      setClientResumes([])
      setSelectedResumeId('')
      setSavedJobs([])
    }
  }, [selectedClient?.client_id])

  useEffect(() => {
    if (!selectedClient?.client_id) return

    const intake = getIntakeContext(selectedClient)
    const treatmentPlan = getTreatmentPlanContext(selectedClient)
    const needKeys = getNeedKeys(selectedClient)
    const goalText = [
      ...(Array.isArray(treatmentPlan.goals) ? treatmentPlan.goals : []),
      intake.goals,
    ]
      .map((goal) => typeof goal === 'string' ? goal : goal?.description)
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    const suggestedKeywords = goalText.includes('warehouse')
      ? 'warehouse'
      : goalText.includes('office') || goalText.includes('administrative')
        ? 'office assistant'
        : goalText.includes('food') || goalText.includes('restaurant')
          ? 'food service'
          : 'background friendly entry level'

    setSearchForm((prev) => ({
      ...prev,
      keywords: prev.keywords || (needKeys.has('job_search') ? suggestedKeywords : prev.keywords),
      location: prev.location === 'Los Angeles' ? clientLocation(selectedClient, prev.location) : prev.location,
      backgroundFriendly: prev.backgroundFriendly || Boolean(intake.prior_convictions || needKeys.has('job_search')),
    }))
  }, [selectedClient?.client_id])

  const resolveCraigslistJobsBase = (locationValue) => {
    const normalized = (locationValue || '').toLowerCase()
    const matchedRegion = CRAIGSLIST_JOB_REGIONS.find((region) =>
      region.match.some((token) => normalized.includes(token))
    )
    return matchedRegion?.base || 'https://losangeles.craigslist.org'
  }

  const openCraigslistJobsSearch = () => {
    const location = (searchForm.location || 'Los Angeles, CA').trim()
    const keywords = (searchForm.keywords || 'jobs').trim()
    const base = resolveCraigslistJobsBase(location)
    const queryParts = [keywords]

    if (searchForm.backgroundFriendly) {
      queryParts.push('second chance')
      queryParts.push('felony friendly')
    }

    const craigslistParams = new URLSearchParams({
      query: queryParts.join(' '),
      sort: 'date'
    })

    if (searchForm.jobType === 'full-time') {
      craigslistParams.set('employment_type', '1')
    } else if (searchForm.jobType === 'part-time') {
      craigslistParams.set('employment_type', '2')
    } else if (searchForm.jobType === 'contract') {
      craigslistParams.set('employment_type', '3')
    }

    window.open(`${base}/search/jjj?${craigslistParams.toString()}`, '_blank', 'noopener,noreferrer')
  }

  const fetchClientResumes = async (clientId) => {
    try {
      const response = await apiFetch(`/api/resume/list/${clientId}`)
      if (!response.ok) {
        throw new Error('Failed to load client resumes')
      }
      const data = await response.json()
      const resumes = data.resumes || []
      setClientResumes(resumes)
      setSelectedResumeId(resumes[0]?.resume_id || '')
    } catch (error) {
      console.error('Error fetching client resumes:', error)
      setClientResumes([])
      setSelectedResumeId('')
    }
  }

  const fetchSavedJobs = async (clientId) => {
    try {
      const response = await apiFetch(`/api/jobs/saved/${clientId}`)
      if (!response.ok) {
        throw new Error('Failed to load saved jobs')
      }

      const data = await response.json()
      setSavedJobs(data.saved_jobs || [])
    } catch (error) {
      console.error('Error fetching saved jobs:', error)
      setSavedJobs([])
    }
  }

  const searchJobs = async (page = pagination.currentPage, overrides = null) => {
    setLoading(true)
    
    // Scroll to top when changing pages
    if (page !== pagination.currentPage) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    
    try {
      const effectiveForm = overrides || searchForm
      // Choose endpoint based on search type
      const searchEndpoint = effectiveForm.searchType === 'general' 
        ? '/api/jobs/search/quick'
        : '/api/jobs/search/scrapers';
      
      // Build search parameters
      const params = new URLSearchParams({
        keywords: effectiveForm.keywords || 'jobs',
        location: effectiveForm.location || 'Los Angeles, CA',
        background_friendly: String(!!effectiveForm.backgroundFriendly),
        page: String(page),
        per_page: String(pagination.perPage)
      })
      
      // Add sources parameter for scraper search
      if (effectiveForm.searchType === 'specific') {
        params.set('sources', 'craigslist,builtinla,government,city_la')
      }
      
      // Update URL parameters for bookmarking
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('keywords', effectiveForm.keywords || 'jobs')
      newSearchParams.set('location', effectiveForm.location || 'Los Angeles, CA')
      newSearchParams.set('backgroundFriendly', String(!!effectiveForm.backgroundFriendly))
      newSearchParams.set('searchType', effectiveForm.searchType)
      newSearchParams.set('page', String(page))
      if (selectedCategory) {
        newSearchParams.set('jobCategory', selectedCategory)
      } else {
        newSearchParams.delete('jobCategory')
      }
      setSearchParams(newSearchParams)
      
      const response = await apiFetch(`${searchEndpoint}?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Paginated Jobs API Response:', data)
        
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
          
          // Transform paginated job results
          const transformedJobs = (data.jobs || []).map((result, index) => ({
            id: `job_${data.pagination.current_page}_${index}`,
            title: result.title,
            company: result.provider || result.metadata?.company || result.source || 'See job posting',
            location: result.location || result.metadata?.location || effectiveForm.location,
            salary: result.salary || result.metadata?.salary || 'See job posting',
            type: result.metadata?.employment_type || 'See job posting',
            posted: result.metadata?.posted_date || 'See job posting',
            description: result.description || 'See job posting',
            requirements: result.metadata?.requirements || ['Visit the job posting for specific requirements'],
            benefits: result.metadata?.benefits || ['Visit the job posting for benefits information'],
            backgroundFriendly: (result.background_friendly_score || 0) >= 60,
            backgroundScore: result.background_friendly_score ?? null,
            isSecondChance: (result.background_friendly_score || 0) >= 60,
            url: result.url || result.link,
            isScraped: result.metadata?.scraped || false,
            contactInfo: result.metadata?.contact_info || {
              phone: 'Visit job posting',
              email: 'Visit job posting'
            }
          }))
          
          setJobs(transformedJobs)
          const searchTypeLabel = effectiveForm.searchType === 'general' ? 'job sites' : 'specific listings'
          toast.success(`Found ${data.pagination.total_results.toLocaleString()} ${searchTypeLabel} (showing page ${page})`)
        } else {
          throw new Error(data.error || 'Search API returned invalid data')
        }
      } else {
        throw new Error('Search API not available')
      }
    } catch (error) {
      console.error('Job search error:', error)
      const errorMessage = effectiveForm.searchType === 'specific' 
        ? 'Scraper search failed. Try switching to General Search.'
        : 'Search failed. Please try again.'
      toast.error(errorMessage)
      setJobs([])
      setPagination(prev => ({ ...prev, totalResults: 0, totalPages: 0 }))
    } finally {
      setLoading(false)
    }
  }

  const saveJob = async (job, note = '') => {
    const clientId = selectedClient?.client_id
    if (!clientId) {
      toast.error('Please select a client before saving a job')
      return
    }

    try {
      const response = await apiFetch('/api/jobs/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: job.id,
          client_id: clientId,
          title: job.title,
          company: job.company,
          location: job.location,
          salary: job.salary,
          url: job.url || '',
          notes: note
        })
      })

      if (response.ok) {
        toast.success('Job saved successfully!')
        await fetchSavedJobs(clientId)
      } else {
        throw new Error('Save failed')
      }
    } catch (error) {
      console.error('Save job error:', error)
      toast.error(error?.message || 'Failed to save job')
    }
  }

  const handleSaveJob = (job) => {
    const note = prompt('Add a note about why this job is a good fit:')
    if (note !== null) {
      saveJob(job, note)
    }
  }

  const openApplyModal = (job) => {
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }
    if (clientResumes.length === 0) {
      toast.error('This client needs a saved resume before applying')
      return
    }
    setApplyingJob(job)
    setSelectedResumeId(clientResumes[0]?.resume_id || '')
    setShowApplyModal(true)
  }

  const submitApplication = async () => {
    if (!selectedClient?.client_id || !applyingJob || !selectedResumeId) {
      toast.error('Client, job, or resume selection is missing')
      return
    }

    try {
      setApplyLoading(true)
      const response = await apiFetch('/api/resume/apply-job', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          resume_id: selectedResumeId,
          job_title: applyingJob.title,
          company_name: applyingJob.company,
          job_description: applyingJob.description || ''
        })
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to create application' }))
        throw new Error(error.detail || 'Failed to create application')
      }

      const data = await response.json()
      toast.success(`Application tracked. Match score: ${data.match_score}%`)
      setShowApplyModal(false)
      setApplyingJob(null)
    } catch (error) {
      console.error('Apply with resume error:', error)
      toast.error(error.message || 'Failed to track application')
    } finally {
      setApplyLoading(false)
    }
  }

  // Pagination handlers
  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, currentPage: newPage }))
    searchJobs(newPage)
  }

  const handleNewSearch = () => {
    // Reset to page 1 for new searches
    setPagination(prev => ({ ...prev, currentPage: 1 }))
    searchJobs(1)
  }

  const applyJobCategory = (category) => {
    const nextForm = {
      ...searchForm,
      keywords: category.keywords,
    }
    setSelectedCategory(category.id)
    setSearchForm(nextForm)
    setPagination(prev => ({ ...prev, currentPage: 1 }))
    searchJobs(1, nextForm)
  }

  const clearJobCategory = () => {
    setSelectedCategory('')
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      next.delete('jobCategory')
      return next
    })
  }

  const generateClientSearchLinks = async () => {
    if (!searchForm.keywords.trim()) {
      toast.error('Enter job keywords first')
      return
    }

    try {
      setLinksLoading(true)
      const params = new URLSearchParams({
        keywords: searchForm.keywords.trim(),
        location: searchForm.location || 'Los Angeles, CA'
      })

      const response = await apiFetch(`/api/jobs/search/links?${params}`)
      if (!response.ok) {
        throw new Error('Failed to generate search links')
      }

      const data = await response.json()
      setLinkResources(data)
      toast.success('Client-ready search links generated')
    } catch (error) {
      console.error('Generate job links error:', error)
      toast.error(error.message || 'Failed to generate search links')
      setLinkResources(null)
    } finally {
      setLinksLoading(false)
    }
  }

  const openJobPosting = (job) => {
    if (job.url) {
      window.open(job.url, '_blank', 'noopener,noreferrer')
      return
    }

    const query = [job.title, job.company, job.location, 'job']
      .filter(Boolean)
      .join(' ')
      .trim()

    const fallbackUrl = `https://www.google.com/search?${new URLSearchParams({ q: query }).toString()}`
    window.open(fallbackUrl, '_blank', 'noopener,noreferrer')
    toast.success('Opened a search for this job because no direct posting link was available')
  }

  // Load initial results from URL parameters
  useEffect(() => {
    if (searchParams.get('keywords') || searchParams.get('location')) {
      searchJobs(pagination.currentPage)
    }
  }, []) // Only run on mount

  const stats = [
    { icon: Briefcase, label: 'Available Jobs', value: jobs.length.toString(), variant: 'primary' },
    { icon: Star, label: 'Background Friendly', value: jobs.filter(j => j.backgroundFriendly).length.toString(), variant: 'success' },
    { icon: Bookmark, label: 'Saved Jobs', value: savedJobs.length.toString(), variant: 'secondary' },
    { icon: Clock, label: 'Recent Postings', value: jobs.filter(j => j.posted.includes('1 day') || j.posted.includes('2 days')).length.toString(), variant: 'warning' },
  ]

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl shadow-lg">
                <Briefcase className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-emerald-200 to-blue-200 bg-clip-text text-transparent">
                  Job Search
                </h1>
                <p className="text-gray-300 text-lg">Find background-friendly employment opportunities</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
          {/* Client Selection - FIXED with proper z-index */}
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20 mb-8 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-white">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector 
              onClientSelect={setSelectedClient}
              includeOperationalContext
              placeholder="Select a client to search jobs for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-3 p-4 bg-gradient-to-r from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                <p className="text-sm text-blue-200">
                  Searching jobs for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
                </p>
              </div>
            )}
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, index) => (
              <StatsCard key={index} {...stat} />
            ))}
          </div>

          {/* Tabs */}
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex border-b border-white/10">
              {[
                { id: 'search', label: 'Job Search', icon: Search, gradient: 'from-emerald-500 to-blue-500' },
                { id: 'links', label: 'Client Search Links', icon: ExternalLink, gradient: 'from-orange-500 to-amber-500' },
                { id: 'saved', label: 'Saved Jobs', icon: Bookmark, gradient: 'from-purple-500 to-pink-500' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group flex items-center gap-3 px-8 py-6 font-medium transition-all duration-300 relative ${
                    activeTab === tab.id
                      ? 'text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <div className={`p-2 rounded-lg transition-all duration-300 ${
                    activeTab === tab.id 
                      ? `bg-gradient-to-r ${tab.gradient} shadow-lg` 
                      : 'bg-white/10 group-hover:bg-white/20'
                  }`}>
                    <tab.icon className="h-5 w-5 text-white" />
                  </div>
                  {tab.label}
                  {activeTab === tab.id && (
                    <div className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${tab.gradient}`}></div>
                  )}
                </button>
              ))}
            </div>

            <div className="p-8">
              {/* Job Search Tab */}
              {activeTab === 'search' && (
                <div>
                  {/* Search Form */}
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/20 mb-8">
                    <div className="flex items-center gap-3 mb-8">
                      <div className="p-2 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg">
                        <Search className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Search Jobs</h2>
                    </div>
                    
                    {/* Search Type Toggle */}
                    <div className="mb-8 p-6 bg-gradient-to-r from-black/20 to-purple-900/20 backdrop-blur-sm rounded-xl border border-white/10">
                      <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
                        <Zap className="h-4 w-4 text-yellow-400" />
                        Search Type
                      </h3>
                      <div className="flex gap-8">
                        <label className="flex items-center cursor-pointer group">
                          <input
                            type="radio"
                            name="searchType"
                            value="general"
                            checked={searchForm.searchType === 'general'}
                            onChange={(e) => setSearchForm(prev => ({ ...prev, searchType: e.target.value }))}
                            className="mr-4 h-4 w-4 text-emerald-500 focus:ring-emerald-400 border-gray-400 bg-white/10"
                          />
                          <div>
                            <span className="text-sm font-medium text-white group-hover:text-emerald-200 transition-colors">General Search</span>
                            <p className="text-xs text-gray-400 group-hover:text-gray-300 transition-colors">Search across major job sites (faster)</p>
                          </div>
                        </label>
                        <label className="flex items-center cursor-pointer group">
                          <input
                            type="radio"
                            name="searchType"
                            value="specific"
                            checked={searchForm.searchType === 'specific'}
                            onChange={(e) => setSearchForm(prev => ({ ...prev, searchType: e.target.value }))}
                            className="mr-4 h-4 w-4 text-purple-500 focus:ring-purple-400 border-gray-400 bg-white/10"
                          />
                          <div>
                            <span className="text-sm font-medium text-white group-hover:text-purple-200 transition-colors">Specific Listings</span>
                            <p className="text-xs text-gray-400 group-hover:text-gray-300 transition-colors">Direct scraping from job sites (more detailed)</p>
                          </div>
                        </label>
                      </div>
                    </div>

                    <div className="mb-8 p-6 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                      <div className="flex items-center justify-between gap-4 mb-5">
                        <div>
                          <h3 className="text-lg font-semibold text-white">Browse by category</h3>
                          <p className="text-sm text-gray-300 mt-1">Give clients an easy starting point when they are not sure what kind of work to pursue.</p>
                        </div>
                        {selectedCategory && (
                          <button
                            type="button"
                            onClick={clearJobCategory}
                            className="px-4 py-2 rounded-xl border border-white/20 bg-white/10 text-sm font-medium text-gray-200 hover:bg-white/20 hover:text-white transition-all duration-300"
                          >
                            Clear category
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {JOB_CATEGORY_TILES.map((category) => (
                          <button
                            key={category.id}
                            type="button"
                            onClick={() => applyJobCategory(category)}
                            className={`group rounded-2xl border p-4 text-left transition-all duration-300 hover:scale-[1.02] hover:shadow-lg ${
                              selectedCategory === category.id
                                ? `bg-gradient-to-r ${category.gradient} border-white/20 text-white shadow-xl`
                                : 'border-white/15 bg-white/5 text-gray-200 hover:bg-white/10 hover:border-white/25'
                            }`}
                          >
                            <div className={`inline-flex rounded-xl p-2 mb-3 ${selectedCategory === category.id ? 'bg-white/20' : `bg-gradient-to-r ${category.gradient}`}`}>
                              <category.icon className="h-5 w-5 text-white" />
                            </div>
                            <p className="font-semibold">{category.label}</p>
                            <p className={`text-xs mt-1 ${selectedCategory === category.id ? 'text-white/80' : 'text-gray-400'}`}>
                              Search: {category.keywords}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">Keywords</label>
                        <input
                          type="text"
                          value={searchForm.keywords}
                          onChange={(e) => setSearchForm(prev => ({ ...prev, keywords: e.target.value }))}
                          placeholder="server restaurant hospitality"
                          className="w-full px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                          data-testid="job-keywords"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">Location</label>
                        <LocationSelector
                          value={searchForm.location}
                          onChange={(nextValue) => setSearchForm(prev => ({ ...prev, location: nextValue }))}
                          placeholder="Search city or state"
                          className="w-full"
                          inputClassName="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">Job Type</label>
                        <select
                          value={searchForm.jobType}
                          onChange={(e) => setSearchForm(prev => ({ ...prev, jobType: e.target.value }))}
                          className="w-full px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-white transition-all duration-300 hover:bg-white/15"
                        >
                          <option value="all" className="bg-gray-800 text-white">All Types</option>
                          <option value="full-time" className="bg-gray-800 text-white">Full-time</option>
                          <option value="part-time" className="bg-gray-800 text-white">Part-time</option>
                          <option value="contract" className="bg-gray-800 text-white">Contract</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 mb-8">
                      <label className="flex items-center group cursor-pointer">
                        <input
                          type="checkbox"
                          checked={searchForm.backgroundFriendly}
                          onChange={(e) => setSearchForm(prev => ({ ...prev, backgroundFriendly: e.target.checked }))}
                          className="mr-4 h-5 w-5 text-yellow-500 focus:ring-yellow-400 border-gray-400 rounded bg-white/10"
                          data-testid="background-friendly-filter"
                        />
                        <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
                          Background-friendly employers only
                        </span>
                      </label>
                    </div>

                    <button
                      onClick={handleNewSearch}
                      disabled={loading}
                      className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-emerald-600 to-blue-600 hover:from-emerald-500 hover:to-blue-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-emerald-500/25 disabled:opacity-50 disabled:hover:scale-100"
                      data-testid="search-jobs-button"
                    >
                      <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                        <Search className="h-5 w-5" />
                      </div>
                      {loading 
                        ? (searchForm.searchType === 'specific' ? 'Scraping job sites...' : 'Searching...') 
                        : 'Search Jobs'
                      }
                    </button>
                    <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
                      <button
                        type="button"
                        onClick={openCraigslistJobsSearch}
                        className="inline-flex items-center justify-center gap-2 rounded-xl border border-orange-500/30 bg-gradient-to-r from-orange-500/15 to-amber-500/15 px-6 py-3 text-sm font-medium text-orange-200 transition-all duration-300 hover:border-orange-400/50 hover:bg-orange-500/20 hover:text-white"
                      >
                        <ExternalLink size={16} />
                        Search Craigslist Jobs
                      </button>
                      <p className="text-sm text-gray-400">
                        Opens a Craigslist jobs search using these keywords and location for more direct local postings.
                      </p>
                    </div>
                  </div>

                  {/* Job Results */}
                  <div data-testid="job-results">
                    <div className="flex items-center justify-between mb-8">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                          <TrendingUp className="h-6 w-6 text-white" />
                        </div>
                        <h3 className="text-2xl font-bold text-white">
                          Job Results
                          {pagination.totalResults > 0 && (
                            <span className="text-gray-400 font-normal ml-3 text-lg">
                              ({pagination.totalResults.toLocaleString()} total found)
                            </span>
                          )}
                        </h3>
                      </div>
                      {pagination.totalResults > 0 && (
                        <div className="px-4 py-2 bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30">
                          <span className="text-sm text-purple-200">
                            Page {pagination.currentPage} of {pagination.totalPages.toLocaleString()}
                          </span>
                        </div>
                      )}
                    </div>
                    
                    {loading ? (
                      <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                        <div className="relative mx-auto mb-6 w-12 h-12">
                          <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-500/20 border-t-purple-500"></div>
                          <div className="absolute inset-2 animate-spin rounded-full border-2 border-emerald-500/20 border-t-emerald-500" style={{animationDirection: 'reverse'}}></div>
                        </div>
                        <p className="text-gray-300 font-medium">
                          {searchForm.searchType === 'specific' 
                            ? 'Scraping specific job listings... This may take longer.'
                            : 'Searching for jobs...'
                          }
                        </p>
                      </div>
                    ) : jobs.length === 0 ? (
                      <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                        <div className="p-4 bg-gradient-to-r from-gray-500/20 to-gray-600/20 rounded-2xl w-fit mx-auto mb-6">
                          <Briefcase size={48} className="text-gray-400" />
                        </div>
                        <h3 className="text-xl font-medium mb-3 text-white">No jobs found</h3>
                        <p className="text-gray-400">Try adjusting your search criteria</p>
                      </div>
                    ) : (
                      <>
                        <div className="space-y-6">
                          {jobs.map((job) => (
                            <div key={job.id} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-8 hover:border-white/30 transition-all duration-500 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20">
                              <div className="flex items-start justify-between mb-6">
                                <div className="flex-1">
                                  <div className="flex items-center gap-4 mb-3">
                                    <h3 className="text-2xl font-bold text-white group-hover:text-emerald-200 transition-colors">{job.title}</h3>
                                    {job.isScraped && (
                                      <span className="px-3 py-1 bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 text-xs font-medium rounded-full border border-green-500/30">
                                        Direct Scrape
                                      </span>
                                    )}
                                    {job.backgroundScore >= 60 && (
                                      <span className="px-3 py-1 bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 text-xs font-medium rounded-full border border-yellow-500/30">
                                        Background Friendly ({job.backgroundScore})
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xl text-emerald-400 font-semibold mb-3 group-hover:text-emerald-300 transition-colors">{job.company}</p>
                                  <div className="flex items-center gap-6 text-sm text-gray-300 mb-4">
                                    <span className="flex items-center gap-2">
                                      <MapPin size={16} className="text-blue-400" />
                                      {job.location}
                                    </span>
                                    <span className="flex items-center gap-2">
                                      <DollarSign size={16} className="text-green-400" />
                                      {job.salary}
                                    </span>
                                    <span className="flex items-center gap-2">
                                      <Clock size={16} className="text-purple-400" />
                                      {job.posted}
                                    </span>
                                  </div>
                                </div>
                                
                                <div className="flex gap-3">
                                  <button
                                    onClick={() => openApplyModal(job)}
                                    className="group/btn flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-emerald-500/25"
                                  >
                                    <Send size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                                    Apply with Resume
                                  </button>
                                  <button
                                    onClick={() => handleSaveJob(job)}
                                    className="group/btn flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25"
                                    data-testid="save-job-0"
                                  >
                                    <Bookmark size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                                    Save
                                  </button>
                                  <button 
                                    onClick={() => openJobPosting(job)}
                                    className="group/btn flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-xl font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300 transform hover:scale-105"
                                    title={job.url ? 'Open job posting' : 'Open fallback search for this job'}
                                  >
                                    <ExternalLink size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                                    {job.isScraped ? 'Search for Job' : 'View Job Posting'}
                                  </button>
                                </div>
                              </div>
                              
                              <p className="text-gray-300 mb-6 leading-relaxed">{job.description}</p>
                              
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                                <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                                    Requirements:
                                  </h4>
                                  <ul className="text-gray-300 space-y-2">
                                    {job.requirements.map((req, index) => (
                                      <li key={index} className="flex items-start gap-2">
                                        <span className="text-emerald-400 mt-1">•</span>
                                        {req}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                                <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                    Benefits:
                                  </h4>
                                  <ul className="text-gray-300 space-y-2">
                                    {job.benefits.map((benefit, index) => (
                                      <li key={index} className="flex items-start gap-2">
                                        <span className="text-blue-400 mt-1">•</span>
                                        {benefit}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                                <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                                  <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                                    Contact:
                                  </h4>
                                  <div className="text-gray-300 space-y-2">
                                    <p>Phone: {job.contactInfo.phone}</p>
                                    <p>Email: {job.contactInfo.email}</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                        
                        {/* Pagination Component */}
                        <Pagination
                          currentPage={pagination.currentPage}
                          totalPages={pagination.totalPages}
                          totalResults={pagination.totalResults}
                          perPage={pagination.perPage}
                          onPageChange={handlePageChange}
                          loading={loading}
                          className="mt-8 border-t border-white/10 pt-8"
                        />
                      </>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'links' && (
                <div>
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/20 mb-8">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                        <ExternalLink className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Client Search Links</h2>
                    </div>
                    <p className="text-gray-300 mb-6">
                      Generate direct search links you can text or email to a client instead of reviewing hundreds of scraped listings.
                    </p>
                    <button
                      onClick={generateClientSearchLinks}
                      disabled={linksLoading}
                      className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-orange-500/25 disabled:opacity-50 disabled:hover:scale-100"
                    >
                      <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                        <ExternalLink className="h-5 w-5" />
                      </div>
                      {linksLoading ? 'Generating Links...' : 'Generate Search Links'}
                    </button>
                  </div>

                  {linksLoading ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="relative mx-auto mb-6 w-12 h-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-orange-500/20 border-t-orange-500"></div>
                        <div className="absolute inset-2 animate-spin rounded-full border-2 border-amber-500/20 border-t-amber-500" style={{animationDirection: 'reverse'}}></div>
                      </div>
                      <p className="text-gray-300 font-medium">Building client-ready job board links...</p>
                    </div>
                  ) : !linkResources ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="p-4 bg-gradient-to-r from-orange-500/20 to-amber-500/20 rounded-2xl w-fit mx-auto mb-6">
                        <ExternalLink size={48} className="text-orange-400" />
                      </div>
                      <h3 className="text-xl font-medium mb-3 text-white">No search links generated yet</h3>
                      <p className="text-gray-400">Use the current keywords and location above, then generate direct links for the client.</p>
                    </div>
                  ) : (
                    <div className="space-y-8">
                      <div className="bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-xl shadow-purple-500/10">
                        <div className="flex items-center justify-between gap-4 flex-wrap">
                          <div>
                            <h3 className="text-xl font-bold text-white">Search Links for {linkResources.keywords}</h3>
                            <p className="text-gray-300 mt-1">Location: {linkResources.location}</p>
                          </div>
                          <div className="px-4 py-2 bg-gradient-to-r from-orange-500/20 to-amber-500/20 backdrop-blur-sm rounded-xl border border-orange-500/30">
                            <span className="text-sm text-orange-200">Send these links directly to the client</span>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {Object.entries(linkResources.search_urls || {}).map(([platform, url]) => (
                          <div key={platform} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-6 hover:border-white/30 transition-all duration-300">
                            <h4 className="text-lg font-bold text-white mb-2 capitalize">{platform.replace(/_/g, ' ')}</h4>
                            <p className="text-sm text-gray-400 mb-4 break-all">{url}</p>
                            <button
                              onClick={() => window.open(url, '_blank', 'noopener,noreferrer')}
                              className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300"
                            >
                              <ExternalLink size={16} />
                              Open Search
                            </button>
                          </div>
                        ))}
                      </div>

                      {!!linkResources.background_friendly_searches?.length && (
                        <div>
                          <h3 className="text-xl font-bold text-white mb-4">Background-Friendly Search Variations</h3>
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {linkResources.background_friendly_searches.map((searchLink, index) => (
                              <div key={`${searchLink.platform}-${index}`} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-5">
                                <div className="flex items-center justify-between gap-4 mb-3">
                                  <div>
                                    <p className="text-sm uppercase tracking-wide text-amber-300">{searchLink.platform}</p>
                                    <p className="text-white font-semibold">{searchLink.keywords}</p>
                                  </div>
                                  <button
                                    onClick={() => window.open(searchLink.url, '_blank', 'noopener,noreferrer')}
                                    className="px-4 py-2 bg-white/10 border border-white/20 text-white rounded-lg hover:bg-white/20"
                                  >
                                    Open
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {!!linkResources.known_employers?.length && (
                        <div>
                          <h3 className="text-xl font-bold text-white mb-4">Known Fair-Chance Employer Leads</h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {linkResources.known_employers.map((employer) => (
                              <div key={employer.name} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-5">
                                <h4 className="text-lg font-bold text-white">{employer.name}</h4>
                                <p className="text-emerald-300 text-sm mt-1">{employer.industry}</p>
                                <p className="text-gray-300 text-sm mt-3">{employer.why}</p>
                                <button
                                  onClick={() => window.open(employer.careers_url, '_blank', 'noopener,noreferrer')}
                                  className="mt-4 flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/20 text-white rounded-lg hover:bg-white/20"
                                >
                                  <ExternalLink size={15} />
                                  Open Careers Page
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Saved Jobs Tab */}
              {activeTab === 'saved' && (
                <div>
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                        <Bookmark className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Saved Jobs</h2>
                    </div>
                    <div className="px-4 py-2 bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30">
                      <span className="text-sm text-purple-200" data-testid="saved-jobs-count">
                        {savedJobs.length} saved job{savedJobs.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  {savedJobs.length === 0 ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="p-4 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl w-fit mx-auto mb-6">
                        <Bookmark size={48} className="text-purple-400" />
                      </div>
                      <h3 className="text-xl font-medium mb-3 text-white">No saved jobs</h3>
                      <p className="text-gray-400">Jobs you save will appear here</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
{savedJobs.map((job, index) => (
                        <div key={index} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-purple-500/10">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-semibold text-white group-hover:text-purple-200 transition-colors">{job.title || job.job_id}</h3>
                            <span className="text-sm text-gray-400 px-3 py-1 bg-white/10 rounded-full">
                              Saved: {new Date(job.saved_date).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-gray-300 text-sm mb-3">
                            {[job.company, job.location].filter(Boolean).join(' • ') || 'Saved job lead'}
                          </p>
                          {job.salary && (
                            <p className="text-emerald-300 text-sm mb-3">{job.salary}</p>
                          )}
                          {job.notes && (
                            <p className="text-gray-400 text-sm italic bg-white/5 p-3 rounded-lg border border-white/10">
                              Notes: {job.notes}
                            </p>
                          )}
                          {job.url && (
                            <div className="mt-4">
                              <button
                                onClick={() => window.open(job.url, '_blank', 'noopener,noreferrer')}
                                className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-white hover:bg-white/20"
                              >
                                <ExternalLink size={15} />
                                Open Saved Posting
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showApplyModal && applyingJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-slate-900/95 p-6 shadow-2xl">
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h3 className="text-2xl font-bold text-white">Apply with Resume</h3>
                <p className="mt-2 text-gray-300">
                  Track an application for <span className="font-semibold text-white">{applyingJob.title}</span> at <span className="font-semibold text-white">{applyingJob.company}</span>.
                </p>
              </div>
              <button
                onClick={() => {
                  setShowApplyModal(false)
                  setApplyingJob(null)
                }}
                className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-gray-400">Client</p>
                <p className="mt-1 text-white">{selectedClient?.first_name} {selectedClient?.last_name}</p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">Select Resume</label>
                <select
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-4 text-white focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500"
                >
                  {clientResumes.map((resume) => (
                    <option key={resume.resume_id} value={resume.resume_id} className="bg-gray-900 text-white">
                      {resume.resume_title} • ATS {resume.ats_score || 0}
                    </option>
                  ))}
                </select>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-gray-400">Job summary used for tracking</p>
                <p className="mt-2 text-sm leading-relaxed text-gray-200">{applyingJob.description}</p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowApplyModal(false)
                  setApplyingJob(null)
                }}
                className="rounded-xl border border-white/20 px-5 py-3 text-gray-300 hover:bg-white/10 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={submitApplication}
                disabled={applyLoading || !selectedResumeId}
                className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-3 font-medium text-white hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50"
              >
                {applyLoading ? 'Tracking Application...' : 'Track Application'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Jobs
