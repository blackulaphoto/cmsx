import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClipboardList, Loader2, Sparkles, Copy, CheckCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const LOCCheckbox = ({ label, checked }) => (
  <span className="inline-flex items-center gap-1 mr-4 text-sm text-slate-200">
    <span className={`inline-block w-4 h-4 border rounded ${checked ? 'bg-emerald-500 border-emerald-500' : 'border-slate-500'} flex items-center justify-center`}>
      {checked && <span className="text-white text-xs font-bold">✓</span>}
    </span>
    {label}
  </span>
)

const ProblemSection = ({ problem }) => (
  <div className="space-y-3">
    <p className="text-sm font-bold text-emerald-300">Problem {problem.number}: {problem.title}</p>

    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Problem {problem.number}: Goal</p>
      <p className="mt-1 text-sm text-slate-200">{problem.goal}</p>
    </div>

    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Problem {problem.number}: Objective</p>
      <p className="mt-1 text-sm text-slate-200">{problem.objective}</p>
    </div>

    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Problem {problem.number}: Plan</p>
      <p className="mt-1 text-sm text-slate-200">{problem.plan_intro}</p>
      {(problem.plan_items || []).map((item, i) => (
        <p key={i} className="mt-1 text-sm text-slate-200 pl-3">- {item}</p>
      ))}
    </div>

    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Frequency / Duration</p>
        <p className="mt-1 text-sm text-slate-200">{problem.frequency}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Target Date</p>
        <p className="mt-1 text-sm text-slate-200">{problem.target_date}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Status</p>
        <p className="mt-1 text-sm text-slate-200">{problem.status}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Outcome</p>
        <p className="mt-1 text-sm text-slate-200">{problem.outcome}</p>
      </div>
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Comment</p>
        <p className="mt-1 text-sm text-slate-200">{problem.comment}</p>
      </div>
    </div>
  </div>
)

const slugify = (value, fallback = 'item') =>
  String(value || fallback)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || fallback

const buildDraftPayload = ({ result, aftercarePlan, barriers, needs }) => {
  const problems = (result?.problems || []).map((problem, index) => ({
    problem_id: `problem_${index + 1}`,
    domain: slugify(problem.title || 'case_management', 'case_management'),
    description: problem.title || barriers || 'Treatment plan problem requires review',
    source: 'treatment_plan_assist',
  }))

  const goals = (result?.problems || [])
    .map((problem, index) => problem?.goal ? {
      goal_id: `goal_${index + 1}`,
      description: problem.goal,
      status: 'draft',
      source: 'treatment_plan_assist',
    } : null)
    .filter(Boolean)

  const objectives = (result?.problems || [])
    .map((problem, index) => problem?.objective ? {
      objective_id: `objective_${index + 1}`,
      description: problem.objective,
      measure: problem.frequency || 'Case manager review',
      status: 'draft',
      source: 'treatment_plan_assist',
    } : null)
    .filter(Boolean)

  const interventions = (result?.problems || []).flatMap((problem, problemIndex) =>
    (problem?.plan_items || []).map((item, itemIndex) => ({
      intervention_id: `intervention_${problemIndex + 1}_${itemIndex + 1}`,
      description: item,
      frequency: problem.frequency || '',
      assigned_to: 'case_manager',
      status: 'draft',
      source: 'treatment_plan_assist',
    }))
  )

  const operationalNeeds = (needs || []).map((need, index) => ({
    need_id: `need_${index + 1}`,
    need_key: slugify(need, `need_${index + 1}`),
    domain: slugify(need, 'case_management'),
    priority: 'medium',
    status: 'pending',
    source: 'treatment_plan_assist',
    reason: `Identified during treatment plan assist: ${need}`,
  }))

  const payload = {
    source: 'treatment_plan_assist',
    problems,
    goals,
    objectives,
    interventions,
    operational_needs: operationalNeeds,
  }

  const aftercareSummary = result?.aftercare_plan || aftercarePlan
  if (aftercareSummary) {
    payload.aftercare_plan = {
      summary: aftercareSummary,
      notes: result?.progress_summary || '',
      source: 'treatment_plan_assist',
    }
  }

  return payload
}

