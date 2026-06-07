import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Compass,
  FileSpreadsheet,
  Filter,
  Globe,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Upload,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DirectoryListingCard from '../components/DirectoryListingCard'
import { buildListingPayload, defaultListingForm, soberLivingDirectoryApi } from '../utils/soberLivingDirectory'

const defaultFilters = {
  location_query: '',
  zip_code: '',
  state: 'CA',
  population_served: '',
  accepts_mat: '',
  accepts_insurance: '',
  certification: '',
  funding: '',
  verification_status: '',
  radius_miles: '25',
  min_trust_score: '',
}

const defaultWebSearchForm = {
  source_key: 'ccapp',
  query: '',
}

const discoverySourceTemplates = {
  ccapp: {
    source_name: 'CCAPP Recovery Residences',
    source_type: 'certification_directory',
    base_url: 'https://ccapprecoveryresidences.org/search/',
    trust_level: 'high',
    supports_api: false,
    supports_scraping: true,
    requires_manual_review: true,
    is_active: true,
    connectorLabel: 'Trusted certification search',
  },
  oxford: {
    source_name: 'Oxford House',
    source_type: 'public_directory',
    base_url: 'https://www.oxfordvacancies.com/',
    trust_level: 'high',
    supports_api: false,
    supports_scraping: true,
    requires_manual_review: true,
    is_active: true,
    connectorLabel: 'Public recovery housing search',
  },
}

const verificationOptions = [
  { value: 'verified_recently', label: 'Verified in last 30 days' },
  { value: 'needs_reverification', label: 'Needs reverification' },
  { value: 'pending_review', label: 'Pending review' },
  { value: 'approved_only', label: 'Approved only' },
  { value: 'use_caution', label: 'Use caution' },
]

const fundingOptions = [
  { value: 'accepts_insurance', label: 'Insurance accepted' },
  { value: 'deposit_required', label: 'Deposit required' },
  { value: 'no_deposit', label: 'No deposit required' },
]

const booleanOptions = [
  { value: 'true', label: 'Yes' },
  { value: 'false', label: 'No' },
]

const normalizeListings = (payload) => (Array.isArray(payload?.listings) ? payload.listings.filter(Boolean) : [])

const humanizeToken = (value, fallback = 'Unknown') => {
  if (typeof value !== 'string' || !value.trim()) {
    return fallback
  }
  return value.replaceAll('_', ' ')
}

const normalizeText = (value) => String(value || '').trim().toLowerCase()

const toBooleanFilter = (value) => {
  if (value === 'true') return true
  if (value === 'false') return false
  return null
}

const parseNumber = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

const parseDate = (value) => {
  if (!value) return null
  const timestamp = Date.parse(value)
  return Number.isNaN(timestamp) ? null : new Date(timestamp)
}

const withinDays = (value, days) => {
  const date = parseDate(value)
  if (!date) return false
  return Date.now() - date.getTime() <= days * 24 * 60 * 60 * 1000
}

