import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  BellRing,
  Building2,
  CalendarClock,
  ClipboardList,
  Download,
  FileSpreadsheet,
  FileText,
  MessageSquare,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Upload,
  Users
} from 'lucide-react'
import toast from 'react-hot-toast'

import ClientSelector from '../components/ClientSelector'
import DocumentationAssistPanel from '../components/DocumentationAssistPanel'
import { apiFetch } from '../api/config'
import { useAuth } from '../contexts/AuthContext'
import {
  filterFmlaCases,
  formatFmlaLabel,
  getCaseDisplayName,
  getDeadlineBuckets,
  getDeadlineState,
  getFmlaStatusBadgeClass,
  getMissingChecklist,
  getSubjectBadge
} from '../utils/fmla'

const STATUS_OPTIONS = ['draft', 'pending documents', 'submitted', 'approved', 'denied', 'expired', 'closed']
const APPROVAL_OPTIONS = ['pending', 'approved', 'denied', 'needs more information', 'expired', 'closed']
const LEAVE_TYPES = ['continuous', 'intermittent', 'reduced schedule']
const REQUEST_TYPES = ['new request', 'extension', 'recertification', 'return-to-work', 'intermittent leave']
const TAB_OPTIONS = ['overview', 'documents', 'reminders', 'correspondence', 'intermittent usage', 'exports']

const emptyCaseForm = () => ({
  case_subject_type: 'client',
  client_id: '',
  client_name: '',
  staff_identifier: '',
  staff_name: '',
  staff_department: '',
  staff_job_title: '',
  date_of_birth: '',
  assigned_case_manager: '',
  treatment_status: '',
  employer_name: '',
  hr_contact_name: '',
  hr_phone: '',
  hr_email: '',
  employer_fax: '',
  employer_address: '',
  preferred_communication_method: 'phone',
  provider_name: '',
  clinic_name: '',
  provider_phone: '',
  provider_fax: '',
  provider_email: '',
  provider_address: '',
  roi_status: 'unknown',
  fmla_request_type: 'new request',
  leave_type: 'continuous',
  leave_start_date: '',
  leave_end_date: '',
  expected_return_date: '',
  employer_response_deadline: '',
  certification_expiration_date: '',
  return_to_work_date: '',
  paperwork_deadline: '',
  paperwork_received_date: '',
  paperwork_completed_date: '',
  paperwork_sent_date: '',
  paperwork_sent_method: 'fax',
  confirmation_received: false,
  approval_status: 'pending',
  status: 'draft',
  notes: '',
  internal_comments: ''
})

const emptyDocumentForm = () => ({
  batch_id: '',
  batch_name: '',
  document_type: 'employer packet',
  document_status: 'needed',
  file_name: '',
  file_path: '',
  file_size: 0,
  content_type: '',
  date_requested: '',
  date_received: '',
  date_completed: '',
  date_sent: '',
  sent_to: '',
  sent_by: '',
  confirmation_number: '',
  notes: ''
})

const emptyCorrespondenceForm = () => ({
  correspondence_at: new Date().toISOString().slice(0, 16),
  contact_type: 'phone',
  person_contacted: '',
  organization: '',
  contact_information: '',
  summary: '',
  outcome: '',
  next_step_needed: '',
  follow_up_date: '',
  staff_member: ''
})

const emptyReminderForm = () => ({
  reminder_text: '',
  due_date: '',
  priority: 'Medium',
  case_manager_id: '',
  reason: ''
})

const emptyLeaveUsageForm = () => ({
  usage_date: new Date().toISOString().slice(0, 10),
  duration_minutes: 60,
  reason_category: 'flare-up',
  notes: ''
})

const emptyExportForm = () => ({
  export_type: 'employer packet',
  custom_instructions: '',
  draft_title: '',
  draft_content: '',
  review_notes: '',
  warning_text: '',
  export_id: ''
})

const Field = ({ label, children, hint }) => (
  <label className="space-y-2 block">
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm font-medium text-slate-200">{label}</span>
      {hint ? <span className="text-xs text-slate-400">{hint}</span> : null}
    </div>
    {children}
  </label>
)

const Input = (props) => (
  <input
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none ${props.className || ''}`}
  />
)

const Textarea = (props) => (
  <textarea
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none ${props.className || ''}`}
  />
)

