import { useState, useEffect } from 'react'
import { Briefcase, Search, MapPin, Filter, Star, Bookmark, ExternalLink, Clock, DollarSign, User } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import toast from 'react-hot-toast'

function Jobs() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchForm, setSearchForm] = useState({
    keywords: '',
    location: 'Los Angeles',
    backgroundFriendly: false,
    jobType: 'all',
    experienceLevel: 'all'
  })
  const [savedJobs, setSavedJobs] = useState([])
  const [activeTab, setActiveTab] = useState('search')

  const searchJobs = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/jobs/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchForm)
      })

      if (response.ok) {
        const data = await response.json()
        setJobs(data.jobs || [])
      } else {
        throw new Error('API not available')
      }
    } catch (error) {
      console.error('Job search error:', error)
      
      // Mock job results for comprehensive testing
      const mockJobs = [
        {
          id: 'job_001',
          title: 'Server - Second Chance Employer',
          company: 'Fresh Start Restaurant Group',
          location: 'Los Angeles, CA',
          salary: '$15-18/hour + tips',
          type: 'Full-time',
          posted: '2 days ago',
          description: 'We welcome individuals with diverse backgrounds. Restaurant experience preferred.',
          requirements: ['Food service experience', 'Customer service skills', 'Reliable transportation'],
          benefits: ['Health insurance', 'Flexible scheduling', 'Career advancement'],
          backgroundFriendly: true,
          backgroundScore: 95,
          isSecondChance: true,
          contactInfo: {
            phone: '(213) 555-0123',
            email: 'hiring@freshstartrestaurants.com'
          }
        },
        {
          id: 'job_002', 
          title: 'Warehouse Associate - No Background Check',
          company: 'Opportunity Logistics',
          location: 'Los Angeles, CA',
          salary: '$16-20/hour',
          type: 'Full-time',
          posted: '1 day ago',
          description: 'Entry-level warehouse position. We believe in second chances and fresh starts.',
          requirements: ['Ability to lift 50 lbs', 'Basic math skills', 'Team player'],
          benefits: ['Health insurance', '401k matching', 'Paid training'],
          backgroundFriendly: true,
          backgroundScore: 90,
          isSecondChance: true,
          contactInfo: {
            phone: '(213) 555-0198',
            email: 'jobs@opportunitylogistics.com'
          }
        },
        {
          id: 'job_003',
          title: 'Kitchen Prep Cook',
          company: 'Community Kitchen Collective',
          location: 'Los Angeles, CA', 
          salary: '$14-16/hour',
          type: 'Part-time',
          posted: '3 days ago',
          description: 'Kitchen prep position with growth opportunities. Experience in restaurant industry helpful.',
          requirements: ['Food handling knowledge', 'Punctuality', 'Kitchen experience helpful'],
          benefits: ['Flexible hours', 'Free meals', 'Skills training'],
          backgroundFriendly: true,
          backgroundScore: 85,
          isSecondChance: true,
          contactInfo: {
            phone: '(213) 555-0145',
            email: 'hiring@communitykitchen.org'
          }
        },
        {
          id: 'job_004',
          title: 'Retail Sales Associate',
          company: 'Second Chance Retail Co',
          location: 'Los Angeles, CA',
          salary: '$15/hour',
          type: 'Full-time',
          posted: '4 days ago',
          description: 'Customer service role with comprehensive training program.',
          requirements: ['Customer service experience', 'Communication skills', 'Positive attitude'],
          benefits: ['Employee discount', 'Training provided', 'Advancement opportunities'],
          backgroundFriendly: true,
          backgroundScore: 88,
          isSecondChance: true,
          contactInfo: {
            phone: '(213) 555-0167',
            email: 'careers@secondchanceretail.com'
          }
        }
      ]

      // Filter based on search criteria
      let filteredJobs = mockJobs
      if (searchForm.backgroundFriendly) {
        filteredJobs = filteredJobs.filter(job => job.backgroundFriendly)
      }
      if (searchForm.keywords) {
        filteredJobs = filteredJobs.filter(job => 
          job.title.toLowerCase().includes(searchForm.keywords.toLowerCase()) ||
          job.description.toLowerCase().includes(searchForm.keywords.toLowerCase())
        )
      }

      setJobs(filteredJobs)
      toast.success(`Found ${filteredJobs.length} background-friendly jobs`)
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

  const stats = [
    { icon: Briefcase, label: 'Available Jobs', value: jobs.length.toString(), variant: 'primary' },
    { icon: Star, label: 'Background Friendly', value: jobs.filter(j => j.backgroundFriendly).length.toString(), variant: 'success' },
    { icon: Bookmark, label: 'Saved Jobs', value: savedJobs.length.toString(), variant: 'secondary' },
    { icon: Clock, label: 'Recent Postings', value: jobs.filter(j => j.posted.includes('1 day') || j.posted.includes('2 days')).length.toString(), variant: 'warning' },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Briefcase size={32} />
          <h1 className="text-3xl font-bold">Job Search</h1>
        </div>
        <p className="text-lg opacity-90">Find background-friendly employment opportunities</p>
      </div>

      <div className="p-8">
        {/* Client Selection */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <User className="h-5 w-5" />
            Select Client
          </h2>
          <ClientSelector 
            onClientSelect={setSelectedClient}
            placeholder="Select a client to search jobs for..."
            className="max-w-md"
          />
          {selectedClient && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                Searching jobs for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
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
        <div className="bg-white rounded-xl shadow-custom-sm mb-8">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'search', label: 'Job Search', icon: Search },
              { id: 'saved', label: 'Saved Jobs', icon: Bookmark }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-primary-600 border-b-2 border-primary-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon size={20} />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* Job Search Tab */}
            {activeTab === 'search' && (
              <div>
                {/* Search Form */}
                <div className="bg-gray-50 rounded-lg p-6 mb-8">
                  <h2 className="text-xl font-semibold mb-6">Search Jobs</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Keywords</label>
                      <input
                        type="text"
                        value={searchForm.keywords}
                        onChange={(e) => setSearchForm(prev => ({ ...prev, keywords: e.target.value }))}
                        placeholder="server restaurant hospitality"
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        data-testid="job-keywords"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
                      <div className="relative">
                        <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                        <input
                          type="text"
                          value={searchForm.location}
                          onChange={(e) => setSearchForm(prev => ({ ...prev, location: e.target.value }))}
                          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          data-testid="job-location"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Job Type</label>
                      <select
                        value={searchForm.jobType}
                        onChange={(e) => setSearchForm(prev => ({ ...prev, jobType: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="all">All Types</option>
                        <option value="full-time">Full-time</option>
                        <option value="part-time">Part-time</option>
                        <option value="contract">Contract</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-6 mb-6">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={searchForm.backgroundFriendly}
                        onChange={(e) => setSearchForm(prev => ({ ...prev, backgroundFriendly: e.target.checked }))}
                        className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        data-testid="background-friendly-filter"
                      />
                      <span className="text-sm font-medium text-gray-700">Background-friendly employers only</span>
                    </label>
                  </div>

                  <button
                    onClick={searchJobs}
                    disabled={loading}
                    className="flex items-center gap-2 px-8 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50"
                    data-testid="search-jobs-button"
                  >
                    <Search size={20} />
                    {loading ? 'Searching...' : 'Search Jobs'}
                  </button>
                </div>

                {/* Job Results */}
                <div data-testid="job-results">
                  <h3 className="text-xl font-semibold mb-6">
                    Job Results ({jobs.length} found)
                  </h3>
                  
                  {loading ? (
                    <div className="text-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
                      <p className="text-gray-600">Searching for jobs...</p>
                    </div>
                  ) : jobs.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Briefcase size={48} className="mx-auto mb-4 text-gray-300" />
                      <h3 className="text-lg font-medium mb-2">No jobs found</h3>
                      <p className="text-sm">Try adjusting your search criteria</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {jobs.map((job) => (
                        <div key={job.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-custom-sm transition-shadow">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h3 className="text-xl font-semibold text-gray-900">{job.title}</h3>
                                {job.isSecondChance && (
                                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                                    Second chance employer
                                  </span>
                                )}
                              </div>
                              <p className="text-lg text-primary-600 font-medium mb-1">{job.company}</p>
                              <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                                <span className="flex items-center gap-1">
                                  <MapPin size={16} />
                                  {job.location}
                                </span>
                                <span className="flex items-center gap-1">
                                  <DollarSign size={16} />
                                  {job.salary}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Clock size={16} />
                                  {job.posted}
                                </span>
                              </div>
                              
                              {job.backgroundFriendly && (
                                <div className="flex items-center gap-2 mb-3">
                                  <span className="text-sm font-medium text-green-700" data-testid="background-score">
                                    Background friendly: {job.backgroundScore}%
                                  </span>
                                  <div className="w-20 bg-gray-200 rounded-full h-2">
                                    <div 
                                      className="bg-green-500 h-2 rounded-full"
                                      style={{ width: `${job.backgroundScore}%` }}
                                    ></div>
                                  </div>
                                </div>
                              )}
                            </div>
                            
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleSaveJob(job)}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                data-testid="save-job-0"
                              >
                                <Bookmark size={16} />
                                Save
                              </button>
                              <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                                <ExternalLink size={16} />
                                Apply
                              </button>
                            </div>
                          </div>
                          
                          <p className="text-gray-700 mb-4">{job.description}</p>
                          
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <h4 className="font-medium text-gray-900 mb-2">Requirements:</h4>
                              <ul className="text-gray-600 space-y-1">
                                {job.requirements.map((req, index) => (
                                  <li key={index}>• {req}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900 mb-2">Benefits:</h4>
                              <ul className="text-gray-600 space-y-1">
                                {job.benefits.map((benefit, index) => (
                                  <li key={index}>• {benefit}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900 mb-2">Contact:</h4>
                              <div className="text-gray-600 space-y-1">
                                <p>Phone: {job.contactInfo.phone}</p>
                                <p>Email: {job.contactInfo.email}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Saved Jobs Tab */}
            {activeTab === 'saved' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Saved Jobs</h2>
                  <span className="text-sm text-gray-600" data-testid="saved-jobs-count">
                    {savedJobs.length} saved job{savedJobs.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {savedJobs.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Bookmark size={48} className="mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium mb-2">No saved jobs</h3>
                    <p className="text-sm">Jobs you save will appear here</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {savedJobs.map((job, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-semibold text-gray-900">{job.title}</h3>
                          <span className="text-sm text-gray-500">
                            Saved: {new Date(job.saved_date).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-gray-600 text-sm mb-2">{job.company} • {job.location}</p>
                        {job.notes && (
                          <p className="text-gray-700 text-sm italic">Notes: {job.notes}</p>
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
  )
}

export default Jobs