import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Clock,
  PlusCircle,
  RefreshCw,
  Sparkles,
  Target,
  ThumbsUp,
  X,
  AlertTriangle,
  Tag,
  Zap,
  Pencil,
  Save,
  Plus,
  Trash2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ClientSelector from '../components/ClientSelector'
import { apiFetch } from '../api/config'
import { fetchClientWithOperationalContext, getIntakeContext } from '../utils/clientOperationalContext'
import { useAuth } from '../contexts/AuthContext'

const STATUS_STYLES = {
  draft: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
  active: 'bg-green-500/20 text-green-300 border border-green-500/30',
  review_due: 'bg-orange-500/20 text-orange-300 border border-orange-500/30',
  completed: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  superseded: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
}

const PRIORITY_STYLES = {
  urgent: 'bg-red-500/20 text-red-300 border border-red-500/30',
  high: 'bg-orange-500/20 text-orange-300 border border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
  low: 'bg-green-500/20 text-green-300 border border-green-500/30',
}

function SectionCard({ title, icon: Icon, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white/5 border border-white/15 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-white/5 transition-colors"
      >
        <Icon size={16} className="text-cyan-400 flex-shrink-0" />
        <span className="font-semibold text-white text-sm">{title}</span>
        <span className="ml-auto text-white/40">
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </span>
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

// Auto-expanding textarea: grows with its content so case managers get a
// roomy writing surface instead of a cramped 2-row box. Falls back gracefully
// in jsdom (where scrollHeight is 0) by honoring the inline min-height.
function AutoTextarea({ value, onChange, className = '', minHeight = 112, ...rest }) {
  const ref = useRef(null)

  const resize = () => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.max(el.scrollHeight, minHeight)}px`
  }

  useEffect(() => {
    resize()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => {
        onChange(e)
        resize()
      }}
      style={{ minHeight }}
      className={className}
      {...rest}
    />
  )
}

function NeedTag({ need }) {
  const priority = (need.priority || 'medium').toLowerCase()
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${PRIORITY_STYLES[priority] || PRIORITY_STYLES.medium}`}>
      <Tag size={10} />
      {String(need.need_key || '').replace(/_/g, ' ')}
    </span>
  )
}

