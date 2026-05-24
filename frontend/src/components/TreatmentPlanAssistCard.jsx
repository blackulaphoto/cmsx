import { useState } from 'react'
import { ClipboardList, Loader2, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const TreatmentPlanAssistCard = ({
  clientId = '',
  clientName = '',
  clientGoals = '',
  barriers = '',
  needs = [],
  onApplySuggestions
}) => {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const loadSuggestions = async () => {
    try {
      setLoading(true)
      const response = await apiFetch('/api/ai-documentation/treatment-plan-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId || undefined,
          client_name: clientName || undefined,
          context: {
            client_goals: clientGoals,
            barriers,
            needs
          }
        })
      })
      if (!response.ok) {
        throw new Error('Failed to load treatment plan suggestions')
      }
      const data = await response.json()
      setResult(data)
      toast.success('Treatment plan suggestions generated')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load treatment plan suggestions')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-emerald-100">Treatment Plan Assist</p>
          <p className="text-xs text-slate-400">Suggested goals, objectives, interventions, and SMART formatting help.</p>
        </div>
        <ClipboardList className="h-4 w-4 text-emerald-300" />
      </div>

      <button
        onClick={loadSuggestions}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        Generate Treatment Plan Suggestions
      </button>

      {result ? (
        <div className="space-y-4 rounded-xl border border-white/10 bg-slate-950/40 p-4">
          <div>
            <p className="text-sm font-semibold text-white">Suggested Goal</p>
            <p className="mt-1 text-sm text-slate-200">{result.goal}</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Suggested Objective</p>
            <p className="mt-1 text-sm text-slate-200">{result.objective}</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Suggested Interventions</p>
            <ul className="mt-1 space-y-2 text-sm text-slate-200">
              {(result.interventions || []).map((item) => (
                <li key={item}>- {item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">SMART Goal Help</p>
            <ul className="mt-1 space-y-2 text-sm text-slate-200">
              {(result.smart_formatting_help || []).map((item) => (
                <li key={item}>- {item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Progress Summary</p>
            <p className="mt-1 text-sm text-slate-200">{result.progress_summary}</p>
          </div>
          <button
            onClick={() => onApplySuggestions?.(result)}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-white transition hover:bg-white/10"
          >
            Apply To Client Form
          </button>
        </div>
      ) : null}
    </div>
  )
}

export default TreatmentPlanAssistCard