const TreatmentPlanAssistCard = ({
  clientId = '',
  clientName = '',
  clientGoals = '',
  barriers = '',
  strengths = '',
  weaknesses = '',
  reasonForTreatment = '',
  dischargePlan = '',
  aftercarePlan = '',
  education = '',
  levelOfCare = 'IOP',
  projectedLos = '30-45 days',
  admitDate = '',
  legalNeeds = '',
  medicalNeeds = '',
  housingStatus = '',
  employmentStatus = '',
  legalStatus = '',
  medicalConditions = '',
  caseManagerName = '',
  needs = [],
  onApplySuggestions
}) => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [creatingDraft, setCreatingDraft] = useState(false)
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)

  const loadSuggestions = async () => {
    try {
      setLoading(true)
      const response = await apiFetch('/api/ai-documentation/treatment-plan-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId || undefined,
          client_name: clientName || undefined,
          strengths,
          weaknesses,
          reason_for_treatment: reasonForTreatment,
          discharge_plan: dischargePlan,
          level_of_care: levelOfCare,
          projected_los: projectedLos,
          admit_date: admitDate || undefined,
          education,
          aftercare_plan: aftercarePlan,
          legal_needs: legalNeeds,
          medical_needs: medicalNeeds,
          case_manager_name: caseManagerName,
          context: {
            client_goals: clientGoals,
            barriers,
            needs,
            housing_status: housingStatus,
            employment_status: employmentStatus,
            legal_status: legalStatus,
            medical_conditions: medicalConditions,
          }
        })
      })
      if (!response.ok) throw new Error('Failed to load treatment plan suggestions')
      const data = await response.json()
      setResult(data)
      toast.success('Treatment plan generated')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to generate treatment plan')
    } finally {
      setLoading(false)
    }
  }

  const buildPlainText = (r) => {
    const loc = r.loc_options || {}
    const locLine = ['PHP', 'IOP', 'OP'].map(l => `${loc[l] ? '☑' : '☐'} ${l}`).join('  ')
    const lines = [
      'TREATMENT PLAN REVIEW',
      '',
      `Level of Care: ${locLine}`,
      `Date of Review: ${r.review_date}`,
      `Case Manager: ${r.case_manager_name || 'Case Manager'}   Date assigned: ${r.admit_date}`,
      `Projected length of stay: ${r.projected_los}`,
      '',
      '---',
    ]
    if (r.client_strengths) lines.push(`Client strengths:\nCT stated "${r.client_strengths}"`, '')
    if (r.client_weaknesses) lines.push(`Client Weaknesses:\nCT stated "${r.client_weaknesses}"`, '')
    if (r.reason_for_treatment) lines.push(`I am here because:\nCT stated "${r.reason_for_treatment}"`, '')
    if (r.discharge_plan_stated) lines.push(`My discharge plans are:\nCT stated "${r.discharge_plan_stated}"`, '')
    lines.push('---', '')
    for (const p of (r.problems || [])) {
      lines.push(
        `Problem ${p.number}: ${p.title}`, '',
        `Problem ${p.number}: Goal`, p.goal, '',
        `Problem ${p.number}: Objective`, p.objective, '',
        `Problem ${p.number}: Plan`, p.plan_intro,
        ...(p.plan_items || []).map(i => `- ${i}`),
        '',
        `Problem ${p.number}: Frequency/Duration: ${p.frequency}`,
        `Problem ${p.number}: Target Date: ${p.target_date}`,
        `Problem ${p.number}: Status: ${p.status}`,
        `Problem ${p.number}: Outcome: ${p.outcome}`,
        `Problem ${p.number}: Comment: ${p.comment}`,
        '', '---', ''
      )
    }
    lines.push(
      'I acknowledge that I have participated in the development of my treatment plans, I have reviewed and received a copy of this Treatment Plan and I agree to participate in this part of my treatment to the best of my ability.',
      '',
      'I have read this report and: agree with its contents.',
      '',
      'Please send to portal for client signature.'
    )
    return lines.join('\n')
  }

  const handleCopy = () => {
    if (!result) return
    navigator.clipboard.writeText(buildPlainText(result)).then(() => {
      setCopied(true)
      toast.success('Treatment plan copied to clipboard')
      setTimeout(() => setCopied(false), 2500)
    })
  }

  const handleCreateDraft = async () => {
    if (!clientId) {
      toast.error('Save the client before creating a treatment plan draft')
      return
    }
    if (!result) {
      toast.error('Generate treatment plan suggestions first')
      return
    }

    try {
      setCreatingDraft(true)
      const response = await apiFetch(`/api/clients/${encodeURIComponent(clientId)}/treatment-plan/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildDraftPayload({ result, aftercarePlan, barriers, needs })),
      })
      if (!response.ok) throw new Error('Failed to create treatment plan draft')
      toast.success('Treatment plan draft created')
      navigate(`/treatment-plan?client=${encodeURIComponent(clientId)}`)
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to create treatment plan draft')
    } finally {
      setCreatingDraft(false)
    }
  }

  return (
    <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-emerald-100">Treatment Plan Assist</p>
          <p className="text-xs text-slate-400">Generates a clinical treatment plan from the intake information above.</p>
        </div>
        <ClipboardList className="h-4 w-4 text-emerald-300 shrink-0" />
      </div>

      <button
        onClick={loadSuggestions}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        Generate Treatment Plan
      </button>

      {result && (
        <div className="space-y-5 rounded-xl border border-white/10 bg-slate-950/60 p-5">
          {/* Header */}
          <div className="border-b border-white/10 pb-4">
            <p className="text-base font-bold text-white tracking-wide">TREATMENT PLAN REVIEW</p>
            <div className="mt-2 flex flex-wrap gap-1 text-sm">
              {['PHP', 'IOP', 'OP'].map(loc => (
                <LOCCheckbox key={loc} label={loc} checked={!!(result.loc_options || {})[loc]} />
              ))}
            </div>
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-1 text-sm text-slate-300">
              <span><span className="text-slate-500">Date of Review:</span> {result.review_date}</span>
              <span><span className="text-slate-500">Projected LOS:</span> {result.projected_los}</span>
              <span><span className="text-slate-500">Case Manager:</span> {result.case_manager_name || 'Case Manager'}</span>
              <span><span className="text-slate-500">Date Assigned:</span> {result.admit_date}</span>
            </div>
          </div>

          {/* Client Voice */}
          {(result.client_strengths || result.client_weaknesses || result.reason_for_treatment || result.discharge_plan_stated) && (
            <div className="space-y-3 border-b border-white/10 pb-4">
              {result.client_strengths && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Client Strengths</p>
                  <p className="mt-1 text-sm text-slate-200">CT stated &ldquo;{result.client_strengths}&rdquo;</p>
                </div>
              )}
              {result.client_weaknesses && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Client Weaknesses</p>
                  <p className="mt-1 text-sm text-slate-200">CT stated &ldquo;{result.client_weaknesses}&rdquo;</p>
                </div>
              )}
              {result.reason_for_treatment && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">I am here because</p>
                  <p className="mt-1 text-sm text-slate-200">CT stated &ldquo;{result.reason_for_treatment}&rdquo;</p>
                </div>
              )}
              {result.discharge_plan_stated && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">My discharge plans are</p>
                  <p className="mt-1 text-sm text-slate-200">CT stated &ldquo;{result.discharge_plan_stated}&rdquo;</p>
                </div>
              )}
            </div>
          )}

          {/* Problems */}
          {(result.problems || []).map((p, i) => (
            <div key={i} className={i < (result.problems.length - 1) ? 'border-b border-white/10 pb-4' : ''}>
              <ProblemSection problem={p} />
            </div>
          ))}

          {/* Signature block */}
          <div className="border-t border-white/10 pt-4 space-y-2">
            <p className="text-xs text-slate-400 italic">
              I acknowledge that I have participated in the development of my treatment plans, I have reviewed and received a copy of this Treatment Plan and I agree to participate in this part of my treatment to the best of my ability.
            </p>
            <p className="text-xs text-slate-400 italic">I have read this report and: agree with its contents.</p>
            <p className="text-xs text-emerald-400 font-medium">Please send to portal for client signature.</p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              onClick={handleCreateDraft}
              disabled={!clientId || creatingDraft}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
            >
              {creatingDraft ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Create Treatment Plan Draft
            </button>
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/10"
            >
              {copied ? <CheckCheck className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy as Text'}
            </button>
            <button
              onClick={() => onApplySuggestions?.(result)}
              className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-500/20"
            >
              Apply Suggestions to Intake Form
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default TreatmentPlanAssistCard
