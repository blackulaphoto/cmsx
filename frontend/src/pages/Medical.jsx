import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Building2,
  CalendarClock,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Filter,
  HeartPulse,
  MapPin,
  Phone,
  PlusCircle,
  Search,
  Shield,
  Stethoscope,
  Syringe,
  User,
} from 'lucide-react'
import toast from 'react-hot-toast'

import ClientSelector from '../components/ClientSelector'
import LocationSelector from '../components/LocationSelector'
import { apiFetch } from '../api/config'
import {
  clientLocation,
  fetchClientWithOperationalContext,
  formatNeedSummary,
  getIntakeContext,
  getNeedKeys,
} from '../utils/clientOperationalContext'

const DEFAULT_PAGE_SIZE = 12

const MEDICAL_PATHS = [
  {
    key: 'medi-cal',
    label: 'Medi-Cal Providers',
    description: 'Doctors, clinics, and verified provider records accepting Medi-Cal.',
    icon: Stethoscope,
    gradient: 'from-cyan-500 to-blue-500',
    sourceLabel: 'Medi-Cal dataset',
  },
  {
    key: 'private-insurance',
    label: 'Private Insurance',
    description: 'Residential, outpatient, and specialty programs that accept private insurance.',
    icon: Shield,
    gradient: 'from-emerald-500 to-teal-500',
    sourceLabel: 'Treatment directory',
  },
  {
    key: 'dental-urgent',
    label: 'Dental & Urgent Care',
    description: 'Urgent dental care and fast-access clinic style resources.',
    icon: Activity,
    gradient: 'from-amber-500 to-orange-500',
    sourceLabel: 'Dental resources',
  },
  {
    key: 'suboxone-mat',
    label: 'Suboxone & MAT',
    description: 'Medication-assisted treatment and recovery support options.',
    icon: Syringe,
    gradient: 'from-pink-500 to-rose-500',
    sourceLabel: 'MAT directory',
  },
  {
    key: 'treatment-centers',
    label: 'Treatment Centers',
    description: 'Residential, outpatient, detox, and higher-acuity treatment programs.',
    icon: HeartPulse,
    gradient: 'from-purple-500 to-indigo-500',
    sourceLabel: 'Treatment directory',
  },
]

const APPOINTMENT_STATUS_OPTIONS = ['scheduled', 'completed', 'cancelled', 'no_show']
const REFERRAL_STATUS_OPTIONS = ['Identified', 'Called', 'Scheduled', 'Completed']
const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'name', label: 'Name' },
  { value: 'distance', label: 'Distance' },
]
const INSURANCE_FILTER_OPTIONS = [
  { value: 'all', label: 'All coverage' },
  { value: 'medi-cal', label: 'Medi-Cal' },
  { value: 'private-insurance', label: 'Private Insurance' },
]

const GENERIC_PROVIDER_LABELS = new Set([
  'PHYSICIAN',
  'PRACTITIONER',
  'NONE REPORTED',
  'PATHOLOGIST',
  'THERAPIST',
  'ASSISTANT',
  'REGISTERED',
  'GROUP',
  'MEDICINE PHYSICIAN',
  'DISEASE PHYSICIAN',
])

const GENERIC_PROVIDER_PATTERNS = [
  /.+\s+PHYSICIAN$/,
  /.+\s+PRACTITIONER$/,
  /^[A-Z]?\d{4,}(?:\s+GROUP)?$/,
]

// Categories whose datasets are small enough to load without backend city filtering.
// City matching for these is handled entirely on the frontend with LA-area alias expansion.
const FRONTEND_CITY_FILTER_CATEGORIES = new Set([
  'treatment-centers',
  'private-insurance',
  'suboxone-mat',
  'dental-urgent',
])

// LA neighborhoods and adjacent cities that should match a "Los Angeles" city query.
const LA_AREA_NEIGHBORHOODS = new Set([
  'los angeles', 'la',
  'hollywood', 'north hollywood', 'west hollywood', 'east hollywood',
  'van nuys', 'sherman oaks', 'encino', 'studio city', 'tarzana',
  'woodland hills', 'canoga park', 'winnetka', 'reseda', 'northridge',
  'chatsworth', 'granada hills', 'mission hills', 'sylmar',
  'westwood', 'brentwood', 'pacific palisades', 'bel air',
  'beverly hills', 'culver city', 'santa monica', 'venice', 'mar vista',
  'west los angeles', 'downtown los angeles',
  'silver lake', 'silverlake', 'echo park', 'los feliz', 'atwater village',
  'koreatown', 'leimert park', 'crenshaw', 'mid-city',
  'boyle heights', 'lincoln heights', 'highland park', 'eagle rock',
  'el sereno', 'glassell park', 'cypress park', 'mount washington',
  'pasadena', 'glendale', 'burbank', 'alhambra', 'monterey park',
  'el monte', 'azusa', 'monrovia', 'arcadia',
  'long beach', 'compton', 'inglewood', 'hawthorne', 'gardena', 'torrance',
  'carson', 'watts', 'south gate', 'lynwood', 'huntington park',
  'east los angeles', 'montebello', 'commerce', 'bell', 'maywood',
  'manhattan beach', 'redondo beach', 'hermosa beach', 'el segundo',
])

