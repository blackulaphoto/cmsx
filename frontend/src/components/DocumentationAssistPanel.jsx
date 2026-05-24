import { useState } from 'react'
import { Sparkles, ClipboardCheck, BellRing, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const DocumentationAssistPanel = ({
  module = 'case_management',
  noteKind = 'progress_note',
  clientId = '',
  clientName = '',
  currentText = '',
  context = {},
  onApplyDraft
}) => {
  const [prompt, setPrompt] = useState('')
  const [loadingDraft, setLoadingDraft] = useState(false)
  const [loadingReview, setLoadingReview] = useState(false)
  const [draftResult, setDraftResult] = useState(null)
  const [reviewResult, setReviewResult] = useState(null)
  const [creatingTaskIndex, setCreatingTaskIndex] = useState(null)

  const generateDraft = async () => {
    try {
      setLoadingDraft(true)
      const response = await apiFetch('/api/ai-documentation/note-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module,
          note_kind: noteKind,
          client_id: clientId || undefined,
          client_name: clientName || undefined,
          user_prompt: prompt,
          current_text: currentText,
          context
        })
      })
      if (!response.ok) {
        throw new Error('Failed to generate note draft')
      }
      const data = await response.json()
      setDraftResult(data)
      if (data.compliance_preview) {
        setReviewResult(data.compliance_preview)
      }
      toast.success('Draft generated')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to generate draft')
    } finally {
      setLoadingDraft(false)
    }
  }

  const reviewDraft = async () => {
    try {
      setLoadingReview(true)
      const response = await apiFetch('/api/ai-documentation/compliance-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          note_kind: noteKind,
          content: currentText || draftResult?.draft || '',
          context
        })
      })
      if (!response.ok) {
        throw new Error('Failed to review documentation')
      }
      const data = await response.json()
      setReviewResult(data)
      toast.success('Compliance review complete')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to review documentation')
    } finally {
      setLoadingReview(false)
    }
  }

  const createTask = async (task, index) => {
    if (!clientId) {
      toast.error('A client must be linked before creating a follow-up task')
      return
    }
    try {
      setCreatingTaskIndex(index)
      const response = await apiFetch('/api/ai-documentation/follow-up-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          ...task
        })
      })
      if (!response.ok) {
        throw new Error('Failed to create follow-up task')
      }
      toast.success('Follow-up task created')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to create follow-up task')
    } finally {
      setCreatingTaskIndex(null)
    }
  }

  return (
    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-cyan-100">AI Documentation Assist</p>
          <p className="text-xs text-slate-400">Optional drafting, continuity help, and follow-up suggestions.</p>
        </div>
        <Sparkles className="h-4 w-4 text-cyan-300" />
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        placeholder="What should this note cover? Example: client discussed housing barriers, cravings, and probation follow-up."
        className="w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
      />

      <div className="flex flex-wrap gap-3">
        <button
          onClick={generateDraft}
          disabled={loadingDraft}
          className="inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-60"
        >
          {loadingDraft ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Draft Note
        </button>
        <button
          onClick={reviewDraft}
          disabled={loadingReview || (!currentText && !draftResult?.draft)}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10 disabled:opacity-60"
        >
          {loadingReview ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}
          Compliance Review
        </button>
      </div>

      {draftResult?.draft ? (
        <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-white">Generated Draft</p>
            <span className="text-xs text-slate-400">{draftResult.source === 'openai' ? 'AI drafted' : 'Template drafted'}</span>
          </div>
          <pre className="whitespace-pre-wrap text-sm text-slate-200 font-sans">{draftResult.draft}</pre>
          <button
            onClick={() => onApplyDraft?.(draftResult.draft)}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
          >
            Apply Draft
          </button>
        </div>
      ) : null}

      {reviewResult?.warnings?.length ? (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
          <p className="text-sm font-semibold text-amber-100">Compliance Suggestions</p>
          <ul className="mt-2 space-y-2 text-sm text-amber-50">
            {reviewResult.warnings.map((warning) => (
              <li key={warning}>- {warning}</li>
            ))}
          </ul>
        </div>
      ) : reviewResult ? (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
          Documentation review found no obvious missing sections.
        </div>
      ) : null}

      {draftResult?.suggested_tasks?.length ? (
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 p-4 space-y-3">
          <p className="text-sm font-semibold text-violet-100">Suggested Follow-Up Tasks</p>
          {draftResult.suggested_tasks.map((task, index) => (
            <div key={`${task.title}-${index}`} className="rounded-lg border border-white/10 bg-slate-950/40 p-3">
              <p className="text-sm font-medium text-white">{task.title}</p>
              <p className="mt-1 text-xs text-slate-300">{task.description}</p>
              <p className="mt-1 text-xs text-slate-400">Priority: {task.priority} | Due: {task.due_date || 'TBD'}</p>
              <button
                onClick={() => createTask(task, index)}
                disabled={creatingTaskIndex === index}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white transition hover:bg-white/10 disabled:opacity-60"
              >
                {creatingTaskIndex === index ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <BellRing className="h-3.5 w-3.5" />}
                Create Task
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default DocumentationAssistPanel
