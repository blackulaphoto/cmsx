import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Briefcase, Search, MapPin, Bookmark, ExternalLink, User,
  Package, ShoppingBag, Truck, UtensilsCrossed, Camera, Building2,
  Wrench, GraduationCap, Users, FileText, CheckSquare, Car, ClipboardList,
} from 'lucide-react'
import ClientSelector from '../components/ClientSelector'
import LocationSelector from '../components/LocationSelector'
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

function resolveCraigslistBase(loc) {
  const normalized = (loc || '').toLowerCase()
  const region = CRAIGSLIST_JOB_REGIONS.find(r => r.match.some(t => normalized.includes(t)))
  return region?.base || 'https://losangeles.craigslist.org'
}

const JOB_CATEGORY_TILES = [
  { id: 'delivery',    label: 'Delivery',       keywords: 'delivery driver courier non CDL driver',            icon: Truck,         gradient: 'from-amber-500 to-orange-600' },
  { id: 'warehouse',   label: 'Warehouse',      keywords: 'warehouse associate picker packer material handler', icon: Package,       gradient: 'from-emerald-500 to-green-600' },
  { id: 'food-service',label: 'Food Service',   keywords: 'dishwasher line cook food service worker',          icon: UtensilsCrossed,gradient: 'from-cyan-500 to-blue-600' },
  { id: 'retail',      label: 'Retail',         keywords: 'retail associate cashier sales associate',          icon: ShoppingBag,   gradient: 'from-pink-500 to-rose-600' },
  { id: 'office',      label: 'Office',         keywords: 'office assistant receptionist data entry',          icon: Building2,     gradient: 'from-sky-500 to-cyan-600' },
  { id: 'maintenance', label: 'Maintenance',    keywords: 'janitor custodian maintenance technician',          icon: Wrench,        gradient: 'from-slate-500 to-slate-700' },
  { id: 'photography', label: 'Photography',    keywords: 'photographer photo assistant studio assistant',     icon: Camera,        gradient: 'from-violet-500 to-purple-600' },
  { id: 'entry-level', label: 'Entry Level',    keywords: 'entry level no experience paid training',           icon: GraduationCap, gradient: 'from-indigo-500 to-blue-600' },
  { id: 'staffing',    label: 'Staffing / Temp',keywords: 'staffing agency temp agency immediate hire',        icon: Users,         gradient: 'from-teal-500 to-emerald-600' },
]

const JOB_BOARDS = [
  { id: 'indeed',       name: 'Indeed',        description: 'Largest US job board',                    gradient: 'from-blue-600 to-blue-700'    },
  { id: 'craigslist',   name: 'Craigslist',    description: 'Local listings, often immediate hire',    gradient: 'from-purple-600 to-purple-700' },
  { id: 'caljobs',      name: 'CalJOBS',       description: 'California state workforce system',       gradient: 'from-red-600 to-red-700'      },
  { id: 'google',       name: 'Google Jobs',   description: 'Aggregates results across all sites',     gradient: 'from-green-600 to-green-700'  },
  { id: 'ziprecruiter', name: 'ZipRecruiter',  description: 'Fast apply, many local openings',         gradient: 'from-orange-600 to-orange-700'},
  { id: 'snagajob',     name: 'Snagajob',      description: 'Hourly and part-time focused',            gradient: 'from-yellow-600 to-amber-600' },
  { id: 'simplyhired',  name: 'SimplyHired',   description: 'Aggregator with salary estimates',        gradient: 'from-teal-600 to-teal-700'    },
  { id: 'linkedin',     name: 'LinkedIn Jobs', description: 'Professional network, larger employers',  gradient: 'from-sky-600 to-sky-700'      },
  { id: 'glassdoor',    name: 'Glassdoor',     description: 'Reviews + salary data with listings',     gradient: 'from-emerald-600 to-emerald-700'},
  { id: 'monster',      name: 'Monster',       description: 'Broad listings, entry level friendly',    gradient: 'from-violet-600 to-violet-700' },
]

