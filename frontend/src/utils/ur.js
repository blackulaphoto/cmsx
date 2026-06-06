const normalize = (value) => (value || '').toString().trim()

export const UR_STATUS_OPTIONS = [
  'auth_needed',
  'submitted',
  'approved',
  'denied',
  'appeal_pending',
  'closed'
]

export const UR_EVENT_TYPE_OPTIONS = [
  'initial_auth',
  'concurrent_review',
  'extension_request',
  'denial',
  'peer_review',
  'appeal'
]

export const WORKFLOW_STEPS = [
  'Submit Initial Authorization',
  'Await Insurance Decision',
  'Record Approval',
  'Schedule Concurrent Review',
  'Request Extension',
  'Appeal if Needed',
  'Close Case'
]

export const LOC_OPTIONS = ['Detox', 'Residential', 'PHP', 'IOP', 'OP', 'Other']
export const PROGRAM_OPTIONS = ['Detox', 'Residential', 'PHP', 'IOP', 'OP', 'MAT', 'Other']
export const COMMUNICATION_METHOD_OPTIONS = ['Portal', 'Fax', 'Phone', 'Email', 'Voicemail', 'Other']

export const formatUrLabel = (value) => {
  const normalized = normalize(value)
  if (!normalized) return 'Not set'
  return normalized
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const formatCurrency = (value) => {
  const numeric = Number(value || 0)
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(Number.isFinite(numeric) ? numeric : 0)
}

export const formatPercent = (value) => `${Math.round((Number(value || 0) * 100))}%`

export const getApprovalRate = (urCase) => {
  const requested = Number(urCase?.requested_days || 0)
  const approved = Number(urCase?.approved_days || 0)
  if (requested <= 0) return 0
  return approved / requested
}

export const getDeniedDays = (urCase) => {
  const requested = Number(urCase?.requested_days || 0)
  const approved = Number(urCase?.approved_days || 0)
  const denied = urCase?.denied_days
  if (denied === '' || denied == null) {
    return Math.max(requested - approved, 0)
  }
  return Number(denied || 0)
}

export const parseDateOnly = (value) => {
  const raw = normalize(value)
  if (!raw) return null
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return null
  parsed.setHours(0, 0, 0, 0)
  return parsed
}

export const formatDisplayDate = (value, fallback = 'Not set') => {
  const parsed = parseDateOnly(value)
  if (!parsed) return fallback
  return parsed.toLocaleDateString()
}

export const getDeadlineState = (value) => {
  const parsed = parseDateOnly(value)
  if (!parsed) return { label: 'No date', tone: 'muted', daysUntil: null }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysUntil = Math.round((parsed - today) / 86400000)
  if (daysUntil < 0) return { label: `${Math.abs(daysUntil)} day${Math.abs(daysUntil) === 1 ? '' : 's'} overdue`, tone: 'danger', daysUntil }
  if (daysUntil === 0) return { label: 'Due today', tone: 'danger', daysUntil }
  if (daysUntil <= 3) return { label: `Due in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`, tone: 'warning', daysUntil }
  return { label: `Due in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`, tone: 'ok', daysUntil }
}

export const deriveCurrentWorkflowStep = (urCase) => {
  const status = normalize(urCase?.status).toLowerCase()
  if (status === 'closed') return 6
  if (status === 'appeal_pending') return 5
  if (status === 'denied') return 5
  if (status === 'approved' && urCase?.next_review_date) return 3
  if (status === 'approved') return 2
  if (status === 'submitted') return 1
  return 0
}

export const deriveNextAction = (urCase) => {
  const status = normalize(urCase?.status).toLowerCase()
  const nextReview = getDeadlineState(urCase?.next_review_date)
  const appealDeadline = getDeadlineState(urCase?.appeal_deadline)
  const peerReviewDeadline = getDeadlineState(urCase?.peer_review_deadline)
  const authEnd = getDeadlineState(urCase?.approved_end_date)

  if (status === 'denied') {
    if (peerReviewDeadline.daysUntil != null && peerReviewDeadline.daysUntil <= 3) return 'Prepare peer review discussion'
    if (appealDeadline.daysUntil != null && appealDeadline.daysUntil <= 3) return 'Prepare appeal packet'
    return 'Review denial reason and next escalation'
  }
  if (status === 'appeal_pending') return 'Track appeal deadline and supporting evidence'
  if (status === 'approved') {
    if (nextReview.daysUntil != null && nextReview.daysUntil <= 3) return 'Prepare concurrent review packet'
    if (authEnd.daysUntil != null && authEnd.daysUntil <= 3) return 'Request extension before auth expires'
    return 'Monitor approved span and next review'
  }
  if (status === 'submitted') return 'Await insurance decision and log outcome'
  if (status === 'closed') return 'Case complete unless readmission or appeal reopens'
  return 'Submit initial authorization request'
}

export const buildStatusBanner = (urCase) => {
  return {
    statusLabel: formatUrLabel(urCase?.status),
    approvedDaysLabel: `${Number(urCase?.approved_days || 0)} day${Number(urCase?.approved_days || 0) === 1 ? '' : 's'} approved`,
    approvedSpanLabel: urCase?.approved_end_date ? `Expires ${formatDisplayDate(urCase.approved_end_date)}` : 'No auth end date',
    nextReviewLabel: urCase?.next_review_date ? formatDisplayDate(urCase.next_review_date) : 'Not set',
    reviewerLabel: urCase?.reviewer_name || 'Reviewer not set',
    reviewerCompanyLabel: urCase?.reviewer_company || 'Company not set',
    nextAction: deriveNextAction(urCase)
  }
}

export const sortEventsNewestFirst = (events = []) => {
  return [...events].sort((a, b) => {
    const aValue = normalize(a?.event_date || a?.created_at)
    const bValue = normalize(b?.event_date || b?.created_at)
    return bValue.localeCompare(aValue)
  })
}

export const getSummaryCards = (summary = {}) => ([
  { key: 'total_authorized_days', label: 'Total Authorized Days', value: Number(summary.total_authorized_days || 0) },
  { key: 'total_denied_days', label: 'Total Denied Days', value: Number(summary.total_denied_days || 0) },
  { key: 'average_approval_rate', label: 'Average Approval Rate', value: formatPercent(summary.average_approval_rate || 0) },
  { key: 'reviews_due_today', label: 'Reviews Due Today', value: Number(summary.reviews_due_today || 0) },
  { key: 'due_in_72_hours', label: 'Due in 72 Hours', value: Number(summary.due_in_72_hours || 0) },
  { key: 'auth_expiring', label: 'Auth Expiring', value: Number(summary.auth_expiring || 0) },
  { key: 'denials_needing_action', label: 'Denials Needing Action', value: Number(summary.denials_needing_action || 0) },
  { key: 'appeals_due', label: 'Appeals Due', value: Number(summary.appeals_due || 0) },
  { key: 'revenue_at_risk', label: 'Revenue At Risk', value: formatCurrency(summary.revenue_at_risk || 0) }
])
