import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  FileSpreadsheet,
  Plus,
  CalendarClock,
  ShieldCheck,
  AlertTriangle,
  ClipboardList,
  Building2,
  Phone,
  Mail,
  FileText,
  Upload,
  Download,
  Send,
  MessageSquare,
  Save,
  RefreshCw,
  BellRing,
  Search
} from 'lucide-react'
import toast from 'react-hot-toast'
import ClientSelector from '../components/ClientSelector'
import DocumentationAssistPanel from '../components/DocumentationAssistPanel'
import { apiFetch } from '../api/config'
import { useAuth } from '../contexts/AuthContext'
import {
  filterFmlaCases,
  formatFmlaLabel,
  getDeadlineState,
  getFmlaStatusBadgeClass,
  getMissingChecklist,
  getWorkflowSnapshot,
  normalizeFmlaStatusValue,
  WORKFLOW_ACTION_BUCKETS,
  WORKFLOW_STAGES
} from '../utils/fmla'

const FMLA_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'pending documents', label: 'Pending Documents' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'approved', label: 'Approved' },
  { value: 'denied', label: 'Denied' },
  { value: 'expired', label: 'Expired' },
  { value: 'closed', label: 'Closed' }
]

const LEAVE_TYPE_OPTIONS = [
  { value: 'continuous', label: 'Continuous' },
  { value: 'intermittent', label: 'Intermittent' },
  { value: 'reduced schedule', label: 'Reduced Schedule' }
]

