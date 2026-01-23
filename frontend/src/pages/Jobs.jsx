import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Briefcase, Search, MapPin, Filter, Star, Bookmark, ExternalLink, Clock, DollarSign, User, Sparkles, Zap, TrendingUp } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import Pagination from '../components/Pagination'
import toast from 'react-hot-toast'

function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
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
  
  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: parseInt(searchParams.get('page')) || 1,
    totalPages: 0,
    totalResults: 0,
    perPage: 10,
    hasNextPage: false,
    hasPrevPage: false
  })

  const searchJobs = async (page = pagination.currentPage) => {
    setLoading(true)
    
    // Scroll to top when changing pages
    if (page !== pagination.currentPage) {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    
    try {
      // Choose endpoint based on search type
      const searchEndpoint = searchForm.searchType === 'general' 
        ? '/api/jobs/search/quick'
        : '/api/jobs/search/scrapers';
      
      // Build search parameters
      const params = new URLSearchParams({
        keywords: searchForm.keywords || 'jobs',
        location: searchForm.location || 'Los Angeles, CA',
        background_friendly: String(!!searchForm.backgroundFriendly),
        page: String(page),
        per_page: String(pagination.perPage)
      })
      
      // Add sources parameter for scraper search
      if (searchForm.searchType === 'specific') {
        params.set('sources', 'craigslist,builtinla,government,city_la')
      }
      
      // Update URL parameters for bookmarking
      const newSearchParams = new URLSearchParams(searchParams)
      newSearchParams.set('keywords', searchForm.keywords || 'jobs')
      newSearchParams.set('location', searchForm.location || 'Los Angeles, CA')
      newSearchParams.set('backgroundFriendly', String(!!searchForm.backgroundFriendly))
      newSearchParams.set('searchType', searchForm.searchType)
      newSearchParams.set('page', String(page))
      setSearchParams(newSearchParams)
      
      const response = await fetch(`${searchEndpoint}?${params}`, {
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
            location: result.location || result.metadata?.location || searchForm.location,
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
          const searchTypeLabel = searchForm.searchType === 'general' ? 'job sites' : 'specific listings'
          toast.success(`Found ${data.pagination.total_results.toLocaleString()} ${searchTypeLabel} (showing page ${page})`)
        } else {
          throw new Error(data.error || 'Search API returned invalid data')
        }
      } else {
        throw new Error('Search API not available')
      }
    } catch (error) {
      console.error('Job search error:', error)
      const errorMessage = searchForm.searchType === 'specific' 
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
    try {
      const response = await fetch('/api/jobs/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: job.id,
          client_id: 'client_maria', // For Maria Santos
          notes: note
        })
      })

      if (response.ok) {
        toast.success('Job saved successfully!')
      } else {
        throw new Error('Save failed')
      }
    } catch (error) {
      console.error('Save job error:', error)
      
      // Mock save success
      const savedJob = {
        ...job,
        saved_date: new Date().toISOString(),
        notes: note,
        client_id: 'client_maria'
      }
      setSavedJobs(prev => [savedJob, ...prev])
      toast.success('Job saved for client!')
    }
  }

  const handleSaveJob = (job) => {
    const note = prompt('Add a note about why this job is a good fit:')
    if (note !== null) {
      saveJob(job, note)
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
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

        <div className="max-w-7xl mx-auto px-6 py-8">
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
                        <div className="relative">
                          <MapPin className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                          <input
                            type="text"
                            value={searchForm.location}
                            onChange={(e) => setSearchForm(prev => ({ ...prev, location: e.target.value }))}
                            className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                            data-testid="job-location"
                          />
                        </div>
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
                                    onClick={() => handleSaveJob(job)}
                                    className="group/btn flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25"
                                    data-testid="save-job-0"
                                  >
                                    <Bookmark size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                                    Save
                                  </button>
                                  <button 
                                    onClick={() => {
                                      if (job.url) {
                                        window.open(job.url, '_blank')
                                      } else {
                                        toast.info('No direct link available for this job')
                                      }
                                    }}
                                    className="group/btn flex items-center gap-2 px-6 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-xl font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300 transform hover:scale-105"
                                    title={job.url ? 'Open job posting' : 'No direct link available'}
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
                            <h3 className="font-semibold text-white group-hover:text-purple-200 transition-colors">{job.title}</h3>
                            <span className="text-sm text-gray-400 px-3 py-1 bg-white/10 rounded-full">
                              Saved: {new Date(job.saved_date).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-gray-300 text-sm mb-3">{job.company} • {job.location}</p>
                          {job.notes && (
                            <p className="text-gray-400 text-sm italic bg-white/5 p-3 rounded-lg border border-white/10">
                              Notes: {job.notes}
                            </p>
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
    </div>
  )
}

export default Jobs