function PlanList({ plans, selectedId, onSelect }) {
  if (!plans.length) return null
  return (
    <div className="space-y-2">
      {plans.map(plan => (
        <button
          key={plan.plan_id}
          onClick={() => onSelect(plan)}
          className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
            selectedId === plan.plan_id
              ? 'border-cyan-500/50 bg-cyan-500/10'
              : 'border-white/10 bg-white/5 hover:bg-white/10'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-white truncate">
              {plan.status === 'active' ? 'Active Plan' : `Plan — ${plan.status}`}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[plan.status] || STATUS_STYLES.draft}`}>
              {plan.status}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Created {plan.created_at ? new Date(plan.created_at).toLocaleDateString() : '—'}
          </p>
        </button>
      ))}
    </div>
  )
}

export default function TreatmentPlan() {
  const [searchParams] = useSearchParams()
  const { profile } = useAuth()
  const [selectedClient, setSelectedClient] = useState(null)
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [approving, setApproving] = useState(false)
  const [createdTasks, setCreatedTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState(null)

  useEffect(() => {
    const clientId = searchParams.get('client')
    if (clientId && !selectedClient) {
      fetchClientWithOperationalContext(apiFetch, clientId)
        .then(setSelectedClient)
        .catch(() => {})
    }
  }, [searchParams])

  useEffect(() => {
    setEditing(false)
    setEditForm(null)
    if (!selectedClient?.client_id) {
      setPlans([])
      setSelectedPlan(null)
      setCreatedTasks([])
      return
    }
    loadPlans(selectedClient.client_id)
  }, [selectedClient?.client_id])

  const loadPlans = async (clientId) => {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/clients/${encodeURIComponent(clientId)}/treatment-plan`)
      if (res.ok) {
        const data = await res.json()
        const allPlans = data.plans || []
        setPlans(allPlans)
        setSelectedPlan(data.current_plan || allPlans[0] || null)
      }
    } catch {
      toast.error('Failed to load treatment plans')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateDraft = async () => {
    if (!selectedClient?.client_id) return
    setGenerating(true)
    try {
      const intake = getIntakeContext(selectedClient)
      const res = await apiFetch(`/api/clients/${encodeURIComponent(selectedClient.client_id)}/treatment-plan/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: {
            housing_status: intake.housing_status,
            employment_status: intake.employment_status,
            legal_status: intake.legal_status,
            medical_conditions: intake.medical_conditions,
            mental_health_status: intake.mental_health_status,
            goals: intake.goals,
            barriers: intake.barriers,
          },
        }),
      })
      if (!res.ok) throw new Error('Failed to generate draft')
      const data = await res.json()
      toast.success('AI draft treatment plan created!')
      await loadPlans(selectedClient.client_id)
      if (data.plan) setSelectedPlan(data.plan)
    } catch (err) {
      toast.error('Failed to generate treatment plan draft')
    } finally {
      setGenerating(false)
    }
  }

  const handleApprovePlan = async () => {
    if (!selectedClient?.client_id || !selectedPlan?.plan_id) return
    setApproving(true)
    try {
      const res = await apiFetch(
        `/api/clients/${encodeURIComponent(selectedClient.client_id)}/treatment-plan/${encodeURIComponent(selectedPlan.plan_id)}/approve`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error('Approval failed')
      const data = await res.json()
      toast.success(`Plan approved! ${data.created_task_count || 0} tasks generated.`)
      setCreatedTasks(data.created_tasks || [])
      await loadPlans(selectedClient.client_id)
    } catch {
      toast.error('Failed to approve treatment plan')
    } finally {
      setApproving(false)
    }
  }

  const listOrEmpty = (val) => (Array.isArray(val) ? val : [])

  // ---- Draft edit mode ----------------------------------------------------
  const handleSelectPlan = (plan) => {
    setEditing(false)
    setEditForm(null)
    setSelectedPlan(plan)
  }

  const beginEdit = () => {
    if (!selectedPlan) return
    const toObj = (item, key = 'description') =>
      typeof item === 'string' ? { [key]: item } : { ...(item || {}) }
    setEditForm({
      problems: listOrEmpty(selectedPlan.problems).map((p) => toObj(p)),
      goals: listOrEmpty(selectedPlan.goals).map((g) => toObj(g)),
      objectives: listOrEmpty(selectedPlan.objectives).map((o) => toObj(o)),
      interventions: listOrEmpty(selectedPlan.interventions).map((iv) => toObj(iv)),
      aftercare_plan: { ...(selectedPlan.aftercare_plan && typeof selectedPlan.aftercare_plan === 'object' ? selectedPlan.aftercare_plan : {}) },
      completion_criteria: listOrEmpty(selectedPlan.completion_criteria).map((c) =>
        typeof c === 'string' ? c : (c?.description || ''),
      ),
      operational_needs: listOrEmpty(selectedPlan.operational_needs).map((n) => ({ ...(n || {}) })),
    })
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setEditForm(null)
  }

  const updateItem = (section, index, field, value) => {
    setEditForm((prev) => {
      const list = [...(prev[section] || [])]
      list[index] = { ...list[index], [field]: value }
      return { ...prev, [section]: list }
    })
  }

  const removeItem = (section, index) => {
    setEditForm((prev) => ({
      ...prev,
      [section]: (prev[section] || []).filter((_, i) => i !== index),
    }))
  }

  const addItem = (section, blank) => {
    setEditForm((prev) => ({ ...prev, [section]: [...(prev[section] || []), blank] }))
  }

  const updateCriterion = (index, value) => {
    setEditForm((prev) => {
      const list = [...(prev.completion_criteria || [])]
      list[index] = value
      return { ...prev, completion_criteria: list }
    })
  }

  const updateAftercare = (field, value) => {
    setEditForm((prev) => ({ ...prev, aftercare_plan: { ...prev.aftercare_plan, [field]: value } }))
  }

  const handleSaveEdit = async () => {
    if (!selectedClient?.client_id || !selectedPlan?.plan_id || !editForm) return
    setSaving(true)
    try {
      const res = await apiFetch(
        `/api/clients/${encodeURIComponent(selectedClient.client_id)}/treatment-plan/${encodeURIComponent(selectedPlan.plan_id)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            problems: editForm.problems,
            goals: editForm.goals,
            objectives: editForm.objectives,
            interventions: editForm.interventions,
            aftercare_plan: editForm.aftercare_plan,
            completion_criteria: (editForm.completion_criteria || [])
              .map((c) => (typeof c === 'string' ? c.trim() : c))
              .filter(Boolean),
            operational_needs: editForm.operational_needs,
          }),
        },
      )
      if (!res.ok) throw new Error('Save failed')
      const data = await res.json()
      toast.success('Treatment plan updated')
      setEditing(false)
      setEditForm(null)
      if (data.plan) setSelectedPlan(data.plan)
      await loadPlans(selectedClient.client_id)
    } catch {
      toast.error('Failed to save treatment plan')
    } finally {
      setSaving(false)
    }
  }

  const inputCls =
    'w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500/50'

  // Roomy writing surface for free-text fields: larger padding, comfortable
  // line spacing, and resize-y so a case manager can drag it taller too.
  const textareaCls =
    'w-full bg-white/5 border border-white/15 rounded-lg px-3.5 py-2.5 text-sm text-gray-100 placeholder-gray-500 leading-relaxed resize-y focus:outline-none focus:border-cyan-500/50'

  const fieldLabelCls = 'block text-xs font-medium text-gray-400 mb-1'

  const AddRowButton = ({ onClick, label }) => (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-xs font-medium text-gray-200 transition-colors"
    >
      <Plus size={12} /> {label}
    </button>
  )

  const RemoveRowButton = ({ onClick }) => (
    <button
      type="button"
      onClick={onClick}
      aria-label="Remove item"
      className="flex-shrink-0 p-1.5 rounded-lg border border-white/10 text-gray-400 hover:text-red-300 hover:border-red-500/30 hover:bg-red-500/10 transition-colors"
    >
      <Trash2 size={13} />
    </button>
  )

  const renderEditForm = () => {
    if (!editForm) return null
    return (
      <div className="space-y-4">
        {/* Problems */}
        <SectionCard title="Problems" icon={AlertTriangle}>
          <div className="space-y-3 pt-1">
            {editForm.problems.map((p, i) => (
              <div key={i} className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex-1 space-y-3">
                  <div>
                    <label className={fieldLabelCls}>Domain</label>
                    <input
                      className={inputCls}
                      placeholder="Domain (e.g. housing)"
                      value={p.domain || ''}
                      onChange={(e) => updateItem('problems', i, 'domain', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={fieldLabelCls}>Description</label>
                    <AutoTextarea
                      className={textareaCls}
                      placeholder="Describe the problem in the client's words and clinical terms…"
                      value={p.description || ''}
                      onChange={(e) => updateItem('problems', i, 'description', e.target.value)}
                    />
                  </div>
                </div>
                <RemoveRowButton onClick={() => removeItem('problems', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('problems', { domain: '', description: '' })} label="Add problem" />
          </div>
        </SectionCard>

        {/* Goals */}
        <SectionCard title="Goals" icon={Target}>
          <div className="space-y-3 pt-1">
            {editForm.goals.map((g, i) => (
              <div key={i} className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex-1 space-y-3">
                  <div>
                    <label className={fieldLabelCls}>Goal</label>
                    <AutoTextarea
                      className={textareaCls}
                      placeholder="Describe the goal the client is working toward…"
                      value={g.description || ''}
                      onChange={(e) => updateItem('goals', i, 'description', e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                      className={inputCls}
                      placeholder="Target date"
                      value={g.target_date || ''}
                      onChange={(e) => updateItem('goals', i, 'target_date', e.target.value)}
                    />
                    <select
                      className={inputCls}
                      value={g.status || 'draft'}
                      onChange={(e) => updateItem('goals', i, 'status', e.target.value)}
                    >
                      <option className="bg-gray-800" value="draft">draft</option>
                      <option className="bg-gray-800" value="active">active</option>
                      <option className="bg-gray-800" value="completed">completed</option>
                    </select>
                  </div>
                </div>
                <RemoveRowButton onClick={() => removeItem('goals', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('goals', { description: '', status: 'draft' })} label="Add goal" />
          </div>
        </SectionCard>

        {/* Objectives */}
        <SectionCard title="Objectives" icon={ChevronRight}>
          <div className="space-y-3 pt-1">
            {editForm.objectives.map((o, i) => (
              <div key={i} className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex-1 space-y-3">
                  <div>
                    <label className={fieldLabelCls}>Objective</label>
                    <AutoTextarea
                      className={textareaCls}
                      placeholder="Describe the measurable step toward the goal…"
                      value={o.description || ''}
                      onChange={(e) => updateItem('objectives', i, 'description', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={fieldLabelCls}>Measure</label>
                    <input
                      className={inputCls}
                      placeholder="How progress is measured"
                      value={o.measure || ''}
                      onChange={(e) => updateItem('objectives', i, 'measure', e.target.value)}
                    />
                  </div>
                </div>
                <RemoveRowButton onClick={() => removeItem('objectives', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('objectives', { description: '', measure: '' })} label="Add objective" />
          </div>
        </SectionCard>

        {/* Interventions */}
        <SectionCard title="Interventions" icon={Zap}>
          <div className="space-y-3 pt-1">
            {editForm.interventions.map((iv, i) => (
              <div key={i} className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex-1 space-y-3">
                  <div>
                    <label className={fieldLabelCls}>Intervention</label>
                    <AutoTextarea
                      className={textareaCls}
                      placeholder="Describe the service or support being provided…"
                      value={iv.description || ''}
                      onChange={(e) => updateItem('interventions', i, 'description', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={fieldLabelCls}>Frequency</label>
                    <input
                      className={inputCls}
                      placeholder="Frequency (e.g. weekly)"
                      value={iv.frequency || ''}
                      onChange={(e) => updateItem('interventions', i, 'frequency', e.target.value)}
                    />
                  </div>
                </div>
                <RemoveRowButton onClick={() => removeItem('interventions', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('interventions', { description: '', frequency: '' })} label="Add intervention" />
          </div>
        </SectionCard>

        {/* Aftercare Plan */}
        <SectionCard title="Aftercare Plan" icon={ClipboardList} defaultOpen={false}>
          <div className="space-y-3 pt-1">
            <div>
              <label className={fieldLabelCls}>Summary</label>
              <input
                className={inputCls}
                placeholder="Aftercare summary"
                value={editForm.aftercare_plan.summary || ''}
                onChange={(e) => updateAftercare('summary', e.target.value)}
              />
            </div>
            <div>
              <label className={fieldLabelCls}>Notes</label>
              <AutoTextarea
                className={textareaCls}
                minHeight={144}
                placeholder="Document the aftercare plan: referrals, follow-up cadence, support network, relapse-prevention steps…"
                value={editForm.aftercare_plan.notes || ''}
                onChange={(e) => updateAftercare('notes', e.target.value)}
              />
            </div>
          </div>
        </SectionCard>

        {/* Completion Criteria */}
        <SectionCard title="Completion Criteria" icon={CheckCircle} defaultOpen={false}>
          <div className="space-y-3 pt-1">
            {editForm.completion_criteria.map((c, i) => (
              <div key={i} className="flex items-start gap-2">
                <AutoTextarea
                  className={textareaCls}
                  minHeight={72}
                  placeholder="Describe what 'done' looks like for this plan…"
                  value={c}
                  onChange={(e) => updateCriterion(i, e.target.value)}
                />
                <RemoveRowButton onClick={() => removeItem('completion_criteria', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('completion_criteria', '')} label="Add criterion" />
          </div>
        </SectionCard>

        {/* Operational Needs */}
        <SectionCard title="Operational Needs" icon={Tag} defaultOpen={false}>
          <div className="space-y-3 pt-1">
            {editForm.operational_needs.map((n, i) => (
              <div key={i} className="flex items-start gap-2 bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    className={inputCls}
                    placeholder="Need key (e.g. dental)"
                    value={n.need_key || ''}
                    onChange={(e) => updateItem('operational_needs', i, 'need_key', e.target.value)}
                  />
                  <select
                    className={inputCls}
                    value={(n.priority || 'medium').toLowerCase()}
                    onChange={(e) => updateItem('operational_needs', i, 'priority', e.target.value)}
                  >
                    <option className="bg-gray-800" value="urgent">urgent</option>
                    <option className="bg-gray-800" value="high">high</option>
                    <option className="bg-gray-800" value="medium">medium</option>
                    <option className="bg-gray-800" value="low">low</option>
                  </select>
                </div>
                <RemoveRowButton onClick={() => removeItem('operational_needs', i)} />
              </div>
            ))}
            <AddRowButton onClick={() => addItem('operational_needs', { need_key: '', priority: 'medium' })} label="Add need" />
          </div>
        </SectionCard>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 border border-emerald-500/30 rounded-2xl">
            <Brain size={28} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-emerald-200 to-cyan-300 bg-clip-text text-transparent">
              Treatment Plan
            </h1>
            <p className="text-gray-400 text-sm mt-0.5">
              AI-drafted, case-manager approved service bible
            </p>
          </div>
        </div>

        {/* Client Selector */}
        <div className="bg-white/5 border border-white/15 rounded-2xl p-5">
          <ClientSelector
            onClientSelect={setSelectedClient}
            selectedClient={selectedClient}
            includeOperationalContext
            placeholder="Select a client to view or create a treatment plan…"
          />
        </div>

        {/* Empty-state guidance — shown only when no client is selected */}
        {!selectedClient && (
          <div
            data-testid="treatment-plan-empty-state"
            className="bg-white/5 border border-white/15 rounded-2xl p-6 text-center"
          >
            <ClipboardList size={36} className="text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-400 max-w-sm mx-auto">
              Select a client to view or create their treatment plan.
            </p>
            <p className="text-xs text-gray-500 mt-3">
              You can also open a treatment plan from a client&apos;s profile.
            </p>
          </div>
        )}

        {selectedClient && (
          <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-6">

            {/* Left: plan list + actions */}
            <div className="space-y-4">
              <div className="bg-white/5 border border-white/15 rounded-2xl p-5 space-y-4">
                <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Plans</h2>

                {loading ? (
                  <p className="text-gray-500 text-sm">Loading…</p>
                ) : plans.length === 0 ? (
                  <p className="text-gray-500 text-sm">No plans yet.</p>
                ) : (
                  <PlanList plans={plans} selectedId={selectedPlan?.plan_id} onSelect={handleSelectPlan} />
                )}

                <button
                  onClick={handleGenerateDraft}
                  disabled={generating}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all"
                >
                  {generating ? (
                    <><RefreshCw size={15} className="animate-spin" /> Generating…</>
                  ) : (
                    <><Sparkles size={15} /> Generate AI Draft</>
                  )}
                </button>
              </div>

              {/* Client intake snapshot */}
              {selectedClient && (
                <div className="bg-white/5 border border-white/15 rounded-2xl p-5 space-y-3">
                  <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Intake Snapshot</h2>
                  {(() => {
                    const intake = getIntakeContext(selectedClient)
                    const fields = [
                      { label: 'Housing', value: intake.housing_status },
                      { label: 'Employment', value: intake.employment_status },
                      { label: 'Legal', value: intake.legal_status },
                      { label: 'Benefits', value: intake.benefits_status },
                      { label: 'Medical', value: intake.medical_conditions },
                    ]
                    return fields.map(f =>
                      f.value ? (
                        <div key={f.label} className="flex gap-2">
                          <span className="text-xs text-gray-500 w-20 flex-shrink-0">{f.label}</span>
                          <span className="text-xs text-gray-300 truncate">{f.value}</span>
                        </div>
                      ) : null
                    )
                  })()}
                </div>
              )}
            </div>

            {/* Right: plan detail */}
            <div className="space-y-4">
              {!selectedPlan ? (
                <div className="bg-white/5 border border-white/15 rounded-2xl p-12 text-center">
                  <ClipboardList size={48} className="text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-400">No plan selected</h3>
                  <p className="text-gray-500 text-sm mt-2">
                    Generate an AI draft or select a plan from the list.
                  </p>
                </div>
              ) : (
                <>
                  {/* Plan header */}
                  <div className="bg-gradient-to-br from-white/8 to-white/3 border border-white/15 rounded-2xl p-6">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <h2 className="text-xl font-bold text-white">
                            {selectedPlan.status === 'active' ? 'Active Treatment Plan' : 'Treatment Plan Draft'}
                          </h2>
                          <span className={`text-xs px-3 py-1 rounded-full ${STATUS_STYLES[selectedPlan.status] || STATUS_STYLES.draft}`}>
                            {selectedPlan.status}
                          </span>
                        </div>
                        <p className="text-sm text-gray-400 mt-1">
                          Created {selectedPlan.created_at ? new Date(selectedPlan.created_at).toLocaleString() : '—'}
                          {selectedPlan.approved_at && ` · Approved ${new Date(selectedPlan.approved_at).toLocaleDateString()}`}
                        </p>
                      </div>

                      {selectedPlan.status === 'draft' && !editing && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={beginEdit}
                            className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 border border-white/15 text-white rounded-xl font-semibold text-sm transition-all"
                          >
                            <Pencil size={14} /> Edit Draft
                          </button>
                          <button
                            onClick={handleApprovePlan}
                            disabled={approving}
                            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all"
                          >
                            {approving ? (
                              <><RefreshCw size={14} className="animate-spin" /> Approving…</>
                            ) : (
                              <><ThumbsUp size={14} /> Approve Plan</>
                            )}
                          </button>
                        </div>
                      )}

                      {selectedPlan.status === 'draft' && editing && (
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={handleSaveEdit}
                            disabled={saving}
                            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all"
                          >
                            {saving ? (
                              <><RefreshCw size={14} className="animate-spin" /> Saving…</>
                            ) : (
                              <><Save size={14} /> Save Changes</>
                            )}
                          </button>
                          <button
                            onClick={cancelEdit}
                            disabled={saving}
                            className="flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 border border-white/15 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-all"
                          >
                            <X size={14} /> Cancel
                          </button>
                        </div>
                      )}

                      {selectedPlan.status !== 'draft' && (
                        <p className="text-xs text-gray-400 max-w-[14rem] text-right">
                          Approved plans require a revision before editing.
                        </p>
                      )}
                    </div>
                  </div>

                  {editing && renderEditForm()}

                  {!editing && (
                  <>
                  {/* Operational Needs */}
                  {listOrEmpty(selectedPlan.operational_needs).length > 0 && (
                    <SectionCard title="Operational Needs" icon={Target}>
                      <div className="flex flex-wrap gap-2 pt-1">
                        {listOrEmpty(selectedPlan.operational_needs).map((need, i) => (
                          <NeedTag key={i} need={need} />
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {/* Problems */}
                  {listOrEmpty(selectedPlan.problems).length > 0 && (
                    <SectionCard title="Problems" icon={AlertTriangle}>
                      <div className="space-y-3 pt-1">
                        {listOrEmpty(selectedPlan.problems).map((p, i) => (
                          <div key={i} className="bg-white/5 rounded-lg p-3">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                {p.domain || 'general'}
                              </span>
                              {p.source && (
                                <span className="text-xs text-gray-500">{p.source}</span>
                              )}
                            </div>
                            <p className="text-sm text-gray-200">{p.description}</p>
                          </div>
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {/* Goals */}
                  {listOrEmpty(selectedPlan.goals).length > 0 && (
                    <SectionCard title="Goals" icon={Target}>
                      <div className="space-y-3 pt-1">
                        {listOrEmpty(selectedPlan.goals).map((g, i) => (
                          <div key={i} className="flex items-start gap-3 bg-white/5 rounded-lg p-3">
                            <div className="w-6 h-6 rounded-full bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-xs text-cyan-300 font-bold">{i + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-gray-200">{g.description || g}</p>
                              {g.target_date && (
                                <p className="text-xs text-gray-500 mt-1">
                                  <Clock size={10} className="inline mr-1" />
                                  Target: {g.target_date}
                                </p>
                              )}
                            </div>
                            {g.status && (
                              <span className={`text-xs px-2 py-0.5 rounded flex-shrink-0 ${
                                g.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-white/10 text-gray-400'
                              }`}>
                                {g.status}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {/* Objectives */}
                  {listOrEmpty(selectedPlan.objectives).length > 0 && (
                    <SectionCard title="Objectives" icon={ChevronRight} defaultOpen={false}>
                      <div className="space-y-2 pt-1">
                        {listOrEmpty(selectedPlan.objectives).map((o, i) => (
                          <div key={i} className="bg-white/5 rounded-lg p-3">
                            <p className="text-sm text-gray-200">{o.description || o}</p>
                            {o.measure && <p className="text-xs text-gray-500 mt-1">Measure: {o.measure}</p>}
                          </div>
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {/* Interventions */}
                  {listOrEmpty(selectedPlan.interventions).length > 0 && (
                    <SectionCard title="Interventions" icon={Zap} defaultOpen={false}>
                      <div className="space-y-2 pt-1">
                        {listOrEmpty(selectedPlan.interventions).map((iv, i) => (
                          <div key={i} className="bg-white/5 rounded-lg p-3 flex items-start gap-3">
                            <div className="flex-1">
                              <p className="text-sm text-gray-200">{iv.description || iv}</p>
                              {iv.assigned_module && (
                                <p className="text-xs text-gray-500 mt-1">
                                  Module: {String(iv.assigned_module).replace(/_/g, ' ')} · {iv.frequency || 'as needed'}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </SectionCard>
                  )}

                  {/* Aftercare Plan */}
                  {selectedPlan.aftercare_plan && Object.keys(selectedPlan.aftercare_plan).length > 0 && (
                    <SectionCard title="Aftercare Plan" icon={ClipboardList} defaultOpen={false}>
                      <div className="grid grid-cols-2 gap-3 pt-1">
                        {Object.entries(selectedPlan.aftercare_plan).map(([key, val]) =>
                          key !== 'notes' && typeof val === 'boolean' ? (
                            <div key={key} className={`flex items-center gap-2 px-3 py-2 rounded-lg ${val ? 'bg-green-500/10 border border-green-500/20' : 'bg-white/5 border border-white/10'}`}>
                              <CheckCircle size={13} className={val ? 'text-green-400' : 'text-gray-600'} />
                              <span className="text-xs text-gray-300 capitalize">
                                {String(key).replace(/_needed|_/g, m => m === '_needed' ? '' : ' ').trim()}
                              </span>
                            </div>
                          ) : null
                        )}
                        {selectedPlan.aftercare_plan.notes && (
                          <div className="col-span-2 text-sm text-gray-300 bg-white/5 rounded-lg p-3">
                            {selectedPlan.aftercare_plan.notes}
                          </div>
                        )}
                      </div>
                    </SectionCard>
                  )}

                  {/* Completion Criteria */}
                  {listOrEmpty(selectedPlan.completion_criteria).length > 0 && (
                    <SectionCard title="Completion Criteria" icon={CheckCircle} defaultOpen={false}>
                      <ul className="space-y-2 pt-1">
                        {listOrEmpty(selectedPlan.completion_criteria).map((c, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                            <CheckCircle size={13} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                            {typeof c === 'string' ? c : c.description || JSON.stringify(c)}
                          </li>
                        ))}
                      </ul>
                    </SectionCard>
                  )}

                  {/* Generated tasks after approval */}
                  {createdTasks.length > 0 && (
                    <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/30 rounded-2xl p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <CheckCircle size={20} className="text-green-400" />
                        <h3 className="font-bold text-green-300">
                          {createdTasks.length} Tasks Generated from Approved Plan
                        </h3>
                      </div>
                      <div className="space-y-2">
                        {createdTasks.map(task => (
                          <div key={task.task_id} className="flex items-center gap-3 bg-white/5 rounded-lg px-4 py-2.5">
                            <span className={`text-xs px-2 py-0.5 rounded ${PRIORITY_STYLES[(task.priority || 'medium').toLowerCase()] || PRIORITY_STYLES.medium}`}>
                              {task.priority}
                            </span>
                            <span className="text-sm text-gray-200 flex-1">{task.title}</span>
                            {task.module && (
                              <span className="text-xs text-gray-500 capitalize">
                                {String(task.module).replace(/_/g, ' ')}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  </>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
