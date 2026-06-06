import { apiFetch } from '../api/config'

// ---------------------------------------------------------------------------
// Bed status display helpers
// ---------------------------------------------------------------------------

export const BED_STATUS_COLORS = {
  available:    { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  occupied:     { bg: 'bg-rose-500/20',    text: 'text-rose-300',    border: 'border-rose-500/30',    dot: 'bg-rose-400'    },
  reserved:     { bg: 'bg-amber-500/20',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400'   },
  maintenance:  { bg: 'bg-slate-500/20',   text: 'text-slate-300',   border: 'border-slate-500/30',   dot: 'bg-slate-400'   },
  unavailable:  { bg: 'bg-zinc-500/20',    text: 'text-zinc-400',    border: 'border-zinc-500/30',    dot: 'bg-zinc-500'    },
}

export const BED_STATUS_LABELS = {
  available:   'Available',
  occupied:    'Occupied',
  reserved:    'Reserved',
  maintenance: 'Maintenance',
  unavailable: 'Unavailable',
}

export const BED_STATUS_OPTIONS = Object.entries(BED_STATUS_LABELS).map(([value, label]) => ({ value, label }))

export const GENDER_POLICY_OPTIONS = [
  { value: 'any',    label: 'Any Gender' },
  { value: 'male',   label: 'Male Only' },
  { value: 'female', label: 'Female Only' },
  { value: 'other',  label: 'Other' },
]

export const DISCHARGE_REASON_OPTIONS = [
  'Completed program',
  'Voluntary departure',
  'Lease non-renewal',
  'Rule violation',
  'Relapse',
  'Medical transfer',
  'Incarceration',
  'Housing secured',
  'Other',
]

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const BASE = '/api/sober-living'

export const slApi = {
  getSummary:          ()              => apiFetch(`${BASE}/summary`),
  listHouses:          ()              => apiFetch(`${BASE}/houses`),
  createHouse:         (data)          => apiFetch(`${BASE}/houses`, { method: 'POST', body: JSON.stringify(data) }),
  getHouse:            (id)            => apiFetch(`${BASE}/houses/${id}`),
  updateHouse:         (id, data)      => apiFetch(`${BASE}/houses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  listRooms:           (houseId)       => apiFetch(`${BASE}/houses/${houseId}/rooms`),
  createRoom:          (houseId, data) => apiFetch(`${BASE}/houses/${houseId}/rooms`, { method: 'POST', body: JSON.stringify(data) }),
  listBeds:            (houseId)       => apiFetch(`${BASE}/houses/${houseId}/beds`),
  createBed:           (houseId, data) => apiFetch(`${BASE}/houses/${houseId}/beds`, { method: 'POST', body: JSON.stringify(data) }),
  updateBed:           (bedId, data)   => apiFetch(`${BASE}/beds/${bedId}`, { method: 'PUT', body: JSON.stringify(data) }),
  listResidents:       (houseId)       => apiFetch(`${BASE}/houses/${houseId}/residents`),
  createResident:      (data)          => apiFetch(`${BASE}/residents`, { method: 'POST', body: JSON.stringify(data) }),
  createStay:          (data)          => apiFetch(`${BASE}/stays`, { method: 'POST', body: JSON.stringify(data) }),
  updateStay:          (stayId, data)  => apiFetch(`${BASE}/stays/${stayId}`, { method: 'PUT', body: JSON.stringify(data) }),
  dischargeStay:       (stayId, data)  => apiFetch(`${BASE}/stays/${stayId}/discharge`, { method: 'POST', body: JSON.stringify(data) }),
  transferBed:         (stayId, newBedId) => apiFetch(`${BASE}/stays/${stayId}/transfer-bed`, { method: 'POST', body: JSON.stringify({ new_bed_id: newBedId }) }),
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

export const occupancyColor = (rate) => {
  if (rate >= 90) return 'text-rose-400'
  if (rate >= 70) return 'text-amber-400'
  return 'text-emerald-400'
}

export const formatMoveInDate = (dateStr) => {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return dateStr
  }
}
