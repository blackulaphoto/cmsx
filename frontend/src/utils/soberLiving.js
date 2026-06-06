import { apiFetch } from '../api/config'

// ---------------------------------------------------------------------------
// Bed status display helpers
// ---------------------------------------------------------------------------

export const BED_STATUS_COLORS = {
  available:   { bg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  occupied:    { bg: 'bg-rose-500/20',    text: 'text-rose-300',    border: 'border-rose-500/30',    dot: 'bg-rose-400'    },
  reserved:    { bg: 'bg-amber-500/20',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400'   },
  maintenance: { bg: 'bg-slate-500/20',   text: 'text-slate-300',   border: 'border-slate-500/30',   dot: 'bg-slate-400'   },
  unavailable: { bg: 'bg-zinc-500/20',    text: 'text-zinc-400',    border: 'border-zinc-500/30',    dot: 'bg-zinc-500'    },
}

export const BED_STATUS_LABELS = {
  available:   'Available',
  occupied:    'Occupied',
  reserved:    'Reserved',
  maintenance: 'Maintenance',
  unavailable: 'Unavailable',
}

export const BED_STATUS_OPTIONS = Object.entries(BED_STATUS_LABELS).map(([value, label]) => ({ value, label }))

export const HOUSE_TYPE_OPTIONS = [
  { value: 'any',    label: 'Any Gender' },
  { value: 'men',    label: 'Men Only' },
  { value: 'women',  label: 'Women Only' },
  { value: 'co-ed',  label: 'Co-Ed' },
  { value: 'other',  label: 'Other' },
]

// Kept for legacy import compatibility
export const GENDER_POLICY_OPTIONS = HOUSE_TYPE_OPTIONS

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

export const INCIDENT_TYPES = [
  'relapse', 'rule_violation', 'physical_altercation', 'medical_emergency',
  'mental_health_crisis', 'theft', 'unauthorized_visitor', 'property_damage',
  'noise_complaint', 'missing_resident', 'medication_issue', 'curfew_violation',
  'overdose', 'other',
]

export const PAYMENT_METHODS = [
  'Cash', 'Check', 'Money Order', 'EBT', 'Venmo', 'Zelle',
  'CashApp', 'Credit Card', 'Debit Card', 'Insurance', 'Voucher', 'Other',
]

// ---------------------------------------------------------------------------
// Core fetch wrapper — always parses JSON, throws on non-OK responses
// ---------------------------------------------------------------------------

const BASE = '/api/sober-living'

async function sl(endpoint, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const res = await apiFetch(endpoint, { ...options, headers })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || body.message || detail
    } catch {}
    throw new Error(detail)
  }
  // 204 No Content
  if (res.status === 204) return null
  return res.json()
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const slApi = {
  // Summary
  getSummary: () => sl(`${BASE}/summary`),

  // Houses
  listHouses:  ()            => sl(`${BASE}/houses`),
  createHouse: (data)        => sl(`${BASE}/houses`, { method: 'POST', body: JSON.stringify(data) }),
  getHouse:    (id)          => sl(`${BASE}/houses/${id}`),
  updateHouse: (id, data)    => sl(`${BASE}/houses/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Rooms
  listRooms:  (houseId)        => sl(`${BASE}/houses/${houseId}/rooms`),
  createRoom: (houseId, data)  => sl(`${BASE}/houses/${houseId}/rooms`, { method: 'POST', body: JSON.stringify(data) }),
  updateRoom: (roomId, data)   => sl(`${BASE}/rooms/${roomId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Beds
  listBeds:  (houseId)       => sl(`${BASE}/houses/${houseId}/beds`),
  createBed: (houseId, data) => sl(`${BASE}/houses/${houseId}/beds`, { method: 'POST', body: JSON.stringify(data) }),
  updateBed: (bedId, data)   => sl(`${BASE}/beds/${bedId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Residents
  listAllResidents: ()             => sl(`${BASE}/residents`),
  listResidents:    (houseId)      => sl(`${BASE}/houses/${houseId}/residents`),
  createResident:   (data)         => sl(`${BASE}/residents`, { method: 'POST', body: JSON.stringify(data) }),
  getResident:      (id)           => sl(`${BASE}/residents/${id}`),
  updateResident:   (id, data)     => sl(`${BASE}/residents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Stays
  createStay:   (data)           => sl(`${BASE}/stays`, { method: 'POST', body: JSON.stringify(data) }),
  updateStay:   (stayId, data)   => sl(`${BASE}/stays/${stayId}`, { method: 'PUT', body: JSON.stringify(data) }),
  dischargeStay:(stayId, data)   => sl(`${BASE}/stays/${stayId}/discharge`, { method: 'POST', body: JSON.stringify(data) }),
  transferBed:  (stayId, newBedId) => sl(`${BASE}/stays/${stayId}/transfer-bed`, { method: 'POST', body: JSON.stringify({ new_bed_id: newBedId }) }),

  // Compliance
  getCompliance:    (stayId)       => sl(`${BASE}/stays/${stayId}/compliance`),
  updateCompliance: (stayId, data) => sl(`${BASE}/stays/${stayId}/compliance`, { method: 'PUT', body: JSON.stringify(data) }),

  // UA Tests
  listUATests:  (houseId, residentId) => sl(`${BASE}/houses/${houseId}/ua-tests${residentId ? `?resident_id=${residentId}` : ''}`),
  createUATest: (data)                => sl(`${BASE}/ua-tests`, { method: 'POST', body: JSON.stringify(data) }),

  // Incidents
  listIncidents:  (houseId) => sl(`${BASE}/houses/${houseId}/incidents`),
  createIncident: (data)    => sl(`${BASE}/incidents`, { method: 'POST', body: JSON.stringify(data) }),
  updateIncident: (id, data)=> sl(`${BASE}/incidents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Rent
  getLedger:       (stayId)  => sl(`${BASE}/stays/${stayId}/ledger`),
  getRentSummary:  (houseId) => sl(`${BASE}/houses/${houseId}/rent-summary`),
  createCharge:    (data)    => sl(`${BASE}/rent-charges`, { method: 'POST', body: JSON.stringify(data) }),
  createPayment:   (data)    => sl(`${BASE}/rent-payments`, { method: 'POST', body: JSON.stringify(data) }),
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

export const occupancyColor = (rate) => {
  const n = Number(rate) || 0
  if (n >= 90) return 'text-rose-400'
  if (n >= 70) return 'text-amber-400'
  return 'text-emerald-400'
}

export const formatCurrency = (amount) => {
  if (amount == null || amount === '') return '—'
  return `$${Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr + (dateStr.includes('T') ? '' : 'T00:00:00'))
      .toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return dateStr
  }
}

export const formatMoveInDate = formatDate