// Search terms the user can type that are treated as "Los Angeles area" queries.
const LA_QUERY_TERMS = new Set([
  'los angeles', 'la', 'l.a.', 'los angeles ca', 'la ca', 'los angeles california',
])

function normalizeLocationQuery(value) {
  return String(value || '').toLowerCase().replace(/[,.]/g, ' ').replace(/\s+/g, ' ').trim()
}

function isLaAreaQuery(filterValue) {
  return LA_QUERY_TERMS.has(normalizeLocationQuery(filterValue))
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim()
}

function normalizedUpper(value) {
  return normalizeText(value).toUpperCase()
}

function isGenericProviderLabel(value) {
  const normalized = normalizedUpper(value)
  if (!normalized) return true
  if (GENERIC_PROVIDER_LABELS.has(normalized)) return true
  return GENERIC_PROVIDER_PATTERNS.some((pattern) => pattern.test(normalized))
}

function uniqueCleanList(values = []) {
  const seen = new Set()
  return values
    .map((value) => normalizeText(value))
    .filter((value) => {
      if (!value) return false
      const key = value.toUpperCase()
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
}

function buildProviderDisplayName(provider) {
  const primaryName = normalizeText(provider.provider_name)
  if (primaryName && !isGenericProviderLabel(primaryName)) {
    return primaryName
  }

  const extra = provider.extra || {}
  const fallbackCandidates = uniqueCleanList([
    extra.organization_name,
    extra.facility_name,
    ...(extra.medical_groups || []),
    ...(extra.hospital_affiliations || []),
    ...(extra.networks || []),
  ])
  const fallbackName = fallbackCandidates.find((candidate) => !isGenericProviderLabel(candidate))
  if (fallbackName) {
    return fallbackName
  }

  return primaryName || 'Provider record'
}

function getProviderSourceLabel(provider) {
  const explicitLabel = normalizeText(provider.extra?.source_label || provider.extra?.source_name)
  if (explicitLabel) return explicitLabel
  return MEDICAL_PATHS.find((path) => path.key === provider.category)?.sourceLabel || 'Provider directory'
}

function getInsuranceBadges(provider) {
  const description = normalizedUpper(provider.description)
  const badges = []

  if (provider.category === 'medi-cal' || description.includes('MEDI-CAL') || provider.extra?.accepts_medi_cal) {
    badges.push('Medi-Cal')
  }
  if (
    provider.category === 'private-insurance' ||
    description.includes('PRIVATE INSURANCE') ||
    provider.extra?.accepts_private_insurance
  ) {
    badges.push('Private Insurance')
  }
  if (provider.category === 'suboxone-mat') {
    badges.push('MAT')
  }

  return uniqueCleanList(badges)
}

function getProviderChips(provider) {
  const extra = provider.extra || {}
  return uniqueCleanList([
    ...(extra.specialties || []),
    ...(extra.services || []),
    extra.serves_population,
  ]).slice(0, 6)
}

function getProviderVerification(provider) {
  const extra = provider.extra || {}
  if (extra.verified) return 'Verified'
  return normalizeText(extra.verification_label || extra.verification_method)
}

function getProviderLogoUrl(provider) {
  return normalizeText(provider.extra?.logo_url || provider.extra?.image_url || provider.logo_url)
}

function matchesInsuranceFilter(provider, filterValue) {
  if (filterValue === 'all') return true
  const badges = getInsuranceBadges(provider).map((badge) => badge.toLowerCase())
  return badges.includes(filterValue)
}

function matchesSpecialtyFilter(provider, filterValue) {
  const normalizedFilter = normalizedUpper(filterValue)
  if (!normalizedFilter) return true

  const haystacks = [
    provider.provider_type,
    provider.description,
    ...(provider.extra?.specialties || []),
    ...(provider.extra?.services || []),
  ].map((value) => normalizedUpper(value))

  return haystacks.some((haystack) => haystack.includes(normalizedFilter))
}

function matchesCityFilter(provider, filterValue) {
  const normalizedFilter = normalizedUpper(filterValue)
  if (!normalizedFilter) return true

  const haystack = normalizedUpper([provider.city, provider.address].filter(Boolean).join(' '))
  if (haystack.includes(normalizedFilter)) return true

  // When the query is a Los Angeles-area term, also match known LA neighborhoods and
  // adjacent cities so records stored under "Hollywood", "Van Nuys", etc. are included.
  if (isLaAreaQuery(filterValue)) {
    const providerCity = normalizeLocationQuery(provider.city)
    if (LA_AREA_NEIGHBORHOODS.has(providerCity)) return true
    const providerAddr = normalizeLocationQuery(provider.address)
    return [...LA_AREA_NEIGHBORHOODS].some((alias) => providerAddr.includes(alias))
  }

  return false
}

function sortProviders(providers, sortBy) {
  const nextProviders = [...providers]
  if (sortBy === 'name') {
    nextProviders.sort((left, right) => left.displayName.localeCompare(right.displayName))
    return nextProviders
  }
  if (sortBy === 'distance') {
    nextProviders.sort((left, right) => {
      const leftDistance = Number(left.extra?.distance_miles)
      const rightDistance = Number(right.extra?.distance_miles)
      const safeLeft = Number.isFinite(leftDistance) ? leftDistance : Number.MAX_SAFE_INTEGER
      const safeRight = Number.isFinite(rightDistance) ? rightDistance : Number.MAX_SAFE_INTEGER
      if (safeLeft !== safeRight) return safeLeft - safeRight
      return left.displayName.localeCompare(right.displayName)
    })
    return nextProviders
  }
  return nextProviders
}

function Medical() {
  const [searchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [activePath, setActivePath] = useState('medi-cal')
  const [city, setCity] = useState('Los Angeles')
  const [search, setSearch] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [providers, setProviders] = useState([])
  const [providerTotalCount, setProviderTotalCount] = useState(0)
  const [providersLoading, setProvidersLoading] = useState(false)
  const [providersError, setProvidersError] = useState('')
  const [sortBy, setSortBy] = useState('relevance')
  const [insuranceFilter, setInsuranceFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [appointments, setAppointments] = useState([])
  const [referrals, setReferrals] = useState([])
  const [appointmentsLoading, setAppointmentsLoading] = useState(false)
  const [referralsLoading, setReferralsLoading] = useState(false)
  const [appointmentDraft, setAppointmentDraft] = useState(null)
  const [appointmentForm, setAppointmentForm] = useState({
    appointment_date: '',
    appointment_time: '09:00',
    appointment_type: 'Medical Appointment',
    notes: '',
    create_reminder: true,
  })

  useEffect(() => {
    const clientId = searchParams.get('client')
    if (!clientId) return

    const loadClient = async () => {
      try {
        const client = await fetchClientWithOperationalContext(apiFetch, clientId)
        setSelectedClient(client)
      } catch (error) {
        console.error('Medical client preload failed:', error)
      }
    }

    loadClient()
  }, [searchParams])

  useEffect(() => {
    loadProviders(activePath, { notifyEmpty: false })
  }, [activePath])

  useEffect(() => {
    if (selectedClient?.client_id) {
      loadAppointments(selectedClient.client_id)
      loadReferrals(selectedClient.client_id)
    } else {
      setAppointments([])
      setReferrals([])
    }
  }, [selectedClient?.client_id])

  useEffect(() => {
    if (!selectedClient?.client_id) return

    const intake = getIntakeContext(selectedClient)
    const needKeys = getNeedKeys(selectedClient, 'medical')
    const nextLocation = clientLocation(selectedClient, city)
    if (nextLocation && city === 'Los Angeles') {
      setCity(nextLocation)
    }

    if (needKeys.has('dental') && activePath === 'medi-cal') {
      setActivePath('dental-urgent')
    } else if (needKeys.has('behavioral_health') && activePath === 'medi-cal') {
      setActivePath('treatment-centers')
    }

    const needSummary = formatNeedSummary(selectedClient, 'medical')
    const notes = [
      intake.medical_conditions && `Medical conditions: ${intake.medical_conditions}`,
      intake.special_needs && `Special needs: ${intake.special_needs}`,
      needSummary && `Open needs: ${needSummary}`,
    ].filter(Boolean).join('\n')
    if (notes) {
      setAppointmentForm((prev) => ({
        ...prev,
        notes: prev.notes || notes,
      }))
    }
  }, [selectedClient?.client_id])

  const loadProviders = async (pathKey = activePath, options = {}) => {
    const { notifyEmpty = true } = options
    setProvidersLoading(true)
    setProvidersError('')

    try {
      // For small-dataset categories the full record set is fetched without a city
      // constraint so the frontend LA-area alias matcher can evaluate every record.
      // Medi-Cal has a large dataset and still needs backend city pre-filtering.
      const backendCity = FRONTEND_CITY_FILTER_CATEGORIES.has(pathKey) ? '' : (city || '')
      const params = new URLSearchParams({
        category: pathKey,
        city: backendCity,
        search: search || '',
        specialty: specialty || '',
        limit: '100',
      })

      const response = await apiFetch(`/api/medical/providers?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load providers')
      }

      const data = await response.json()
      const nextProviders = data.providers || []
      setProviders(nextProviders)
      setProviderTotalCount(data.total_count || nextProviders.length)
      setCurrentPage(1)

      if (notifyEmpty && nextProviders.length === 0) {
        toast('No providers matched those filters')
      }
    } catch (error) {
      console.error('Medical provider load error:', error)
      toast.error('Failed to load medical providers')
      setProviders([])
      setProviderTotalCount(0)
      setProvidersError('We could not load provider results right now.')
    } finally {
      setProvidersLoading(false)
    }
  }

  const loadAppointments = async (clientId) => {
    setAppointmentsLoading(true)
    try {
      const params = new URLSearchParams({ client_id: clientId })
      const response = await apiFetch(`/api/medical/appointments?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load appointments')
      }
      const data = await response.json()
      setAppointments(data.appointments || [])
    } catch (error) {
      console.error('Medical appointments load error:', error)
      toast.error('Failed to load medical appointments')
      setAppointments([])
    } finally {
      setAppointmentsLoading(false)
    }
  }

  const loadReferrals = async (clientId) => {
    setReferralsLoading(true)
    try {
      const params = new URLSearchParams({ client_id: clientId })
      const response = await apiFetch(`/api/medical/referrals?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load referrals')
      }
      const data = await response.json()
      setReferrals(data.referrals || [])
    } catch (error) {
      console.error('Medical referrals load error:', error)
      toast.error('Failed to load medical referrals')
      setReferrals([])
    } finally {
      setReferralsLoading(false)
    }
  }

  const saveReferral = async (provider) => {
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }

    try {
      const response = await apiFetch('/api/medical/referrals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          provider_name: provider.displayName,
          provider_category: provider.category,
          provider_type: provider.provider_type,
          address: provider.address,
          phone: provider.phone,
          website: provider.website,
          city: provider.city,
          insurance_type: getInsuranceBadges(provider).join(', '),
          notes: provider.description,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to save referral')
      }

      toast.success(`Saved referral for ${selectedClient.first_name}`)
      loadReferrals(selectedClient.client_id)
    } catch (error) {
      console.error('Save medical referral error:', error)
      toast.error('Failed to save referral')
    }
  }

  const scheduleAppointment = async () => {
    if (!selectedClient?.client_id || !appointmentDraft) {
      toast.error('Select a client and provider first')
      return
    }
    if (!appointmentForm.appointment_date || !appointmentForm.appointment_time) {
      toast.error('Appointment date and time are required')
      return
    }

    try {
      const response = await apiFetch('/api/medical/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          case_manager_id: selectedClient.case_manager_id || 'default_cm',
          provider_name: appointmentDraft.displayName,
          location: appointmentDraft.address,
          appointment_date: appointmentForm.appointment_date,
          appointment_time: appointmentForm.appointment_time,
          appointment_type: appointmentForm.appointment_type,
          notes: appointmentForm.notes,
          create_reminder: appointmentForm.create_reminder,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to schedule appointment')
      }

      toast.success('Medical appointment scheduled')
      setAppointmentDraft(null)
      setAppointmentForm({
        appointment_date: '',
        appointment_time: '09:00',
        appointment_type: 'Medical Appointment',
        notes: '',
        create_reminder: true,
      })
      loadAppointments(selectedClient.client_id)
    } catch (error) {
      console.error('Schedule medical appointment error:', error)
      toast.error('Failed to schedule appointment')
    }
  }

  const updateAppointmentStatus = async (appointmentId, status) => {
    try {
      const response = await apiFetch(`/api/medical/appointments/${appointmentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!response.ok) {
        throw new Error('Failed to update appointment')
      }
      if (selectedClient?.client_id) {
        loadAppointments(selectedClient.client_id)
      }
      toast.success('Appointment updated')
    } catch (error) {
      console.error('Update appointment status error:', error)
      toast.error('Failed to update appointment')
    }
  }

  const updateReferralStatus = async (referralId, referralStatus) => {
    try {
      const response = await apiFetch(`/api/medical/referrals/${referralId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referral_status: referralStatus }),
      })
      if (!response.ok) {
        throw new Error('Failed to update referral')
      }
      if (selectedClient?.client_id) {
        loadReferrals(selectedClient.client_id)
      }
      toast.success('Referral updated')
    } catch (error) {
      console.error('Update referral status error:', error)
      toast.error('Failed to update referral')
    }
  }

  const activePathMeta = MEDICAL_PATHS.find((path) => path.key === activePath)
  const preparedProviders = providers.map((provider, index) => ({
    ...provider,
    displayName: buildProviderDisplayName(provider),
    insuranceBadges: getInsuranceBadges(provider),
    chips: getProviderChips(provider),
    verificationLabel: getProviderVerification(provider),
    sourceLabel: getProviderSourceLabel(provider),
    logoUrl: getProviderLogoUrl(provider),
    originalIndex: index,
  }))

  const filteredProviders = sortProviders(
    preparedProviders.filter((provider) => (
      matchesInsuranceFilter(provider, insuranceFilter) &&
      matchesCityFilter(provider, city) &&
      matchesSpecialtyFilter(provider, specialty)
    )),
    sortBy,
  )

  const totalPages = Math.max(1, Math.ceil(filteredProviders.length / DEFAULT_PAGE_SIZE))
  const safeCurrentPage = Math.min(currentPage, totalPages)
  const pageStart = (safeCurrentPage - 1) * DEFAULT_PAGE_SIZE
  const paginatedProviders = filteredProviders.slice(pageStart, pageStart + DEFAULT_PAGE_SIZE)

  const resultStart = filteredProviders.length === 0 ? 0 : pageStart + 1
  const resultEnd = Math.min(pageStart + DEFAULT_PAGE_SIZE, filteredProviders.length)

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(135deg,_#120f26_0%,_#2c1654_55%,_#140f2f_100%)] animate-fade-in">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-24 right-0 h-72 w-72 rounded-full bg-cyan-400/15 blur-3xl" />
        <div className="absolute top-1/3 -left-24 h-72 w-72 rounded-full bg-fuchsia-500/12 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>

      <div className="relative z-10">
        <div className="border-b border-white/10 bg-black/20 backdrop-blur-xl">
          <div className="mx-auto max-w-7xl px-3 py-5 sm:px-6 sm:py-8">
            <div className="flex items-center gap-4">
              <div className="rounded-2xl bg-gradient-to-r from-teal-500 to-cyan-500 p-3 shadow-lg shadow-cyan-500/20">
                <Stethoscope className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-4xl font-bold text-transparent">
                  Medical Access
                </h1>
                <p className="text-lg text-gray-300">
                  Search live provider records first, save referrals, and book appointments from one directory.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-3 py-5 sm:px-6 sm:py-8">
          <section className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
            <h2 className="mb-4 flex items-center gap-3 text-xl font-semibold text-white">
              <div className="rounded-lg bg-gradient-to-r from-indigo-500 to-purple-500 p-2">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector
              onClientSelect={setSelectedClient}
              includeOperationalContext
              placeholder="Select a client to coordinate healthcare for..."
              className="relative z-30 max-w-md"
            />
            {selectedClient ? (
              <div className="mt-4 rounded-2xl border border-cyan-400/30 bg-gradient-to-r from-cyan-500/15 to-blue-500/15 p-4 text-sm text-cyan-100">
                Coordinating care for <span className="font-semibold text-white">{selectedClient.first_name} {selectedClient.last_name}</span>
              </div>
            ) : null}
          </section>

          <section className="rounded-3xl border border-white/15 bg-white/8 p-6 backdrop-blur-xl shadow-2xl shadow-purple-900/20">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-lg bg-gradient-to-r from-teal-500 to-cyan-500 p-2">
                <HeartPulse className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Healthcare Paths</h2>
                <p className="text-sm text-gray-300">Keep the existing category tabs, but treat the results below like a real directory.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
              {MEDICAL_PATHS.map((path) => {
                const Icon = path.icon
                const active = activePath === path.key
                return (
                  <button
                    key={path.key}
                    type="button"
                    onClick={() => setActivePath(path.key)}
                    className={`rounded-2xl border p-5 text-left transition-all duration-300 ${
                      active
                        ? `bg-gradient-to-r ${path.gradient} border-white/40 text-white shadow-xl`
                        : 'border-white/10 bg-white/5 text-gray-200 hover:border-white/20 hover:bg-white/10'
                    }`}
                  >
                    <div className={`mb-4 inline-flex rounded-xl p-3 ${active ? 'bg-white/20' : 'bg-white/10'}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mb-2 font-semibold">{path.label}</h3>
                    <p className={`text-sm ${active ? 'text-white/85' : 'text-gray-400'}`}>{path.description}</p>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="rounded-[28px] border border-white/15 bg-[linear-gradient(180deg,_rgba(255,255,255,0.08),_rgba(255,255,255,0.03))] p-6 backdrop-blur-xl shadow-2xl shadow-slate-950/30">
            <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 p-2">
                  <Search className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">{activePathMeta?.label}</h2>
                  <p className="text-gray-300">{activePathMeta?.description}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">Loaded</div>
                  <div className="mt-1 text-lg font-semibold text-white">{providerTotalCount}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">Matching</div>
                  <div className="mt-1 text-lg font-semibold text-white">{filteredProviders.length}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">Pages</div>
                  <div className="mt-1 text-lg font-semibold text-white">{totalPages}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">Per page</div>
                  <div className="mt-1 text-lg font-semibold text-white">{DEFAULT_PAGE_SIZE}</div>
                </div>
              </div>
            </div>

            <div className="mb-6 rounded-3xl border border-white/10 bg-black/20 p-4 sm:p-5">
              <div className="mb-4 flex items-center gap-2 text-sm font-medium text-cyan-100">
                <Filter className="h-4 w-4" />
                Sort and filter directory results
              </div>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-6">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">Category</label>
                  <select
                    value={activePath}
                    onChange={(event) => setActivePath(event.target.value)}
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    {MEDICAL_PATHS.map((path) => (
                      <option key={path.key} value={path.key} className="bg-slate-900 text-white">
                        {path.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">City</label>
                  <LocationSelector
                    value={city}
                    onChange={(value) => {
                      setCity(value)
                      setCurrentPage(1)
                    }}
                    placeholder="Search city or state"
                    className="w-full"
                    inputClassName="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white placeholder-gray-400 transition hover:bg-white/15 focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">Search</label>
                  <input
                    type="text"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Provider name or keyword"
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white placeholder-gray-400 outline-none transition focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">Specialty</label>
                  <input
                    type="text"
                    value={specialty}
                    onChange={(event) => setSpecialty(event.target.value)}
                    placeholder="Psychiatry, detox, family medicine..."
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white placeholder-gray-400 outline-none transition focus:border-cyan-400"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">Insurance</label>
                  <select
                    value={insuranceFilter}
                    onChange={(event) => {
                      setInsuranceFilter(event.target.value)
                      setCurrentPage(1)
                    }}
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    {INSURANCE_FILTER_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} className="bg-slate-900 text-white">
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-300">Sort</label>
                  <select
                    value={sortBy}
                    onChange={(event) => {
                      setSortBy(event.target.value)
                      setCurrentPage(1)
                    }}
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    {SORT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} className="bg-slate-900 text-white">
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-gray-300">
                  {filteredProviders.length === 0
                    ? '0 results'
                    : `${filteredProviders.length} results`}
                  {filteredProviders.length > 0 ? ` · Showing ${resultStart}-${resultEnd}` : ''}
                  {` · Page ${safeCurrentPage} of ${totalPages}`}
                </div>

                <button
                  type="button"
                  onClick={() => loadProviders(activePath, { notifyEmpty: true })}
                  disabled={providersLoading}
                  className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-3 font-medium text-white transition hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50"
                >
                  {providersLoading ? 'Loading...' : 'Search Providers'}
                </button>
              </div>
            </div>

            {providersLoading ? (
              <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-16 text-center">
                <div className="mx-auto mb-4 h-12 w-12 rounded-full border-2 border-cyan-400/40 border-t-cyan-300 animate-spin" />
                <h3 className="text-xl font-semibold text-white">Loading provider directory</h3>
                <p className="mt-2 text-gray-300">Pulling provider records for this path and filter set.</p>
              </div>
            ) : providersError ? (
              <div className="rounded-3xl border border-rose-400/30 bg-rose-500/10 px-6 py-16 text-center">
                <Building2 className="mx-auto mb-4 h-12 w-12 text-rose-200" />
                <h3 className="text-xl font-semibold text-white">Provider search is unavailable</h3>
                <p className="mt-2 text-rose-100">{providersError}</p>
                <button
                  type="button"
                  onClick={() => loadProviders(activePath, { notifyEmpty: false })}
                  className="mt-6 rounded-2xl border border-white/20 bg-white/10 px-5 py-3 font-medium text-white transition hover:bg-white/15"
                >
                  Retry search
                </button>
              </div>
            ) : filteredProviders.length === 0 ? (
              <div className="rounded-3xl border border-white/10 bg-white/5 px-6 py-16 text-center">
                <Building2 className="mx-auto mb-4 h-12 w-12 text-gray-400" />
                <h3 className="text-xl font-semibold text-white">No providers matched this directory view</h3>
                <p className="mt-2 text-gray-300">Try another city, specialty, insurance filter, or healthcare path.</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                  {paginatedProviders.map((provider) => {
                    const Icon = MEDICAL_PATHS.find((path) => path.key === provider.category)?.icon || Building2
                    const websiteLabel = provider.website ? 'Visit Website' : ''

                    return (
                      <article
                        key={provider.provider_id}
                        data-testid={`provider-card-${provider.provider_id}`}
                        className="group overflow-hidden rounded-[28px] border border-white/15 bg-[linear-gradient(180deg,_rgba(255,255,255,0.09),_rgba(255,255,255,0.04))] p-5 shadow-xl shadow-slate-950/20 transition hover:-translate-y-1 hover:border-cyan-300/30"
                      >
                        <div className="mb-5 flex items-start gap-4">
                          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-white/15 bg-black/25">
                            {provider.logoUrl ? (
                              <img
                                src={provider.logoUrl}
                                alt={`${provider.displayName} logo`}
                                className="h-full w-full rounded-2xl object-cover"
                              />
                            ) : (
                              <Icon
                                data-testid={`provider-fallback-icon-${provider.provider_id}`}
                                className="h-7 w-7 text-cyan-200"
                              />
                            )}
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <h3 className="text-xl font-semibold text-white">{provider.displayName}</h3>
                                <p className="mt-1 text-sm text-cyan-100">{provider.provider_type || activePathMeta?.label}</p>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                <span className="rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-100">
                                  {provider.sourceLabel}
                                </span>
                                {provider.verificationLabel ? (
                                  <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-100">
                                    {provider.verificationLabel}
                                  </span>
                                ) : null}
                              </div>
                            </div>

                            <div className="mt-3 flex flex-wrap gap-2">
                              <span className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-medium text-gray-100">
                                {MEDICAL_PATHS.find((path) => path.key === provider.category)?.label || 'Provider'}
                              </span>
                              {provider.insuranceBadges.map((badge) => (
                                <span
                                  key={`${provider.provider_id}-${badge}`}
                                  className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-100"
                                >
                                  {badge}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        <p className="mb-4 text-sm leading-6 text-gray-200">{provider.description || 'Provider record available.'}</p>

                        {provider.chips.length > 0 ? (
                          <div className="mb-4 flex flex-wrap gap-2">
                            {provider.chips.map((chip) => (
                              <span
                                key={`${provider.provider_id}-${chip}`}
                                className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-gray-200"
                              >
                                {chip}
                              </span>
                            ))}
                          </div>
                        ) : null}

                        <div className="mb-5 space-y-3 text-sm text-gray-200">
                          {provider.address ? (
                            <div className="flex items-start gap-3">
                              <MapPin className="mt-0.5 h-4 w-4 text-cyan-300" />
                              <span>{provider.address}</span>
                            </div>
                          ) : null}
                          {provider.phone ? (
                            <div className="flex items-center gap-3">
                              <Phone className="h-4 w-4 text-blue-300" />
                              <span>{provider.phone}</span>
                            </div>
                          ) : null}
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <button
                            type="button"
                            onClick={() => saveReferral(provider)}
                            className="min-w-[150px] flex-1 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-3 font-medium text-white transition hover:from-emerald-500 hover:to-teal-500"
                          >
                            Save Referral
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (!selectedClient?.client_id) {
                                toast.error('Please select a client first')
                                return
                              }
                              setAppointmentDraft(provider)
                              setAppointmentForm((prev) => ({
                                ...prev,
                                appointment_type: `Medical - ${provider.provider_type || activePathMeta?.label}`,
                              }))
                            }}
                            className="min-w-[150px] flex-1 rounded-2xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-3 font-medium text-white transition hover:from-cyan-500 hover:to-blue-500"
                          >
                            Book Appointment
                          </button>
                          {provider.website ? (
                            <button
                              type="button"
                              onClick={() => window.open(provider.website, '_blank', 'noopener,noreferrer')}
                              className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-gray-100 transition hover:bg-white/15"
                            >
                              <span className="inline-flex items-center gap-2">
                                {websiteLabel}
                                <ExternalLink className="h-4 w-4" />
                              </span>
                            </button>
                          ) : null}
                        </div>
                      </article>
                    )
                  })}
                </div>

                <div className="mt-6 flex flex-col gap-4 rounded-3xl border border-white/10 bg-black/20 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-sm text-gray-300">
                    {`Showing ${resultStart}-${resultEnd} of ${filteredProviders.length} results`}
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                      disabled={safeCurrentPage === 1}
                      className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      Previous
                    </button>
                    <div className="rounded-2xl border border-white/10 bg-white/10 px-4 py-2 text-sm text-white">
                      {`Page ${safeCurrentPage} of ${totalPages}`}
                    </div>
                    <button
                      type="button"
                      onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                      disabled={safeCurrentPage >= totalPages}
                      className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      Next
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>

          <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
            <section className="rounded-3xl border border-white/15 bg-white/8 p-6 backdrop-blur-xl shadow-2xl shadow-purple-900/20 xl:col-span-1">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-lg bg-gradient-to-r from-emerald-500 to-green-500 p-2">
                  <CalendarClock className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">Book Appointment</h2>
                  <p className="text-sm text-gray-400">Create a tracked medical appointment and reminder.</p>
                </div>
              </div>

              {appointmentDraft ? (
                <div className="space-y-4">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="mb-1 text-sm text-gray-400">Provider</p>
                    <p className="font-semibold text-white">{appointmentDraft.displayName}</p>
                    <p className="mt-1 text-xs text-cyan-200">{appointmentDraft.provider_type}</p>
                  </div>

                  <div>
                    <label htmlFor="medical-appointment-date" className="mb-2 block text-sm font-medium text-gray-300">Date</label>
                    <input
                      id="medical-appointment-date"
                      type="date"
                      value={appointmentForm.appointment_date}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_date: event.target.value }))}
                      className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white"
                    />
                  </div>

                  <div>
                    <label htmlFor="medical-appointment-time" className="mb-2 block text-sm font-medium text-gray-300">Time</label>
                    <input
                      id="medical-appointment-time"
                      type="time"
                      value={appointmentForm.appointment_time}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_time: event.target.value }))}
                      className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white"
                    />
                  </div>

                  <div>
                    <label htmlFor="medical-appointment-type" className="mb-2 block text-sm font-medium text-gray-300">Appointment Type</label>
                    <input
                      id="medical-appointment-type"
                      type="text"
                      value={appointmentForm.appointment_type}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_type: event.target.value }))}
                      className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white"
                    />
                  </div>

                  <div>
                    <label htmlFor="medical-appointment-notes" className="mb-2 block text-sm font-medium text-gray-300">Notes</label>
                    <textarea
                      id="medical-appointment-notes"
                      rows={4}
                      value={appointmentForm.notes}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, notes: event.target.value }))}
                      placeholder="Insurance instructions, what to bring, client concerns..."
                      className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-white placeholder-gray-400"
                    />
                  </div>

                  <label className="flex items-center gap-3 text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={appointmentForm.create_reminder}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, create_reminder: event.target.checked }))}
                      className="h-4 w-4 rounded border-white/20 bg-white/10"
                    />
                    Create reminder the day before
                  </label>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={scheduleAppointment}
                      className="flex-1 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-3 font-medium text-white transition hover:from-emerald-500 hover:to-teal-500"
                    >
                      Schedule
                    </button>
                    <button
                      type="button"
                      onClick={() => setAppointmentDraft(null)}
                      className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-gray-200 transition hover:bg-white/15"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              ) : (
                <div className="rounded-3xl border border-white/10 bg-white/5 py-12 text-center">
                  <PlusCircle className="mx-auto mb-4 h-10 w-10 text-gray-400" />
                  <p className="mb-2 font-medium text-white">Pick a provider first</p>
                  <p className="text-sm text-gray-400">Use the provider directory above, then click Book Appointment.</p>
                </div>
              )}
            </section>

            <div className="grid grid-cols-1 gap-8 xl:col-span-2">
              <section className="rounded-3xl border border-white/15 bg-white/8 p-6 backdrop-blur-xl shadow-2xl shadow-purple-900/20">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Upcoming Medical Appointments</h2>
                    <p className="text-sm text-gray-400">Track what is booked and what still needs follow-up.</p>
                  </div>
                  <div className="rounded-full bg-white/10 px-3 py-1 text-sm text-gray-300">{appointments.length} tracked</div>
                </div>

                {appointmentsLoading ? (
                  <div className="py-10 text-center text-gray-300">Loading appointments...</div>
                ) : appointments.length === 0 ? (
                  <div className="rounded-3xl border border-white/10 bg-white/5 py-10 text-center">
                    <Clock3 className="mx-auto mb-4 h-10 w-10 text-gray-400" />
                    <p className="font-medium text-white">No medical appointments yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {appointments.map((appointment) => (
                      <div key={appointment.appointment_id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                          <div>
                            <h3 className="text-lg font-semibold text-white">{appointment.provider_name || appointment.appointment_type}</h3>
                            <p className="mt-1 text-sm text-cyan-200">{appointment.appointment_type}</p>
                            <div className="mt-3 space-y-1 text-sm text-gray-300">
                              <p>{appointment.appointment_date} at {appointment.appointment_time || 'TBD'}</p>
                              {appointment.location ? <p>{appointment.location}</p> : null}
                              {appointment.notes ? <p className="text-gray-400">{appointment.notes}</p> : null}
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {APPOINTMENT_STATUS_OPTIONS.map((status) => (
                              <button
                                key={status}
                                type="button"
                                onClick={() => updateAppointmentStatus(appointment.appointment_id, status)}
                                className={`rounded-xl border px-3 py-2 text-sm transition ${
                                  appointment.status === status
                                    ? 'border-emerald-500/30 bg-emerald-500/20 text-emerald-200'
                                    : 'border-white/10 bg-white/5 text-gray-300 hover:bg-white/10'
                                }`}
                              >
                                {status.replace('_', ' ')}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="rounded-3xl border border-white/15 bg-white/8 p-6 backdrop-blur-xl shadow-2xl shadow-purple-900/20">
                <div className="mb-6 flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Referral Tracker</h2>
                    <p className="text-sm text-gray-400">Keep provider outreach organized by status.</p>
                  </div>
                  <div className="rounded-full bg-white/10 px-3 py-1 text-sm text-gray-300">{referrals.length} referrals</div>
                </div>

                {referralsLoading ? (
                  <div className="py-10 text-center text-gray-300">Loading referrals...</div>
                ) : referrals.length === 0 ? (
                  <div className="rounded-3xl border border-white/10 bg-white/5 py-10 text-center">
                    <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-gray-400" />
                    <p className="font-medium text-white">No medical referrals saved yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {referrals.map((referral) => (
                      <div key={referral.referral_id} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                          <div>
                            <h3 className="text-lg font-semibold text-white">{referral.provider_name}</h3>
                            <p className="mt-1 text-sm text-cyan-200">{referral.provider_type || referral.provider_category}</p>
                            <div className="mt-3 space-y-1 text-sm text-gray-300">
                              {referral.address ? <p>{referral.address}</p> : null}
                              {referral.phone ? <p>{referral.phone}</p> : null}
                              {referral.notes ? <p className="text-gray-400">{referral.notes}</p> : null}
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {REFERRAL_STATUS_OPTIONS.map((status) => (
                              <button
                                key={status}
                                type="button"
                                onClick={() => updateReferralStatus(referral.referral_id, status)}
                                className={`rounded-xl border px-3 py-2 text-sm transition ${
                                  referral.referral_status === status
                                    ? 'border-blue-500/30 bg-blue-500/20 text-blue-200'
                                    : 'border-white/10 bg-white/5 text-gray-300 hover:bg-white/10'
                                }`}
                              >
                                {status}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Medical
