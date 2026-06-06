export const FMLA_STATUS_BADGES = {
  draft: 'bg-slate-500/20 text-slate-200 border-slate-400/30',
  'pending documents': 'bg-amber-500/20 text-amber-200 border-amber-400/30',
  submitted: 'bg-blue-500/20 text-blue-200 border-blue-400/30',
  approved: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30',
  denied: 'bg-rose-500/20 text-rose-200 border-rose-400/30',
  expired: 'bg-orange-500/20 text-orange-200 border-orange-400/30',
  closed: 'bg-zinc-500/20 text-zinc-200 border-zinc-400/30',
  Draft: 'bg-slate-500/20 text-slate-200 border-slate-400/30',
  Approved: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30',
  Denied: 'bg-rose-500/20 text-rose-200 border-rose-400/30',
  Closed: 'bg-zinc-500/20 text-zinc-200 border-zinc-400/30'
}

const normalize = (value) => (value || '').toString().trim()

export const WORKFLOW_STAGES = [
  'Case Opened',
  'Employer Contacted',
  'Packet Requested',
  'Packet Received',
  'Sent to Provider',
  'Provider Completed',
  'Returned to Employer',
  'Decision Pending',
  'Approved',
  'Denied',
  'Closed / RTW'
]

export const WORKFLOW_ACTION_BUCKETS = {
  employer_follow_up: 'Employer Follow-Up Needed',
  packet_not_received: 'Packet Not Received',
  provider_docs_pending: 'Provider Docs Pending',
  due_within_3_days: 'Due Within 3 Days',
  ready_to_submit: 'Ready to Submit',
  rtw_extension_needed: 'RTW / Extension Needed',
  monitoring: 'Monitoring'
}

const LEGACY_STATUS_MAP = {
  draft: 'draft',
  'waiting on client': 'pending documents',
  'waiting on employer': 'pending documents',
  'waiting on provider': 'pending documents',
  'paperwork received': 'pending documents',
  'paperwork sent': 'submitted',
  'confirmation pending': 'submitted',
  'extension needed': 'pending documents',
  approved: 'approved',
  denied: 'denied',
  expired: 'expired',
  closed: 'closed'
}

export const normalizeFmlaStatusValue = (status) => {
  const normalized = normalize(status).toLowerCase()
  return LEGACY_STATUS_MAP[normalized] || normalized
}

export const getFmlaStatusBadgeClass = (status) => {
  const normalized = normalizeFmlaStatusValue(status) || normalize(status)
  return FMLA_STATUS_BADGES[normalized] || FMLA_STATUS_BADGES[normalized.toLowerCase()] || 'bg-slate-500/20 text-slate-200 border-slate-400/30'
}