const CASE_MANAGER_TOOLS = [
  { icon: ClipboardList, label: 'Application Tracker',    description: 'Log job applications and follow-up dates.' },
  { icon: CheckSquare,   label: 'Resume Checklist',       description: 'Review client resume before applying.' },
  { icon: FileText,      label: 'Interview Prep',         description: 'Common interview questions and tips.' },
  { icon: Briefcase,     label: 'Documents Needed',       description: 'ID, work authorization, employer paperwork.' },
  { icon: Car,           label: 'Transportation Notes',   description: 'Check commute from client address to job site.' },
]

function buildBoardUrls(keywords, location, lowBarrier) {
  const base = (keywords || '').trim() || 'jobs'
  const kw   = lowBarrier ? `${base} entry level` : base
  const loc  = (location || 'Los Angeles, CA').trim()
  const q    = encodeURIComponent(kw)
  const l    = encodeURIComponent(loc)
  const clBase = resolveCraigslistBase(loc)

  return {
    indeed:       `https://www.indeed.com/jobs?q=${q}&l=${l}`,
    craigslist:   `${clBase}/search/jjj?query=${q}&sort=date`,
    caljobs:      `https://www.caljobs.ca.gov/vosnet/jobseeker/jobsearch/quicksearch.aspx?pu=1&searchkeywords=${q}&locationstring=${l}`,
    google:       `https://www.google.com/search?q=${encodeURIComponent(`${kw} jobs ${loc}`)}`,
    ziprecruiter: `https://www.ziprecruiter.com/jobs-search?search=${q}&location=${l}`,
    snagajob:     `https://www.snagajob.com/jobs/?keyword=${q}&location=${l}`,
    simplyhired:  `https://www.simplyhired.com/search?q=${q}&l=${l}`,
    linkedin:     `https://www.linkedin.com/jobs/search/?keywords=${q}&location=${l}`,
    glassdoor:    `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${q}&locT=C&locName=${l}`,
    monster:      `https://www.monster.com/jobs/search?q=${q}&where=${l}`,
  }
}

function buildStaffingUrls(location) {
  const loc = (location || 'Los Angeles, CA').trim()
  const l   = encodeURIComponent(loc)
  return [
    { label: 'Staffing agency jobs',    url: `https://www.indeed.com/jobs?q=${encodeURIComponent('staffing agency')}&l=${l}` },
    { label: 'Temp agency jobs',        url: `https://www.indeed.com/jobs?q=${encodeURIComponent('temp agency')}&l=${l}` },
    { label: `Day labor near ${loc}`,   url: `https://www.google.com/search?q=${encodeURIComponent(`day labor jobs ${loc}`)}` },
  ]
}

