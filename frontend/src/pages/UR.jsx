import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BellRing, ClipboardList, Plus, Save, ShieldAlert } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'
import { useAuth } from '../contexts/AuthContext'
import ClientSelector from '../components/ClientSelector'
import { getIntakeContext } from '../utils/clientOperationalContext'
import {
  buildStatusBanner,
  COMMUNICATION_METHOD_OPTIONS,
  deriveCurrentWorkflowStep,
  formatCurrency,
  formatDisplayDate,
  formatPercent,
  formatUrLabel,
  deriveSuggestedStatus,
  getApprovalRate,
  getDeadlineState,
  getDeniedDays,
  getSummaryCards,
  LOC_OPTIONS,
  PROGRAM_OPTIONS,
  sortEventsNewestFirst,
  UR_EVENT_TYPE_OPTIONS,
  UR_STATUS_OPTIONS,
  WORKFLOW_STEPS
} from '../utils/ur'

const emptyCaseForm = () => ({
  client_id: '',
  client_name: '',
  assigned_case_manager: '',
  payer: '',
  member_id: '',
  policy_group_number: '',
  facility: '',
  program: '',
  current_level_of_care: '',
  requested_level_of_care: '',
  approved_level_of_care: '',
  admit_date: '',
  diagnosis: '',
  asam_level: '',
  auth_required: true,
  auth_number: '',
  requested_days: 0,
  approved_days: 0,
  denied_days: '',
  approved_start_date: '',
  approved_end_date: '',
  next_review_date: '',
  reviewer_name: '',
  reviewer_company: '',
  reviewer_phone: '',
  reviewer_fax: '',
  reviewer_email: '',
  auth_submission_method: 'Portal',
  decision_received_method: 'Portal',
  clinical_criteria_used: 'ASAM',
  clinical_justification_summary: '',
  denial_reason: '',
  peer_review_deadline: '',
  appeal_deadline: '',
  revenue_at_risk_amount: 0,
  status: 'auth_needed'
})

const emptyEventForm = () => ({
  event_type: 'initial_auth',
  event_date: new Date().toISOString().slice(0, 16),
  status: '',
  notes: '',
  requested_days: 0,
  approved_days: 0,
  denied_days: '',
  approved_start_date: '',
  approved_end_date: '',
  reviewer_name: '',
  reviewer_company: '',
  reviewer_phone: '',
  reviewer_fax: '',
  reviewer_email: '',
  auth_submission_method: 'Portal',
  decision_received_method: 'Portal',
  denial_reason: '',
  peer_review_deadline: '',
  appeal_deadline: ''
})

const Field = ({ label, children, helper }) => (
  <label className="space-y-2 block">
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm font-medium text-slate-200">{label}</span>
      {helper ? <span className="text-xs text-slate-400">{helper}</span> : null}
    </div>
    {children}
  </label>
)

const Input = (props) => (
  <input
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-amber-400 focus:outline-none ${props.className || ''}`}
  />
)

const Textarea = (props) => (
  <textarea
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-amber-400 focus:outline-none ${props.className || ''}`}
  />
)

const Select = (props) => (
  <select
    {...props}
    className={`w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white focus:border-amber-400 focus:outline-none ${props.className || ''}`}
  />
)

const WorkflowCoach = ({ currentStep }) => (
  <div className="rounded-3xl border border-amber-500/20 bg-amber-500/10 p-5">
    <div className="flex items-center justify-between gap-3">
      <div>
        <p className="text-sm font-semibold text-amber-100">UR Workflow Coach</p>
        <p className="mt-1 text-sm text-amber-50/80">Use the step guide to keep authorizations, concurrent reviews, extensions, and appeals moving.</p>
      </div>
      <ShieldAlert className="h-5 w-5 text-amber-200" />
    </div>
    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-7">
      {WORKFLOW_STEPS.map((step, index) => {
        const active = index === currentStep
        return (
          <div key={step} className={`rounded-2xl border px-4 py-3 text-sm ${active ? 'border-amber-300/40 bg-amber-400/15 text-amber-50' : 'border-white/10 bg-slate-950/30 text-slate-300'}`}>
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Step {index + 1}</p>
            <p className="mt-2 font-medium">{step}</p>
          </div>
        )
      })}
    </div>
  </div>
)

