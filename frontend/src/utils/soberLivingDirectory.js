import { apiCall, apiFetch } from '../api/config'

const buildQuery = (params = {}) => {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    searchParams.set(key, value)
  })
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export const soberLivingDirectoryApi = {
  listListings: (filters = {}) =>
    apiCall(`/api/sober-living-directory/listings${buildQuery(filters)}`),

  getListing: (listingId) =>
    apiCall(`/api/sober-living-directory/listings/${encodeURIComponent(listingId)}`),

  createListing: (payload) =>
    apiCall('/api/sober-living-directory/listings', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  searchLive: (payload) =>
    apiCall('/api/sober-living-directory/search/live', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateListing: (listingId, payload) =>
    apiCall(`/api/sober-living-directory/listings/${encodeURIComponent(listingId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  verifyListing: (listingId, payload) =>
    apiCall(`/api/sober-living-directory/listings/${encodeURIComponent(listingId)}/verify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  archiveListing: (listingId) =>
    apiCall(`/api/sober-living-directory/listings/${encodeURIComponent(listingId)}/archive`, {
      method: 'POST',
    }),

  getReviewQueue: () =>
    apiCall('/api/sober-living-directory/review'),

  listRawRecords: (filters = {}) =>
    apiCall(`/api/sober-living-directory/raw-records${buildQuery(filters)}`),

  getRawRecord: (rawId) =>
    apiCall(`/api/sober-living-directory/raw-records/${encodeURIComponent(rawId)}`),

  approveRawRecord: (rawId, payload = {}) =>
    apiCall(`/api/sober-living-directory/raw-records/${encodeURIComponent(rawId)}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rejectRawRecord: (rawId, payload = {}) =>
    apiCall(`/api/sober-living-directory/raw-records/${encodeURIComponent(rawId)}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  markRawRecordError: (rawId, payload = {}) =>
    apiCall(`/api/sober-living-directory/raw-records/${encodeURIComponent(rawId)}/mark-error`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listSources: () =>
    apiCall('/api/sober-living-directory/sources'),

  getSource: (sourceId) =>
    apiCall(`/api/sober-living-directory/sources/${encodeURIComponent(sourceId)}`),

  createSource: (payload) =>
    apiCall('/api/sober-living-directory/sources', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateSource: (sourceId, payload) =>
    apiCall(`/api/sober-living-directory/sources/${encodeURIComponent(sourceId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  listDiscoveryJobs: () =>
    apiCall('/api/sober-living-directory/discovery/jobs'),

  getDiscoveryJob: (jobId) =>
    apiCall(`/api/sober-living-directory/discovery/jobs/${encodeURIComponent(jobId)}`),

  createDiscoveryJob: (payload) =>
    apiCall('/api/sober-living-directory/discovery/jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateDiscoveryJob: (jobId, payload) =>
    apiCall(`/api/sober-living-directory/discovery/jobs/${encodeURIComponent(jobId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  updateDiscoveryJobSchedule: (jobId, payload) =>
    apiCall(`/api/sober-living-directory/discovery/jobs/${encodeURIComponent(jobId)}/schedule`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  listDiscoveryRuns: (jobId) =>
    apiCall(`/api/sober-living-directory/discovery/runs${buildQuery({ job_id: jobId })}`),

  getDiscoveryRun: (runId) =>
    apiCall(`/api/sober-living-directory/discovery/runs/${encodeURIComponent(runId)}`),

  listSchedulerPreview: () =>
    apiCall('/api/sober-living-directory/discovery/scheduler/preview'),

  getSchedulerStatus: () =>
    apiCall('/api/sober-living-directory/discovery/scheduler/status'),

  startSchedulerWorker: () =>
    apiCall('/api/sober-living-directory/discovery/scheduler/start', {
      method: 'POST',
    }),

  stopSchedulerWorker: () =>
    apiCall('/api/sober-living-directory/discovery/scheduler/stop', {
      method: 'POST',
    }),

  runSchedulerOnce: () =>
    apiCall('/api/sober-living-directory/discovery/scheduler/run-once', {
      method: 'POST',
    }),

  runDiscoveryJobTest: (jobId) =>
    apiCall(`/api/sober-living-directory/discovery/jobs/${encodeURIComponent(jobId)}/run-test`, {
      method: 'POST',
    }),

  runDiscoveryJob: (jobId) =>
    apiCall(`/api/sober-living-directory/discovery/jobs/${encodeURIComponent(jobId)}/run`, {
      method: 'POST',
    }),

  getDuplicateCandidate: (candidateId) =>
    apiCall(`/api/sober-living-directory/duplicates/${encodeURIComponent(candidateId)}`),

  mergeDuplicateCandidate: (candidateId, payload = {}) =>
    apiCall(`/api/sober-living-directory/duplicates/${encodeURIComponent(candidateId)}/merge`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  keepDuplicateCandidateSeparate: (candidateId, payload = {}) =>
    apiCall(`/api/sober-living-directory/duplicates/${encodeURIComponent(candidateId)}/keep-separate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rejectDuplicateCandidate: (candidateId, payload = {}) =>
    apiCall(`/api/sober-living-directory/duplicates/${encodeURIComponent(candidateId)}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listTasks: (listingId) =>
    apiCall(`/api/sober-living-directory/tasks${buildQuery({ listing_id: listingId })}`),

  createTask: (payload) =>
    apiCall('/api/sober-living-directory/tasks', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateTask: (taskId, payload) =>
    apiCall(`/api/sober-living-directory/tasks/${encodeURIComponent(taskId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  importListings: async ({ file, sourceName, sourceType = 'spreadsheet_import' }) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_name', sourceName)
    formData.append('source_type', sourceType)
    const response = await apiFetch('/api/sober-living-directory/import', {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || data.message || `HTTP ${response.status}`)
    }
    return response.json()
  },
}

export const defaultListingForm = {
  name: '',
  operator_name: '',
  website: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  state: 'CA',
  zip_code: '',
  latitude: '',
  longitude: '',
  neighborhood: '',
  population_served: '',
  house_type: '',
  certification_status: '',
  certification_body: '',
  certification_expiration_date: '',
  monthly_rent_min: '',
  monthly_rent_max: '',
  deposit_required: false,
  accepts_insurance: false,
  accepts_mat: false,
  accepts_probation_parole: false,
  pets_allowed: false,
  bed_availability_status: 'unknown',
  last_availability_check_date: '',
  last_verified_date: '',
  verification_method: '',
  risk_flags_json: '',
  notes: '',
  internal_referral_notes: '',
  source_urls_json: '',
  status: 'pending_review',
}

const parseDelimitedText = (value) =>
  String(value || '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)

export const buildListingPayload = (formState) => ({
  name: formState.name.trim(),
  operator_name: formState.operator_name.trim() || null,
  website: formState.website.trim() || null,
  phone: formState.phone.trim() || null,
  email: formState.email.trim() || null,
  address: formState.address.trim() || null,
  city: formState.city.trim(),
  state: (formState.state || 'CA').trim().toUpperCase(),
  zip_code: formState.zip_code.trim() || null,
  latitude: formState.latitude === '' ? null : Number(formState.latitude),
  longitude: formState.longitude === '' ? null : Number(formState.longitude),
  neighborhood: formState.neighborhood.trim() || null,
  population_served: formState.population_served.trim() || null,
  house_type: formState.house_type.trim() || null,
  certification_status: formState.certification_status.trim() || null,
  certification_body: formState.certification_body.trim() || null,
  certification_expiration_date: formState.certification_expiration_date || null,
  monthly_rent_min: formState.monthly_rent_min === '' ? null : Number(formState.monthly_rent_min),
  monthly_rent_max: formState.monthly_rent_max === '' ? null : Number(formState.monthly_rent_max),
  deposit_required: Boolean(formState.deposit_required),
  accepts_insurance: Boolean(formState.accepts_insurance),
  accepts_mat: Boolean(formState.accepts_mat),
  accepts_probation_parole: Boolean(formState.accepts_probation_parole),
  pets_allowed: Boolean(formState.pets_allowed),
  bed_availability_status: formState.bed_availability_status || null,
  last_availability_check_date: formState.last_availability_check_date || null,
  last_verified_date: formState.last_verified_date || null,
  verification_method: formState.verification_method.trim() || null,
  risk_flags_json: parseDelimitedText(formState.risk_flags_json),
  notes: formState.notes.trim() || null,
  internal_referral_notes: formState.internal_referral_notes.trim() || null,
  source_urls_json: parseDelimitedText(formState.source_urls_json),
  status: formState.status,
})

export const mapListingToForm = (listing = {}) => ({
  ...defaultListingForm,
  ...listing,
  latitude: listing.latitude ?? '',
  longitude: listing.longitude ?? '',
  monthly_rent_min: listing.monthly_rent_min ?? '',
  monthly_rent_max: listing.monthly_rent_max ?? '',
  risk_flags_json: Array.isArray(listing.risk_flags_json) ? listing.risk_flags_json.join('\n') : '',
  source_urls_json: Array.isArray(listing.source_urls_json) ? listing.source_urls_json.join('\n') : '',
})

export const fetchJsonOrThrow = async (endpoint) => {
  const response = await apiFetch(endpoint)
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || data.message || `HTTP ${response.status}`)
  }
  return response.json()
}