function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [keywords, setKeywords] = useState(searchParams.get('keywords') || '')
  const [location, setLocation]   = useState(searchParams.get('location') || 'Los Angeles, CA')
  const [lowBarrier, setLowBarrier] = useState(searchParams.get('lowBarrier') === 'true')
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('jobCategory') || '')
  const [savedJobs, setSavedJobs] = useState([])
  const [activeTab, setActiveTab] = useState('search')

  // ── Client loading ─────────────────────────────────────────────────────────
  useEffect(() => {
    const clientId = searchParams.get('client')
    if (!clientId || selectedClient?.client_id === clientId) return
    fetchClientWithOperationalContext(apiFetch, clientId)
      .then(setSelectedClient)
      .catch(() => {})
  }, [searchParams, selectedClient?.client_id])

  useEffect(() => {
    if (selectedClient?.client_id) fetchSavedJobs(selectedClient.client_id)
    else setSavedJobs([])
  }, [selectedClient?.client_id])

  // Auto-suggest keywords / location from client context
  useEffect(() => {
    if (!selectedClient?.client_id) return
    const intake       = getIntakeContext(selectedClient)
    const treatmentPlan = getTreatmentPlanContext(selectedClient)
    const needKeys     = getNeedKeys(selectedClient)
    const goalText = [
      ...(Array.isArray(treatmentPlan.goals) ? treatmentPlan.goals : []),
      intake.goals,
    ].map(g => (typeof g === 'string' ? g : g?.description)).filter(Boolean).join(' ').toLowerCase()

    setKeywords(prev => {
      if (prev) return prev
      if (goalText.includes('warehouse'))                                     return 'warehouse associate picker packer'
      if (goalText.includes('office') || goalText.includes('administrative')) return 'office assistant receptionist'
      if (goalText.includes('food') || goalText.includes('restaurant'))       return 'dishwasher line cook food service'
      if (needKeys.has('job_search'))                                         return 'entry level no experience paid training'
      return prev
    })
    setLocation(prev =>
      prev === 'Los Angeles, CA' || prev === 'Los Angeles'
        ? clientLocation(selectedClient, prev)
        : prev
    )
    if (intake.prior_convictions || needKeys.has('job_search')) setLowBarrier(true)
  }, [selectedClient?.client_id])

  // ── Saved jobs ─────────────────────────────────────────────────────────────
  const fetchSavedJobs = async (clientId) => {
    try {
      const resp = await apiFetch(`/api/jobs/saved/${clientId}`)
      if (!resp.ok) throw new Error()
      const data = await resp.json()
      setSavedJobs(data.saved_jobs || [])
    } catch {
      setSavedJobs([])
    }
  }

  // ── URL generation (pure, no API calls) ───────────────────────────────────
  const boardUrls    = useMemo(() => buildBoardUrls(keywords, location, lowBarrier),    [keywords, location, lowBarrier])
  const staffingLinks = useMemo(() => buildStaffingUrls(location),                       [location])

  // ── Category selection — fills keyword field only, no API call ─────────────
  const applyCategory = (cat) => {
    setKeywords(cat.keywords)
    setSelectedCategory(cat.id)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('keywords', cat.keywords)
      next.set('jobCategory', cat.id)
      return next
    })
  }

  const clearCategory = () => {
    setSelectedCategory('')
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.delete('jobCategory')
      return next
    })
  }

  const updateLocationParam = (val) => {
    setLocation(val)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('location', val)
      return next
    }, { replace: true })
  }

  const updateLowBarrierParam = (val) => {
    setLowBarrier(val)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('lowBarrier', String(val))
      return next
    }, { replace: true })
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Background blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl animate-pulse delay-2000" />
      </div>

      <div className="relative z-10">
        {/* ── Page header ── */}
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl shadow-lg">
                <Briefcase className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-emerald-200 to-blue-200 bg-clip-text text-transparent">
                  Job Search Hub
                </h1>
                <p className="text-gray-300 text-lg">Find employment opportunities — verify requirements directly on each job board</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8 space-y-8">
          {/* ── Client selector ── */}
          <div className="bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-white">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector
              onClientSelect={setSelectedClient}
              includeOperationalContext
              placeholder="Select a client to tailor the job search..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-3 p-4 bg-gradient-to-r from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                <p className="text-sm text-blue-200">
                  Searching for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
                </p>
              </div>
            )}
          </div>

          {/* ── Main card with tabs ── */}
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl shadow-purple-500/10">
            {/* Tab bar */}
            <div className="flex border-b border-white/10">
              {[
                { id: 'search', label: 'Job Search Hub', icon: Search,   gradient: 'from-emerald-500 to-blue-500' },
                { id: 'saved',  label: 'Saved Jobs',     icon: Bookmark, gradient: 'from-purple-500 to-pink-500'  },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group flex items-center gap-3 px-8 py-6 font-medium transition-all duration-300 relative ${activeTab === tab.id ? 'text-white' : 'text-gray-400 hover:text-gray-200'}`}
                >
                  <div className={`p-2 rounded-lg transition-all duration-300 ${activeTab === tab.id ? `bg-gradient-to-r ${tab.gradient} shadow-lg` : 'bg-white/10 group-hover:bg-white/20'}`}>
                    <tab.icon className="h-5 w-5 text-white" />
                  </div>
                  {tab.label}
                  {activeTab === tab.id && (
                    <div className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${tab.gradient}`} />
                  )}
                </button>
              ))}
            </div>

            <div className="p-8">
              {/* ════════════════ SEARCH TAB ════════════════ */}
              {activeTab === 'search' && (
                <div className="space-y-12">
                  {/* ── Search parameters ── */}
                  <section>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg">
                        <Search className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Search Parameters</h2>
                    </div>
                    <p className="text-gray-400 text-sm mb-8">
                      CMSX opens trusted job boards with your search terms. Verify requirements directly on the employer or job board site.
                    </p>

                    {/* Category chips */}
                    <div className="mb-8 p-6 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                      <div className="flex items-center justify-between mb-5">
                        <div>
                          <h3 className="text-lg font-semibold text-white">Browse by category</h3>
                          <p className="text-sm text-gray-400 mt-1">Click a category to pre-fill the keyword field.</p>
                        </div>
                        {selectedCategory && (
                          <button
                            type="button"
                            onClick={clearCategory}
                            className="px-4 py-2 rounded-xl border border-white/20 bg-white/10 text-sm font-medium text-gray-200 hover:bg-white/20 hover:text-white transition-all duration-300"
                          >
                            Clear
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                        {JOB_CATEGORY_TILES.map(cat => (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => applyCategory(cat)}
                            className={`group rounded-2xl border p-4 text-left transition-all duration-300 hover:scale-[1.02] ${
                              selectedCategory === cat.id
                                ? `bg-gradient-to-r ${cat.gradient} border-white/20 text-white shadow-xl`
                                : 'border-white/15 bg-white/5 text-gray-200 hover:bg-white/10 hover:border-white/25'
                            }`}
                          >
                            <div className={`inline-flex rounded-xl p-2 mb-3 ${selectedCategory === cat.id ? 'bg-white/20' : `bg-gradient-to-r ${cat.gradient}`}`}>
                              <cat.icon className="h-5 w-5 text-white" />
                            </div>
                            <p className="font-semibold text-sm leading-snug">{cat.label}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Keyword + Location inputs */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">Job Title / Keywords</label>
                        <div className="relative">
                          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
                          <input
                            type="text"
                            value={keywords}
                            onChange={e => setKeywords(e.target.value)}
                            onBlur={() => setSearchParams(prev => {
                              const next = new URLSearchParams(prev)
                              next.set('keywords', keywords)
                              return next
                            }, { replace: true })}
                            placeholder="e.g. delivery driver, dishwasher, warehouse"
                            className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                            data-testid="job-keywords"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">Location</label>
                        <LocationSelector
                          value={location}
                          onChange={updateLocationParam}
                          placeholder="City or zip code"
                          className="w-full"
                          inputClassName="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                        />
                      </div>
                    </div>

                    {/* Low-barrier toggle */}
                    <label className="flex items-start gap-4 cursor-pointer group w-fit">
                      <input
                        type="checkbox"
                        checked={lowBarrier}
                        onChange={e => updateLowBarrierParam(e.target.checked)}
                        className="mt-1 h-5 w-5 text-emerald-500 focus:ring-emerald-400 border-gray-400 rounded bg-white/10 flex-shrink-0"
                        data-testid="low-barrier-filter"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
                          Add low-barrier search terms
                        </span>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Appends "entry level" to your search on each job board.
                        </p>
                      </div>
                    </label>
                  </section>

                  {/* ── Job board launcher ── */}
                  <section>
                    <h2 className="text-2xl font-bold text-white mb-2">Open Job Boards</h2>
                    <p className="text-gray-400 text-sm mb-6">
                      Each button opens that site in a new tab with your current keyword and location applied.
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                      {JOB_BOARDS.map(board => (
                        <button
                          key={board.id}
                          onClick={() => window.open(boardUrls[board.id], '_blank', 'noopener,noreferrer')}
                          className="group flex flex-col items-start gap-2 p-5 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 hover:border-white/30 hover:bg-white/10 transition-all duration-300 hover:scale-[1.03] hover:shadow-xl text-left"
                          data-testid={`open-${board.id}`}
                        >
                          <div className={`p-2 bg-gradient-to-r ${board.gradient} rounded-xl mb-1`}>
                            <ExternalLink className="h-5 w-5 text-white" />
                          </div>
                          <span className="text-white font-semibold text-sm">{board.name}</span>
                          <span className="text-gray-400 text-xs leading-snug">{board.description}</span>
                        </button>
                      ))}
                    </div>
                  </section>

                  {/* ── Staffing agencies ── */}
                  <section>
                    <h2 className="text-xl font-bold text-white mb-2">Staffing Agencies</h2>
                    <p className="text-gray-400 text-sm mb-4">
                      Staffing and temp agencies often hire without background checks or with same-day placement.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      {staffingLinks.map(item => (
                        <button
                          key={item.label}
                          onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}
                          className="flex items-center gap-3 p-4 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 hover:border-white/25 hover:bg-white/10 transition-all duration-300 text-left"
                        >
                          <div className="p-2 bg-gradient-to-r from-teal-600 to-emerald-600 rounded-lg flex-shrink-0">
                            <Users className="h-4 w-4 text-white" />
                          </div>
                          <span className="text-gray-200 text-sm font-medium flex-1">{item.label}</span>
                          <ExternalLink size={14} className="text-gray-500 flex-shrink-0" />
                        </button>
                      ))}
                    </div>
                  </section>

                  {/* ── Case Manager Tools ── */}
                  <section>
                    <h2 className="text-xl font-bold text-white mb-2">Case Manager Tools</h2>
                    <p className="text-gray-400 text-sm mb-4">
                      Tools to support your client through the full job search process — coming soon.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                      {CASE_MANAGER_TOOLS.map(tool => (
                        <div
                          key={tool.label}
                          className="flex flex-col gap-2 p-5 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 opacity-60 cursor-not-allowed"
                        >
                          <div className="p-2 bg-white/10 rounded-xl w-fit">
                            <tool.icon className="h-5 w-5 text-gray-300" />
                          </div>
                          <span className="text-white font-semibold text-sm">{tool.label}</span>
                          <span className="text-gray-400 text-xs leading-snug">{tool.description}</span>
                          <span className="text-xs text-gray-500 italic mt-auto">Coming soon</span>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>
              )}

              {/* ════════════════ SAVED JOBS TAB ════════════════ */}
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

                  {!selectedClient ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="p-4 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl w-fit mx-auto mb-6">
                        <User size={48} className="text-purple-400" />
                      </div>
                      <h3 className="text-xl font-medium mb-3 text-white">Select a client first</h3>
                      <p className="text-gray-400">Choose a client above to see their saved jobs.</p>
                    </div>
                  ) : savedJobs.length === 0 ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="p-4 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl w-fit mx-auto mb-6">
                        <Bookmark size={48} className="text-purple-400" />
                      </div>
                      <h3 className="text-xl font-medium mb-3 text-white">No saved jobs</h3>
                      <p className="text-gray-400">Jobs saved for this client will appear here.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {savedJobs.map((job, index) => (
                        <div
                          key={index}
                          className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.01] hover:shadow-xl hover:shadow-purple-500/10"
                        >
                          <div className="flex items-start justify-between gap-4 mb-3">
                            <h3 className="font-semibold text-white group-hover:text-purple-200 transition-colors">
                              {job.title || job.job_id || 'Saved job'}
                            </h3>
                            <span className="text-xs text-gray-400 px-3 py-1 bg-white/10 rounded-full whitespace-nowrap flex-shrink-0">
                              {new Date(job.saved_date).toLocaleDateString()}
                            </span>
                          </div>
                          {(job.company || job.location) && (
                            <p className="text-gray-300 text-sm mb-2">
                              {[job.company, job.location].filter(Boolean).join(' · ')}
                            </p>
                          )}
                          {job.salary && (
                            <p className="text-emerald-300 text-sm mb-2">{job.salary}</p>
                          )}
                          {job.notes && (
                            <p className="text-gray-400 text-sm italic bg-white/5 p-3 rounded-lg border border-white/10 mt-3">
                              Notes: {job.notes}
                            </p>
                          )}
                          {job.url && (
                            <div className="mt-4">
                              <button
                                onClick={() => window.open(job.url, '_blank', 'noopener,noreferrer')}
                                className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-4 py-2 text-sm text-white hover:bg-white/20 transition-colors"
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
    </div>
  )
}

export default Jobs