function UR() {
  const { profile } = useAuth()
  const [searchParams] = useSearchParams()
  const clientIdFromUrl = searchParams.get('client') || ''
  const defaultCaseManagerId = profile?.case_manager_id || ''
  const [summary, setSummary] = useState({})
  const [cases, setCases] = useState([])
  const [selectedCaseId, setSelectedCaseId] = useState(null)
  const [events, setEvents] = useState([])
  const [filters, setFilters] = useState({
    search: '',
    payer: '',
    status: '',
    case_manager: defaultCaseManagerId,
    due_window: ''
  })
  const [caseForm, setCaseForm] = useState(emptyCaseForm())
  const [eventForm, setEventForm] = useState(emptyEventForm())
  const [creatingNewCase, setCreatingNewCase] = useState(true)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const summaryCards = useMemo(() => getSummaryCards(summary), [summary])
  const banner = useMemo(() => buildStatusBanner(caseForm), [caseForm])
  const workflowStep = useMemo(() => deriveCurrentWorkflowStep(caseForm), [caseForm])
  const sortedEvents = useMemo(() => sortEventsNewestFirst(events), [events])
  const approvalRate = useMemo(() => formatPercent(getApprovalRate(caseForm)), [caseForm])
  const deniedDaysPreview = useMemo(() => getDeniedDays(caseForm), [caseForm])

  useEffect(() => {
    if (!defaultCaseManagerId) return
    setFilters((prev) => ({ ...prev, case_manager: prev.case_manager || defaultCaseManagerId }))
  }, [defaultCaseManagerId])

  useEffect(() => {
    if (!defaultCaseManagerId) return
    fetchSummary()
    fetchCases()
  }, [defaultCaseManagerId])

  const fetchSummary = async () => {
    try {
      const response = await apiFetch(`/api/ur/summary?case_manager_id=${encodeURIComponent(defaultCaseManagerId)}`)
      if (!response.ok) throw new Error('Failed to load UR summary')
      const data = await response.json()
      if (data.success) setSummary(data)
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load UR summary')
    }
  }

  const fetchCases = async (nextFilters = filters) => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value) params.set(key, value)
      })
      const response = await apiFetch(`/api/ur?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load UR cases')
      const data = await response.json()
      if (data.success) {
        setCases(data.cases || [])
        if (!clientIdFromUrl && !selectedCaseId && data.cases?.length && creatingNewCase) {
          loadCaseDetail(data.cases[0].case_id)
        }
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load UR cases')
    } finally {
      setLoading(false)
    }
  }

  const loadCaseDetail = async (caseId) => {
    try {
      const response = await apiFetch(`/api/ur/${caseId}`)
      if (!response.ok) throw new Error('Failed to load UR case detail')
      const data = await response.json()
      if (data.success) {
        setSelectedCaseId(caseId)
        setEvents(data.events || [])
        setCaseForm({
          ...emptyCaseForm(),
          ...data.case,
          denied_days: data.case.denied_days ?? ''
        })
        setCreatingNewCase(false)
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load UR case detail')
    }
  }

  const handleFilterChange = (key, value) => {
    const nextFilters = { ...filters, [key]: value }
    setFilters(nextFilters)
    fetchCases(nextFilters)
  }

  const handleCaseFieldChange = (key, value) => {
    setCaseForm((prev) => ({ ...prev, [key]: value }))
  }

  const handleClientSelected = (client) => {
    if (!client?.client_id) return
    if (!creatingNewCase && caseForm.client_id === client.client_id) return

    const intake = getIntakeContext(client)
    setCreatingNewCase(true)
    setSelectedCaseId(null)
    setEvents([])
    setCaseForm((prev) => ({
      ...emptyCaseForm(),
      ...(creatingNewCase ? prev : {}),
      client_id: client.client_id || '',
      client_name: `${client.first_name || ''} ${client.last_name || ''}`.trim(),
      assigned_case_manager: client.case_manager_id || prev.assigned_case_manager || defaultCaseManagerId,
      payer: client.insurance_provider || intake.insurance_provider || prev.payer,
      member_id: client.insurance_member_id || intake.insurance_member_id || prev.member_id,
      program: client.program_type || intake.program_type || prev.program,
      admit_date: client.admission_date || client.intake_date || intake.admission_date || prev.admit_date,
      diagnosis: client.diagnosis || intake.diagnosis || prev.diagnosis,
      current_level_of_care: client.level_of_care || intake.level_of_care || prev.current_level_of_care
    }))
    setEventForm(emptyEventForm())
  }

  const startNewCase = () => {
    setCreatingNewCase(true)
    setSelectedCaseId(null)
    setEvents([])
    setCaseForm({
      ...emptyCaseForm(),
      client_id: clientIdFromUrl,
      assigned_case_manager: defaultCaseManagerId
    })
    setEventForm(emptyEventForm())
  }

  const saveCase = async () => {
    try {
      setSaving(true)
      const normalizedStatus = deriveSuggestedStatus(caseForm)
      const payload = {
        ...caseForm,
        requested_days: Number(caseForm.requested_days || 0),
        approved_days: Number(caseForm.approved_days || 0),
        denied_days: caseForm.denied_days === '' ? null : Number(caseForm.denied_days || 0),
        revenue_at_risk_amount: Number(caseForm.revenue_at_risk_amount || 0),
        status: normalizedStatus
      }
      const endpoint = creatingNewCase ? '/api/ur' : `/api/ur/${selectedCaseId}`
      const method = creatingNewCase ? 'POST' : 'PUT'
      const response = await apiFetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!response.ok) throw new Error('Failed to save UR case')
      const data = await response.json()
      if (data.success) {
        toast.success(creatingNewCase ? 'UR case created' : 'UR case updated')
        await fetchSummary()
        await fetchCases()
        await loadCaseDetail(data.case.case_id)
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to save UR case')
    } finally {
      setSaving(false)
    }
  }

  const addEvent = async () => {
    if (!selectedCaseId) {
      toast.error('Create or select a UR case first')
      return
    }
    try {
      const response = await apiFetch(`/api/ur/${selectedCaseId}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...eventForm,
          requested_days: Number(eventForm.requested_days || 0),
          approved_days: Number(eventForm.approved_days || 0),
          denied_days: eventForm.denied_days === '' ? null : Number(eventForm.denied_days || 0)
        })
      })
      if (!response.ok) throw new Error('Failed to create review event')
      const data = await response.json()
      if (data.success) {
        toast.success('Review event added')
        setEvents((prev) => sortEventsNewestFirst([data.event, ...prev]))
        setEventForm(emptyEventForm())
        await fetchCases()
        await fetchSummary()
      }
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to create review event')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950 px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[96rem] space-y-6">
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl shadow-amber-950/30">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-amber-200">Utilization Review</p>
              <h1 className="mt-3 text-4xl font-bold">Utilization Review Command Center</h1>
              <p className="mt-3 max-w-3xl text-sm text-slate-300">
                Track authorizations, concurrent reviews, denials, appeals, and revenue at risk in one standalone UR workspace.
              </p>
            </div>
            <button onClick={startNewCase} className="inline-flex items-center gap-2 rounded-2xl bg-amber-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300">
              <Plus className="h-4 w-4" />
              New UR Case
            </button>
          </div>
        </section>

        <WorkflowCoach currentStep={workflowStep} />

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
          {summaryCards.map((card) => (
            <div key={card.key} className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{card.label}</p>
              <p className="mt-3 text-2xl font-bold">{card.value}</p>
            </div>
          ))}
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <h2 className="text-lg font-semibold">Case Filters</h2>
              <div className="mt-4 space-y-4">
                <Field label="Search"><Input value={filters.search} onChange={(e) => handleFilterChange('search', e.target.value)} placeholder="Client, payer, program" /></Field>
                <Field label="Payer"><Input value={filters.payer} onChange={(e) => handleFilterChange('payer', e.target.value)} placeholder="Health Net" /></Field>
                <Field label="Status">
                  <Select value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)}>
                    <option value="">All statuses</option>
                    {UR_STATUS_OPTIONS.map((item) => <option key={item} value={item}>{formatUrLabel(item)}</option>)}
                  </Select>
                </Field>
                <Field label="Due window">
                  <Select value={filters.due_window} onChange={(e) => handleFilterChange('due_window', e.target.value)}>
                    <option value="">All windows</option>
                    <option value="today">Reviews due today</option>
                    <option value="72_hours">Due in 72 hours</option>
                    <option value="auth_expiring">Auth expiring</option>
                    <option value="denials">Denials needing action</option>
                    <option value="appeals">Appeals due</option>
                  </Select>
                </Field>
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">UR Cases</h2>
                <span className="text-xs text-slate-400">{cases.length} total</span>
              </div>
              <div className="mt-4 space-y-3">
                {loading ? (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">Loading cases…</div>
                ) : cases.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No UR cases match the current filters.</div>
                ) : cases.map((record) => {
                  const active = record.case_id === selectedCaseId
                  return (
                    <button
                      key={record.case_id}
                      type="button"
                      onClick={() => loadCaseDetail(record.case_id)}
                      className={`w-full rounded-2xl border p-4 text-left transition ${active ? 'border-amber-300/40 bg-amber-500/15' : 'border-white/10 bg-slate-950/30 hover:bg-white/10'}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold">{record.client_name}</p>
                        <span className="rounded-full bg-white/10 px-2 py-1 text-[11px] uppercase tracking-widest text-slate-300">{formatUrLabel(record.status)}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-300">{record.payer} • {record.program || 'Program not set'}</p>
                      <p className="mt-1 text-xs text-slate-400">{record.current_level_of_care || 'LOC not set'} • Next review {formatDisplayDate(record.next_review_date, 'Not set')}</p>
                      <p className="mt-1 text-xs text-slate-400">Revenue at risk {formatCurrency(record.revenue_at_risk_amount || 0)}</p>
                    </button>
                  )
                })}
              </div>
            </div>
          </aside>

          <div className="space-y-6">
            <section className="rounded-3xl border border-emerald-500/15 bg-emerald-500/10 p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-emerald-200">{banner.statusLabel}</p>
                  <h2 className="mt-3 text-2xl font-bold">{creatingNewCase ? 'New UR Case' : (caseForm.client_name || 'UR Case')}</h2>
                  <p className="mt-2 text-sm text-emerald-50/80">{banner.approvedDaysLabel} • {banner.approvedSpanLabel}</p>
                </div>
                <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Next Review Due</p>
                    <p className="mt-2 font-semibold">{banner.nextReviewLabel}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Reviewer</p>
                    <p className="mt-2 font-semibold">{banner.reviewerLabel}</p>
                    <p className="text-xs text-slate-400">{banner.reviewerCompanyLabel}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Next Action</p>
                    <p className="mt-2 font-semibold">{banner.nextAction}</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">Case Detail</h2>
                  <p className="mt-1 text-sm text-slate-400">Coverage, placement, authorization detail, reviewer contacts, and clinical justification.</p>
                </div>
                <button onClick={saveCase} disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:opacity-60">
                  <Save className="h-4 w-4" />
                  {saving ? 'Saving…' : creatingNewCase ? 'Create UR Case' : 'Save UR Case'}
                </button>
              </div>

              <div className="mt-5 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-emerald-200">Case-management client</p>
                <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(320px,430px)] lg:items-center">
                  <p className="text-sm text-emerald-50/80">
                    Select the Case Management client before creating UR authorization records so intake identity, program, admission, insurance, and diagnosis data stay bound to this file.
                  </p>
                  <ClientSelector
                    selectedClientId={caseForm.client_id || clientIdFromUrl || null}
                    onClientSelect={handleClientSelected}
                    includeOperationalContext
                    showCreateNew={false}
                    placeholder="Select a case-management client for UR..."
                    className="w-full"
                  />
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
                <div className="space-y-6">
                  <SectionHeading title="Coverage & Placement" helper="Keep facility, program, and all level-of-care distinctions explicit." />
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Client"><Input value={caseForm.client_name} onChange={(e) => handleCaseFieldChange('client_name', e.target.value)} /></Field>
                    <Field label="Client ID"><Input value={caseForm.client_id} onChange={(e) => handleCaseFieldChange('client_id', e.target.value)} /></Field>
                    <Field label="Payer"><Input value={caseForm.payer} onChange={(e) => handleCaseFieldChange('payer', e.target.value)} /></Field>
                    <Field label="Member ID"><Input value={caseForm.member_id} onChange={(e) => handleCaseFieldChange('member_id', e.target.value)} /></Field>
                    <Field label="Policy / Group"><Input value={caseForm.policy_group_number} onChange={(e) => handleCaseFieldChange('policy_group_number', e.target.value)} /></Field>
                    <Field label="Facility"><Input value={caseForm.facility} onChange={(e) => handleCaseFieldChange('facility', e.target.value)} /></Field>
                    <Field label="Program">
                      <Select value={caseForm.program} onChange={(e) => handleCaseFieldChange('program', e.target.value)}>
                        <option value="">Select program</option>
                        {PROGRAM_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Admit Date"><Input type="date" value={caseForm.admit_date} onChange={(e) => handleCaseFieldChange('admit_date', e.target.value)} /></Field>
                    <Field label="Current Level of Care">
                      <Select value={caseForm.current_level_of_care} onChange={(e) => handleCaseFieldChange('current_level_of_care', e.target.value)}>
                        <option value="">Select LOC</option>
                        {LOC_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Requested Level of Care">
                      <Select value={caseForm.requested_level_of_care} onChange={(e) => handleCaseFieldChange('requested_level_of_care', e.target.value)}>
                        <option value="">Select LOC</option>
                        {LOC_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Approved Level of Care">
                      <Select value={caseForm.approved_level_of_care} onChange={(e) => handleCaseFieldChange('approved_level_of_care', e.target.value)}>
                        <option value="">Select LOC</option>
                        {LOC_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="ASAM Level"><Input value={caseForm.asam_level} onChange={(e) => handleCaseFieldChange('asam_level', e.target.value)} placeholder="3.5" /></Field>
                    <div className="md:col-span-2">
                      <Field label="Diagnosis"><Textarea rows={2} value={caseForm.diagnosis} onChange={(e) => handleCaseFieldChange('diagnosis', e.target.value)} /></Field>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <SectionHeading title="Authorization Detail" helper="Requested, approved, denied, and reviewer information drive the UR metrics." />
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Status">
                      <p className="text-xs text-amber-200/80">
                        Manual status. If this stays on Auth Needed, saving with approved days or an approved date range will promote it to Approved.
                      </p>
                      <Select value={caseForm.status} onChange={(e) => handleCaseFieldChange('status', e.target.value)}>
                        {UR_STATUS_OPTIONS.map((item) => <option key={item} value={item}>{formatUrLabel(item)}</option>)}
                      </Select>
                    </Field>
                    <Field label="Auth Required">
                      <Select value={caseForm.auth_required ? 'yes' : 'no'} onChange={(e) => handleCaseFieldChange('auth_required', e.target.value === 'yes')}>
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </Select>
                    </Field>
                    <Field label="Auth Number"><Input value={caseForm.auth_number} onChange={(e) => handleCaseFieldChange('auth_number', e.target.value)} /></Field>
                    <Field label="Clinical Criteria Used"><Input value={caseForm.clinical_criteria_used} onChange={(e) => handleCaseFieldChange('clinical_criteria_used', e.target.value)} /></Field>
                    <Field label="Requested Days"><Input type="number" min="0" value={caseForm.requested_days} onChange={(e) => handleCaseFieldChange('requested_days', e.target.value)} /></Field>
                    <Field label="Approved Days"><Input type="number" min="0" value={caseForm.approved_days} onChange={(e) => handleCaseFieldChange('approved_days', e.target.value)} /></Field>
                    <Field label="Denied Days" helper={`Derived preview: ${deniedDaysPreview}`}>
                      <Input type="number" min="0" value={caseForm.denied_days} onChange={(e) => handleCaseFieldChange('denied_days', e.target.value)} />
                    </Field>
                    <Field label="Approval Rate"><Input value={approvalRate} readOnly /></Field>
                    <Field label="Approved Start"><Input type="date" value={caseForm.approved_start_date} onChange={(e) => handleCaseFieldChange('approved_start_date', e.target.value)} /></Field>
                    <Field label="Approved End"><Input type="date" value={caseForm.approved_end_date} onChange={(e) => handleCaseFieldChange('approved_end_date', e.target.value)} /></Field>
                    <Field label="Next Review"><Input type="date" value={caseForm.next_review_date} onChange={(e) => handleCaseFieldChange('next_review_date', e.target.value)} /></Field>
                    <Field label="Revenue At Risk"><Input type="number" min="0" step="0.01" value={caseForm.revenue_at_risk_amount} onChange={(e) => handleCaseFieldChange('revenue_at_risk_amount', e.target.value)} /></Field>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
                <div>
                  <SectionHeading title="Reviewer & Communication" helper="Capture reviewer identity and how the authorization moved." />
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Reviewer Name"><Input value={caseForm.reviewer_name} onChange={(e) => handleCaseFieldChange('reviewer_name', e.target.value)} /></Field>
                    <Field label="Reviewer Company"><Input value={caseForm.reviewer_company} onChange={(e) => handleCaseFieldChange('reviewer_company', e.target.value)} /></Field>
                    <Field label="Reviewer Phone"><Input value={caseForm.reviewer_phone} onChange={(e) => handleCaseFieldChange('reviewer_phone', e.target.value)} /></Field>
                    <Field label="Reviewer Fax"><Input value={caseForm.reviewer_fax} onChange={(e) => handleCaseFieldChange('reviewer_fax', e.target.value)} /></Field>
                    <Field label="Reviewer Email"><Input value={caseForm.reviewer_email} onChange={(e) => handleCaseFieldChange('reviewer_email', e.target.value)} /></Field>
                    <Field label="Submission Method">
                      <Select value={caseForm.auth_submission_method} onChange={(e) => handleCaseFieldChange('auth_submission_method', e.target.value)}>
                        {COMMUNICATION_METHOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                    <Field label="Decision Method">
                      <Select value={caseForm.decision_received_method} onChange={(e) => handleCaseFieldChange('decision_received_method', e.target.value)}>
                        {COMMUNICATION_METHOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </Select>
                    </Field>
                  </div>
                </div>

                <div>
                  <SectionHeading title="Action Deadlines" helper="Denial reason and active deadlines determine escalation risk." />
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Peer Review Deadline">
                      <Input type="date" value={caseForm.peer_review_deadline} onChange={(e) => handleCaseFieldChange('peer_review_deadline', e.target.value)} />
                    </Field>
                    <Field label="Appeal Deadline">
                      <Input type="date" value={caseForm.appeal_deadline} onChange={(e) => handleCaseFieldChange('appeal_deadline', e.target.value)} />
                    </Field>
                    <div className="md:col-span-2">
                      <Field label="Denial Reason">
                        <Textarea rows={3} value={caseForm.denial_reason} onChange={(e) => handleCaseFieldChange('denial_reason', e.target.value)} />
                      </Field>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <SectionHeading title="Clinical Justification Summary" helper="Plain-text medical necessity summary for why treatment should continue." />
                <Textarea rows={8} value={caseForm.clinical_justification_summary} onChange={(e) => handleCaseFieldChange('clinical_justification_summary', e.target.value)} placeholder="Describe symptoms, risks, participation, barriers, step-down readiness, and why continued treatment is medically necessary." />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold">Review Timeline</h2>
                    <p className="mt-1 text-sm text-slate-400">Chronological authorization, review, denial, peer review, and appeal history.</p>
                  </div>
                  <ClipboardList className="h-5 w-5 text-slate-300" />
                </div>
                <div className="mt-5 space-y-3">
                  {sortedEvents.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-4 text-sm text-slate-400">No review events recorded yet.</div>
                  ) : sortedEvents.map((event) => {
                    const eventDeadline = getDeadlineState(event.appeal_deadline || event.peer_review_deadline || event.approved_end_date)
                    return (
                      <div key={event.event_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="font-semibold">{formatUrLabel(event.event_type)}</p>
                            <p className="mt-1 text-xs text-slate-400">{formatDisplayDate(event.event_date, event.event_date || 'No date')}</p>
                          </div>
                          <span className="rounded-full bg-white/10 px-2 py-1 text-xs uppercase tracking-wider text-slate-300">{formatUrLabel(event.status || 'logged')}</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-300">{event.notes || 'No notes entered.'}</p>
                        <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-400 md:grid-cols-2">
                          <p>Outcome: {event.approved_days || 0} approved / {event.denied_days || 0} denied</p>
                          <p>Reviewer: {event.reviewer_name || 'Not set'}{event.reviewer_company ? ` • ${event.reviewer_company}` : ''}</p>
                          <p>Auth span: {formatDisplayDate(event.approved_start_date)} - {formatDisplayDate(event.approved_end_date)}</p>
                          <p>Key deadline: {eventDeadline.label}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold">Add Review Event</h2>
                    <p className="mt-1 text-sm text-slate-400">Quick-log the latest insurance touchpoint and keep the timeline current.</p>
                  </div>
                  <BellRing className="h-5 w-5 text-slate-300" />
                </div>
                <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="Event Type">
                    <Select value={eventForm.event_type} onChange={(e) => setEventForm((prev) => ({ ...prev, event_type: e.target.value }))}>
                      {UR_EVENT_TYPE_OPTIONS.map((item) => <option key={item} value={item}>{formatUrLabel(item)}</option>)}
                    </Select>
                  </Field>
                  <Field label="Event Date">
                    <Input type="datetime-local" value={eventForm.event_date} onChange={(e) => setEventForm((prev) => ({ ...prev, event_date: e.target.value }))} />
                  </Field>
                  <Field label="Requested Days"><Input type="number" min="0" value={eventForm.requested_days} onChange={(e) => setEventForm((prev) => ({ ...prev, requested_days: e.target.value }))} /></Field>
                  <Field label="Approved Days"><Input type="number" min="0" value={eventForm.approved_days} onChange={(e) => setEventForm((prev) => ({ ...prev, approved_days: e.target.value }))} /></Field>
                  <Field label="Denied Days"><Input type="number" min="0" value={eventForm.denied_days} onChange={(e) => setEventForm((prev) => ({ ...prev, denied_days: e.target.value }))} /></Field>
                  <Field label="Status"><Input value={eventForm.status} onChange={(e) => setEventForm((prev) => ({ ...prev, status: e.target.value }))} placeholder="approved, denied, pending" /></Field>
                  <Field label="Approved Start"><Input type="date" value={eventForm.approved_start_date} onChange={(e) => setEventForm((prev) => ({ ...prev, approved_start_date: e.target.value }))} /></Field>
                  <Field label="Approved End"><Input type="date" value={eventForm.approved_end_date} onChange={(e) => setEventForm((prev) => ({ ...prev, approved_end_date: e.target.value }))} /></Field>
                  <Field label="Reviewer Name"><Input value={eventForm.reviewer_name} onChange={(e) => setEventForm((prev) => ({ ...prev, reviewer_name: e.target.value }))} /></Field>
                  <Field label="Reviewer Company"><Input value={eventForm.reviewer_company} onChange={(e) => setEventForm((prev) => ({ ...prev, reviewer_company: e.target.value }))} /></Field>
                  <Field label="Reviewer Phone"><Input value={eventForm.reviewer_phone} onChange={(e) => setEventForm((prev) => ({ ...prev, reviewer_phone: e.target.value }))} /></Field>
                  <Field label="Reviewer Fax"><Input value={eventForm.reviewer_fax} onChange={(e) => setEventForm((prev) => ({ ...prev, reviewer_fax: e.target.value }))} /></Field>
                  <Field label="Reviewer Email"><Input value={eventForm.reviewer_email} onChange={(e) => setEventForm((prev) => ({ ...prev, reviewer_email: e.target.value }))} /></Field>
                  <Field label="Submission Method">
                    <Select value={eventForm.auth_submission_method} onChange={(e) => setEventForm((prev) => ({ ...prev, auth_submission_method: e.target.value }))}>
                      {COMMUNICATION_METHOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                    </Select>
                  </Field>
                  <Field label="Decision Method">
                    <Select value={eventForm.decision_received_method} onChange={(e) => setEventForm((prev) => ({ ...prev, decision_received_method: e.target.value }))}>
                      {COMMUNICATION_METHOD_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
                    </Select>
                  </Field>
                  <Field label="Peer Review Deadline"><Input type="date" value={eventForm.peer_review_deadline} onChange={(e) => setEventForm((prev) => ({ ...prev, peer_review_deadline: e.target.value }))} /></Field>
                  <Field label="Appeal Deadline"><Input type="date" value={eventForm.appeal_deadline} onChange={(e) => setEventForm((prev) => ({ ...prev, appeal_deadline: e.target.value }))} /></Field>
                  <div className="md:col-span-2">
                    <Field label="Denial Reason"><Textarea rows={2} value={eventForm.denial_reason} onChange={(e) => setEventForm((prev) => ({ ...prev, denial_reason: e.target.value }))} /></Field>
                  </div>
                  <div className="md:col-span-2">
                    <Field label="Notes"><Textarea rows={4} value={eventForm.notes} onChange={(e) => setEventForm((prev) => ({ ...prev, notes: e.target.value }))} /></Field>
                  </div>
                </div>
                <button onClick={addEvent} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300">
                  <Plus className="h-4 w-4" />
                  Add Review Event
                </button>
              </div>
            </section>
          </div>
        </section>
      </div>
    </div>
  )
}

const SectionHeading = ({ title, helper }) => (
  <div className="mb-4">
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="mt-1 text-sm text-slate-400">{helper}</p>
  </div>
)

export default UR