const emptyCaseForm = () => ({
  client_id: '',
  client_name: '',
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

const formatFileSize = (size = 0) => {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

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

const formatDisplayDate = (value, fallback = 'Not set') => {
  if (!value) return fallback
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString()
}

const WorkflowMetric = ({ label, value, tone = 'default' }) => {
  const toneClass = {
    default: 'border-white/10 bg-slate-950/30 text-white',
    warning: 'border-amber-400/20 bg-amber-500/10 text-amber-100',
    danger: 'border-rose-400/20 bg-rose-500/10 text-rose-100',
    success: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100'
  }[tone] || 'border-white/10 bg-slate-950/30 text-white'

  return (
    <div className={`rounded-2xl border p-4 ${toneClass}`}>
      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className="mt-2 text-sm font-semibold">{value}</p>
    </div>
  )
}

const TOP_PROGRESS_STEPS = [
  'Case Opened',
  'Employer Contacted',
  'Packet Requested',
  'Packet Received',
  'Sent to Provider',
  'Provider Completed',
  'Returned to Employer',
  'Decision Pending',
  'Approved / Denied',
  'RTW / Extension / Closed'
]

const GUIDE_STEPS = [
  'Contact the employer or FMLA company and confirm where the packet should come from.',
  'Request the packet and record the request date so follow-up has a paper trail.',
  'Wait for the packet, then upload or store it as soon as it arrives.',
  'Track the next due date before the employer, provider, or client misses the window.',
  'Send the packet to the provider or medical team and monitor completion.',
  'Return completed documents to the employer or FMLA company and confirm receipt.',
  'Track whether the case is approved, denied, or needs more information.',
  'Follow up on return-to-work dates, extensions, and final closure.'
]

const getTopProgressIndex = (workflowStage) => {
  if (workflowStage === 'Approved' || workflowStage === 'Denied') return 8
  if (workflowStage === 'Closed / RTW') return 9
  return Math.max(TOP_PROGRESS_STEPS.indexOf(workflowStage), 0)
}

const SectionHeading = ({ title, helper }) => (
  <div className="mb-4">
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="mt-1 text-sm text-slate-400">{helper}</p>
  </div>
)

function FMLA() {
  const { profile } = useAuth()
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
  const [filters, setFilters] = useState({
    search: searchParams.get('search') || '',
    status: searchParams.get('status') || '',
    employer: searchParams.get('employer') || '',
    deadline: searchParams.get('deadline') || '',
    case_manager: searchParams.get('case_manager') || defaultCaseManagerId,
    workflow_bucket: searchParams.get('workflow_bucket') || ''
  })
  const [caseForm, setCaseForm] = useState(emptyCaseForm())
  const [documentForm, setDocumentForm] = useState(emptyDocumentForm())
  const [correspondenceForm, setCorrespondenceForm] = useState(emptyCorrespondenceForm())
  const [reminderForm, setReminderForm] = useState(emptyReminderForm())
  const [selectedUploads, setSelectedUploads] = useState([])
  const [documentInputKey, setDocumentInputKey] = useState(0)
  const [creatingNewCase, setCreatingNewCase] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const visibleCases = useMemo(() => filterFmlaCases(cases, filters), [cases, filters])
  const missingChecklist = useMemo(() => getMissingChecklist(selectedCase, documents), [selectedCase, documents])
  const visibleCaseSnapshots = useMemo(
    () => visibleCases.map((item) => ({ caseItem: item, workflow: getWorkflowSnapshot(item) })),
    [visibleCases]
  )
  const selectedWorkflow = useMemo(
    () => getWorkflowSnapshot(selectedCase || caseForm, documents, correspondence, reminders),
    [selectedCase, caseForm, documents, correspondence, reminders]
  )

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
        if (key === 'workflow_bucket') return
        if (value) params.set(key, value)
      })
      const response = await apiFetch(`/api/fmla?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load FMLA cases')
      const data = await response.json()
      setCases((data.cases || []).map((item) => ({ ...item, status: normalizeFmlaStatusValue(item.status) })))
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
      setSelectedCase(data.case ? { ...data.case, status: normalizeFmlaStatusValue(data.case.status) } : null)
      setCaseForm(data.case ? { ...data.case, status: normalizeFmlaStatusValue(data.case.status) } : emptyCaseForm())
      setDocuments(data.documents || [])
      setCorrespondence(data.correspondence || [])
      setReminders(data.reminders || [])
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load FMLA case detail')
    }
  }

  const handleCaseFieldChange = (field, value) => {
    setCaseForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleClientSelected = (client) => {
    if (!creatingNewCase) return
    setCaseForm((prev) => ({
      ...prev,
      client_id: client.client_id || '',
      client_name: `${client.first_name || ''} ${client.last_name || ''}`.trim(),
      date_of_birth: client.date_of_birth || '',
      assigned_case_manager: client.case_manager_id || prev.assigned_case_manager,
      treatment_status: client.case_status || ''
    }))
  }

  const saveCase = async () => {
    if (!caseForm.client_name.trim()) {
      toast.error('Client name is required')
      return
    }
    setSaving(true)
    try {
      const method = creatingNewCase ? 'POST' : 'PUT'
      const endpoint = creatingNewCase ? '/api/fmla' : `/api/fmla/${selectedCaseId}`
      const response = await apiFetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(caseForm)
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
        selectedUploads.forEach((file) => {
          formData.append('files', file)
        })
        Object.entries(documentForm).forEach(([key, value]) => {
          if (['file_name', 'file_path', 'file_size', 'content_type'].includes(key)) {
            return
          }
          formData.append(key, value ?? '')
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
      const data = await response.json()
      if (selectedUploads.length > 0) {
        setDocuments((prev) => [...(data.documents || []), ...prev])
      } else {
        setDocuments((prev) => [data.document, ...prev])
      }
      setDocumentForm(emptyDocumentForm())
      setSelectedUploads([])
      setDocumentInputKey((prev) => prev + 1)
      loadSummary()
      toast.success(selectedUploads.length > 0 ? `${data.document_count || selectedUploads.length} file(s) uploaded` : 'Document entry added')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to add document')
    }
  }

  const downloadDocument = (documentId) => {
    window.open(`/api/fmla/documents/${documentId}/download`, '_blank', 'noopener,noreferrer')
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
      const data = await response.json()
      setCorrespondence((prev) => [data.correspondence, ...prev])
      setCorrespondenceForm(emptyCorrespondenceForm())
      loadSummary()
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
      const data = await response.json()
      setReminders((prev) => [data.reminder, ...prev])
      setReminderForm(emptyReminderForm())
      toast.success('Reminder created in main reminders module')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to create reminder')
    }
  }

  const deadlineState = getDeadlineState(selectedCase?.paperwork_deadline)

  const actionCards = useMemo(() => ([
    { key: 'employer_follow_up', label: WORKFLOW_ACTION_BUCKETS.employer_follow_up, icon: BellRing },
    { key: 'packet_not_received', label: WORKFLOW_ACTION_BUCKETS.packet_not_received, icon: AlertTriangle },
    { key: 'provider_docs_pending', label: WORKFLOW_ACTION_BUCKETS.provider_docs_pending, icon: ClipboardList },
    { key: 'due_within_3_days', label: WORKFLOW_ACTION_BUCKETS.due_within_3_days, icon: CalendarClock },
    { key: 'ready_to_submit', label: WORKFLOW_ACTION_BUCKETS.ready_to_submit, icon: Send },
    { key: 'rtw_extension_needed', label: WORKFLOW_ACTION_BUCKETS.rtw_extension_needed, icon: ShieldCheck }
  ].map((item) => ({
    ...item,
    value: visibleCaseSnapshots.filter(({ workflow }) => workflow.actionBucket === item.key).length
  }))), [visibleCaseSnapshots])

  const selectedStageIndex = WORKFLOW_STAGES.indexOf(selectedWorkflow.stage)
  const topProgressIndex = getTopProgressIndex(selectedWorkflow.stage)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-cyan-950 to-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8 space-y-8">
        <section className="rounded-3xl border border-cyan-500/20 bg-slate-900/70 backdrop-blur-xl p-8 shadow-2xl shadow-cyan-900/20">
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
                <FileSpreadsheet className="h-4 w-4" />
                FMLA Workflow Coach
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  onClick={() => {
                    setCreatingNewCase(true)
                    setSelectedCaseId(null)
                    setCaseForm(emptyCaseForm())
                  }}
                  className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
                >
                  <Plus className="h-4 w-4" />
                  New FMLA Case
                </button>
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
              <h1 className="mt-5 text-4xl font-bold">FMLA Case File Command Center</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Start a new case at the top, then work the file from employer contact through packet handling, provider completion, employer return, and RTW follow-up.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Current coaching focus</p>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <WorkflowMetric label="Current stage" value={selectedWorkflow.stage} tone="default" />
                <WorkflowMetric label="Waiting on" value={selectedWorkflow.waitingOn} tone="warning" />
                <WorkflowMetric label="Next action" value={selectedWorkflow.nextAction} tone="danger" />
                <WorkflowMetric
                  label="Next due"
                  value={selectedWorkflow.nextDue ? `${selectedWorkflow.nextDue.label} · ${formatDisplayDate(selectedWorkflow.nextDue.value)}` : 'No active deadline'}
                  tone={selectedWorkflow.nextDue?.state?.tone === 'danger' ? 'danger' : selectedWorkflow.nextDue?.state?.tone === 'warning' ? 'warning' : 'success'}
                />
              </div>
              <p className="mt-4 text-sm text-slate-400">
                Use these cues to decide who to contact next, what document is blocking progress, and which deadline matters first.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold">FMLA Progress Tracker</h2>
              <p className="mt-1 text-sm text-slate-400">
                Follow the same lifecycle every time so a new case manager knows the next step without guessing.
              </p>
            </div>
            <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">
              Current focus: {selectedWorkflow.stage}
            </span>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {TOP_PROGRESS_STEPS.map((stage, index) => {
              const isCurrent = index === topProgressIndex
              const isComplete = index < topProgressIndex
              return (
                <span
                  key={stage}
                  className={`rounded-full border px-3 py-2 text-xs ${
                    isCurrent
                      ? 'border-cyan-400/40 bg-cyan-400/15 text-cyan-100'
                      : isComplete
                        ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                        : 'border-white/10 bg-slate-950/30 text-slate-300'
                  }`}
                >
                  {stage}
                </span>
              )
            })}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold">FMLA Guide</h2>
                <p className="mt-1 text-sm text-slate-400">
                  Plain-language steps for new case managers handling a leave case from start to finish.
                </p>
              </div>
              <span className="rounded-full border border-white/10 bg-slate-950/30 px-3 py-1 text-xs text-slate-300">
                Guide + workflow coach
              </span>
            </div>
            <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
              {GUIDE_STEPS.map((step, index) => (
                <div key={step} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                  <p className="text-[11px] uppercase tracking-[0.2em] text-cyan-200">Step {index + 1}</p>
                  <p className="mt-2 text-sm text-slate-200">{step}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-3xl border border-white/10 bg-slate-950/30 p-6">
            <h2 className="text-lg font-semibold">What to watch today</h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-300">
              <li>Confirm whether the packet has been requested, received, or is still outstanding.</li>
              <li>Look at the next due date before calling the employer or provider.</li>
              <li>Use reminders, documents, and correspondence to keep the timeline complete.</li>
              <li>Move approved cases into RTW or extension follow-up instead of leaving them idle.</li>
            </ul>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          {actionCards.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                onClick={() => setFilters((prev) => ({ ...prev, workflow_bucket: item.key }))}
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
              <Input value={filters.search} onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))} placeholder="Client or employer" className="pl-9" />
            </div>
          </Field>
          <Field label="Status">
            <Select value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}>
              <option value="">All statuses</option>
              {FMLA_STATUS_OPTIONS.map((status) => (
                <option key={status.value} value={status.value}>{status.label}</option>
              ))}
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
          <Field label="Needs action">
            <Select value={filters.workflow_bucket} onChange={(e) => setFilters((prev) => ({ ...prev, workflow_bucket: e.target.value }))}>
              <option value="">All workflow buckets</option>
              {Object.entries(WORKFLOW_ACTION_BUCKETS).filter(([key]) => key !== 'monitoring').map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </Select>
          </Field>
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
          <aside className="rounded-3xl border border-white/10 bg-white/5 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">FMLA Cases</h2>
              <span className="text-xs text-slate-400">{visibleCases.length} shown</span>
            </div>
            <div className="space-y-3 max-h-[900px] overflow-y-auto pr-1">
              {loading ? (
                <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4 text-sm text-slate-300">Loading cases…</div>
              ) : visibleCases.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4 text-sm text-slate-300">No FMLA cases match the current filters.</div>
              ) : visibleCaseSnapshots.map(({ caseItem: item, workflow }) => {
                const state = workflow.nextDue?.state || getDeadlineState(item.paperwork_deadline)
                return (
                  <button
                    key={item.case_id}
                    onClick={() => setSelectedCaseId(item.case_id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      selectedCaseId === item.case_id
                        ? 'border-cyan-400/60 bg-cyan-400/10'
                        : 'border-white/10 bg-slate-950/30 hover:border-white/20 hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">{item.client_name}</h3>
                        <p className="text-sm text-slate-400">{item.employer_name || 'Employer not added'}</p>
                      </div>
                      <span className={`rounded-full border px-2 py-1 text-[11px] ${getFmlaStatusBadgeClass(item.status)}`}>
                        {formatFmlaLabel(item.status)}
                      </span>
                    </div>
                    <div className="mt-3 rounded-xl border border-cyan-400/20 bg-cyan-400/10 px-3 py-2 text-xs text-cyan-100">
                      Stage: <span className="font-semibold text-white">{workflow.stage}</span>
                    </div>
                    <div className="mt-3 space-y-2 text-xs text-slate-300">
                      <div>Next action: <span className="text-white">{workflow.nextAction}</span></div>
                      <div>Waiting on: <span className="text-white">{workflow.waitingOn}</span></div>
                      <div>Next due: <span className="text-white">{workflow.nextDue ? `${workflow.nextDue.label} · ${formatDisplayDate(workflow.nextDue.value)}` : 'No active deadline'}</span></div>
                      <div>Last contact: <span className="text-white">{formatDisplayDate(workflow.lastContactDate, 'No contact logged')}</span></div>
                    </div>
                    <div className={`mt-3 rounded-xl px-3 py-2 text-xs ${
                      state.tone === 'danger' ? 'bg-rose-500/10 text-rose-200' :
                      state.tone === 'warning' ? 'bg-amber-500/10 text-amber-200' :
                      state.tone === 'ok' ? 'bg-emerald-500/10 text-emerald-200' :
                      'bg-slate-500/10 text-slate-300'
                    }`}>
                      {state.label}
                    </div>
                    <div className="mt-3 text-right">
                      <span className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white">
                        Open Case
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </aside>

          <div className="space-y-6">
            <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-2xl font-semibold">{creatingNewCase ? 'New FMLA Case' : (selectedCase?.client_name || 'Select an FMLA case')}</h2>
                  <p className="text-sm text-slate-400">
                    Move the case from employer contact through packet handling, provider completion, employer return, and RTW follow-up.
                  </p>
                </div>
                {!creatingNewCase && selectedCase ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">{selectedWorkflow.stage}</span>
                    <span className={`rounded-full border px-3 py-1 text-xs ${getFmlaStatusBadgeClass(selectedCase.status)}`}>{formatFmlaLabel(selectedCase.status)}</span>
                    <span className="rounded-full bg-slate-950/40 px-3 py-1 text-xs text-slate-300">{deadlineState.label}</span>
                  </div>
                ) : null}
              </div>

              {creatingNewCase ? (
                <div className="mb-6">
                  <ClientSelector onClientSelect={handleClientSelected} placeholder="Link to an existing client" className="max-w-md" />
                </div>
              ) : null}

              {!creatingNewCase && !selectedCase ? (
                <div className="rounded-2xl border border-dashed border-white/15 bg-slate-950/20 p-8 text-sm text-slate-400">
                  Select an FMLA case from the list or create a new one.
                </div>
              ) : (
                <div className="space-y-8">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-lg font-semibold">Workflow Stage Tracker</h3>
                      <span className="text-xs text-slate-400">Last contact: {formatDisplayDate(selectedWorkflow.lastContactDate, 'No contact logged')}</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {WORKFLOW_STAGES.map((stage, index) => {
                        const isCurrent = stage === selectedWorkflow.stage
                        const isComplete = selectedStageIndex > -1 && index < selectedStageIndex
                        return (
                          <span
                            key={stage}
                            className={`rounded-full border px-3 py-1 text-xs ${
                              isCurrent
                                ? 'border-cyan-400/40 bg-cyan-400/15 text-cyan-100'
                                : isComplete
                                  ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                                  : 'border-white/10 bg-white/5 text-slate-300'
                            }`}
                          >
                            {stage}
                          </span>
                        )
                      })}
                    </div>
                  </div>

                  <div>
                    <SectionHeading
                      title="Overview"
                      helper="Capture the basic case identity, request type, and status so anyone opening the file knows what kind of leave is being managed."
                    />
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <Field label="Client name"><Input value={caseForm.client_name} onChange={(e) => handleCaseFieldChange('client_name', e.target.value)} /></Field>
                    <Field label="Linked client">
                      <Input
                        value={caseForm.client_name || ''}
                        readOnly
                        placeholder="Link a client from the selector above"
                      />
                    </Field>
                    <Field label="Date of birth"><Input type="date" value={caseForm.date_of_birth || ''} onChange={(e) => handleCaseFieldChange('date_of_birth', e.target.value)} /></Field>
                    <Field label="Assigned case manager"><Input value={caseForm.assigned_case_manager} onChange={(e) => handleCaseFieldChange('assigned_case_manager', e.target.value)} /></Field>
                    <Field label="Treatment/program status" hint="Optional"><Input value={caseForm.treatment_status || ''} onChange={(e) => handleCaseFieldChange('treatment_status', e.target.value)} /></Field>
                    <Field label="FMLA request type">
                      <Select value={caseForm.fmla_request_type} onChange={(e) => handleCaseFieldChange('fmla_request_type', e.target.value)}>
                        {['new request','extension','recertification','return-to-work','intermittent leave'].map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Status">
                      <Select value={caseForm.status} onChange={(e) => handleCaseFieldChange('status', e.target.value)}>
                        {FMLA_STATUS_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                      </Select>
                    </Field>
                    <Field label="Approval status">
                      <Select value={caseForm.approval_status} onChange={(e) => handleCaseFieldChange('approval_status', e.target.value)}>
                        {['pending','approved','denied','needs more information','expired','closed'].map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                  </div>
                  </div>

                  <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                      <SectionHeading
                        title={<span className="flex items-center gap-2"><Building2 className="h-5 w-5 text-cyan-300" /> Employer Contact and Packet Request</span>}
                        helper="Record who the employer or FMLA company is, how to reach them, and when the packet should come back so follow-up is concrete."
                      />
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Field label="Employer name"><Input value={caseForm.employer_name || ''} onChange={(e) => handleCaseFieldChange('employer_name', e.target.value)} /></Field>
                        <Field label="HR contact name"><Input value={caseForm.hr_contact_name || ''} onChange={(e) => handleCaseFieldChange('hr_contact_name', e.target.value)} /></Field>
                        <Field label="HR phone"><Input value={caseForm.hr_phone || ''} onChange={(e) => handleCaseFieldChange('hr_phone', e.target.value)} /></Field>
                        <Field label="HR email"><Input value={caseForm.hr_email || ''} onChange={(e) => handleCaseFieldChange('hr_email', e.target.value)} /></Field>
                        <Field label="Employer fax"><Input value={caseForm.employer_fax || ''} onChange={(e) => handleCaseFieldChange('employer_fax', e.target.value)} /></Field>
                        <Field label="Preferred communication method">
                          <Select value={caseForm.preferred_communication_method || ''} onChange={(e) => handleCaseFieldChange('preferred_communication_method', e.target.value)}>
                            {['phone','email','fax','mail','portal'].map((item) => <option key={item} value={item}>{item}</option>)}
                          </Select>
                        </Field>
                        <Field label="Employer response deadline"><Input type="date" value={caseForm.employer_response_deadline || ''} onChange={(e) => handleCaseFieldChange('employer_response_deadline', e.target.value)} /></Field>
                        <div className="md:col-span-2">
                          <Field label="Employer address"><Textarea rows={2} value={caseForm.employer_address || ''} onChange={(e) => handleCaseFieldChange('employer_address', e.target.value)} /></Field>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                      <SectionHeading
                        title={<span className="flex items-center gap-2"><Phone className="h-5 w-5 text-cyan-300" /> Medical / Provider</span>}
                        helper="Track the provider side of the workflow here so you know who has the packet, how to follow up, and when certification expires."
                      />
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Field label="Provider / doctor name"><Input value={caseForm.provider_name || ''} onChange={(e) => handleCaseFieldChange('provider_name', e.target.value)} /></Field>
                        <Field label="Clinic / facility name"><Input value={caseForm.clinic_name || ''} onChange={(e) => handleCaseFieldChange('clinic_name', e.target.value)} /></Field>
                        <Field label="Phone"><Input value={caseForm.provider_phone || ''} onChange={(e) => handleCaseFieldChange('provider_phone', e.target.value)} /></Field>
                        <Field label="Fax"><Input value={caseForm.provider_fax || ''} onChange={(e) => handleCaseFieldChange('provider_fax', e.target.value)} /></Field>
                        <Field label="Email"><Input value={caseForm.provider_email || ''} onChange={(e) => handleCaseFieldChange('provider_email', e.target.value)} /></Field>
                        <Field label="ROI status">
                          <Select value={caseForm.roi_status || ''} onChange={(e) => handleCaseFieldChange('roi_status', e.target.value)}>
                            {['unknown','not needed','needed','requested','received','expired'].map((item) => <option key={item} value={item}>{item}</option>)}
                          </Select>
                        </Field>
                        <Field label="Certification expiration"><Input type="date" value={caseForm.certification_expiration_date || ''} onChange={(e) => handleCaseFieldChange('certification_expiration_date', e.target.value)} /></Field>
                        <div className="md:col-span-2">
                          <Field label="Provider address"><Textarea rows={2} value={caseForm.provider_address || ''} onChange={(e) => handleCaseFieldChange('provider_address', e.target.value)} /></Field>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-5 space-y-4">
                    <SectionHeading
                      title={<span className="flex items-center gap-2"><CalendarClock className="h-5 w-5 text-cyan-300" /> Submission &amp; Decision</span>}
                      helper="Use these dates to manage when leave begins, when paperwork moves, when decisions come back, and what RTW timing the employer expects."
                    />
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <Field label="Leave type">
                        <Select value={caseForm.leave_type || 'continuous'} onChange={(e) => handleCaseFieldChange('leave_type', e.target.value)}>
                          {LEAVE_TYPE_OPTIONS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                        </Select>
                      </Field>
                      <Field label="Leave start date"><Input type="date" value={caseForm.leave_start_date || ''} onChange={(e) => handleCaseFieldChange('leave_start_date', e.target.value)} /></Field>
                      <Field label="Leave end date"><Input type="date" value={caseForm.leave_end_date || ''} onChange={(e) => handleCaseFieldChange('leave_end_date', e.target.value)} /></Field>
                      <Field label="Expected return date"><Input type="date" value={caseForm.expected_return_date || ''} onChange={(e) => handleCaseFieldChange('expected_return_date', e.target.value)} /></Field>
                      <Field label="Deadline to submit paperwork"><Input type="date" value={caseForm.paperwork_deadline || ''} onChange={(e) => handleCaseFieldChange('paperwork_deadline', e.target.value)} /></Field>
                      <Field label="Return-to-work date"><Input type="date" value={caseForm.return_to_work_date || ''} onChange={(e) => handleCaseFieldChange('return_to_work_date', e.target.value)} /></Field>
                      <Field label="Confirmation received">
                        <Select value={caseForm.confirmation_received ? 'yes' : 'no'} onChange={(e) => handleCaseFieldChange('confirmation_received', e.target.value === 'yes')}>
                          <option value="no">No</option>
                          <option value="yes">Yes</option>
                        </Select>
                      </Field>
                      <Field label="Date paperwork received"><Input type="date" value={caseForm.paperwork_received_date || ''} onChange={(e) => handleCaseFieldChange('paperwork_received_date', e.target.value)} /></Field>
                      <Field label="Date paperwork completed"><Input type="date" value={caseForm.paperwork_completed_date || ''} onChange={(e) => handleCaseFieldChange('paperwork_completed_date', e.target.value)} /></Field>
                      <Field label="Date paperwork sent"><Input type="date" value={caseForm.paperwork_sent_date || ''} onChange={(e) => handleCaseFieldChange('paperwork_sent_date', e.target.value)} /></Field>
                      <Field label="Method sent">
                        <Select value={caseForm.paperwork_sent_method || ''} onChange={(e) => handleCaseFieldChange('paperwork_sent_method', e.target.value)}>
                          {['fax','email','mail','portal','hand-delivered'].map((item) => <option key={item} value={item}>{item}</option>)}
                        </Select>
                      </Field>
                    </div>
                    <Field label="Notes">
                      <Textarea rows={4} value={caseForm.notes || ''} onChange={(e) => handleCaseFieldChange('notes', e.target.value)} placeholder="Add case notes, blockers, missing items, or follow-up details." />
                    </Field>
                    <Field label="Internal comments">
                      <Textarea rows={3} value={caseForm.internal_comments || ''} onChange={(e) => handleCaseFieldChange('internal_comments', e.target.value)} placeholder="Internal case manager comments only." />
                    </Field>
                    <div className="mt-4">
                      <DocumentationAssistPanel
                        module="fmla"
                        noteKind="fmla_case_note"
                        clientId={caseForm.client_id || ''}
                        clientName={caseForm.client_name || ''}
                        currentText={caseForm.notes || ''}
                        context={{
                          goals: caseForm.fmla_request_type,
                          observations: `Status: ${caseForm.status}; Approval: ${caseForm.approval_status}; Employer: ${caseForm.employer_name}; Provider: ${caseForm.provider_name || caseForm.clinic_name}`,
                          next_steps: `Paperwork deadline ${caseForm.paperwork_deadline || 'not set'}, expected return ${caseForm.expected_return_date || 'not set'}`,
                          paperwork_deadline: caseForm.paperwork_deadline
                        }}
                        onApplyDraft={(draft) => handleCaseFieldChange('notes', draft)}
                      />
                    </div>
                  </div>

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
              )}
            </section>

            {selectedCase || creatingNewCase ? (
              <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                  <SectionHeading
                    title="Workflow Snapshot"
                    helper="This quick summary tells you what stage the case is in, who is holding the ball, and what should happen next."
                  />
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Stage</span><span className="text-right">{selectedWorkflow.stage}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Waiting on</span><span className="text-right">{selectedWorkflow.waitingOn}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Next action</span><span className="text-right">{selectedWorkflow.nextAction}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Next due</span><span className="text-right">{selectedWorkflow.nextDue ? `${selectedWorkflow.nextDue.label} · ${formatDisplayDate(selectedWorkflow.nextDue.value)}` : deadlineState.label}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Employer</span><span className="text-right">{caseForm.employer_name || 'Not added'}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Provider</span><span className="text-right">{caseForm.provider_name || caseForm.clinic_name || 'Not added'}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Request type</span><span className="text-right">{formatFmlaLabel(caseForm.fmla_request_type)}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Leave type</span><span className="text-right">{formatFmlaLabel(caseForm.leave_type)}</span></div>
                    <div className="flex justify-between gap-4"><span className="text-slate-400">Return-to-work</span><span className="text-right">{caseForm.return_to_work_date || 'Not set'}</span></div>
                  </div>
                  <div className="mt-6 rounded-2xl bg-slate-950/30 p-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Missing items</p>
                    <ul className="mt-3 space-y-2 text-sm">
                      {missingChecklist.length === 0 ? <li className="text-emerald-300">No missing items flagged.</li> : missingChecklist.map((item) => <li key={item} className="text-amber-200">• {item}</li>)}
                    </ul>
                  </div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-white/5 p-6 xl:col-span-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">Follow-Up / RTW / Extension</h3>
                      <p className="mt-1 text-sm text-slate-400">
                        Create reminders here when the next move is a check-in, a return-to-work update, or an extension request that cannot be missed.
                      </p>
                    </div>
                    <span className="text-xs text-slate-400">Persisted reminders for employer, provider, RTW, and extension follow-up</span>
                  </div>
                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
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
                    {reminders.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No reminders linked to this FMLA case yet.</div>
                    ) : reminders.map((reminder) => (
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
              </section>
            ) : null}

            {selectedCase || creatingNewCase ? (
            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Packet & Documents</h3>
                    <p className="mt-1 text-sm text-slate-400">
                      Store the employer packet, track missing items, and log what has been received, completed, or sent back out.
                    </p>
                  </div>
                  <span className="text-xs text-slate-400">Receive/store packet, track missing paperwork, and return completed documents</span>
                </div>
                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Document type">
                      <Select value={documentForm.document_type} onChange={(e) => setDocumentForm((prev) => ({ ...prev, document_type: e.target.value }))}>
                        {['employer packet','medical certification','ROI','provider letter','extension form','denial letter','approval letter','return-to-work form','other'].map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Status">
                      <Select value={documentForm.document_status} onChange={(e) => setDocumentForm((prev) => ({ ...prev, document_status: e.target.value }))}>
                        {['needed','requested','received','completed','sent','confirmed'].map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Packet name" hint="Group multi-file submissions together">
                      <Input value={documentForm.batch_name} onChange={(e) => setDocumentForm((prev) => ({ ...prev, batch_name: e.target.value }))} placeholder="Initial employer packet" />
                    </Field>
                    <Field label="Date requested"><Input type="date" value={documentForm.date_requested} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_requested: e.target.value }))} /></Field>
                    <Field label="Date received"><Input type="date" value={documentForm.date_received} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_received: e.target.value }))} /></Field>
                    <Field label="Date completed"><Input type="date" value={documentForm.date_completed} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_completed: e.target.value }))} /></Field>
                    <Field label="Date sent"><Input type="date" value={documentForm.date_sent} onChange={(e) => setDocumentForm((prev) => ({ ...prev, date_sent: e.target.value }))} /></Field>
                    <Field label="Sent to"><Input value={documentForm.sent_to} onChange={(e) => setDocumentForm((prev) => ({ ...prev, sent_to: e.target.value }))} /></Field>
                    <Field label="Sent by"><Input value={documentForm.sent_by} onChange={(e) => setDocumentForm((prev) => ({ ...prev, sent_by: e.target.value }))} /></Field>
                    <Field label="Confirmation number"><Input value={documentForm.confirmation_number} onChange={(e) => setDocumentForm((prev) => ({ ...prev, confirmation_number: e.target.value }))} /></Field>
                    <Field label="Upload document or image" hint="PDF, DOC, JPG, PNG, and other file types">
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
                  {selectedUploads.length > 0 ? (
                    <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-sm text-cyan-100">
                      <p className="font-medium">Ready to upload {selectedUploads.length} file(s).</p>
                      <div className="mt-2 space-y-1 text-xs text-cyan-100/90">
                        {selectedUploads.map((file) => (
                          <div key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3">
                            <span className="truncate">{file.name}</span>
                            <span>{formatFileSize(file.size)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">
                      No file selected. You can still create a checklist-only document entry for requested or missing paperwork.
                    </div>
                  )}
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
                            {doc.file_name ? (
                              <p className="mt-1 text-xs text-slate-400">
                                {doc.file_name} {doc.file_size ? `• ${formatFileSize(doc.file_size)}` : ''}
                              </p>
                            ) : null}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-cyan-500/20 px-2 py-1 text-xs text-cyan-200 capitalize">{doc.document_status}</span>
                            {doc.file_path ? (
                              <button
                                onClick={() => downloadDocument(doc.document_id)}
                                className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white transition hover:bg-white/10"
                              >
                                <Download className="h-3.5 w-3.5" />
                                Download
                              </button>
                            ) : null}
                          </div>
                        </div>
                        <p className="mt-2 text-xs text-slate-400">
                          Requested {doc.date_requested || '—'} • Received {doc.date_received || '—'} • Sent {doc.date_sent || '—'}
                        </p>
                        {doc.notes ? <p className="mt-2 text-sm text-slate-300">{doc.notes}</p> : null}
                      </div>
                    ))}
                  </div>
                </div>

              <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Timeline</h3>
                    <p className="mt-1 text-sm text-slate-400">
                      Log calls, emails, faxes, and updates so the next case manager can see the full sequence of employer, provider, and client activity.
                    </p>
                  </div>
                  <span className="text-xs text-slate-400">Employer, provider, and follow-up activity history</span>
                </div>
                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Date/time"><Input type="datetime-local" value={correspondenceForm.correspondence_at} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, correspondence_at: e.target.value }))} /></Field>
                    <Field label="Contact type">
                      <Select value={correspondenceForm.contact_type} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, contact_type: e.target.value }))}>
                        {['phone','voicemail','email','fax','mail','portal','in-person'].map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Person contacted"><Input value={correspondenceForm.person_contacted} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, person_contacted: e.target.value }))} /></Field>
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
                        clientName={caseForm.client_name || ''}
                        currentText={correspondenceForm.summary}
                        context={{
                          observations: `Contact type: ${correspondenceForm.contact_type}; Person: ${correspondenceForm.person_contacted}; Organization: ${correspondenceForm.organization}`,
                          next_steps: correspondenceForm.next_step_needed,
                          paperwork_deadline: caseForm.paperwork_deadline
                        }}
                        onApplyDraft={(draft) => setCorrespondenceForm((prev) => ({ ...prev, summary: draft }))}
                      />
                    </div>
                    <Field label="Outcome"><Input value={correspondenceForm.outcome} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, outcome: e.target.value }))} /></Field>
                    <Field label="Next step needed"><Input value={correspondenceForm.next_step_needed} onChange={(e) => setCorrespondenceForm((prev) => ({ ...prev, next_step_needed: e.target.value }))} /></Field>
                  </div>
                  <button onClick={addCorrespondence} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-orange-400">
                    <MessageSquare className="h-4 w-4" />
                    Add Correspondence Entry
                  </button>
                  <div className="mt-6 space-y-3">
                    {correspondence.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No correspondence logged yet.</div>
                    ) : correspondence.map((entry) => (
                      <div key={entry.correspondence_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium capitalize">{entry.contact_type} with {entry.person_contacted || entry.organization || 'contact'}</p>
                          <span className="text-xs text-slate-400">{new Date(entry.correspondence_at).toLocaleString()}</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">{entry.summary}</p>
                        <p className="mt-2 text-xs text-slate-400">Outcome: {entry.outcome || '—'} • Follow-up: {entry.follow_up_date || '—'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  )
}

export default FMLA
