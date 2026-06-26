import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ClipboardCheck,
  ArrowLeft,
  CheckCircle2,
  Clock,
  PenLine,
  Paperclip,
  RotateCcw,
  AlertTriangle,
  ChevronDown,
  Loader2,
  RefreshCw,
  User,
  CalendarClock,
  XCircle,
  ShieldAlert,
  FileSearch,
  FileX,
  CircleDot,
  Plus,
  CreditCard,
  Stethoscope,
  Scale,
  Sparkles,
  Activity,
  X,
  Minus,
  EyeOff,
  ArrowRight,
  BadgeCheck,
} from 'lucide-react'
import { apiFetch } from '../api/config'
import FinancialCoordinationPanel from '../components/admissions/FinancialCoordinationPanel'

// ── Constants ────────────────────────────────────────────────────────────────

const FORM_STATUSES = [
  'Not Started',
  'In Progress',
  'Needs Signature',
  'Completed',
  'Expired',
  'Revoked',
  'Missing Attachment',
  'Staff Review Needed',
]

const TIMING_ORDER = ['admission', '72_hours', '7_days']

const TIMING_LABELS = {
  admission: 'Required at Admission',
  '72_hours': 'Within First 72 Hours',
  '7_days': 'Within First 7 Days',
}

const STATUS_CONFIG = {
  'Not Started': {
    icon: CircleDot,
    color: 'text-gray-400',
    bg: 'bg-gray-500/15 border-gray-500/25',
    dot: 'bg-gray-400',
  },
  'In Progress': {
    icon: Loader2,
    color: 'text-blue-300',
    bg: 'bg-blue-500/15 border-blue-500/25',
    dot: 'bg-blue-400',
  },
  'Needs Signature': {
    icon: PenLine,
    color: 'text-purple-300',
    bg: 'bg-purple-500/15 border-purple-500/25',
    dot: 'bg-purple-400',
  },
  Completed: {
    icon: CheckCircle2,
    color: 'text-emerald-300',
    bg: 'bg-emerald-500/15 border-emerald-500/25',
    dot: 'bg-emerald-400',
  },
  Expired: {
    icon: CalendarClock,
    color: 'text-amber-300',
    bg: 'bg-amber-500/15 border-amber-500/25',
    dot: 'bg-amber-400',
  },
  Revoked: {
    icon: XCircle,
    color: 'text-red-300',
    bg: 'bg-red-500/15 border-red-500/25',
    dot: 'bg-red-400',
  },
  'Missing Attachment': {
    icon: FileX,
    color: 'text-orange-300',
    bg: 'bg-orange-500/15 border-orange-500/25',
    dot: 'bg-orange-400',
  },
  'Staff Review Needed': {
    icon: FileSearch,
    color: 'text-sky-300',
    bg: 'bg-sky-500/15 border-sky-500/25',
    dot: 'bg-sky-400',
  },
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function groupForms(forms) {
  const groups = {}
  for (const form of forms) {
    const key = form.timing_group || 'admission'
    if (!groups[key]) groups[key] = []
    groups[key].push(form)
  }
  return groups
}

function calcStats(forms) {
  const total = forms.length
  const required = forms.filter((f) => f.required)
  const completed = forms.filter((f) => f.status === 'Completed')
  const needsSig = forms.filter((f) => f.status === 'Needs Signature')
  const missingRequired = required.filter(
    (f) => f.status === 'Not Started' || f.status === 'Missing Attachment'
  )
  const expiringSoon = forms.filter((f) => {
    if (!f.expires_at) return false
    const diff = (new Date(f.expires_at) - Date.now()) / 86400000
    return diff >= 0 && diff <= 30
  })
  const progress = required.length
    ? Math.round((completed.filter((f) => f.required).length / required.length) * 100)
    : 0
  return { total, completed: completed.length, needsSig: needsSig.length, missingRequired: missingRequired.length, expiringSoon: expiringSoon.length, progress }
}

function formatDate(value) {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// Derive a readiness label for the packet header from the completion stats.
// Purely presentational — does not alter packet/form status.
function packetReadiness(stats) {
  if (stats.missingRequired > 0) {
    return { label: 'Action Needed', tone: 'bg-rose-500/15 border-rose-500/30 text-rose-300' }
  }
  if (stats.needsSig > 0) {
    return { label: 'Awaiting Signatures', tone: 'bg-purple-500/15 border-purple-500/30 text-purple-300' }
  }
  if (stats.progress === 100) {
    return { label: 'Ready for Review', tone: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300' }
  }
  return { label: 'In Progress', tone: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-300' }
}

// Pick the single next form a case manager should open. Required incomplete
// forms come first (in packet order), then optional incomplete forms. Returns
// null when nothing is outstanding. Read-only over the existing forms array.
function nextBestAction(forms) {
  const incomplete = (f) => f.status !== 'Completed' && f.status !== 'Revoked'
  const nextRequired = forms.find((f) => f.required && incomplete(f))
  if (nextRequired) {
    return { form: nextRequired, kind: 'required' }
  }
  const nextOptional = forms.find((f) => !f.required && incomplete(f))
  if (nextOptional) {
    return { form: nextOptional, kind: 'optional' }
  }
  return null
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG['Not Started']
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs border ${cfg.bg} ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      {status}
    </span>
  )
}

// Static (non-animated) leading status glyph for a form card — gives each card
// a clear, scannable completion indicator without changing any status logic.
function StatusGlyph({ status, size = 'md' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG['Not Started']
  const Icon = cfg.icon
  const box = size === 'lg' ? 'w-11 h-11 rounded-xl' : 'w-8 h-8 rounded-lg'
  const glyph = size === 'lg' ? 'h-5 w-5' : 'h-4 w-4'
  return (
    <span className={`flex items-center justify-center border flex-shrink-0 ${box} ${cfg.bg} ${cfg.color}`}>
      <Icon className={glyph} />
    </span>
  )
}

function StatusDropdown({ form, packetId, onUpdate, disabled }) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleSelect = async (newStatus) => {
    if (newStatus === form.status) { setOpen(false); return }
    setSaving(true)
    setOpen(false)
    try {
      await onUpdate(packetId, form.form_key, newStatus)
    } finally {
      setSaving(false)
    }
  }

  if (saving) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs bg-white/10 text-gray-400 border border-white/10">
        <Loader2 className="h-3 w-3 animate-spin" />
        Saving…
      </span>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        className="inline-flex items-center gap-1 focus:outline-none disabled:cursor-not-allowed"
        title="Change status"
      >
        <StatusBadge status={form.status} />
        {!disabled && <ChevronDown className={`h-3 w-3 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`} />}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 w-52 rounded-xl border border-white/15 bg-slate-900/95 backdrop-blur-xl shadow-2xl shadow-purple-900/30 py-1 overflow-hidden">
            {FORM_STATUSES.map((s) => {
              const cfg = STATUS_CONFIG[s] || {}
              return (
                <button
                  key={s}
                  onClick={() => handleSelect(s)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs text-left hover:bg-white/8 transition-colors ${
                    s === form.status ? 'bg-white/8 font-medium' : ''
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot || 'bg-gray-400'}`} />
                  <span className={cfg.color || 'text-gray-300'}>{s}</span>
                  {s === form.status && <CheckCircle2 className="h-3 w-3 text-emerald-400 ml-auto" />}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// Visual treatment for a form card derived from its (unchanged) status. This is
// purely presentational — it never alters status or completion logic.
function cardVariant(form) {
  if (form.status === 'Completed') return 'completed'
  if (form.status === 'Revoked' || form.status === 'Expired') return 'inactive'
  if (form.required && (form.status === 'Not Started' || form.status === 'Missing Attachment')) {
    return 'pending'
  }
  if (form.status === 'Needs Signature') return 'signature'
  return 'default'
}

const CARD_VARIANTS = {
  completed: 'bg-emerald-500/[0.07] border-emerald-500/30 border-l-4 border-l-emerald-400/70',
  pending:   'bg-rose-500/[0.05] border-rose-500/20 border-l-4 border-l-rose-400/60',
  signature: 'bg-purple-500/[0.05] border-purple-500/20 border-l-4 border-l-purple-400/60',
  inactive:  'bg-white/[0.02] border-white/8 border-l-4 border-l-gray-600/60',
  default:   'bg-white/[0.035] border-white/10 border-l-4 border-l-white/15 hover:bg-white/[0.06]',
}

function FormCard({ form, packetId, clientId, onUpdate }) {
  const variant = cardVariant(form)
  const completed = form.status === 'Completed'

  return (
    <div className={`rounded-xl border transition-colors ${CARD_VARIANTS[variant]}`}>
      <div className="flex flex-col sm:flex-row sm:items-start gap-3.5 p-4">
        {/* Leading status glyph */}
        <StatusGlyph status={form.status} size="lg" />

        {/* Title + metadata */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className={`text-base font-semibold leading-tight ${completed ? 'text-emerald-50' : 'text-white'}`}>
              {form.form_name}
            </h4>
            {completed && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 border border-emerald-500/40 text-emerald-200">
                <CheckCircle2 className="h-3.5 w-3.5" />
                {form.completed_at ? `Completed ${formatDate(form.completed_at)}` : 'Completed'}
              </span>
            )}
          </div>

          {/* Required / category — the primary classification line */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-md border ${
              form.required
                ? 'bg-rose-500/15 border-rose-500/30 text-rose-200'
                : 'bg-white/8 border-white/12 text-gray-400'
            }`}>
              {form.required ? 'Required' : 'Optional'}
            </span>
            {form.category && (
              <span className="text-xs px-2 py-0.5 rounded-md border bg-white/5 border-white/10 text-gray-300">
                {form.category}
              </span>
            )}
          </div>

          {/* Secondary metadata — signatures, attachments, review, expiry */}
          {(form.requires_signature ||
            form.allow_attachments || form.attachment_count > 0 ||
            (form.review_status && form.review_status !== 'Not Reviewed') ||
            form.expires_at || form.allow_revocation) && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mt-2 text-xs">
              {form.requires_signature && (
                <span className="inline-flex items-center gap-1 text-purple-300">
                  <PenLine className="h-3 w-3" />
                  {form.signatures_required?.join(', ') || 'Signature'}
                </span>
              )}
              {(form.allow_attachments || form.attachment_count > 0) && (
                <span className="inline-flex items-center gap-1 text-sky-300">
                  <Paperclip className="h-3 w-3" />
                  {form.attachment_count > 0
                    ? `${form.attachment_count} file${form.attachment_count !== 1 ? 's' : ''}`
                    : 'Attachments'}
                </span>
              )}
              {form.review_status && form.review_status !== 'Not Reviewed' && (
                <span className={`inline-flex items-center px-1.5 py-0.5 rounded border ${
                  form.review_status === 'Approved'
                    ? 'bg-emerald-500/15 border-emerald-500/25 text-emerald-300'
                    : 'bg-amber-500/15 border-amber-500/25 text-amber-300'
                }`}>
                  {form.review_status}
                </span>
              )}
              {form.expires_at && (
                <span className="inline-flex items-center gap-1 text-amber-300">
                  <Clock className="h-3 w-3" />
                  Exp {new Date(form.expires_at).toLocaleDateString()}
                </span>
              )}
              {form.allow_revocation && (
                <span className="inline-flex items-center gap-1 text-gray-500">
                  <RotateCcw className="h-3 w-3" />
                  Revocable
                </span>
              )}
            </div>
          )}
        </div>

        {/* Status + action */}
        <div className="flex items-center justify-between sm:flex-col sm:items-end gap-2 flex-shrink-0 sm:pt-0.5">
          <StatusDropdown form={form} packetId={packetId} onUpdate={onUpdate} disabled={false} />
          <Link
            to={`/admissions/${clientId}/forms/${form.form_key}`}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              completed
                ? 'text-emerald-200 border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20'
                : 'text-gray-100 border border-white/15 bg-white/8 hover:bg-white/15 hover:border-white/25'
            }`}
          >
            {completed ? 'Review' : 'Open'}
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  )
}

// Per-stage completion stats — read-only over the (unchanged) forms list.
function sectionStats(forms) {
  const total = forms.length
  const completed = forms.filter((f) => f.status === 'Completed').length
  const requiredCount = forms.filter((f) => f.required).length
  const missingRequired = forms.filter(
    (f) => f.required && (f.status === 'Not Started' || f.status === 'Missing Attachment')
  ).length
  const pct = total ? Math.round((completed / total) * 100) : 0
  return { total, completed, requiredCount, missingRequired, pct, allDone: completed === total }
}

function TimingSection({ timingKey, forms, packetId, clientId, onUpdate }) {
  const label = TIMING_LABELS[timingKey] || timingKey
  const s = sectionStats(forms)

  // Stage tone: complete → emerald, missing required → rose, otherwise active.
  const tone = s.allDone ? 'emerald' : s.missingRequired > 0 ? 'rose' : 'cyan'
  const TONES = {
    emerald: { head: 'bg-emerald-500/10 border-emerald-500/25', icon: 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300', title: 'text-emerald-200', bar: 'bg-emerald-400' },
    rose:    { head: 'bg-rose-500/[0.07] border-rose-500/20', icon: 'bg-rose-500/15 border-rose-500/25 text-rose-300', title: 'text-rose-100', bar: 'bg-gradient-to-r from-orange-400 to-amber-400' },
    cyan:    { head: 'bg-white/[0.04] border-white/10', icon: 'bg-purple-500/15 border-purple-500/25 text-purple-300', title: 'text-purple-200', bar: 'bg-gradient-to-r from-cyan-400 to-blue-500' },
  }
  const t = TONES[tone]

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
      {/* Stage header */}
      <div className={`flex flex-col sm:flex-row sm:items-center gap-3 px-4 sm:px-5 py-3.5 border-b ${t.head}`}>
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          <span className={`flex items-center justify-center w-7 h-7 rounded-lg border flex-shrink-0 ${t.icon}`}>
            {s.allDone ? <CheckCircle2 className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
          </span>
          <div className="min-w-0">
            <h3 className={`text-sm font-bold ${t.title}`}>{label}</h3>
            <p className="text-xs text-gray-500">Clinical assessment stage</p>
          </div>
        </div>
        {/* Stat chips */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/12 border border-emerald-500/20 text-emerald-300">
            <CheckCircle2 className="h-3 w-3" />
            {s.completed}/{s.total} done
          </span>
          {s.requiredCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/8 border border-white/12 text-gray-300">
              {s.requiredCount} required
            </span>
          )}
          {s.missingRequired > 0 && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/25 text-rose-200">
              <AlertTriangle className="h-3 w-3" />
              {s.missingRequired} missing
            </span>
          )}
        </div>
      </div>

      {/* Stage progress bar */}
      <div className="h-1 bg-white/5">
        <div className={`h-full ${t.bar} transition-all duration-700`} style={{ width: `${s.pct}%` }} />
      </div>

      {/* Form cards */}
      <div className="p-3 sm:p-4 space-y-2.5">
        {forms.map((form) => (
          <FormCard key={form.form_key} form={form} packetId={packetId} clientId={clientId} onUpdate={onUpdate} />
        ))}
      </div>
    </div>
  )
}

// ── Operational Summary Panel ─────────────────────────────────────────────────

const PRIORITY_STYLES = {
  critical: { bg: 'bg-red-500/12 border-red-500/25', dot: 'bg-red-500', text: 'text-red-300', badge: 'bg-red-500/20 text-red-200 border-red-500/30' },
  high:     { bg: 'bg-orange-500/10 border-orange-500/20', dot: 'bg-orange-400', text: 'text-orange-300', badge: 'bg-orange-500/20 text-orange-200 border-orange-500/30' },
  medium:   { bg: 'bg-blue-500/8 border-blue-500/15', dot: 'bg-blue-400', text: 'text-blue-300', badge: 'bg-blue-500/15 text-blue-200 border-blue-500/25' },
  low:      { bg: 'bg-white/4 border-white/8', dot: 'bg-gray-500', text: 'text-gray-400', badge: 'bg-white/8 text-gray-400 border-white/12' },
}

function reminderPriority(p) {
  return p === 'critical' ? 'High' : p === 'high' ? 'High' : p === 'medium' ? 'Medium' : 'Low'
}

function SuggestedTask({
  task, caseManagerId, clientId,
  alreadyCreated, onCreated,
  alreadyDismissed, alreadyNotApplicable, onSuppressed,
}) {
  const [state, setState] = useState(alreadyCreated ? 'done' : 'idle') // idle | creating | done | error
  const [suppressing, setSuppressing] = useState(false)
  const ps = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium

  const handleCreate = async () => {
    setState('creating')
    try {
      const res = await apiFetch('/api/reminders/create', {
        method: 'POST',
        body: JSON.stringify({
          client_id: clientId,
          reminder_text: task.title,
          priority: reminderPriority(task.priority),
          case_manager_id: caseManagerId,
          reminder_type: 'Admissions',
          description: task.description,
        }),
      })
      if (!res.ok) throw new Error('Server error')
      const rd = await res.json().catch(() => ({}))
      const reminderId = rd.reminder_id || null
      await apiFetch(`/api/admissions/packets/${clientId}/task-keys`, {
        method: 'POST',
        body: JSON.stringify({
          task_key: task.task_key,
          reminder_id: reminderId,
          case_manager_id: caseManagerId,
        }),
      }).catch(() => {})
      setState('done')
      if (onCreated) onCreated(task.task_key)
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 2500)
    }
  }

  const handleSuppress = async (status) => {
    setSuppressing(true)
    try {
      await apiFetch(`/api/admissions/packets/${clientId}/task-suppressions`, {
        method: 'POST',
        body: JSON.stringify({ task_key: task.task_key, status }),
      })
      if (onSuppressed) onSuppressed(task.task_key, status)
    } catch {
      // non-fatal
    } finally {
      setSuppressing(false)
    }
  }

  if (alreadyDismissed) return null

  return (
    <div className={`flex items-start gap-3 px-3.5 py-3 rounded-xl border ${alreadyNotApplicable ? 'bg-white/3 border-white/6 opacity-60' : ps.bg} transition-colors`}>
      <span className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${alreadyNotApplicable ? 'bg-gray-600' : ps.dot}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className={`text-sm font-medium leading-snug ${alreadyNotApplicable ? 'text-gray-500' : ps.text}`}>
            {task.title}
          </p>
          {alreadyNotApplicable && (
            <span className="text-xs px-1.5 py-0.5 rounded border bg-white/6 border-white/10 text-gray-500">N/A</span>
          )}
        </div>
        {task.description && (
          <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{task.description}</p>
        )}
        {task.due_context && (
          <span className="inline-block text-xs text-gray-600 mt-1">
            <Clock className="inline h-3 w-3 mr-0.5 -mt-0.5" />{task.due_context}
          </span>
        )}
      </div>
      <div className="flex-shrink-0 flex items-center gap-1.5">
        {alreadyNotApplicable ? null : state === 'done' ? (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs bg-emerald-500/15 text-emerald-300 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            {alreadyCreated ? 'In Smart Daily' : 'Added'}
          </span>
        ) : state === 'error' ? (
          <span className="text-xs text-red-400">Failed</span>
        ) : (
          <>
            <button
              onClick={handleCreate}
              disabled={state === 'creating' || suppressing}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-gray-300 border border-white/12 bg-white/5 hover:bg-white/10 hover:text-white disabled:opacity-40 transition-colors"
            >
              {state === 'creating' ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
              Smart Daily
            </button>
            <button
              onClick={() => handleSuppress('not_applicable')}
              disabled={suppressing}
              title="Mark as not applicable"
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-gray-500 border border-white/8 bg-white/4 hover:bg-white/10 hover:text-gray-300 disabled:opacity-40 transition-colors"
            >
              <Minus className="h-3 w-3" />
              N/A
            </button>
            <button
              onClick={() => handleSuppress('dismissed')}
              disabled={suppressing}
              title="Dismiss this suggestion"
              className="inline-flex items-center px-2 py-1 rounded-lg text-xs text-gray-600 border border-white/6 bg-white/3 hover:bg-white/8 hover:text-gray-400 disabled:opacity-40 transition-colors"
            >
              <X className="h-3 w-3" />
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function KeyDataItem({ icon: Icon, label, value, alert }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2.5">
      <Icon className={`h-3.5 w-3.5 flex-shrink-0 mt-0.5 ${alert ? 'text-orange-400' : 'text-gray-500'}`} />
      <div className="min-w-0">
        <span className="text-xs text-gray-500">{label}: </span>
        <span className={`text-xs ${alert ? 'text-orange-300' : 'text-gray-200'}`}>{value}</span>
      </div>
    </div>
  )
}

function OperationalSummaryPanel({ clientId, packetCaseManagerId }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [collapsed, setCollapsed] = useState(false)
  const [createdKeys, setCreatedKeys] = useState(new Set())
  const [suppressedKeys, setSuppressedKeys] = useState(new Set())
  const [naKeys, setNaKeys] = useState(new Set())
  const [dismissedOpen, setDismissedOpen] = useState(false)

  useEffect(() => {
    if (!clientId) return
    setLoading(true)
    apiFetch(`/api/admissions/packets/${clientId}/operational-summary`)
      .then((r) => r.json())
      .then((d) => {
        const s = d.summary || null
        setSummary(s)
        if (s?.created_task_keys?.length) setCreatedKeys(new Set(s.created_task_keys))
        if (s?.suppressed_task_keys?.length) setSuppressedKeys(new Set(s.suppressed_task_keys))
        if (s?.not_applicable_task_keys?.length) setNaKeys(new Set(s.not_applicable_task_keys))
        const hasCritical = (s?.suggested_tasks || []).some((t) => t.priority === 'critical')
        setCollapsed(!hasCritical)
      })
      .catch(() => setSummary(null))
      .finally(() => setLoading(false))
  }, [clientId])

  const handleTaskCreated = (taskKey) => {
    setCreatedKeys((prev) => new Set([...prev, taskKey]))
  }

  const handleSuppressed = (taskKey, status) => {
    if (status === 'dismissed') {
      setSuppressedKeys((prev) => new Set([...prev, taskKey]))
      setNaKeys((prev) => { const n = new Set(prev); n.delete(taskKey); return n })
    } else {
      setNaKeys((prev) => new Set([...prev, taskKey]))
      setSuppressedKeys((prev) => { const n = new Set(prev); n.delete(taskKey); return n })
    }
  }

  if (loading) {
    return (
      <div className="bg-white/3 border border-white/8 rounded-2xl p-4 flex items-center gap-2 text-xs text-gray-600">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Loading operational summary…
      </div>
    )
  }

  if (!summary || !summary.has_packet) return null

  const { medical_flags = [], legal_flags = [], suggested_tasks = [], key_admissions_data: kad = {} } = summary
  const allFlags = [...medical_flags, ...legal_flags]
  const hasCritical = allFlags.some((f) => f.priority === 'critical')

  const activeTasks = suggested_tasks.filter((t) => !suppressedKeys.has(t.task_key))
  const dismissedTasks = suggested_tasks.filter((t) => suppressedKeys.has(t.task_key))
  const activeCount = activeTasks.filter((t) => !naKeys.has(t.task_key)).length

  return (
    <div className={`rounded-2xl border overflow-hidden ${hasCritical ? 'border-red-500/25 bg-red-500/4' : 'border-white/10 bg-white/3'}`}>
      {/* Header */}
      <button
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/4 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Sparkles className={`h-4 w-4 ${hasCritical ? 'text-red-400' : 'text-purple-400'}`} />
          <span className="text-sm font-semibold text-white">Operational Summary</span>
          {hasCritical && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-500/20 border border-red-500/30 text-red-300">
              Action Required
            </span>
          )}
          {activeTasks.length > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-white/8 border border-white/10 text-gray-400">
              {activeCount} task{activeCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
      </button>

      {!collapsed && (
        <div className="px-5 pb-5 space-y-5 border-t border-white/8">

          {/* Flags / Alerts */}
          {allFlags.length > 0 && (
            <div className="space-y-2 pt-4">
              {allFlags.map((flag, i) => {
                const ps = PRIORITY_STYLES[flag.priority] || PRIORITY_STYLES.medium
                return (
                  <div key={i} className={`flex items-start gap-2.5 px-3 py-2.5 rounded-xl border ${ps.bg}`}>
                    <AlertTriangle className={`h-3.5 w-3.5 flex-shrink-0 mt-0.5 ${ps.text}`} />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${ps.text}`}>{flag.label}</p>
                      {flag.details && <p className="text-xs text-gray-500 mt-0.5">{flag.details}</p>}
                    </div>
                    <span className={`text-xs px-1.5 py-0.5 rounded border capitalize flex-shrink-0 ${ps.badge}`}>
                      {flag.priority}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {/* Key extracted data */}
          {(kad.payer_type || kad.asam_loc || kad.roi_receiving_party || kad.payment_arrangement || kad.allergies) && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2.5">Key Intake Data</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 bg-white/3 border border-white/8 rounded-xl p-3.5">
                <KeyDataItem icon={CreditCard} label="Payer" value={[kad.payer_type, kad.plan_name].filter(Boolean).join(' · ') || null} alert={kad.payer_incomplete} />
                <KeyDataItem icon={Activity} label="ASAM LOC" value={kad.asam_loc || null} />
                <KeyDataItem icon={Scale} label="Legal" value={legal_flags.length > 0 ? legal_flags[0].label : null} alert />
                <KeyDataItem icon={CreditCard} label="Payment" value={kad.payment_arrangement || null} alert={kad.payment_arrangement && ['Installment plan', 'To be determined with billing'].includes(kad.payment_arrangement)} />
                <KeyDataItem icon={User} label="ROI" value={kad.roi_receiving_party ? `${kad.roi_receiving_party}${kad.roi_days_until_expiry != null ? ` · ${kad.roi_days_until_expiry}d` : ''}` : null} alert={kad.roi_days_until_expiry != null && kad.roi_days_until_expiry <= 14} />
                <KeyDataItem icon={Stethoscope} label="Allergies" value={kad.allergies || null} />
                {kad.has_medications && <KeyDataItem icon={Stethoscope} label="Medications" value="On file" />}
                {kad.interpreter_needed && <KeyDataItem icon={User} label="Interpreter" value={`Needed · ${kad.primary_language || 'language not specified'}`} alert />}
              </div>
            </div>
          )}

          {/* ASAM narrative if available */}
          {kad.asam_medical_necessity && (
            <div className="bg-white/3 border border-white/8 rounded-xl p-3.5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Medical Necessity (ASAM)</p>
              <p className="text-xs text-gray-300 leading-relaxed line-clamp-3">{kad.asam_medical_necessity}</p>
            </div>
          )}

          {/* Suggested tasks (active + NA) */}
          {activeTasks.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2.5">
                Suggested Tasks ({activeCount})
              </p>
              <div className="space-y-2">
                {activeTasks.map((task) => (
                  <SuggestedTask
                    key={task.task_key}
                    task={task}
                    caseManagerId={packetCaseManagerId}
                    clientId={clientId}
                    alreadyCreated={createdKeys.has(task.task_key)}
                    onCreated={handleTaskCreated}
                    alreadyDismissed={false}
                    alreadyNotApplicable={naKeys.has(task.task_key)}
                    onSuppressed={handleSuppressed}
                  />
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-2.5 px-1">
                Use N/A to mark a task as not relevant, or × to dismiss it.
              </p>
            </div>
          )}

          {activeTasks.length === 0 && allFlags.length === 0 && !kad.payer_type && (
            <div className="pt-4 text-center text-xs text-gray-600">
              Complete intake forms to see operational data here.
            </div>
          )}

          {/* Dismissed tasks (collapsed section) */}
          {dismissedTasks.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setDismissedOpen((v) => !v)}
                className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-400 transition-colors"
              >
                <EyeOff className="h-3 w-3" />
                Dismissed ({dismissedTasks.length})
                <ChevronDown className={`h-3 w-3 transition-transform ${dismissedOpen ? 'rotate-180' : ''}`} />
              </button>
              {dismissedOpen && (
                <div className="space-y-1.5 mt-2 opacity-50">
                  {dismissedTasks.map((task) => (
                    <div key={task.task_key} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/3 border border-white/6">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-600 flex-shrink-0" />
                      <span className="text-xs text-gray-500 line-through">{task.title}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdmissionsPacket() {
  const { client_id } = useParams()
  const navigate = useNavigate()
  const [packet, setPacket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchPacket = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true)
      else setRefreshing(true)
      setError(null)
      try {
        const res = await apiFetch(`/api/admissions/packets/${client_id}`)
        if (res.status === 404) {
          setPacket(null)
          return
        }
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `Server error ${res.status}`)
        }
        const data = await res.json()
        setPacket(data.packet)
      } catch (err) {
        setError(err.message || 'Failed to load admissions packet.')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [client_id]
  )

  useEffect(() => {
    fetchPacket()
  }, [fetchPacket])

  const handleUpdateStatus = async (packetId, formKey, newStatus) => {
    try {
      const res = await apiFetch(
        `/api/admissions/packets/${packetId}/forms/${formKey}/status`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status: newStatus }),
        }
      )
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error ${res.status}`)
      }
      await fetchPacket(true)
    } catch (err) {
      setError(`Status update failed: ${err.message}`)
    }
  }

  // ── Loading / error / not-found states ──────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-gray-400">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
          <span className="text-sm">Loading admissions packet…</span>
        </div>
      </div>
    )
  }

  if (error && !packet) {
    return (
      <div className="min-h-screen p-6 flex items-start justify-center pt-24">
        <div className="max-w-md w-full bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-center">
          <AlertTriangle className="h-10 w-10 text-red-400 mx-auto mb-3" />
          <h2 className="text-white font-semibold mb-2">Failed to load packet</h2>
          <p className="text-sm text-red-300 mb-4">{error}</p>
          <button
            onClick={() => fetchPacket()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 text-white text-sm hover:bg-white/15 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Try again
          </button>
        </div>
      </div>
    )
  }

  if (!packet) {
    return (
      <div className="min-h-screen p-6 flex items-start justify-center pt-24">
        <div className="max-w-md w-full bg-white/5 border border-white/10 rounded-2xl p-8 text-center">
          <ClipboardCheck className="h-10 w-10 text-cyan-400 mx-auto mb-3" />
          <h2 className="text-white font-semibold mb-2">No admissions packet found</h2>
          <p className="text-sm text-gray-400 mb-5">
            No packet has been started for this client yet.
          </p>
          <button
            onClick={() => navigate('/admissions/new')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium hover:from-cyan-400 hover:to-blue-500 transition-all shadow-lg shadow-cyan-500/20"
          >
            <ClipboardCheck className="h-4 w-4" />
            Start Admission Packet
          </button>
        </div>
      </div>
    )
  }

  // ── Packet loaded ────────────────────────────────────────────────────

  const forms = packet.forms || []
  const stats = calcStats(forms)
  const grouped = groupForms(forms)
  const readiness = packetReadiness(stats)
  const nextAction = nextBestAction(forms)

  const progressColor =
    stats.progress === 100
      ? 'from-emerald-500 to-teal-500'
      : stats.progress >= 50
      ? 'from-cyan-500 to-blue-500'
      : 'from-orange-500 to-amber-500'

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Back + refresh */}
        <div className="flex items-center justify-between">
          <Link
            to="/admissions"
            className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Admissions
          </Link>
          <button
            onClick={() => fetchPacket(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Error banner (non-fatal) */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-300">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-200">
              <XCircle className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Client + packet header */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
          <div className="flex flex-col sm:flex-row sm:items-start gap-4">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="w-11 h-11 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
                {(packet.client_name?.[0] || '?').toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-cyan-300/80 mb-0.5">
                  <ClipboardCheck className="h-3 w-3" />
                  Clinical Assessment Packet
                </p>
                <h1 className="text-xl font-bold text-white truncate">{packet.client_name}</h1>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <User className="h-3 w-3" />
                    {packet.client_id}
                  </span>
                  <span className="text-gray-600">·</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${readiness.tone}`}>
                    {readiness.label}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    packet.status === 'Completed'
                      ? 'bg-emerald-500/15 border-emerald-500/25 text-emerald-300'
                      : 'bg-cyan-500/15 border-cyan-500/25 text-cyan-300'
                  }`}>
                    {packet.status}
                  </span>
                  <span className="text-xs text-gray-500">
                    Started {new Date(packet.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-gray-400">Packet Progress</span>
              <span className={`text-sm font-bold ${stats.progress === 100 ? 'text-emerald-400' : 'text-white'}`}>
                {stats.progress}%
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-white/8 overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${progressColor} transition-all duration-700`}
                style={{ width: `${stats.progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              label: 'Total Forms',
              value: stats.total,
              icon: ClipboardCheck,
              color: 'from-blue-500 to-cyan-500',
            },
            {
              label: 'Completed',
              value: stats.completed,
              icon: CheckCircle2,
              color: 'from-emerald-500 to-teal-500',
            },
            {
              label: 'Needs Signature',
              value: stats.needsSig,
              icon: PenLine,
              color: 'from-purple-500 to-indigo-500',
            },
            {
              label: 'Missing Required',
              value: stats.missingRequired,
              icon: AlertTriangle,
              color: stats.missingRequired > 0 ? 'from-rose-500 to-red-500' : 'from-gray-500 to-slate-500',
              alert: stats.missingRequired > 0,
            },
          ].map(({ label, value, icon: Icon, color, alert }) => (
            <div
              key={label}
              className={`rounded-2xl p-4 border ${
                alert
                  ? 'bg-rose-500/8 border-rose-500/20'
                  : 'bg-white/5 border-white/10'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div className={`p-1 rounded-md bg-gradient-to-r ${color}`}>
                  <Icon className="h-3 w-3 text-white" />
                </div>
                <span className="text-xs text-gray-400">{label}</span>
              </div>
              <p className={`text-2xl font-bold ${alert && value > 0 ? 'text-rose-300' : 'text-white'}`}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* Missing required alert */}
        {stats.missingRequired > 0 && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-500/8 border border-rose-500/20">
            <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-rose-300">
                {stats.missingRequired} required form{stats.missingRequired !== 1 ? 's' : ''} not started
              </p>
              <p className="text-xs text-rose-400/70 mt-0.5">
                Open each form below to complete it. Status updates automatically on save.
              </p>
            </div>
          </div>
        )}

        {/* Next best action — guided "what to do next" for the case manager */}
        {nextAction ? (
          <div className={`relative overflow-hidden rounded-2xl border p-5 ${
            nextAction.kind === 'required'
              ? 'bg-gradient-to-br from-cyan-500/15 via-blue-500/10 to-transparent border-cyan-500/30 shadow-lg shadow-cyan-900/20'
              : 'bg-white/[0.04] border-white/12'
          }`}>
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className={`flex items-center justify-center w-12 h-12 rounded-2xl flex-shrink-0 ${
                nextAction.kind === 'required' ? 'bg-cyan-500/25 text-cyan-200 ring-1 ring-cyan-400/30' : 'bg-white/8 text-gray-300'
              }`}>
                <CircleDot className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-bold uppercase tracking-wider ${
                  nextAction.kind === 'required' ? 'text-cyan-300' : 'text-gray-400'
                }`}>
                  Next Best Action
                </p>
                <p className="text-lg font-semibold text-white leading-tight mt-0.5 truncate">
                  {nextAction.form.form_name}
                </p>
                <p className="flex flex-wrap items-center gap-1.5 text-xs text-gray-400 mt-1">
                  <span className={`px-1.5 py-0.5 rounded border ${
                    nextAction.kind === 'required'
                      ? 'bg-rose-500/15 border-rose-500/25 text-rose-200'
                      : 'bg-white/8 border-white/12 text-gray-400'
                  }`}>
                    {nextAction.kind === 'required' ? 'Required' : 'Optional'}
                  </span>
                  <span>{TIMING_LABELS[nextAction.form.timing_group] || 'Assessment'}</span>
                  <span className="text-gray-600">·</span>
                  <span>Currently {nextAction.form.status}</span>
                </p>
              </div>
              <Link
                to={`/admissions/${client_id}/forms/${nextAction.form.form_key}`}
                className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold flex-shrink-0 transition-all ${
                  nextAction.kind === 'required'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/25'
                    : 'bg-white/10 text-gray-100 border border-white/15 hover:bg-white/15'
                }`}
              >
                {nextAction.kind === 'required' ? 'Open next required form' : 'Open form'}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 p-5 rounded-2xl border bg-gradient-to-br from-emerald-500/15 to-transparent border-emerald-500/30 shadow-lg shadow-emerald-900/15">
            <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-emerald-500/25 text-emerald-200 ring-1 ring-emerald-400/30 flex-shrink-0">
              <BadgeCheck className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <p className="text-base font-semibold text-emerald-100">Packet complete — all forms addressed</p>
              <p className="text-xs text-emerald-400/70 mt-0.5">No outstanding forms remain in this assessment packet.</p>
            </div>
          </div>
        )}

        {/* Operational Summary panel */}
        <OperationalSummaryPanel
          clientId={client_id}
          packetCaseManagerId={packet.case_manager_id}
        />

        {/* Financial Coordination panel */}
        <FinancialCoordinationPanel clientId={client_id} />

        {/* Grouped checklist */}
        <div className="flex items-center gap-2 pt-1">
          <ClipboardCheck className="h-4 w-4 text-cyan-400" />
          <h2 className="text-sm font-semibold text-white">Assessment Forms</h2>
          <span className="text-xs text-gray-500">{stats.completed}/{stats.total} complete</span>
        </div>
        <div className="space-y-5">
          {TIMING_ORDER.filter((k) => grouped[k]?.length > 0).map((timingKey) => (
            <TimingSection
              key={timingKey}
              timingKey={timingKey}
              forms={grouped[timingKey]}
              packetId={packet.id}
              clientId={client_id}
              onUpdate={handleUpdateStatus}
            />
          ))}
          {/* Any timing groups not in TIMING_ORDER */}
          {Object.keys(grouped)
            .filter((k) => !TIMING_ORDER.includes(k))
            .map((timingKey) => (
              <TimingSection
                key={timingKey}
                timingKey={timingKey}
                forms={grouped[timingKey]}
                packetId={packet.id}
                clientId={client_id}
                onUpdate={handleUpdateStatus}
              />
            ))}
        </div>

      </div>
    </div>
  )
}