const Select = (props) => (
  <select
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white focus:border-cyan-400 focus:outline-none ${props.className || ''}`}
  />
)

const formatFileSize = (size = 0) => {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function FMLA() {
  const { profile } = useAuth()
  const canManageStaff = profile?.role === 'admin'
  const defaultCaseManagerId = profile?.case_manager_id || ''
  const [searchParams, setSearchParams] = useSearchParams()
  const [summary, setSummary] = useState({
    total_active_cases: 0,
    deadlines_next_7_days: 0,
    missing_paperwork: 0,
    needing_follow_up: 0,
    approved_cases: 0,
    denied_cases: 0
  })
  const [cases, setCases] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState(null)
  const [selectedCase, setSelectedCase] = useState(null)
  const [documents, setDocuments] = useState([])
  const [correspondence, setCorrespondence] = useState([])
  const [reminders, setReminders] = useState([])
  const [leaveUsage, setLeaveUsage] = useState([])
  const [leaveUsageSummary, setLeaveUsageSummary] = useState({ total_minutes: 0, total_hours: 0, entry_count: 0 })
  const [exportsList, setExportsList] = useState([])
  const [auditLog, setAuditLog] = useState([])
  const [activeTab, setActiveTab] = useState('overview')
  const [filters, setFilters] = useState({
    search: searchParams.get('search') || '',
    status: searchParams.get('status') || '',
    employer: searchParams.get('employer') || '',
    deadline: searchParams.get('deadline') || '',
    case_manager: searchParams.get('case_manager') || defaultCaseManagerId,
    case_subject_type: searchParams.get('case_subject_type') || ''
  })
  const [caseForm, setCaseForm] = useState(emptyCaseForm())
  const [documentForm, setDocumentForm] = useState(emptyDocumentForm())
  const [correspondenceForm, setCorrespondenceForm] = useState(emptyCorrespondenceForm())
  const [reminderForm, setReminderForm] = useState(emptyReminderForm())
  const [leaveUsageForm, setLeaveUsageForm] = useState(emptyLeaveUsageForm())
  const [exportForm, setExportForm] = useState(emptyExportForm())
  const [selectedUploads, setSelectedUploads] = useState([])
  const [documentInputKey, setDocumentInputKey] = useState(0)
  const [creatingNewCase, setCreatingNewCase] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)

  const visibleCases = useMemo(() => filterFmlaCases(cases, filters), [cases, filters])
  const missingChecklist = useMemo(() => getMissingChecklist(selectedCase || caseForm, documents), [selectedCase, caseForm, documents])
  const deadlineBuckets = useMemo(() => getDeadlineBuckets(selectedCase || caseForm, reminders), [selectedCase, caseForm, reminders])
  const deadlineState = getDeadlineState(selectedCase?.paperwork_deadline || caseForm.paperwork_deadline)
  const currentDisplayName = getCaseDisplayName(selectedCase || caseForm)

  useEffect(() => {
    loadSummary()
  }, [])

  useEffect(() => {
    if (!defaultCaseManagerId) return
    setFilters((current) => ({ ...current, case_manager: current.case_manager || defaultCaseManagerId }))
    setCaseForm((current) => ({ ...current, assigned_case_manager: current.assigned_case_manager || defaultCaseManagerId }))
    setCorrespondenceForm((current) => ({ ...current, staff_member: current.staff_member || profile?.full_name || defaultCaseManagerId }))
    setReminderForm((current) => ({ ...current, case_manager_id: current.case_manager_id || defaultCaseManagerId }))
  }, [defaultCaseManagerId, profile?.full_name])

  useEffect(() => {
    loadCases()
    const next = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value) next.set(key, value)
    })
    setSearchParams(next, { replace: true })
  }, [filters])

  useEffect(() => {
    if (selectedCaseId) {
      loadCaseDetail(selectedCaseId)
      setCreatingNewCase(false)
    } else {
      setSelectedCase(null)
      setDocuments([])
      setCorrespondence([])
      setReminders([])
      setLeaveUsage([])
      setLeaveUsageSummary({ total_minutes: 0, total_hours: 0, entry_count: 0 })
      setExportsList([])
      setAuditLog([])
    }
  }, [selectedCaseId])

  const loadSummary = async () => {
    try {
      const response = await apiFetch(`/api/fmla/summary?case_manager_id=${encodeURIComponent(defaultCaseManagerId)}`)
      if (!response.ok) throw new Error('Failed to load FMLA summary')
      const data = await response.json()
      if (data.success) {
        setSummary({
          total_active_cases: data.total_active_cases || 0,
          deadlines_next_7_days: data.deadlines_next_7_days || 0,
          missing_paperwork: data.missing_paperwork || 0,
          needing_follow_up: data.needing_follow_up || 0,
          approved_cases: data.approved_cases || 0,
          denied_cases: data.denied_cases || 0
        })
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load FMLA summary')
    }
  }

  const loadCases = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, value)
      })
      const response = await apiFetch(`/api/fmla?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load FMLA cases')
      const data = await response.json()
      setCases(data.cases || [])
      if (!selectedCaseId && (data.cases || []).length > 0) {
        setSelectedCaseId(data.cases[0].case_id)
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load FMLA cases')
    } finally {
      setLoading(false)
    }
  }

  const loadCaseDetail = async (caseId) => {
    try {
      const response = await apiFetch(`/api/fmla/${caseId}`)
      if (!response.ok) throw new Error('Failed to load FMLA case detail')
      const data = await response.json()
      setSelectedCase(data.case || null)
      setCaseForm({ ...emptyCaseForm(), ...(data.case || {}) })
      setDocuments(data.documents || [])
      setCorrespondence(data.correspondence || [])
      setReminders(data.reminders || [])
      setLeaveUsage(data.leave_usage || [])
      setLeaveUsageSummary(data.leave_usage_summary || { total_minutes: 0, total_hours: 0, entry_count: 0 })
      setExportsList(data.exports || [])
      setAuditLog(data.audit_log || [])
      if ((data.exports || [])[0]) {
        setExportForm({
          export_type: data.exports[0].export_type || 'employer packet',
          custom_instructions: '',
          draft_title: data.exports[0].draft_title || '',
          draft_content: data.exports[0].draft_content || '',
          review_notes: data.exports[0].review_notes || '',
          warning_text: data.exports[0].warning_text || '',
          export_id: data.exports[0].export_id || ''
        })
      } else {
        setExportForm(emptyExportForm())
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load FMLA case detail')
    }
  }

  const updateCaseForm = (field, value) => {
    setCaseForm((prev) => {
      const next = { ...prev, [field]: value }
      if (field === 'case_subject_type' && value === 'client') {
        next.staff_identifier = ''
        next.staff_name = ''
        next.staff_department = ''
        next.staff_job_title = ''
        next.roi_status = prev.roi_status === 'not needed' ? 'unknown' : prev.roi_status
      }
      if (field === 'case_subject_type' && value === 'staff') {
        next.client_id = ''
        next.date_of_birth = ''
        next.treatment_status = ''
        next.roi_status = 'not needed'
      }
      return next
    })
  }

  const handleClientSelected = (client) => {
    if (!creatingNewCase || caseForm.case_subject_type !== 'client') return
    setCaseForm((prev) => ({
      ...prev,
      client_id: client.client_id || '',
      client_name: `${client.first_name || ''} ${client.last_name || ''}`.trim(),
      date_of_birth: client.date_of_birth || '',
      assigned_case_manager: client.case_manager_id || prev.assigned_case_manager,
      treatment_status: client.case_status || ''
    }))
  }

  const startNewCase = (subjectType = 'client') => {
    setCreatingNewCase(true)
    setSelectedCaseId(null)
    setCaseForm({
      ...emptyCaseForm(),
      case_subject_type: subjectType,
      assigned_case_manager: defaultCaseManagerId
    })
    setActiveTab('overview')
    setDocuments([])
    setCorrespondence([])
    setReminders([])
    setLeaveUsage([])
    setExportsList([])
    setAuditLog([])
    setExportForm(emptyExportForm())
  }

  const saveCase = async () => {
    const subjectType = (caseForm.case_subject_type || 'client').toLowerCase()
    if (subjectType === 'client' && !caseForm.client_name.trim()) {
      toast.error('Client name is required')
      return
    }
    if (subjectType === 'staff' && !(caseForm.staff_name || caseForm.staff_identifier).trim()) {
      toast.error('Staff name or staff identifier is required')
      return
    }

    setSaving(true)
    try {
      const payload = {
        ...caseForm,
        client_name: subjectType === 'staff'
          ? (caseForm.staff_name || caseForm.staff_identifier || caseForm.client_name)
          : caseForm.client_name
      }
      const method = creatingNewCase ? 'POST' : 'PUT'
      const endpoint = creatingNewCase ? '/api/fmla' : `/api/fmla/${selectedCaseId}`
      const response = await apiFetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!response.ok) throw new Error('Failed to save FMLA case')
      const data = await response.json()
      toast.success(creatingNewCase ? 'FMLA case created' : 'FMLA case updated')
      await loadSummary()
      await loadCases()
      setSelectedCaseId(data.case.case_id)
      setCreatingNewCase(false)
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to save FMLA case')
    } finally {
      setSaving(false)
    }
  }

  const addDocument = async () => {
    if (!selectedCaseId) {
      toast.error('Select or create an FMLA case first')
      return
    }
    try {
      let response
      if (selectedUploads.length > 0) {
        const formData = new FormData()
        selectedUploads.forEach((file) => formData.append('files', file))
        Object.entries(documentForm).forEach(([key, value]) => {
          if (!['file_name', 'file_path', 'file_size', 'content_type'].includes(key)) formData.append(key, value ?? '')
        })
        response = await apiFetch(`/api/fmla/${selectedCaseId}/documents/upload`, {
          method: 'POST',
          body: formData
        })
      } else {
        response = await apiFetch(`/api/fmla/${selectedCaseId}/documents`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(documentForm)
        })
      }
      if (!response.ok) throw new Error('Failed to add document')
      await loadCaseDetail(selectedCaseId)
      setDocumentForm(emptyDocumentForm())
      setSelectedUploads([])
      setDocumentInputKey((prev) => prev + 1)
      loadSummary()
      toast.success(selectedUploads.length > 0 ? 'Files uploaded' : 'Document entry added')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to add document')
    }
  }

  const addCorrespondence = async () => {
    if (!selectedCaseId || !correspondenceForm.summary.trim()) {
      toast.error('Summary is required')
      return
    }
    try {
      const response = await apiFetch(`/api/fmla/${selectedCaseId}/correspondence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(correspondenceForm)
      })
      if (!response.ok) throw new Error('Failed to add correspondence')
      await loadCaseDetail(selectedCaseId)
      setCorrespondenceForm(emptyCorrespondenceForm())
      toast.success('Correspondence logged')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to add correspondence')
    }
  }

  const addReminder = async () => {
    if (!selectedCaseId || !reminderForm.reminder_text.trim() || !reminderForm.due_date) {
      toast.error('Reminder text and due date are required')
      return
    }
    try {
      const response = await apiFetch(`/api/fmla/${selectedCaseId}/reminders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reminderForm)
      })
      if (!response.ok) throw new Error('Failed to create reminder')
      await loadCaseDetail(selectedCaseId)
      setReminderForm(emptyReminderForm())
      loadSummary()
      toast.success('Reminder created')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to create reminder')
    }
  }

  const addLeaveUsage = async () => {
    if (!selectedCaseId) {
      toast.error('Select a case first')
      return
    }
    try {
      const response = await apiFetch(`/api/fmla/${selectedCaseId}/leave-usage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...leaveUsageForm,
          duration_minutes: Number(leaveUsageForm.duration_minutes)
        })
      })
      if (!response.ok) throw new Error('Failed to add intermittent leave usage')
      await loadCaseDetail(selectedCaseId)
      setLeaveUsageForm(emptyLeaveUsageForm())
      toast.success('Intermittent leave usage saved')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to add intermittent leave usage')
    }
  }

  const generateDraft = async () => {
    if (!selectedCaseId) {
      toast.error('Select a case first')
      return
    }
    try {
      const response = await apiFetch(`/api/fmla/${selectedCaseId}/exports/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exportForm)
      })
      if (!response.ok) throw new Error('Failed to generate employer packet draft')
      const data = await response.json()
      setExportForm({
        export_type: data.export.export_type || 'employer packet',
        custom_instructions: '',
        draft_title: data.export.draft_title || '',
        draft_content: data.export.draft_content || '',
        review_notes: data.export.review_notes || '',
        warning_text: data.export.warning_text || '',
        export_id: data.export.export_id || ''
      })
      await loadCaseDetail(selectedCaseId)
      toast.success('Draft packet generated for review')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to generate draft')
    }
  }

  const finalizePdfExport = async () => {
    if (!selectedCaseId) {
      toast.error('Select a case first')
      return
    }
    if (!exportForm.export_id) {
      toast.error('Generate a draft before exporting to PDF')
      return
    }
    setExporting(true)
    try {
      const response = await apiFetch(`/api/fmla/${selectedCaseId}/exports/${exportForm.export_id}/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(exportForm)
      })
      if (!response.ok) throw new Error('Failed to export PDF')
      const data = await response.json()
      setExportForm((prev) => ({
        ...prev,
        export_id: data.export.export_id || prev.export_id
      }))
      await loadCaseDetail(selectedCaseId)
      toast.success('PDF export created')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to export PDF')
    } finally {
      setExporting(false)
    }
  }

  const downloadDocument = (documentId) => {
    window.open(`/api/fmla/documents/${documentId}/download`, '_blank', 'noopener,noreferrer')
  }

  const downloadExport = (exportId) => {
    window.open(`/api/fmla/exports/${exportId}/download`, '_blank', 'noopener,noreferrer')
  }

  const summaryCards = [
    { key: 'status', label: 'Active FMLA Cases', value: summary.total_active_cases, filter: { status: '' }, icon: ClipboardList },
    { key: 'deadline', label: 'Due In 7 Days', value: summary.deadlines_next_7_days, filter: { deadline: 'next_7_days' }, icon: CalendarClock },
    { key: 'missing', label: 'Missing Paperwork', value: summary.missing_paperwork, filter: { status: '' }, icon: AlertTriangle },
    { key: 'followup', label: 'Needs Follow-Up', value: summary.needing_follow_up, filter: { status: 'pending documents' }, icon: BellRing },
    { key: 'approved', label: 'Approved', value: summary.approved_cases, filter: { status: 'approved' }, icon: ShieldCheck },
    { key: 'denied', label: 'Denied', value: summary.denied_cases, filter: { status: 'denied' }, icon: AlertTriangle }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-cyan-950 to-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8 space-y-8">
        <section className="rounded-3xl border border-cyan-500/20 bg-slate-900/70 backdrop-blur-xl p-8 shadow-2xl shadow-cyan-900/20">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
                <FileSpreadsheet className="h-4 w-4" />
                FMLA Tracker
              </div>
              <h1 className="mt-4 text-4xl font-bold">FMLA Case File Command Center</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Separate client and staff leave workflows, track deadlines and intermittent usage, and export review-only employer packets.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => startNewCase('client')}
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                <Plus className="h-4 w-4" />
                New Client FMLA Case
              </button>
              {canManageStaff ? (
                <button
                  onClick={() => startNewCase('staff')}
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/20"
                >
                  <Users className="h-4 w-4" />
                  New Staff FMLA Case
                </button>
              ) : null}
              <button
                onClick={() => {
                  loadSummary()
                  loadCases()
                  if (selectedCaseId) loadCaseDetail(selectedCaseId)
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          {summaryCards.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                onClick={() => setFilters((prev) => ({ ...prev, ...item.filter }))}
                className="rounded-2xl border border-white/10 bg-white/5 p-4 text-left transition hover:-translate-y-0.5 hover:bg-white/10"
              >
                <div className="flex items-center justify-between">
                  <div className="rounded-xl bg-cyan-500/15 p-3 text-cyan-200">
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-3xl font-bold">{item.value}</span>
                </div>
                <p className="mt-3 text-sm text-slate-300">{item.label}</p>
              </button>
            )
          })}
        </section>

        <section className="grid grid-cols-1 gap-4 rounded-3xl border border-white/10 bg-white/5 p-6 xl:grid-cols-6">
          <Field label="Search">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input value={filters.search} onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))} placeholder="Client, staff, employer" className="pl-9" />
            </div>
          </Field>
          <Field label="Status">
            <Select value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}>
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{formatFmlaLabel(status)}</option>)}
            </Select>
          </Field>
          <Field label="Employer">
            <Input value={filters.employer} onChange={(e) => setFilters((prev) => ({ ...prev, employer: e.target.value }))} placeholder="Employer name" />
          </Field>
          <Field label="Deadline">
            <Select value={filters.deadline} onChange={(e) => setFilters((prev) => ({ ...prev, deadline: e.target.value }))}>
              <option value="">All deadlines</option>
              <option value="next_7_days">Next 7 days</option>
              <option value="overdue">Overdue</option>
            </Select>
          </Field>
          <Field label="Case Manager">
            <Input value={filters.case_manager} onChange={(e) => setFilters((prev) => ({ ...prev, case_manager: e.target.value }))} />
          </Field>
          <Field label="Workflow">
            <Select value={filters.case_subject_type} onChange={(e) => setFilters((prev) => ({ ...prev, case_subject_type: e.target.value }))}>
              <option value="">All cases</option>
              <option value="client">Client FMLA</option>
              {canManageStaff ? <option value="staff">Staff FMLA</option> : null}
            </Select>
          </Field>
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-3xl border border-white/10 bg-white/5 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">FMLA Cases</h2>
                <p className="text-xs text-slate-400">{visibleCases.length} visible</p>
              </div>
              {loading ? <span className="text-xs text-slate-400">Loading…</span> : null}
            </div>
            <div className="mt-4 space-y-3">
              {visibleCases.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4 text-sm text-slate-300">No FMLA cases match the current filters.</div>
              ) : visibleCases.map((item) => {
                const active = selectedCaseId === item.case_id
                const state = getDeadlineState(item.paperwork_deadline || item.return_to_work_date || item.employer_response_deadline)
                return (
                  <button
                    key={item.case_id}
                    onClick={() => {
                      setSelectedCaseId(item.case_id)
                      setActiveTab('overview')
                    }}
                    className={`w-full rounded-2xl border p-4 text-left transition ${active ? 'border-cyan-400/40 bg-cyan-500/10' : 'border-white/10 bg-slate-950/30 hover:bg-slate-900/40'}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{getCaseDisplayName(item)}</p>
                        <p className="mt-1 text-xs text-slate-400">{item.employer_name || 'Employer not set'}</p>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-[11px] ${getFmlaStatusBadgeClass(item.status)}`}>
                        {formatFmlaLabel(item.status)}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                      <span className={`rounded-full border px-2 py-1 ${getSubjectBadge(item)}`}>
                        {(item.case_subject_type || 'client').toLowerCase() === 'staff' ? 'Staff FMLA' : 'Client FMLA'}
                      </span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-slate-200">
                        {formatFmlaLabel(item.leave_type || 'continuous')}
                      </span>
                    </div>
                    <div className="mt-3 text-xs text-slate-400">{state.label}</div>
                  </button>
                )
              })}
            </div>
          </aside>

          <div className="space-y-6">
            <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-2xl font-semibold">{creatingNewCase ? 'New FMLA Case' : currentDisplayName}</h2>
                  <p className="text-sm text-slate-400">
                    {(caseForm.case_subject_type || 'client') === 'staff'
                      ? 'Staff FMLA is isolated from client records and should only contain HR-safe leave data.'
                      : 'Client FMLA tracks employer contacts, provider paperwork, deadlines, and follow-up activity in one case file.'}
                  </p>
                </div>
                {(selectedCase || creatingNewCase) ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`rounded-full border px-3 py-1 text-xs ${getSubjectBadge(caseForm)}`}>
                      {(caseForm.case_subject_type || 'client') === 'staff' ? 'Staff FMLA' : 'Client FMLA'}
                    </span>
                    <span className={`rounded-full border px-3 py-1 text-xs ${getFmlaStatusBadgeClass(caseForm.status)}`}>{formatFmlaLabel(caseForm.status)}</span>
                    <span className="rounded-full bg-slate-950/40 px-3 py-1 text-xs text-slate-300">{deadlineState.label}</span>
                  </div>
                ) : null}
              </div>

              {creatingNewCase && caseForm.case_subject_type === 'client' ? (
                <div className="mb-6">
                  <ClientSelector onClientSelect={handleClientSelected} placeholder="Link to an existing client" className="max-w-md" />
                </div>
              ) : null}

              {!creatingNewCase && !selectedCase ? (
                <div className="rounded-2xl border border-dashed border-white/15 bg-slate-950/20 p-8 text-sm text-slate-400">
                  Select an FMLA case from the list or create a new one.
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-wrap gap-2">
                    {TAB_OPTIONS.map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`rounded-full px-4 py-2 text-sm transition ${activeTab === tab ? 'bg-cyan-500 text-slate-950 font-semibold' : 'bg-slate-950/40 text-slate-300 hover:bg-slate-950/70'}`}
                      >
                        {formatFmlaLabel(tab)}
                      </button>
                    ))}
                  </div>

                  {activeTab === 'overview' ? (
                    <div className="space-y-8">
                      <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                        <p className="text-sm text-amber-100">
                          Generated drafts and exports are review-only. Do not auto-submit anything to employers or HR. Staff must verify minimum necessary disclosure before finalizing.
                        </p>
                      </div>

                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <Field label="Workflow type">
                          <Select value={caseForm.case_subject_type} onChange={(e) => updateCaseForm('case_subject_type', e.target.value)} disabled={!canManageStaff}>
                            <option value="client">Client FMLA</option>
                            <option value="staff">Staff FMLA</option>
                          </Select>
                        </Field>
                        {caseForm.case_subject_type === 'client' ? (
                          <>
                            <Field label="Client name"><Input value={caseForm.client_name} onChange={(e) => updateCaseForm('client_name', e.target.value)} /></Field>
                            <Field label="Linked client ID"><Input value={caseForm.client_id || ''} readOnly placeholder="Use the selector above" /></Field>
                            <Field label="Date of birth"><Input type="date" value={caseForm.date_of_birth || ''} onChange={(e) => updateCaseForm('date_of_birth', e.target.value)} /></Field>
                          </>
                        ) : (
                          <>
                            <Field label="Staff name"><Input value={caseForm.staff_name || ''} onChange={(e) => updateCaseForm('staff_name', e.target.value)} /></Field>
                            <Field label="Staff identifier"><Input value={caseForm.staff_identifier || ''} onChange={(e) => updateCaseForm('staff_identifier', e.target.value)} placeholder="Employee or HR-safe ID" /></Field>
                            <Field label="Department"><Input value={caseForm.staff_department || ''} onChange={(e) => updateCaseForm('staff_department', e.target.value)} /></Field>
                          </>
                        )}
                        {caseForm.case_subject_type === 'staff' ? (
                          <Field label="Job title"><Input value={caseForm.staff_job_title || ''} onChange={(e) => updateCaseForm('staff_job_title', e.target.value)} /></Field>
                        ) : (
                          <Field label="Treatment/program status"><Input value={caseForm.treatment_status || ''} onChange={(e) => updateCaseForm('treatment_status', e.target.value)} /></Field>
                        )}
                        <Field label="Assigned case manager"><Input value={caseForm.assigned_case_manager || ''} onChange={(e) => updateCaseForm('assigned_case_manager', e.target.value)} /></Field>
                        <Field label="FMLA request type">
                          <Select value={caseForm.fmla_request_type} onChange={(e) => updateCaseForm('fmla_request_type', e.target.value)}>
                            {REQUEST_TYPES.map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Leave type">
                          <Select value={caseForm.leave_type} onChange={(e) => updateCaseForm('leave_type', e.target.value)}>
                            {LEAVE_TYPES.map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Status">
                          <Select value={caseForm.status} onChange={(e) => updateCaseForm('status', e.target.value)}>
                            {STATUS_OPTIONS.map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Approval status">
                          <Select value={caseForm.approval_status} onChange={(e) => updateCaseForm('approval_status', e.target.value)}>
                            {APPROVAL_OPTIONS.map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                      </div>

                      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                        <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                          <h3 className="flex items-center gap-2 text-lg font-semibold"><Building2 className="h-5 w-5 text-cyan-300" /> Employer Information</h3>
                          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <Field label="Employer name"><Input value={caseForm.employer_name || ''} onChange={(e) => updateCaseForm('employer_name', e.target.value)} /></Field>
                            <Field label="HR contact name"><Input value={caseForm.hr_contact_name || ''} onChange={(e) => updateCaseForm('hr_contact_name', e.target.value)} /></Field>
                            <Field label="HR phone"><Input value={caseForm.hr_phone || ''} onChange={(e) => updateCaseForm('hr_phone', e.target.value)} /></Field>
                            <Field label="HR email"><Input value={caseForm.hr_email || ''} onChange={(e) => updateCaseForm('hr_email', e.target.value)} /></Field>
                            <Field label="Employer fax"><Input value={caseForm.employer_fax || ''} onChange={(e) => updateCaseForm('employer_fax', e.target.value)} /></Field>
                            <Field label="Preferred communication method">
                              <Select value={caseForm.preferred_communication_method || ''} onChange={(e) => updateCaseForm('preferred_communication_method', e.target.value)}>
                                {['phone', 'email', 'fax', 'mail', 'portal'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                              </Select>
                            </Field>
                            <div className="md:col-span-2">
                              <Field label="Employer address"><Textarea rows={2} value={caseForm.employer_address || ''} onChange={(e) => updateCaseForm('employer_address', e.target.value)} /></Field>
                            </div>
                          </div>
                        </div>

                        <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                          <h3 className="flex items-center gap-2 text-lg font-semibold"><ShieldCheck className="h-5 w-5 text-cyan-300" /> Provider and Compliance</h3>
                          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                            <Field label="Provider / doctor name"><Input value={caseForm.provider_name || ''} onChange={(e) => updateCaseForm('provider_name', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            <Field label="Clinic / facility name"><Input value={caseForm.clinic_name || ''} onChange={(e) => updateCaseForm('clinic_name', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            <Field label="Provider phone"><Input value={caseForm.provider_phone || ''} onChange={(e) => updateCaseForm('provider_phone', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            <Field label="Provider fax"><Input value={caseForm.provider_fax || ''} onChange={(e) => updateCaseForm('provider_fax', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            <Field label="Provider email"><Input value={caseForm.provider_email || ''} onChange={(e) => updateCaseForm('provider_email', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            <Field label="ROI status">
                              <Select value={caseForm.roi_status || ''} onChange={(e) => updateCaseForm('roi_status', e.target.value)} disabled={caseForm.case_subject_type === 'staff'}>
                                {['unknown', 'not needed', 'needed', 'requested', 'received', 'expired'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                              </Select>
                            </Field>
                            <div className="md:col-span-2">
                              <Field label="Provider address"><Textarea rows={2} value={caseForm.provider_address || ''} onChange={(e) => updateCaseForm('provider_address', e.target.value)} disabled={caseForm.case_subject_type === 'staff'} /></Field>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                        <h3 className="flex items-center gap-2 text-lg font-semibold"><CalendarClock className="h-5 w-5 text-cyan-300" /> FMLA Details and Deadlines</h3>
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                          <Field label="Leave start date"><Input type="date" value={caseForm.leave_start_date || ''} onChange={(e) => updateCaseForm('leave_start_date', e.target.value)} /></Field>
                          <Field label="Leave end date"><Input type="date" value={caseForm.leave_end_date || ''} onChange={(e) => updateCaseForm('leave_end_date', e.target.value)} /></Field>
                          <Field label="Expected return date"><Input type="date" value={caseForm.expected_return_date || ''} onChange={(e) => updateCaseForm('expected_return_date', e.target.value)} /></Field>
                          <Field label="Return-to-work date"><Input type="date" value={caseForm.return_to_work_date || ''} onChange={(e) => updateCaseForm('return_to_work_date', e.target.value)} /></Field>
                          <Field label="Paperwork due"><Input type="date" value={caseForm.paperwork_deadline || ''} onChange={(e) => updateCaseForm('paperwork_deadline', e.target.value)} /></Field>
                          <Field label="Employer response deadline"><Input type="date" value={caseForm.employer_response_deadline || ''} onChange={(e) => updateCaseForm('employer_response_deadline', e.target.value)} /></Field>
                          <Field label="Certification expiration"><Input type="date" value={caseForm.certification_expiration_date || ''} onChange={(e) => updateCaseForm('certification_expiration_date', e.target.value)} /></Field>
                          <Field label="Confirmation received">
                            <Select value={caseForm.confirmation_received ? 'yes' : 'no'} onChange={(e) => updateCaseForm('confirmation_received', e.target.value === 'yes')}>
                              <option value="no">No</option>
                              <option value="yes">Yes</option>
                            </Select>
                          </Field>
                          <Field label="Paperwork received"><Input type="date" value={caseForm.paperwork_received_date || ''} onChange={(e) => updateCaseForm('paperwork_received_date', e.target.value)} /></Field>
                          <Field label="Paperwork completed"><Input type="date" value={caseForm.paperwork_completed_date || ''} onChange={(e) => updateCaseForm('paperwork_completed_date', e.target.value)} /></Field>
                          <Field label="Paperwork sent"><Input type="date" value={caseForm.paperwork_sent_date || ''} onChange={(e) => updateCaseForm('paperwork_sent_date', e.target.value)} /></Field>
                          <Field label="Method sent">
                            <Select value={caseForm.paperwork_sent_method || ''} onChange={(e) => updateCaseForm('paperwork_sent_method', e.target.value)}>
                              {['fax', 'email', 'mail', 'portal', 'hand-delivered'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                            </Select>
                          </Field>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                          <h3 className="mb-4 text-lg font-semibold">Case Summary</h3>
                          <div className="space-y-3 text-sm">
                            <div className="flex justify-between gap-4"><span className="text-slate-400">Primary deadline</span><span>{deadlineState.label}</span></div>
                            <div className="flex justify-between gap-4"><span className="text-slate-400">Employer</span><span className="text-right">{caseForm.employer_name || 'Not added'}</span></div>
                            <div className="flex justify-between gap-4"><span className="text-slate-400">Leave type</span><span className="text-right">{formatFmlaLabel(caseForm.leave_type)}</span></div>
                            <div className="flex justify-between gap-4"><span className="text-slate-400">Request type</span><span className="text-right">{formatFmlaLabel(caseForm.fmla_request_type)}</span></div>
                          </div>
                          <div className="mt-6 rounded-2xl bg-slate-950/30 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Missing items</p>
                            <ul className="mt-3 space-y-2 text-sm">
                              {missingChecklist.length === 0 ? <li className="text-emerald-300">No missing items flagged.</li> : missingChecklist.map((item) => <li key={item} className="text-amber-200">• {item}</li>)}
                            </ul>
                          </div>
                        </div>

                        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 xl:col-span-2">
                          <h3 className="text-lg font-semibold">Notes and internal comments</h3>
                          <div className="mt-4 space-y-4">
                            <Field label="Case notes">
                              <Textarea rows={4} value={caseForm.notes || ''} onChange={(e) => updateCaseForm('notes', e.target.value)} placeholder="Summary that can support the leave workflow." />
                            </Field>
                            <DocumentationAssistPanel
                              module="fmla"
                              noteKind="fmla_case_note"
                              clientId={caseForm.client_id || ''}
                              clientName={caseForm.client_name || caseForm.staff_name || ''}
                              currentText={caseForm.notes || ''}
                              context={{
                                goals: caseForm.fmla_request_type,
                                observations: `Status: ${caseForm.status}; Leave type: ${caseForm.leave_type}; Employer: ${caseForm.employer_name}`,
                                next_steps: `Paperwork due ${caseForm.paperwork_deadline || 'not set'}, return to work ${caseForm.return_to_work_date || 'not set'}`,
                                paperwork_deadline: caseForm.paperwork_deadline
                              }}
                              onApplyDraft={(draft) => updateCaseForm('notes', draft)}
                            />
                            <Field label="Internal case manager comments" hint="Not for employer-facing exports">
                              <Textarea rows={4} value={caseForm.internal_comments || ''} onChange={(e) => updateCaseForm('internal_comments', e.target.value)} placeholder="Internal coordination notes, blockers, and review comments." />
                            </Field>
                          </div>
                        </div>
                      </div>

                      {auditLog.length > 0 ? (
                        <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5">
                          <h3 className="text-lg font-semibold">Recent audit activity</h3>
                          <div className="mt-4 space-y-3">
                            {auditLog.slice(0, 5).map((entry) => (
                              <div key={entry.audit_id} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-medium">{formatFmlaLabel(entry.action)}</span>
                                  <span className="text-xs text-slate-400">{new Date(entry.created_at).toLocaleString()}</span>
                                </div>
                                <p className="mt-1 text-xs text-slate-400">{entry.actor_name || entry.actor_case_manager_id}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="flex flex-wrap gap-3">
                        <button onClick={saveCase} disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60">
                          <Save className="h-4 w-4" />
                          {saving ? 'Saving…' : creatingNewCase ? 'Create FMLA Case' : 'Save FMLA Case'}
                        </button>
                        {creatingNewCase ? (
                          <button onClick={() => { setCreatingNewCase(false); setCaseForm(emptyCaseForm()) }} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold transition hover:bg-white/10">
                            Cancel
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ) : null}

                  {activeTab === 'documents' ? (
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold">Attachments and document log</h3>
                        <span className="text-xs text-slate-400">Files persist to backend storage with uploader metadata</span>
                      </div>
                      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Field label="Document type">
                          <Select value={documentForm.document_type} onChange={(e) => setDocumentForm((prev) => ({ ...prev, document_type: e.target.value }))}>
                            {['employer packet', 'medical certification', 'ROI', 'provider letter', 'extension form', 'denial letter', 'approval letter', 'return-to-work form', 'other'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Status">
                          <Select value={documentForm.document_status} onChange={(e) => setDocumentForm((prev) => ({ ...prev, document_status: e.target.value }))}>
                            {['needed', 'requested', 'received', 'completed', 'sent', 'confirmed'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Packet name"><Input value={documentForm.batch_name} onChange={(e) => setDocumentForm((prev) => ({ ...prev, batch_name: e.target.value }))} placeholder="Initial employer packet" /></Field>
                        <Field label="Date requested"><Input type="date" value={documentForm.date_requested} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_requested: e.target.value }))} /></Field>
                        <Field label="Date received"><Input type="date" value={documentForm.date_received} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_received: e.target.value }))} /></Field>
                        <Field label="Date completed"><Input type="date" value={documentForm.date_completed} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_completed: e.target.value }))} /></Field>
                        <Field label="Date sent"><Input type="date" value={documentForm.date_sent} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_sent: e.target.value }))} /></Field>
                        <Field label="Sent to"><Input value={documentForm.sent_to} onChange={(e) => setDocumentForm((prev) => ({ ...prev, sent_to: e.target.value }))} /></Field>
                        <Field label="Sent by"><Input value={documentForm.sent_by} onChange={(e) => setDocumentForm((prev) => ({ ...prev, sent_by: e.target.value }))} /></Field>
                        <Field label="Confirmation number"><Input value={documentForm.confirmation_number} onChange={(e) => setDocumentForm((prev) => ({ ...prev, confirmation_number: e.target.value }))} /></Field>
                        <Field label="Upload document(s)">
                          <input
                            key={documentInputKey}
                            type="file"
                            multiple
                            onChange={(e) => {
                              const files = Array.from(e.target.files || [])
                              setSelectedUploads(files)
                              setDocumentForm((prev) => ({
                                ...prev,
                                file_name: files.map((file) => file.name).join(', '),
                                file_size: files.reduce((total, file) => total + (file.size || 0), 0),
                                content_type: files.length === 1 ? (files[0].type || '') : 'multiple'
                              }))
                            }}
                            className="w-full rounded-xl border border-dashed border-white/15 bg-slate-950/50 px-3 py-2 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-cyan-500 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-cyan-400"
                          />
                        </Field>
                        <div className="md:col-span-2">
                          <Field label="Notes"><Textarea rows={3} value={documentForm.notes} onChange={(e) => setDocumentForm((prev) => ({ ...prev, notes: e.target.value }))} /></Field>
                        </div>
                      </div>
                      <button onClick={addDocument} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400">
                        {selectedUploads.length > 0 ? <Upload className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                        {selectedUploads.length > 0 ? `Upload ${selectedUploads.length} File(s)` : 'Add Document Entry'}
                      </button>
                      <div className="mt-6 space-y-3">
                        {documents.length === 0 ? (
                          <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No document entries yet.</div>
                        ) : documents.map((doc) => (
                          <div key={doc.document_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <p className="font-medium">{doc.batch_name || doc.document_type}</p>
                                <p className="mt-1 text-xs text-slate-400">
                                  {doc.file_name || 'Checklist-only entry'} {doc.file_size ? `• ${formatFileSize(doc.file_size)}` : ''}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="rounded-full bg-cyan-500/20 px-2 py-1 text-xs text-cyan-200 capitalize">{doc.document_status}</span>
                                {doc.file_path ? (
                                  <button onClick={() => downloadDocument(doc.document_id)} className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white transition hover:bg-white/10">
                                    <Download className="h-3.5 w-3.5" />
                                    Download
                                  </button>
                                ) : null}
                              </div>
                            </div>
                            <p className="mt-2 text-xs text-slate-400">
                              Uploaded {doc.created_at ? new Date(doc.created_at).toLocaleString() : '—'} • Uploader {doc.uploader_name || '—'}
                            </p>
                            {doc.notes ? <p className="mt-2 text-sm text-slate-300">{doc.notes}</p> : null}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {activeTab === 'reminders' ? (
                    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Create reminder</h3>
                        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                          <Field label="Reminder text"><Input value={reminderForm.reminder_text} onChange={(e) => setReminderForm((prev) => ({ ...prev, reminder_text: e.target.value }))} placeholder="Follow up with HR" /></Field>
                          <Field label="Reason"><Input value={reminderForm.reason} onChange={(e) => setReminderForm((prev) => ({ ...prev, reason: e.target.value }))} placeholder="Paperwork due date" /></Field>
                          <Field label="Due date"><Input type="date" value={reminderForm.due_date} onChange={(e) => setReminderForm((prev) => ({ ...prev, due_date: e.target.value }))} /></Field>
                          <Field label="Priority">
                            <Select value={reminderForm.priority} onChange={(e) => setReminderForm((prev) => ({ ...prev, priority: e.target.value }))}>
                              {['Low', 'Medium', 'High', 'Critical'].map((item) => <option key={item} value={item}>{item}</option>)}
                            </Select>
                          </Field>
                        </div>
                        <button onClick={addReminder} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-violet-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-violet-400">
                          <BellRing className="h-4 w-4" />
                          Create FMLA Reminder
                        </button>
                        <div className="mt-6 space-y-3">
                          {reminders.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No reminders linked to this FMLA case yet.</div> : reminders.map((reminder) => (
                            <div key={reminder.reminder_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                              <div className="flex items-center justify-between gap-3">
                                <p className="font-medium">{reminder.message}</p>
                                <span className="rounded-full bg-violet-500/20 px-2 py-1 text-xs text-violet-200">{reminder.priority}</span>
                              </div>
                              <p className="mt-2 text-xs text-slate-400">Due {reminder.due_date || 'No due date'} • {reminder.status}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Upcoming and overdue deadlines</h3>
                        <div className="mt-4 space-y-3">
                          {deadlineBuckets.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No deadlines have been added yet.</div> : deadlineBuckets.map((item) => (
                            <div key={item.key} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                              <div className="flex items-center justify-between gap-3">
                                <p className="font-medium">{item.label}</p>
                                <span className="text-xs text-slate-300">{item.value}</span>
                              </div>
                              <p className={`mt-2 text-xs ${item.state.tone === 'danger' ? 'text-rose-200' : item.state.tone === 'warning' ? 'text-amber-200' : 'text-slate-400'}`}>{item.state.label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {activeTab === 'correspondence' ? (
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold">Correspondence timeline</h3>
                        <span className="text-xs text-slate-400">Date/time, contact method, summary, and next action all persist</span>
                      </div>
                      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Field label="Date/time"><Input type="datetime-local" value={correspondenceForm.correspondence_at} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, correspondence_at: e.target.value }))} /></Field>
                        <Field label="Method">
                          <Select value={correspondenceForm.contact_type} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, contact_type: e.target.value }))}>
                            {['phone', 'voicemail', 'email', 'fax', 'mail', 'portal', 'in-person', 'upload'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                          </Select>
                        </Field>
                        <Field label="Contact person"><Input value={correspondenceForm.person_contacted} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, person_contacted: e.target.value }))} /></Field>
                        <Field label="Organization"><Input value={correspondenceForm.organization} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, organization: e.target.value }))} /></Field>
                        <Field label="Contact information"><Input value={correspondenceForm.contact_information} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, contact_information: e.target.value }))} /></Field>
                        <Field label="Follow-up date"><Input type="date" value={correspondenceForm.follow_up_date} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, follow_up_date: e.target.value }))} /></Field>
                        <div className="md:col-span-2">
                          <Field label="Summary"><Textarea rows={3} value={correspondenceForm.summary} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, summary: e.target.value }))} /></Field>
                        </div>
                        <div className="md:col-span-2">
                          <DocumentationAssistPanel
                            module="fmla"
                            noteKind="fmla_correspondence"
                            clientId={caseForm.client_id || ''}
                            clientName={caseForm.client_name || caseForm.staff_name || ''}
                            currentText={correspondenceForm.summary}
                            context={{
                              observations: `Method: ${correspondenceForm.contact_type}; Person: ${correspondenceForm.person_contacted}; Organization: ${correspondenceForm.organization}`,
                              next_steps: correspondenceForm.next_step_needed,
                              paperwork_deadline: caseForm.paperwork_deadline
                            }}
                            onApplyDraft={(draft) => setCorrespondenceForm((prev) => ({ ...prev, summary: draft }))}
                          />
                        </div>
                        <Field label="Outcome"><Input value={correspondenceForm.outcome} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, outcome: e.target.value }))} /></Field>
                        <Field label="Next action"><Input value={correspondenceForm.next_step_needed} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, next_step_needed: e.target.value }))} /></Field>
                      </div>
                      <button onClick={addCorrespondence} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-orange-400">
                        <MessageSquare className="h-4 w-4" />
                        Add Correspondence Entry
                      </button>
                      <div className="mt-6 space-y-3">
                        {correspondence.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No correspondence logged yet.</div> : correspondence.map((entry) => (
                          <div key={entry.correspondence_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <p className="font-medium capitalize">{entry.contact_type} with {entry.person_contacted || entry.organization || 'contact'}</p>
                              <span className="text-xs text-slate-400">{new Date(entry.correspondence_at).toLocaleString()}</span>
                            </div>
                            <p className="mt-2 text-sm text-slate-300">{entry.summary}</p>
                            <p className="mt-2 text-xs text-slate-400">Outcome: {entry.outcome || '—'} • Next action: {entry.next_step_needed || '—'}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {activeTab === 'intermittent usage' ? (
                    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Intermittent leave usage</h3>
                        <p className="mt-2 text-sm text-slate-400">
                          Track episodes, duration, category, and notes. This persists even if the case later changes status.
                        </p>
                        {caseForm.leave_type !== 'intermittent' ? (
                          <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                            This case is currently marked as {formatFmlaLabel(caseForm.leave_type)}. You can still record usage history, but intermittent tracking is most relevant when the leave type is intermittent.
                          </div>
                        ) : null}
                        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                          <Field label="Date"><Input type="date" value={leaveUsageForm.usage_date} onChange={(e) => setLeaveUsageForm((prev) => ({ ...prev, usage_date: e.target.value }))} /></Field>
                          <Field label="Duration (minutes)"><Input type="number" min="1" value={leaveUsageForm.duration_minutes} onChange={(e) => setLeaveUsageForm((prev) => ({ ...prev, duration_minutes: e.target.value }))} /></Field>
                          <Field label="Reason category">
                            <Select value={leaveUsageForm.reason_category} onChange={(e) => setLeaveUsageForm((prev) => ({ ...prev, reason_category: e.target.value }))}>
                              {['flare-up', 'medical appointment', 'treatment', 'recovery', 'other'].map((item) => <option key={item} value={item}>{formatFmlaLabel(item)}</option>)}
                            </Select>
                          </Field>
                          <div className="md:col-span-2">
                            <Field label="Notes"><Textarea rows={3} value={leaveUsageForm.notes} onChange={(e) => setLeaveUsageForm((prev) => ({ ...prev, notes: e.target.value }))} /></Field>
                          </div>
                        </div>
                        <button onClick={addLeaveUsage} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400">
                          <Plus className="h-4 w-4" />
                          Add Usage Entry
                        </button>
                      </div>

                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Usage summary</h3>
                        <div className="mt-4 grid grid-cols-3 gap-4">
                          <div className="rounded-2xl bg-slate-950/30 p-4 text-center">
                            <p className="text-2xl font-bold">{leaveUsageSummary.entry_count || 0}</p>
                            <p className="mt-1 text-xs text-slate-400">Entries</p>
                          </div>
                          <div className="rounded-2xl bg-slate-950/30 p-4 text-center">
                            <p className="text-2xl font-bold">{leaveUsageSummary.total_hours || 0}</p>
                            <p className="mt-1 text-xs text-slate-400">Hours used</p>
                          </div>
                          <div className="rounded-2xl bg-slate-950/30 p-4 text-center">
                            <p className="text-2xl font-bold">{leaveUsageSummary.total_minutes || 0}</p>
                            <p className="mt-1 text-xs text-slate-400">Minutes</p>
                          </div>
                        </div>
                        <div className="mt-6 space-y-3">
                          {leaveUsage.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No intermittent leave entries yet.</div> : leaveUsage.map((entry) => (
                            <div key={entry.usage_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                              <div className="flex items-center justify-between gap-3">
                                <p className="font-medium">{entry.usage_date}</p>
                                <span className="rounded-full bg-cyan-500/20 px-2 py-1 text-xs text-cyan-200">{entry.duration_minutes} min</span>
                              </div>
                              <p className="mt-2 text-xs text-slate-400">{formatFmlaLabel(entry.reason_category)}</p>
                              {entry.notes ? <p className="mt-2 text-sm text-slate-300">{entry.notes}</p> : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {activeTab === 'exports' ? (
                    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Employer-safe packet drafting</h3>
                        <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                          {exportForm.warning_text || 'Generated draft only. Qualified staff must review, edit, and approve the document before it is shared. Avoid unnecessary SUD or mental health disclosure and keep to minimum necessary information.'}
                        </div>
                        <div className="mt-4 space-y-4">
                          <Field label="Export type"><Input value={exportForm.export_type} onChange={(e) => setExportForm((prev) => ({ ...prev, export_type: e.target.value }))} /></Field>
                          <Field label="Reviewer instructions" hint="Used only to shape the draft">
                            <Textarea rows={3} value={exportForm.custom_instructions} onChange={(e) => setExportForm((prev) => ({ ...prev, custom_instructions: e.target.value, review_notes: e.target.value }))} placeholder="Clarify restricted disclosures, timing, or employer-facing tone." />
                          </Field>
                          <button onClick={generateDraft} className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400">
                            <FileText className="h-4 w-4" />
                            Generate Draft Packet
                          </button>
                          <Field label="Draft title"><Input value={exportForm.draft_title} onChange={(e) => setExportForm((prev) => ({ ...prev, draft_title: e.target.value }))} /></Field>
                          <Field label="Draft content">
                            <Textarea rows={14} value={exportForm.draft_content} onChange={(e) => setExportForm((prev) => ({ ...prev, draft_content: e.target.value }))} />
                          </Field>
                          <Field label="Review notes"><Textarea rows={3} value={exportForm.review_notes} onChange={(e) => setExportForm((prev) => ({ ...prev, review_notes: e.target.value }))} placeholder="Document internal review comments before export." /></Field>
                          <button onClick={finalizePdfExport} disabled={exporting} className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60">
                            <Download className="h-4 w-4" />
                            {exporting ? 'Exporting…' : 'Finalize PDF Export'}
                          </button>
                        </div>
                      </div>

                      <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <h3 className="text-lg font-semibold">Saved exports</h3>
                        <p className="mt-2 text-sm text-slate-400">Safe filenames use IDs instead of names to avoid exposing PHI in downloaded files.</p>
                        <div className="mt-6 space-y-3">
                          {exportsList.length === 0 ? <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No draft or PDF exports yet.</div> : exportsList.map((item) => (
                            <div key={item.export_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <p className="font-medium">{item.draft_title}</p>
                                  <p className="mt-1 text-xs text-slate-400">{item.safe_filename || 'Draft not finalized to PDF yet'}</p>
                                  <p className="mt-1 text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</p>
                                </div>
                                {item.file_path ? (
                                  <button onClick={() => downloadExport(item.export_id)} className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white transition hover:bg-white/10">
                                    <Download className="h-3.5 w-3.5" />
                                    Download PDF
                                  </button>
                                ) : null}
                              </div>
                              <button
                                onClick={() => setExportForm({
                                  export_type: item.export_type || 'employer packet',
                                  custom_instructions: '',
                                  draft_title: item.draft_title || '',
                                  draft_content: item.draft_content || '',
                                  review_notes: item.review_notes || '',
                                  warning_text: item.warning_text || '',
                                  export_id: item.export_id || ''
                                })}
                                className="mt-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs transition hover:bg-white/10"
                              >
                                Load into editor
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </section>
          </div>
        </section>
      </div>
    </div>
  )
}

export default FMLA
