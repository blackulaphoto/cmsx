import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Compass, ExternalLink, Filter, Globe, MapPin, Phone, Plus, RefreshCw, Save, Search, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
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
}

const defaultNoteState = {}

const booleanOptions = [
  { value: 'true', label: 'Yes' },
  { value: 'false', label: 'No' },
]

const fundingOptions = [
  { value: 'accepts_insurance', label: 'Insurance accepted' },
  { value: 'deposit_required', label: 'Deposit required' },
  { value: 'no_deposit', label: 'No deposit required' },
]

const verificationOptions = [
  { value: 'verified_recently', label: 'Verified in last 30 days' },
  { value: 'needs_reverification', label: 'Needs reverification' },
  { value: 'pending_review', label: 'Pending review' },
  { value: 'approved_only', label: 'Approved only' },
  { value: 'use_caution', label: 'Use caution' },
]

const sourceStyles = {
  saved: 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100',
  ccapp: 'border-cyan-400/30 bg-cyan-500/15 text-cyan-100',
  oxford: 'border-violet-400/30 bg-violet-500/15 text-violet-100',
  external: 'border-fuchsia-400/30 bg-fuchsia-500/15 text-fuchsia-100',
}

const normalizeListings = (payload) => (Array.isArray(payload?.listings) ? payload.listings.filter(Boolean) : [])
const normalizeExternalResults = (payload) => (Array.isArray(payload?.external_results) ? payload.external_results.filter(Boolean) : [])

const humanizeToken = (value, fallback = 'Unknown') => {
  if (typeof value !== 'string' || !value.trim()) return fallback
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
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? null : new Date(parsed)
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
  if (typeof distance !== 'number' || Number.isNaN(distance)) return null
  return distance < 10 ? `${distance.toFixed(1)} mi` : `${Math.round(distance)} mi`
}

const matchesFunding = (item, funding) => {
  if (!funding) return true
  if (funding === 'accepts_insurance') return Boolean(item.accepts_insurance)
  if (funding === 'deposit_required') return Boolean(item.deposit_required)
  if (funding === 'no_deposit') return item.deposit_required === false
  return true
}

const matchesVerificationStatus = (item, verificationStatus) => {
  if (!verificationStatus) return true
  if (verificationStatus === 'verified_recently') return withinDays(item.last_verified_date, 30)
  if (verificationStatus === 'needs_reverification') return item.status === 'needs_reverification' || !withinDays(item.last_verified_date, 60)
  if (verificationStatus === 'pending_review') return item.status === 'pending_review'
  if (verificationStatus === 'approved_only') return item.status === 'approved'
  if (verificationStatus === 'use_caution') return item.status === 'use_caution'
  return true
}

const deriveSearchScope = (filters) => {
  const raw = (filters.location_query || '').trim()
  const state = (filters.state || 'CA').trim().toUpperCase()
  if (!raw && !filters.zip_code.trim()) {
    return { query: '', city: null, state, zip_code: '' }
  }
  if (raw.includes(',')) {
    const [cityPart, statePart] = raw.split(',').map((item) => item.trim())
    return {
      query: raw,
      city: cityPart || null,
      state: (statePart || state).slice(0, 2).toUpperCase(),
      zip_code: filters.zip_code.trim(),
    }
  }
  return {
    query: raw || filters.zip_code.trim(),
    city: raw || null,
    state,
    zip_code: filters.zip_code.trim(),
  }
}