const haversineMiles = (lat1, lon1, lat2, lon2) => {
  const toRadians = (degrees) => (degrees * Math.PI) / 180
  const earthRadiusMiles = 3958.8
  const dLat = toRadians(lat2 - lat1)
  const dLon = toRadians(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return earthRadiusMiles * c
}

const formatDistance = (distance) => {
  if (typeof distance !== 'number' || Number.isNaN(distance)) {
    return null
  }
  return distance < 10 ? `${distance.toFixed(1)} mi` : `${Math.round(distance)} mi`
}

const matchesFunding = (listing, funding) => {
  if (!funding) return true
  if (funding === 'accepts_insurance') return Boolean(listing.accepts_insurance)
  if (funding === 'deposit_required') return Boolean(listing.deposit_required)
  if (funding === 'no_deposit') return listing.deposit_required === false
  return true
}

const matchesVerificationStatus = (listing, verificationStatus) => {
  if (!verificationStatus) return true
  if (verificationStatus === 'verified_recently') return withinDays(listing.last_verified_date, 30)
  if (verificationStatus === 'needs_reverification') {
    return listing.status === 'needs_reverification' || !withinDays(listing.last_verified_date, 60)
  }
  if (verificationStatus === 'pending_review') return listing.status === 'pending_review'
  if (verificationStatus === 'approved_only') return listing.status === 'approved'
  if (verificationStatus === 'use_caution') return listing.status === 'use_caution'
  return true
}

const sortListings = (listings) =>
  [...listings].sort((left, right) => {
    const rightVerified = parseDate(right.last_verified_date)?.getTime() || 0
    const leftVerified = parseDate(left.last_verified_date)?.getTime() || 0
    if ((right.trust_score || 0) !== (left.trust_score || 0)) {
      return (right.trust_score || 0) - (left.trust_score || 0)
    }
    return rightVerified - leftVerified
  })

function SoberLivingDirectory() {
  const [filters, setFilters] = useState(defaultFilters)
  const [allListings, setAllListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showImportTools, setShowImportTools] = useState(false)
  const [formState, setFormState] = useState(defaultListingForm)
  const [saving, setSaving] = useState(false)
  const [importFile, setImportFile] = useState(null)
  const [importSourceName, setImportSourceName] = useState('CA Sober Living Directory')
  const [importing, setImporting] = useState(false)
  const [importSummary, setImportSummary] = useState(null)
  const [geoState, setGeoState] = useState({
    loading: false,
    enabled: false,
    latitude: null,
    longitude: null,
    error: '',
  })
  const [webSearchForm, setWebSearchForm] = useState(defaultWebSearchForm)
  const [runningWebSearch, setRunningWebSearch] = useState(false)
  const [webSearchSummary, setWebSearchSummary] = useState(null)

  const loadListings = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await soberLivingDirectoryApi.listListings({})
      setAllListings(normalizeListings(data))
    } catch (err) {
      setError(err.message || 'Failed to load directory')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadListings()
  }, [])

  const filterOptions = useMemo(() => {
    const cities = Array.from(new Set(allListings.map((item) => item.city).filter(Boolean))).sort()
    const populations = Array.from(new Set(allListings.map((item) => item.population_served).filter(Boolean))).sort()
    return { cities, populations }
  }, [allListings])

  const filteredListings = useMemo(() => {
    const locationQuery = normalizeText(filters.location_query)
    const zipCode = normalizeText(filters.zip_code)
    const state = normalizeText(filters.state)
    const certification = normalizeText(filters.certification)
    const population = normalizeText(filters.population_served)
    const acceptsMat = toBooleanFilter(filters.accepts_mat)
    const acceptsInsurance = toBooleanFilter(filters.accepts_insurance)
    const minTrustScore = parseNumber(filters.min_trust_score)
    const radiusMiles = parseNumber(filters.radius_miles)

    const prepared = allListings
      .map((listing) => {
        let distanceMiles = null
        if (
          geoState.enabled &&
          geoState.latitude !== null &&
          geoState.longitude !== null &&
          listing.latitude !== null &&
          listing.longitude !== null
        ) {
          distanceMiles = haversineMiles(
            geoState.latitude,
            geoState.longitude,
            Number(listing.latitude),
            Number(listing.longitude)
          )
        }
        return { ...listing, distanceMiles }
      })
      .filter((listing) => {
        const haystack = [
          listing.name,
          listing.operator_name,
          listing.city,
          listing.state,
          listing.zip_code,
          listing.address,
          listing.neighborhood,
          listing.population_served,
          listing.certification_status,
          listing.certification_body,
          listing.website,
          listing.notes,
        ]
          .map(normalizeText)
          .join(' ')

        if (locationQuery && !haystack.includes(locationQuery)) {
          return false
        }
        if (zipCode && !normalizeText(listing.zip_code).includes(zipCode)) {
          return false
        }
        if (state && normalizeText(listing.state) !== state) {
          return false
        }
        if (population && normalizeText(listing.population_served) !== population) {
          return false
        }
        if (acceptsMat !== null && Boolean(listing.accepts_mat) !== acceptsMat) {
          return false
        }
        if (acceptsInsurance !== null && Boolean(listing.accepts_insurance) !== acceptsInsurance) {
          return false
        }
        if (certification) {
          const certificationText = `${normalizeText(listing.certification_status)} ${normalizeText(listing.certification_body)}`
          if (!certificationText.includes(certification)) {
            return false
          }
        }
        if (!matchesFunding(listing, filters.funding)) {
          return false
        }
        if (!matchesVerificationStatus(listing, filters.verification_status)) {
          return false
        }
        if (minTrustScore !== null && Number(listing.trust_score || 0) < minTrustScore) {
          return false
        }
        if (geoState.enabled && radiusMiles !== null) {
          if (typeof listing.distanceMiles !== 'number') {
            return false
          }
          if (listing.distanceMiles > radiusMiles) {
            return false
          }
        }
        return true
      })
      .map((listing) => ({
        ...listing,
        distance_label: formatDistance(listing.distanceMiles),
      }))

    return sortListings(prepared)
  }, [allListings, filters, geoState])

  const connectorLabel = discoverySourceTemplates[webSearchForm.source_key]?.connectorLabel || 'Discovery connector'

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not available in this browser')
      setGeoState((current) => ({ ...current, error: 'Geolocation is not available in this browser.' }))
      return
    }
    setGeoState((current) => ({ ...current, loading: true, error: '' }))
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGeoState({
          loading: false,
          enabled: true,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          error: '',
        })
        toast.success('Using current location for radius filtering')
      },
      (geolocationError) => {
        setGeoState((current) => ({
          ...current,
          loading: false,
          enabled: false,
          error: geolocationError.message || 'Unable to access your current location.',
        }))
        toast.error(geolocationError.message || 'Unable to access your current location')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    )
  }

  const clearLocationMode = () => {
    setGeoState({
      loading: false,
      enabled: false,
      latitude: null,
      longitude: null,
      error: '',
    })
  }

  const resetFilters = () => {
    setFilters(defaultFilters)
    clearLocationMode()
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!formState.name.trim() || !formState.city.trim()) {
      toast.error('Name and city are required')
      return
    }
    setSaving(true)
    try {
      await soberLivingDirectoryApi.createListing(buildListingPayload(formState))
      toast.success('Sober living listing added')
      setFormState(defaultListingForm)
      setShowCreateForm(false)
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Failed to create listing')
    } finally {
      setSaving(false)
    }
  }

  const handleImport = async (event) => {
    event.preventDefault()
    if (!importFile) {
      toast.error('Choose a CSV or XLSX file to import')
      return
    }
    setImporting(true)
    try {
      const data = await soberLivingDirectoryApi.importListings({
        file: importFile,
        sourceName: importSourceName.trim() || 'Manual directory import',
      })
      setImportSummary(data.summary)
      setImportFile(null)
      toast.success(`Imported ${data.summary.listings_created} new listings`)
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  const ensureDiscoverySource = async (sourceKey) => {
    const template = discoverySourceTemplates[sourceKey]
    const sourceResponse = await soberLivingDirectoryApi.listSources()
    const existingSource = (sourceResponse.sources || []).find(
      (source) =>
        source?.source_name === template.source_name ||
        normalizeText(source?.base_url) === normalizeText(template.base_url)
    )
    if (existingSource) {
      return existingSource
    }
    const created = await soberLivingDirectoryApi.createSource(template)
    return created.source
  }

  const ensureDiscoveryJob = async ({ source, sourceKey, city, state, query }) => {
    const jobsResponse = await soberLivingDirectoryApi.listDiscoveryJobs()
    const normalizedCity = normalizeText(city)
    const normalizedState = normalizeText(state)
    const normalizedQuery = normalizeText(query)
    const existingJob = (jobsResponse.jobs || []).find((job) => {
      if (job?.source_id !== source.source_id) return false
      if (normalizeText(job.target_city) !== normalizedCity) return false
      if (normalizeText(job.target_state) !== normalizedState) return false
      return normalizeText(job.query) === normalizedQuery
    })
    if (existingJob) {
      return existingJob
    }
    const label = sourceKey === 'ccapp' ? 'CCAPP' : 'Oxford'
    const created = await soberLivingDirectoryApi.createDiscoveryJob({
      source_id: source.source_id,
      job_name: `${label} ${city || 'Statewide'} ${state}`.trim(),
      job_type: 'city_search',
      target_city: city || null,
      target_state: state || 'CA',
      query: query || null,
      is_active: true,
    })
    return created.job
  }

  const handleSearchWebForMore = async () => {
    const locationText = filters.location_query.trim() || filters.zip_code.trim()
    const sourceKey = webSearchForm.source_key
    const state = (filters.state || 'CA').trim().toUpperCase()
    const query = webSearchForm.query.trim() || locationText

    if (!locationText) {
      toast.error('Enter a city, ZIP, or location before running web discovery')
      return
    }

    setRunningWebSearch(true)
    setWebSearchSummary(null)
    try {
      const source = await ensureDiscoverySource(sourceKey)
      const job = await ensureDiscoveryJob({
        source,
        sourceKey,
        city: filters.location_query.trim() || null,
        state,
        query,
      })
      const response = await soberLivingDirectoryApi.runDiscoveryJob(job.job_id)
      const run = response?.run || {}
      setWebSearchSummary({
        source_name: source.source_name,
        job_name: job.job_name,
        records_found: run.records_found ?? 0,
        raw_records_created: run.raw_records_created ?? 0,
        duplicates_detected: run.duplicates_detected ?? 0,
        errors_count: run.errors_count ?? 0,
      })
      toast.success(`${source.source_name} discovery completed and routed to review`)
    } catch (err) {
      toast.error(err.message || 'Web discovery failed')
    } finally {
      setRunningWebSearch(false)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(160deg,#020617_0%,#0f172a_45%,#083344_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="overflow-hidden rounded-[2.25rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-slate-950/40">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-4xl">
              <p className="text-sm uppercase tracking-[0.32em] text-cyan-300">Referral Intelligence</p>
              <h1 className="mt-2 text-4xl font-bold tracking-tight text-white">Find sober living options near the client</h1>
              <p className="mt-3 text-base text-slate-300">
                Search trusted sober living listings first, then send controlled CCAPP or Oxford discovery into review when the local network needs more options.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={loadListings}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh Listings
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm((prev) => !prev)}
                className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                <Plus className="h-4 w-4" />
                Add Listing
              </button>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <TabLink to="/sober-living-directory" active>
              Directory Search
            </TabLink>
            <TabLink to="/sober-living-directory/review">Review Queue</TabLink>
            <TabLink to="/sober-living-directory/discovery">Advanced Discovery</TabLink>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.6fr_0.9fr]">
          <div className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-cyan-200">Search First</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Location, funding, and verification filters</h2>
                <p className="mt-2 text-sm text-slate-300">
                  Use the saved directory first. Discovery stays review-gated and lives behind the advanced workflow.
                </p>
              </div>
              <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
                {filteredListings.length} match{filteredListings.length === 1 ? '' : 'es'}
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Input
                label="City, ZIP, or location"
                value={filters.location_query}
                onChange={(value) => handleFilterChange('location_query', value)}
                icon={Search}
                placeholder="Los Angeles, Hollywood, or Downtown"
              />
              <Input
                label="ZIP code"
                value={filters.zip_code}
                onChange={(value) => handleFilterChange('zip_code', value)}
                icon={MapPin}
                placeholder="90012"
              />
              <Select
                label="State"
                value={filters.state}
                onChange={(value) => handleFilterChange('state', value)}
                options={['CA']}
              />
              <Input
                label="Radius miles"
                value={filters.radius_miles}
                onChange={(value) => handleFilterChange('radius_miles', value)}
                type="number"
                placeholder="25"
              />
              <Select
                label="Population"
                value={filters.population_served}
                onChange={(value) => handleFilterChange('population_served', value)}
                options={filterOptions.populations}
                allowBlank
              />
              <Select
                label="Insurance"
                value={filters.accepts_insurance}
                onChange={(value) => handleFilterChange('accepts_insurance', value)}
                options={booleanOptions}
                allowBlank
              />
              <Select
                label="MAT"
                value={filters.accepts_mat}
                onChange={(value) => handleFilterChange('accepts_mat', value)}
                options={booleanOptions}
                allowBlank
              />
              <Input
                label="Certification"
                value={filters.certification}
                onChange={(value) => handleFilterChange('certification', value)}
                placeholder="CCAPP, Oxford, certified"
              />
              <Select
                label="Funding"
                value={filters.funding}
                onChange={(value) => handleFilterChange('funding', value)}
                options={fundingOptions}
                allowBlank
              />
              <Select
                label="Verification status"
                value={filters.verification_status}
                onChange={(value) => handleFilterChange('verification_status', value)}
                options={verificationOptions}
                allowBlank
              />
              <Input
                label="Minimum trust score"
                value={filters.min_trust_score}
                onChange={(value) => handleFilterChange('min_trust_score', value)}
                type="number"
                placeholder="40"
              />
              <Select
                label="Quick city"
                value={filterOptions.cities.includes(filters.location_query) ? filters.location_query : ''}
                onChange={(value) => handleFilterChange('location_query', value)}
                options={filterOptions.cities}
                allowBlank
              />
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleUseMyLocation}
                disabled={geoState.loading}
                className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Compass className="h-4 w-4" />
                {geoState.loading ? 'Locating...' : 'Use My Location'}
              </button>
              {geoState.enabled ? (
                <button
                  type="button"
                  onClick={clearLocationMode}
                  className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-200 transition hover:bg-white/10"
                >
                  Clear Current Location
                </button>
              ) : null}
              <button
                type="button"
                onClick={resetFilters}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-200 transition hover:bg-white/10"
              >
                <Filter className="h-4 w-4" />
                Reset Filters
              </button>
            </div>

            {geoState.enabled ? (
              <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                Radius filtering is using the client’s current coordinates. Listings without latitude and longitude will be excluded while radius mode is active.
              </div>
            ) : null}

            {geoState.error ? (
              <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
                {geoState.error}
              </div>
            ) : null}
          </div>

          <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-fuchsia-200">Controlled Discovery</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Search web for more</h2>
              <p className="mt-2 text-sm text-slate-300">
                Run a bounded discovery job when the saved directory is thin. Results go to raw review and duplicate review, never directly into approved referrals.
              </p>
            </div>

            <div className="mt-5 grid gap-4">
              <Select
                label="Connector"
                value={webSearchForm.source_key}
                onChange={(value) => setWebSearchForm((current) => ({ ...current, source_key: value }))}
                options={[
                  { value: 'ccapp', label: 'CCAPP Recovery Residences' },
                  { value: 'oxford', label: 'Oxford House' },
                ]}
              />
              <Input
                label="Discovery query"
                value={webSearchForm.query}
                onChange={(value) => setWebSearchForm((current) => ({ ...current, query: value }))}
                placeholder="Leave blank to use the location query"
              />
              <button
                type="button"
                onClick={handleSearchWebForMore}
                disabled={runningWebSearch}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-fuchsia-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Globe className="h-4 w-4" />
                {runningWebSearch ? 'Running Discovery...' : 'Search Web for More'}
              </button>
            </div>

            <div className="mt-4 rounded-2xl border border-fuchsia-400/20 bg-fuchsia-500/10 p-4 text-sm text-fuchsia-100">
              {connectorLabel}. Every result remains review-gated and must pass raw-record approval or duplicate resolution before becoming a trusted listing.
            </div>

            {webSearchSummary ? (
              <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4 text-sm text-cyan-100">
                <p className="font-semibold text-white">{webSearchSummary.source_name} completed</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <span>Records found: {webSearchSummary.records_found}</span>
                  <span>Raw records created: {webSearchSummary.raw_records_created}</span>
                  <span>Duplicates detected: {webSearchSummary.duplicates_detected}</span>
                  <span>Errors: {webSearchSummary.errors_count}</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    to="/sober-living-directory/review"
                    className="rounded-2xl border border-cyan-300/30 bg-cyan-400/20 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-400/30"
                  >
                    Open Review Queue
                  </Link>
                  <Link
                    to="/sober-living-directory/discovery"
                    className="rounded-2xl border border-white/15 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
                  >
                    Open Advanced Discovery
                  </Link>
                </div>
              </div>
            ) : null}
          </section>
        </section>

        {showCreateForm ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-cyan-200">Manual Directory Entry</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Add a sober living listing</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="text-sm text-slate-300 underline underline-offset-4"
              >
                Close
              </button>
            </div>
            <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={handleCreate}>
              <Input label="Name" value={formState.name} onChange={(value) => setFormState((prev) => ({ ...prev, name: value }))} required />
              <Input label="Operator Name" value={formState.operator_name} onChange={(value) => setFormState((prev) => ({ ...prev, operator_name: value }))} />
              <Input label="Phone" value={formState.phone} onChange={(value) => setFormState((prev) => ({ ...prev, phone: value }))} />
              <Input label="Email" value={formState.email} onChange={(value) => setFormState((prev) => ({ ...prev, email: value }))} />
              <Input label="Address" value={formState.address} onChange={(value) => setFormState((prev) => ({ ...prev, address: value }))} />
              <Input label="City" value={formState.city} onChange={(value) => setFormState((prev) => ({ ...prev, city: value }))} required />
              <Input label="State" value={formState.state} onChange={(value) => setFormState((prev) => ({ ...prev, state: value }))} />
              <Input label="Website" value={formState.website} onChange={(value) => setFormState((prev) => ({ ...prev, website: value }))} />
              <Input label="Population Served" value={formState.population_served} onChange={(value) => setFormState((prev) => ({ ...prev, population_served: value }))} />
              <Input label="Certification Status" value={formState.certification_status} onChange={(value) => setFormState((prev) => ({ ...prev, certification_status: value }))} />
              <Input label="Certification Body" value={formState.certification_body} onChange={(value) => setFormState((prev) => ({ ...prev, certification_body: value }))} />
              <Select
                label="Status"
                value={formState.status}
                onChange={(value) => setFormState((prev) => ({ ...prev, status: value }))}
                options={['pending_review', 'approved', 'needs_reverification', 'use_caution', 'do_not_refer', 'archived']}
              />
              <Toggle label="Accepts MAT" checked={formState.accepts_mat} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_mat: value }))} />
              <Toggle label="Accepts Insurance" checked={formState.accepts_insurance} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_insurance: value }))} />
              <Toggle label="Deposit Required" checked={formState.deposit_required} onChange={(value) => setFormState((prev) => ({ ...prev, deposit_required: value }))} />
              <Toggle label="Pets Allowed" checked={formState.pets_allowed} onChange={(value) => setFormState((prev) => ({ ...prev, pets_allowed: value }))} />
              <TextArea label="Notes" value={formState.notes} onChange={(value) => setFormState((prev) => ({ ...prev, notes: value }))} className="md:col-span-2" />
              <TextArea label="Internal Referral Notes" value={formState.internal_referral_notes} onChange={(value) => setFormState((prev) => ({ ...prev, internal_referral_notes: value }))} className="md:col-span-2" />
              <div className="md:col-span-2 xl:col-span-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? 'Saving...' : 'Create Listing'}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-amber-200">Advanced Intake Tools</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Manual import and admin discovery links</h2>
            </div>
            <button
              type="button"
              onClick={() => setShowImportTools((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
            >
              <FileSpreadsheet className="h-4 w-4" />
              {showImportTools ? 'Hide Tools' : 'Show Tools'}
            </button>
          </div>

          {showImportTools ? (
            <div className="mt-5 space-y-6">
              <form className="grid gap-4 lg:grid-cols-[1.4fr_1fr_auto]" onSubmit={handleImport}>
                <Input label="Source Name" value={importSourceName} onChange={setImportSourceName} />
                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Import File</span>
                  <input
                    type="file"
                    accept=".xlsx,.csv"
                    onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition file:mr-4 file:rounded-xl file:border-0 file:bg-cyan-500 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-cyan-400"
                  />
                </label>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={importing}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Upload className="h-4 w-4" />
                    {importing ? 'Importing...' : 'Run Import'}
                  </button>
                </div>
              </form>

              {importSummary ? (
                <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                  <SummaryCard label="Rows Read" value={importSummary.rows_read} />
                  <SummaryCard label="Raw Created" value={importSummary.raw_created} />
                  <SummaryCard label="New Listings" value={importSummary.listings_created} />
                  <SummaryCard label="Updated" value={importSummary.listings_updated} />
                  <SummaryCard label="Duplicates" value={importSummary.duplicates_detected} />
                  <SummaryCard label="Errors" value={importSummary.errors?.length || 0} danger={Boolean(importSummary.errors?.length)} />
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <Link
                  to="/sober-living-directory/review"
                  className="rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-500/25"
                >
                  Open Review Queue
                </Link>
                <Link
                  to="/sober-living-directory/discovery"
                  className="rounded-2xl border border-fuchsia-400/30 bg-fuchsia-500/15 px-4 py-3 text-sm font-medium text-fuchsia-100 transition hover:bg-fuchsia-500/25"
                >
                  Open Advanced Discovery
                </Link>
              </div>
            </div>
          ) : null}
        </section>

        {loading ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-10 text-center text-slate-300">
            Loading sober living directory...
          </section>
        ) : error ? (
          <section className="rounded-[2rem] border border-red-400/30 bg-red-500/10 p-10 text-center text-red-100">
            Failed to load directory: {error}
          </section>
        ) : filteredListings.length === 0 ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-10 text-center text-slate-300">
            No sober living listings match these location and verification filters. Use the web discovery action to send more leads into review, or add a listing manually.
          </section>
        ) : (
          <section className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Directory Results</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Trusted and reviewable options</h2>
              </div>
              <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-slate-100">
                {filteredListings.length} result{filteredListings.length === 1 ? '' : 's'}
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              {filteredListings.map((listing) => (
                <DirectoryListingCard key={listing.listing_id} listing={listing} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function TabLink({ to, active = false, children }) {
  return (
    <Link
      to={to}
      className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
        active
          ? 'border-cyan-400/30 bg-cyan-500/15 text-cyan-100'
          : 'border-white/15 text-slate-200 hover:bg-white/10'
      }`}
    >
      {children}
    </Link>
  )
}

function Input({ label, value, onChange, icon: Icon, type = 'text', required = false, className = '', placeholder = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <div className="relative">
        {Icon ? <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /> : null}
        <input
          type={type}
          value={value}
          required={required}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className={`w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50 ${Icon ? 'pl-10' : ''}`}
        />
      </div>
    </label>
  )
}

function Select({ label, value, onChange, options = [], allowBlank = false }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      >
        {allowBlank ? <option value="">All</option> : null}
        {options.map((option) => {
          const valueToUse = typeof option === 'string' ? option : option.value
          const labelToUse = typeof option === 'string' ? humanizeToken(option, option) : option.label
          return (
            <option key={valueToUse} value={valueToUse}>
              {labelToUse}
            </option>
          )
        })}
      </select>
    </label>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 rounded border-white/20 bg-slate-900" />
    </label>
  )
}

function TextArea({ label, value, onChange, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      />
    </label>
  )
}

function SummaryCard({ label, value, danger = false }) {
  return (
    <div className={`rounded-2xl border p-4 ${danger ? 'border-red-400/30 bg-red-500/10' : 'border-white/10 bg-slate-950/35'}`}>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${danger ? 'text-red-100' : 'text-white'}`}>{value}</p>
    </div>
  )
}

export default SoberLivingDirectory
