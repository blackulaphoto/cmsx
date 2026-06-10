import { useEffect, useState } from 'react'
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

  useEffect(() => {
    const clientId = searchParams.get('client')
    if (clientId && !selectedClient) {
      fetchClientWithOperationalContext(apiFetch, clientId)
        .then(setSelectedClient)
        .catch(() => {})
    }
  }, [searchParams])

  useEffect(() => {
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
                  <PlanList plans={plans} selectedId={selectedPlan?.plan_id} onSelect={setSelectedPlan} />
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

                      {selectedPlan.status === 'draft' && (
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
                      )}
                    </div>
                  </div>

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
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
