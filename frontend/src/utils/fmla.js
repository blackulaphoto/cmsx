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

export const getFmlaStatusBadgeClass = (status) => {
  const normalized = normalize(status)
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

export const filterFmlaCases = (cases, filters) => {
  const search = normalize(filters.search).toLowerCase()
  const employer = normalize(filters.employer).toLowerCase()
  const status = normalize(filters.status).toLowerCase()
  const caseManager = normalize(filters.case_manager).toLowerCase()
  const deadline = normalize(filters.deadline)
  const subjectType = normalize(filters.case_subject_type).toLowerCase()
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