const buildExternalListingPayload = (result, note) => ({
  name: result.name?.trim() || 'External sober living result',
  operator_name: result.operator_name || null,
  website: result.website || result.source_url || null,
  phone: result.phone || null,
  email: result.email || null,
  address: result.address || null,
  city: result.city || 'Unknown',
  state: (result.state || 'CA').toUpperCase(),
  zip_code: result.zip_code || null,
  latitude: result.latitude ?? null,
  longitude: result.longitude ?? null,
  neighborhood: result.neighborhood || null,
  population_served: result.population_served || null,
  house_type: result.house_type || null,
  certification_status: result.certification_status || null,
  certification_body: result.certification_body || null,
  certification_expiration_date: null,
  monthly_rent_min: result.monthly_rent_min ?? null,
  monthly_rent_max: result.monthly_rent_max ?? null,
  deposit_required: result.deposit_required ?? null,
  accepts_insurance: result.accepts_insurance ?? null,
  accepts_mat: result.accepts_mat ?? null,
  accepts_probation_parole: result.accepts_probation_parole ?? null,
  pets_allowed: result.pets_allowed ?? null,
  bed_availability_status: result.bed_availability_status || 'unknown',
  last_availability_check_date: null,
  last_verified_date: null,
  verification_method: result.verification_method || 'external_search',
  risk_flags_json: Array.isArray(result.risk_flags_json) ? result.risk_flags_json : [],
  notes: [result.notes, note].filter(Boolean).join('\n\n') || null,
  internal_referral_notes: null,
  source_urls_json: Array.isArray(result.source_urls_json)
    ? result.source_urls_json
    : [result.website || result.source_url].filter(Boolean),
  status: 'pending_review',
})

