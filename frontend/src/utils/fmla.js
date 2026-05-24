export const FMLA_STATUS_BADGES = {
  Draft: 'bg-slate-500/20 text-slate-200 border-slate-400/30',
  'Waiting on client': 'bg-amber-500/20 text-amber-200 border-amber-400/30',
  'Waiting on employer': 'bg-orange-500/20 text-orange-200 border-orange-400/30',
  'Waiting on provider': 'bg-yellow-500/20 text-yellow-200 border-yellow-400/30',
  'Paperwork received': 'bg-blue-500/20 text-blue-200 border-blue-400/30',
  'Paperwork sent': 'bg-cyan-500/20 text-cyan-200 border-cyan-400/30',
  'Confirmation pending': 'bg-purple-500/20 text-purple-200 border-purple-400/30',
  Approved: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/30',
  Denied: 'bg-rose-500/20 text-rose-200 border-rose-400/30',
  'Extension needed': 'bg-fuchsia-500/20 text-fuchsia-200 border-fuchsia-400/30',
  Closed: 'bg-zinc-500/20 text-zinc-200 border-zinc-400/30'
}

export const getFmlaStatusBadgeClass = (status) => {
  return FMLA_STATUS_BADGES[status] || 'bg-slate-500/20 text-slate-200 border-slate-400/30'
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

export const filterFmlaCases = (cases, filters) => {
  const search = (filters.search || '').trim().toLowerCase()
  const employer = (filters.employer || '').trim().toLowerCase()
  const status = (filters.status || '').trim()
  const caseManager = (filters.case_manager || '').trim().toLowerCase()
  const deadline = (filters.deadline || '').trim()
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const nextWeek = new Date(today)
  nextWeek.setDate(today.getDate() + 7)

  return (cases || []).filter((item) => {
    const haystack = [
      item.client_name,
      item.employer_name,
      item.assigned_case_manager,
      item.status
    ].join(' ').toLowerCase()

    if (search && !haystack.includes(search)) return false
    if (employer && !(item.employer_name || '').toLowerCase().includes(employer)) return false
    if (status && item.status !== status) return false
    if (caseManager && !(item.assigned_case_manager || '').toLowerCase().includes(caseManager)) return false

    if (deadline === 'next_7_days') {
      if (!item.paperwork_deadline) return false
      const due = new Date(item.paperwork_deadline)
      due.setHours(0, 0, 0, 0)
      return due >= today && due <= nextWeek
    }

    if (deadline === 'overdue') {
      if (!item.paperwork_deadline) return false
      const due = new Date(item.paperwork_deadline)
      due.setHours(0, 0, 0, 0)
      return due < today
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
  if (!documents.some((doc) => doc.document_type === 'ROI')) missing.push('ROI not logged')
  if (documents.some((doc) => ['needed', 'requested'].includes((doc.document_status || '').toLowerCase()))) {
    missing.push('Open document requests')
  }
  return missing
}