export const formatFmlaLabel = (value) => {
  const normalized = normalize(value)
  if (!normalized) return 'Not set'
  return normalized
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const getCaseDisplayName = (fmlaCase) => {
  if (!fmlaCase) return 'Unassigned case'
  if ((fmlaCase.case_subject_type || '').toLowerCase() === 'staff') {
    return fmlaCase.staff_name || fmlaCase.staff_identifier || 'Staff leave case'
  }
  return fmlaCase.client_name || fmlaCase.client_id || 'Client leave case'
}

export const getSubjectBadge = (fmlaCase) => {
  return (fmlaCase?.case_subject_type || 'client').toLowerCase() === 'staff'
    ? 'bg-rose-500/15 text-rose-200 border-rose-400/30'
    : 'bg-cyan-500/15 text-cyan-200 border-cyan-400/30'
}

export const getDeadlineState = (deadline) => {
  if (!deadline) {
    return { label: 'No deadline', tone: 'muted', daysUntil: null }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(deadline)
  due.setHours(0, 0, 0, 0)

  const daysUntil = Math.round((due - today) / 86400000)
  if (Number.isNaN(daysUntil)) {
    return { label: 'Invalid deadline', tone: 'muted', daysUntil: null }
  }
  if (daysUntil < 0) {
    return { label: `${Math.abs(daysUntil)} day${Math.abs(daysUntil) === 1 ? '' : 's'} overdue`, tone: 'danger', daysUntil }
  }
  if (daysUntil === 0) {
    return { label: 'Due today', tone: 'danger', daysUntil }
  }
  if (daysUntil <= 7) {
    return { label: `Due in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`, tone: 'warning', daysUntil }
  }
  return { label: `Due in ${daysUntil} day${daysUntil === 1 ? '' : 's'}`, tone: 'ok', daysUntil }
}

export const getDeadlineBuckets = (fmlaCase, reminders = []) => {
  const items = [
    { key: 'paperwork_deadline', label: 'Paperwork due', value: fmlaCase?.paperwork_deadline || '' },
    { key: 'employer_response_deadline', label: 'Employer response', value: fmlaCase?.employer_response_deadline || '' },
    { key: 'certification_expiration_date', label: 'Certification expires', value: fmlaCase?.certification_expiration_date || '' },
    { key: 'return_to_work_date', label: 'Return to work', value: fmlaCase?.return_to_work_date || '' }
  ]
  const reminderItems = (reminders || []).map((reminder) => ({
    key: reminder.reminder_id,
    label: reminder.reminder_reason || reminder.message || 'Reminder',
    value: reminder.due_date || ''
  }))

  return [...items, ...reminderItems]
    .filter((item) => item.value)
    .map((item) => ({ ...item, state: getDeadlineState(item.value) }))
    .sort((a, b) => {
      const aDays = a.state.daysUntil ?? 99999
      const bDays = b.state.daysUntil ?? 99999
      return aDays - bDays
    })
}

const latestDate = (values = []) => {
  return values
    .filter(Boolean)
    .map((value) => {
      const parsed = new Date(value)
      return Number.isNaN(parsed.getTime()) ? null : { raw: value, time: parsed.getTime() }
    })
    .filter(Boolean)
    .sort((a, b) => b.time - a.time)[0]?.raw || ''
}

const hasDocumentStatus = (documents = [], documentTypes = [], statuses = []) => {
  const normalizedTypes = documentTypes.map((item) => item.toLowerCase())
  const normalizedStatuses = statuses.map((item) => item.toLowerCase())
  return (documents || []).some((doc) => {
    const docType = normalize(doc.document_type).toLowerCase()
    const docStatus = normalize(doc.document_status).toLowerCase()
    const typeMatches = normalizedTypes.length === 0 || normalizedTypes.includes(docType)
    const statusMatches = normalizedStatuses.length === 0 || normalizedStatuses.includes(docStatus)
    return typeMatches && statusMatches
  })
}

export const getLastContactDate = (fmlaCase, correspondence = [], documents = []) => {
  const correspondenceDate = latestDate((correspondence || []).map((entry) => entry.correspondence_at))
  const documentDate = latestDate(
    (documents || []).flatMap((doc) => [doc.date_requested, doc.date_received, doc.date_sent, doc.date_completed, doc.updated_at, doc.created_at])
  )
  const caseDate = latestDate([
    fmlaCase?.paperwork_sent_date,
    fmlaCase?.paperwork_completed_date,
    fmlaCase?.paperwork_received_date,
    fmlaCase?.updated_at
  ])
  return latestDate([correspondenceDate, documentDate, caseDate])
}

export const getNextDueDate = (fmlaCase, reminders = []) => {
  return getDeadlineBuckets(fmlaCase, reminders)[0] || null
}

export const getCurrentWorkflowStage = (fmlaCase, documents = [], correspondence = []) => {
  const status = normalizeFmlaStatusValue(fmlaCase?.status)
  const approvalStatus = normalize(fmlaCase?.approval_status).toLowerCase()
  const hasEmployerContact =
    Boolean(fmlaCase?.hr_contact_name || fmlaCase?.hr_phone || fmlaCase?.hr_email || fmlaCase?.employer_name) &&
    ((correspondence || []).length > 0 || Boolean(fmlaCase?.employer_response_deadline))
  const packetRequested =
    Boolean(fmlaCase?.employer_response_deadline || fmlaCase?.paperwork_deadline) ||
    hasDocumentStatus(documents, ['employer packet'], ['needed', 'requested'])
  const packetReceived =
    Boolean(fmlaCase?.paperwork_received_date) ||
    hasDocumentStatus(documents, ['employer packet'], ['received', 'completed', 'sent', 'confirmed'])
  const providerCompleted =
    Boolean(fmlaCase?.paperwork_completed_date) ||
    hasDocumentStatus(documents, ['medical certification', 'provider letter'], ['completed', 'received', 'confirmed'])
  const returnedToEmployer =
    Boolean(fmlaCase?.paperwork_sent_date) ||
    hasDocumentStatus(documents, [], ['sent', 'confirmed'])

  if (status === 'closed' || approvalStatus === 'closed') return 'Closed / RTW'
  if (status === 'denied' || approvalStatus === 'denied') return 'Denied'
  if (status === 'approved' || approvalStatus === 'approved') return 'Approved'
  if (status === 'submitted') return 'Decision Pending'
  if (returnedToEmployer) return 'Returned to Employer'
  if (providerCompleted) return 'Provider Completed'
  if (packetReceived && (fmlaCase?.provider_name || fmlaCase?.clinic_name || hasDocumentStatus(documents, ['medical certification', 'provider letter'], ['needed', 'requested', 'received']))) {
    return 'Sent to Provider'
  }
  if (packetReceived) return 'Packet Received'
  if (packetRequested) return 'Packet Requested'
  if (hasEmployerContact) return 'Employer Contacted'
  return 'Case Opened'
}

export const getWaitingOnLabel = (fmlaCase, documents = [], correspondence = []) => {
  const stage = getCurrentWorkflowStage(fmlaCase, documents, correspondence)
  if (stage === 'Employer Contacted' || stage === 'Packet Requested' || stage === 'Returned to Employer' || stage === 'Decision Pending') {
    return 'Employer / FMLA company'
  }
  if (stage === 'Sent to Provider') return 'Provider'
  if (stage === 'Approved') return fmlaCase?.return_to_work_date ? 'RTW planning' : 'Return-to-work planning'
  if (stage === 'Denied') return 'Internal review'
  if (stage === 'Closed / RTW') return 'No one'
  return 'Case manager'
}

export const getNextActionLabel = (fmlaCase, documents = [], correspondence = [], reminders = []) => {
  const stage = getCurrentWorkflowStage(fmlaCase, documents, correspondence)
  const nextDue = getNextDueDate(fmlaCase, reminders)
  if (nextDue?.state?.daysUntil != null && nextDue.state.daysUntil <= 0) {
    return `Address overdue item: ${nextDue.label}`
  }
  switch (stage) {
    case 'Case Opened':
      return 'Contact employer / FMLA company'
    case 'Employer Contacted':
      return 'Request employer packet'
    case 'Packet Requested':
      return 'Follow up until packet is received'
    case 'Packet Received':
      return 'Review packet and send to provider'
    case 'Sent to Provider':
      return 'Follow up with provider for completion'
    case 'Provider Completed':
      return 'Return completed documents to employer'
    case 'Returned to Employer':
      return fmlaCase?.confirmation_received ? 'Track decision outcome' : 'Confirm employer receipt'
    case 'Decision Pending':
      return 'Monitor decision / respond to info requests'
    case 'Approved':
      return fmlaCase?.return_to_work_date ? 'Prepare RTW follow-up' : 'Set RTW or extension plan'
    case 'Denied':
      return 'Review denial and determine next steps'
    case 'Closed / RTW':
      return 'Case closed unless extension is needed'
    default:
      return 'Review case'
  }
}

export const getActionBucket = (fmlaCase, documents = [], correspondence = [], reminders = []) => {
  const stage = getCurrentWorkflowStage(fmlaCase, documents, correspondence)
  const nextDue = getNextDueDate(fmlaCase, reminders)
  if ((stage === 'Approved' || normalize(fmlaCase?.fmla_request_type).toLowerCase() === 'extension') && !fmlaCase?.return_to_work_date) {
    return 'rtw_extension_needed'
  }
  if (nextDue?.state?.daysUntil != null && nextDue.state.daysUntil <= 3) {
    return 'due_within_3_days'
  }
  if (stage === 'Provider Completed') return 'ready_to_submit'
  if (stage === 'Sent to Provider') return 'provider_docs_pending'
  if (stage === 'Packet Requested') return 'packet_not_received'
  if (stage === 'Employer Contacted' || stage === 'Returned to Employer' || stage === 'Decision Pending') {
    return 'employer_follow_up'
  }
  return 'monitoring'
}

export const getWorkflowSnapshot = (fmlaCase, documents = [], correspondence = [], reminders = []) => {
  const stage = getCurrentWorkflowStage(fmlaCase, documents, correspondence)
  const nextDue = getNextDueDate(fmlaCase, reminders)
  const lastContactDate = getLastContactDate(fmlaCase, correspondence, documents)
  const actionBucket = getActionBucket(fmlaCase, documents, correspondence, reminders)
  return {
    stage,
    waitingOn: getWaitingOnLabel(fmlaCase, documents, correspondence),
    nextAction: getNextActionLabel(fmlaCase, documents, correspondence, reminders),
    nextDue,
    lastContactDate,
    actionBucket,
    actionBucketLabel: WORKFLOW_ACTION_BUCKETS[actionBucket] || WORKFLOW_ACTION_BUCKETS.monitoring
  }
}

export const filterFmlaCases = (cases, filters) => {
  const search = normalize(filters.search).toLowerCase()
  const employer = normalize(filters.employer).toLowerCase()
  const status = normalize(filters.status).toLowerCase()
  const caseManager = normalize(filters.case_manager).toLowerCase()
  const deadline = normalize(filters.deadline)
  const subjectType = normalize(filters.case_subject_type).toLowerCase()
  const workflowBucket = normalize(filters.workflow_bucket).toLowerCase()
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const nextWeek = new Date(today)
  nextWeek.setDate(today.getDate() + 7)

  const matchesRange = (rawDate) => {
    if (!rawDate) return false
    const due = new Date(rawDate)
    due.setHours(0, 0, 0, 0)
    if (deadline === 'next_7_days') return due >= today && due <= nextWeek
    if (deadline === 'overdue') return due < today
    return true
  }

  return (cases || []).filter((item) => {
    const haystack = [
      item.client_name,
      item.staff_name,
      item.staff_identifier,
      item.employer_name,
      item.assigned_case_manager,
      item.status
    ].join(' ').toLowerCase()

    if (search && !haystack.includes(search)) return false
    if (employer && !(item.employer_name || '').toLowerCase().includes(employer)) return false
    if (status && (item.status || '').toLowerCase() !== status) return false
    if (caseManager && !(item.assigned_case_manager || '').toLowerCase().includes(caseManager)) return false
    if (subjectType && (item.case_subject_type || 'client').toLowerCase() !== subjectType) return false
    if (workflowBucket) {
      const workflow = getWorkflowSnapshot(item)
      if ((workflow.actionBucket || '').toLowerCase() !== workflowBucket) return false
    }

    if (deadline) {
      return [
        item.paperwork_deadline,
        item.employer_response_deadline,
        item.certification_expiration_date,
        item.return_to_work_date
      ].some(matchesRange)
    }

    return true
  })
}

export const getMissingChecklist = (fmlaCase, documents = []) => {
  const missing = []
  if (!fmlaCase?.paperwork_received_date) missing.push('Paperwork not received')
  if (!fmlaCase?.paperwork_completed_date) missing.push('Paperwork not completed')
  if (!fmlaCase?.paperwork_sent_date) missing.push('Paperwork not sent')
  if (!fmlaCase?.confirmation_received) missing.push('Confirmation not received')
  if (!fmlaCase?.expected_return_date) missing.push('Expected return date not set')
  if ((fmlaCase?.leave_type || '').toLowerCase() === 'intermittent' && !fmlaCase?.certification_expiration_date) {
    missing.push('Certification expiration date not set')
  }
  if ((fmlaCase?.case_subject_type || 'client').toLowerCase() === 'client' && !documents.some((doc) => doc.document_type === 'ROI')) {
    missing.push('ROI not logged')
  }
  if (documents.some((doc) => ['needed', 'requested'].includes((doc.document_status || '').toLowerCase()))) {
    missing.push('Open document requests')
  }
  return missing
}