function SoberLivingDirectory() {
  const [filters, setFilters] = useState(defaultFilters)
  const [allListings, setAllListings] = useState([])
  const [savedLoading, setSavedLoading] = useState(true)
  const [savedError, setSavedError] = useState('')
  const [externalLoading, setExternalLoading] = useState(false)
  const [externalError, setExternalError] = useState('')
  const [externalResults, setExternalResults] = useState([])
  const [searchedOnce, setSearchedOnce] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formState, setFormState] = useState(defaultListingForm)
  const [saving, setSaving] = useState(false)
  const [savingResultId, setSavingResultId] = useState('')
  const [verifyingResultId, setVerifyingResultId] = useState('')
  const [noteDrafts, setNoteDrafts] = useState(defaultNoteState)
  const [noteOpenState, setNoteOpenState] = useState({})
  const [geoState, setGeoState] = useState({
    loading: false,
    enabled: false,
    latitude: null,
    longitude: null,
    error: '',
  })

  const loadListings = async () => {
    setSavedLoading(true)
    setSavedError('')
    try {
      const data = await soberLivingDirectoryApi.listListings({})
      setAllListings(normalizeListings(data))
    } catch (err) {
      setSavedError(err.message || 'Failed to load saved directory listings')
    } finally {
      setSavedLoading(false)
    }
  }

  useEffect(() => {
    loadListings()
  }, [])

  const filterOptions = useMemo(() => {
    const populations = Array.from(new Set(allListings.map((item) => item.population_served).filter(Boolean))).sort()
    return { populations }
  }, [allListings])

  const savedResults = useMemo(() => {
    const locationQuery = normalizeText(filters.location_query)
    const zipCode = normalizeText(filters.zip_code)
    const state = normalizeText(filters.state)
    const certification = normalizeText(filters.certification)
    const population = normalizeText(filters.population_served)
    const acceptsMat = toBooleanFilter(filters.accepts_mat)
    const acceptsInsurance = toBooleanFilter(filters.accepts_insurance)
    const radiusMiles = parseNumber(filters.radius_miles)

    return allListings
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
        return {
          ...listing,
          result_id: listing.listing_id,
          result_kind: 'saved',
          source_label: 'Saved Directory Listing',
          source_name: 'Saved Directory Listing',
          snippet: listing.notes || null,
          source_url: Array.isArray(listing.source_urls_json) ? listing.source_urls_json[0] : null,
          distance_label: formatDistance(distanceMiles),
          distanceMiles,
        }
      })
      .filter((item) => {
        const haystack = [
          item.name,
          item.operator_name,
          item.city,
          item.state,
          item.zip_code,
          item.address,
          item.neighborhood,
          item.population_served,
          item.certification_status,
          item.certification_body,
          item.website,
          item.notes,
        ]
          .map(normalizeText)
          .join(' ')

        if (locationQuery && !haystack.includes(locationQuery)) return false
        if (zipCode && item.zip_code && !normalizeText(item.zip_code).includes(zipCode)) return false
        if (state && normalizeText(item.state) !== state) return false
        if (population && normalizeText(item.population_served) !== population) return false
        if (acceptsMat !== null && Boolean(item.accepts_mat) !== acceptsMat) return false
        if (acceptsInsurance !== null && Boolean(item.accepts_insurance) !== acceptsInsurance) return false
        if (certification) {
          const certificationText = `${normalizeText(item.certification_status)} ${normalizeText(item.certification_body)}`
          if (!certificationText.includes(certification)) return false
        }
        if (!matchesFunding(item, filters.funding)) return false
        if (!matchesVerificationStatus(item, filters.verification_status)) return false
        if (geoState.enabled && radiusMiles !== null && typeof item.distanceMiles === 'number') {
          if (item.distanceMiles > radiusMiles) return false
        }
        return true
      })
  }, [allListings, filters, geoState])

  const handleFilterChange = (field, value) => {
    setFilters((current) => ({ ...current, [field]: value }))
  }

  const resetFilters = () => {
    setFilters(defaultFilters)
    setExternalResults([])
    setExternalError('')
    setSearchedOnce(false)
    setGeoState({
      loading: false,
      enabled: false,
      latitude: null,
      longitude: null,
      error: '',
    })
  }

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      const message = 'Geolocation is not available in this browser.'
      setGeoState((current) => ({ ...current, error: message }))
      toast.error(message)
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
      (error) => {
        setGeoState({
          loading: false,
          enabled: false,
          latitude: null,
          longitude: null,
          error: error.message || 'Unable to access your current location.',
        })
        toast.error(error.message || 'Unable to access your current location')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    )
  }

  const handleSearchAll = async () => {
    const scope = deriveSearchScope(filters)
    if (!scope.query && !scope.city && !scope.zip_code) {
      toast.error('Enter a city, ZIP, or location to run a live search')
      return
    }

    setExternalLoading(true)
    setExternalError('')
    setSearchedOnce(true)

    try {
      const response = await soberLivingDirectoryApi.searchLive({
        query: scope.query,
        city: scope.city,
        state: scope.state,
        zip_code: scope.zip_code,
        sources: ['ccapp', 'oxford'],
      })
      setExternalResults(
        normalizeExternalResults(response).map((result) => ({
          ...result,
          result_kind: 'external',
          website_to_open: result.website || result.source_url || null,
        }))
      )
    } catch (err) {
      setExternalError(err.message || 'External search failed')
      setExternalResults([])
    } finally {
      setExternalLoading(false)
    }
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

  const updateNoteDraft = (resultId, value) => {
    setNoteDrafts((current) => ({ ...current, [resultId]: value }))
  }

  const toggleNoteEditor = (resultId) => {
    setNoteOpenState((current) => ({ ...current, [resultId]: !current[resultId] }))
  }

  const handleSaveExternalResult = async (result, { markVerified = false } = {}) => {
    setSavingResultId(result.result_id)
    if (markVerified) {
      setVerifyingResultId(result.result_id)
    }
    try {
      const listingPayload = buildExternalListingPayload(result, noteDrafts[result.result_id])
      const created = await soberLivingDirectoryApi.createListing(listingPayload)
      if (markVerified) {
        await soberLivingDirectoryApi.verifyListing(created.listing.listing_id, {
          verification_method: 'case_manager',
          result_notes: noteDrafts[result.result_id] || `Verified from ${result.source_label}.`,
        })
      }
      toast.success(markVerified ? 'Result saved and marked verified' : 'Result saved to directory')
      setNoteDrafts((current) => {
        const next = { ...current }
        delete next[result.result_id]
        return next
      })
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Failed to save result to directory')
    } finally {
      setSavingResultId('')
      setVerifyingResultId('')
    }
  }

  const handleAddNoteToSavedListing = async (listing) => {
    const note = noteDrafts[listing.result_id]
    if (!note?.trim()) {
      toast.error('Enter a note before saving it')
      return
    }
    try {
      await soberLivingDirectoryApi.updateListing(listing.listing_id, {
        notes: [listing.notes, note.trim()].filter(Boolean).join('\n\n'),
      })
      toast.success('Note added to saved listing')
      setNoteDrafts((current) => {
        const next = { ...current }
        delete next[listing.result_id]
        return next
      })
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Failed to save note')
    }
  }

  const handleVerifySavedListing = async (listing) => {
    setVerifyingResultId(listing.result_id)
    try {
      await soberLivingDirectoryApi.verifyListing(listing.listing_id, {
        verification_method: 'case_manager',
        result_notes: noteDrafts[listing.result_id] || `Verified from directory search.`,
      })
      toast.success('Saved listing marked verified')
      setNoteDrafts((current) => {
        const next = { ...current }
        delete next[listing.result_id]
        return next
      })
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Failed to mark listing verified')
    } finally {
      setVerifyingResultId('')
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(160deg,#020617_0%,#0f172a_45%,#083344_100%)] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[2.25rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl shadow-slate-950/40">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-4xl">
              <p className="text-sm uppercase tracking-[0.32em] text-cyan-300">Referral Search</p>
              <h1 className="mt-2 text-4xl font-bold tracking-tight text-white">Search sober livings like a live research tool</h1>
              <p className="mt-3 text-base text-slate-300">
                Search the saved directory first, then pull in live CCAPP and Oxford results on the same page so the case manager can review, call, and decide what is useful.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={loadListings}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh Saved Listings
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
            <TabLink to="/sober-living-directory" active>Directory Search</TabLink>
            <TabLink to="/sober-living-directory/review">Review Queue</TabLink>
            <TabLink to="/sober-living-directory/discovery">Admin / Advanced</TabLink>
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-200">Search Filters</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Location, population, funding, and verification</h2>
              <p className="mt-2 text-sm text-slate-300">
                External results show immediately on this page. Nothing is auto-saved, and the case manager decides what belongs in the directory.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Input
              label="City or location"
              value={filters.location_query}
              onChange={(value) => handleFilterChange('location_query', value)}
              icon={Search}
              placeholder="Los Angeles, CA"
            />
            <Input
              label="ZIP code"
              value={filters.zip_code}
              onChange={(value) => handleFilterChange('zip_code', value)}
              icon={MapPin}
              placeholder="90012"
            />
            <Select label="State" value={filters.state} onChange={(value) => handleFilterChange('state', value)} options={['CA']} />
            <Input
              label="Radius miles"
              value={filters.radius_miles}
              onChange={(value) => handleFilterChange('radius_miles', value)}
              type="number"
            />
            <Select label="Population" value={filters.population_served} onChange={(value) => handleFilterChange('population_served', value)} options={filterOptions.populations} allowBlank />
            <Select label="Insurance" value={filters.accepts_insurance} onChange={(value) => handleFilterChange('accepts_insurance', value)} options={booleanOptions} allowBlank />
            <Select label="MAT" value={filters.accepts_mat} onChange={(value) => handleFilterChange('accepts_mat', value)} options={booleanOptions} allowBlank />
            <Input label="Certification" value={filters.certification} onChange={(value) => handleFilterChange('certification', value)} placeholder="CCAPP, Oxford, certified" />
            <Select label="Funding" value={filters.funding} onChange={(value) => handleFilterChange('funding', value)} options={fundingOptions} allowBlank />
            <Select label="Verification status" value={filters.verification_status} onChange={(value) => handleFilterChange('verification_status', value)} options={verificationOptions} allowBlank />
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleSearchAll}
              disabled={externalLoading}
              className="inline-flex items-center gap-2 rounded-2xl bg-fuchsia-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Globe className="h-4 w-4" />
              {externalLoading ? 'Searching...' : 'Search Directory + Web'}
            </button>
            <button
              type="button"
              onClick={handleUseMyLocation}
              disabled={geoState.loading}
              className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Compass className="h-4 w-4" />
              {geoState.loading ? 'Locating...' : 'Use My Location'}
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-200 transition hover:bg-white/10"
            >
              <Filter className="h-4 w-4" />
              Reset
            </button>
          </div>

          {geoState.enabled ? (
            <div className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              Radius filtering is using the current device location. Listings without coordinates are excluded while radius mode is active.
            </div>
          ) : null}
          {geoState.error ? (
            <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
              {geoState.error}
            </div>
          ) : null}
        </section>

        {showCreateForm ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Add a sober living listing</h2>
              <button type="button" onClick={() => setShowCreateForm(false)} className="text-sm text-slate-300 underline underline-offset-4">
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

        <SearchResultsSection
          title="Saved Directory Results"
          subtitle="Trusted and previously saved sober living options."
          results={savedResults}
          loading={savedLoading}
          error={savedError}
          emptyMessage="No saved directory listings match this search yet."
          savingResultId={savingResultId}
          verifyingResultId={verifyingResultId}
          noteDrafts={noteDrafts}
          noteOpenState={noteOpenState}
          onNoteChange={updateNoteDraft}
          onToggleNote={toggleNoteEditor}
          onSaveNote={handleAddNoteToSavedListing}
          onMarkVerified={handleVerifySavedListing}
        />

        <SearchResultsSection
          title="Live External Results"
          subtitle="Immediate CCAPP and Oxford results for the current search session."
          results={externalResults}
          loading={externalLoading}
          error={externalError}
          emptyMessage={
            searchedOnce
              ? 'No external results were returned for this search.'
              : 'Run a search to pull live external results onto this page.'
          }
          savingResultId={savingResultId}
          verifyingResultId={verifyingResultId}
          noteDrafts={noteDrafts}
          noteOpenState={noteOpenState}
          onNoteChange={updateNoteDraft}
          onToggleNote={toggleNoteEditor}
          onSaveToDirectory={handleSaveExternalResult}
        />
      </div>
    </div>
  )
}

function SearchResultsSection({
  title,
  subtitle,
  results,
  loading,
  error,
  emptyMessage,
  savingResultId,
  verifyingResultId,
  noteDrafts,
  noteOpenState,
  onNoteChange,
  onToggleNote,
  onSaveToDirectory,
  onSaveNote,
  onMarkVerified,
}) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-white/[0.05] p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">{title}</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{subtitle}</h2>
        </div>
        <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-slate-100">
          {results.length} result{results.length === 1 ? '' : 's'}
        </div>
      </div>

      {loading ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
          Loading results...
        </div>
      ) : error ? (
        <div className="mt-5 rounded-2xl border border-red-400/30 bg-red-500/10 p-6 text-center text-red-100">
          {error}
        </div>
      ) : results.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
          {emptyMessage}
        </div>
      ) : (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {results.map((result) => (
            <ResultCard
              key={result.result_id}
              result={result}
              noteValue={noteDrafts[result.result_id] || ''}
              noteOpen={Boolean(noteOpenState[result.result_id])}
              saving={savingResultId === result.result_id}
              verifying={verifyingResultId === result.result_id}
              onNoteChange={onNoteChange}
              onToggleNote={onToggleNote}
              onSaveToDirectory={onSaveToDirectory}
              onSaveNote={onSaveNote}
              onMarkVerified={onMarkVerified}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function ResultCard({
  result,
  noteValue,
  noteOpen,
  saving,
  verifying,
  onNoteChange,
  onToggleNote,
  onSaveToDirectory,
  onSaveNote,
  onMarkVerified,
}) {
  const websiteHref = result.website || result.source_url || null
  const sourceStyle = sourceStyles[result.result_kind === 'saved' ? 'saved' : result.source_key] || sourceStyles.external

  return (
    <article className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl shadow-slate-950/20">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${sourceStyle}`}>
              {result.source_label}
            </span>
            {result.certification_body ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs text-cyan-100">
                <ShieldCheck className="h-3.5 w-3.5" />
                {result.certification_body}
              </span>
            ) : null}
          </div>
          <h3 className="text-xl font-semibold text-white">{result.name}</h3>
          <div className="flex flex-wrap gap-4 text-sm text-slate-300">
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4 text-cyan-300" />
              {[result.city, result.state].filter(Boolean).join(', ') || 'Location unavailable'}
            </span>
            <span className="inline-flex items-center gap-1">
              <Phone className="h-4 w-4 text-cyan-300" />
              {result.phone || 'No phone listed'}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <InfoPanel label="Website" value={websiteHref ? websiteHref.replace(/^https?:\/\//, '').replace(/\/$/, '') : 'Not listed'} />
        <InfoPanel label="Source" value={result.source_name || result.source_label || 'External Web Result'} />
        <InfoPanel label="Population" value={result.population_served || 'Not specified'} />
        <InfoPanel label="Verification" value={result.last_verified_date ? `Verified ${new Date(result.last_verified_date).toLocaleDateString()}` : humanizeToken(result.verification_method || 'not_verified', 'Not verified')} />
      </div>

      {result.snippet || result.notes ? (
        <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/35 p-4 text-sm text-slate-200">
          {result.snippet || result.notes}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-3">
        {websiteHref ? (
          <a
            href={websiteHref}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
          >
            <ExternalLink className="h-4 w-4" />
            Open Website
          </a>
        ) : null}
        {result.phone ? (
          <a
            href={`tel:${result.phone}`}
            className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm font-medium text-emerald-100 transition hover:bg-emerald-500/20"
          >
            <Phone className="h-4 w-4" />
            Call
          </a>
        ) : null}

        {result.result_kind === 'saved' ? (
          <button
            type="button"
            onClick={() => onMarkVerified?.(result)}
            disabled={verifying}
            className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <ShieldCheck className="h-4 w-4" />
            {verifying ? 'Verifying...' : 'Mark Verified'}
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => onSaveToDirectory?.(result, { markVerified: false })}
              disabled={saving || verifying}
              className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Save to Directory'}
            </button>
            <button
              type="button"
              onClick={() => onSaveToDirectory?.(result, { markVerified: true })}
              disabled={saving || verifying}
              className="inline-flex items-center gap-2 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <ShieldCheck className="h-4 w-4" />
              {verifying ? 'Saving + Verifying...' : 'Mark Verified'}
            </button>
          </>
        )}
        <button
          type="button"
          onClick={() => onToggleNote(result.result_id)}
          className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
        >
          {noteOpen ? 'Hide Note' : 'Add Note'}
        </button>
      </div>

      {noteOpen ? (
      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/35 p-4">
        <label className="block">
          <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Add Note</span>
          <textarea
            rows={3}
            value={noteValue}
            onChange={(event) => onNoteChange(result.result_id, event.target.value)}
            placeholder="Case manager note, call outcome, rent detail, MAT detail, or funding note"
            className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
          />
        </label>
        {result.result_kind === 'saved' ? (
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => onSaveNote?.(result)}
              className="rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
            >
              Save Note
            </button>
          </div>
        ) : null}
      </div>
      ) : null}
    </article>
  )
}

function InfoPanel({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className="mt-2 text-sm text-white">{value}</p>
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

export default SoberLivingDirectory
