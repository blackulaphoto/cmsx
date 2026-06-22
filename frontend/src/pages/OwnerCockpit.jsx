import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock,
  CreditCard,
  DollarSign,
  Flame,
  Globe,
  Inbox,
  Layers,
  LifeBuoy,
  Lock,
  Megaphone,
  MousePointerClick,
  Server,
  ShieldCheck,
  Target,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { apiCall, API_BASE_URL } from '../api/config'

const WINDOW_OPTIONS = [
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: 'all', label: 'All time' },
]

const ATTRIBUTION_LABELS = {
  source: 'Source',
  medium: 'Medium',
  campaign: 'Campaign',
}

const UTM_TEST_URL = '?utm_source=test&utm_medium=manual&utm_campaign=hq_smoke'

const MODULE_LABELS = {
  dashboard: 'Dashboard',
  case_management: 'Case Management',
  admissions: 'Admissions',
  documentation: 'Documentation',
  housing: 'Housing',
  sober_living: 'Sober Living',
  benefits: 'Benefits',
  fmla: 'FMLA',
  owner: 'Owner HQ',
  super_admin: 'Super Admin',
}

const moduleLabel = (key) =>
  MODULE_LABELS[key] || String(key || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const formatCurrency = (value) =>
  typeof value === 'number'
    ? value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
    : '—'

const formatNumber = (value) => (typeof value === 'number' ? value.toLocaleString('en-US') : '—')

const eventTypeLabel = (key) =>
  String(key || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

// Best-effort short timestamp; falls back to the raw value if unparseable.
const formatEventTime = (iso) => {
  if (!iso) return ''
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return String(iso)
  return parsed.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function MetricCard({ icon: Icon, label, value, hint }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-5 shadow-lg shadow-black/20">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{label}</p>
          <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
        </div>
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 text-amber-200">
          <Icon className="h-5 w-5" />
        </span>
      </div>
      {hint ? <p className="mt-3 text-sm text-slate-400">{hint}</p> : null}
    </div>
  )
}

function SectionCard({ icon: Icon, title, eyebrow, children, accent = 'from-slate-200/20 to-transparent' }) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 backdrop-blur">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{eyebrow}</p>
          <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
        </div>
        <span className={`flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${accent} text-white`}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      {children}
    </section>
  )
}

function EmptyHint({ children }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] px-4 py-6 text-center text-sm text-slate-400">
      {children}
    </div>
  )
}

function CountRows({ rows, emptyLabel }) {
  if (!rows || rows.length === 0) {
    return <EmptyHint>{emptyLabel}</EmptyHint>
  }
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li
          key={row.key}
          className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm"
        >
          <span className="text-slate-300">{row.label}</span>
          <span className="font-semibold text-white">{row.value}</span>
        </li>
      ))}
    </ul>
  )
}

function DayActivity({ rows }) {
  const max = rows.reduce((acc, row) => Math.max(acc, row.count || 0), 0) || 1
  return (
    <ul className="space-y-2">
      {rows.map((row) => {
        const pct = Math.max(4, Math.round(((row.count || 0) / max) * 100))
        return (
          <li key={row.day} className="flex items-center gap-3 text-sm">
            <span className="w-20 shrink-0 text-xs text-slate-400">{row.day}</span>
            <span className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-400/70 to-violet-400/70"
                style={{ width: `${pct}%` }}
              />
            </span>
            <span className="w-8 shrink-0 text-right font-semibold text-white">{row.count}</span>
          </li>
        )
      })}
    </ul>
  )
}

function PlaceholderRows({ rows }) {
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li
          key={row.label}
          className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm"
        >
          <span className="text-slate-300">{row.label}</span>
          <span className="font-medium text-slate-500">{row.value}</span>
        </li>
      ))}
    </ul>
  )
}

function StripeFlag({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
      <span className="text-slate-300">{label}</span>
      <span className={value ? 'text-emerald-300' : 'text-amber-200'}>{value ? 'On' : 'Off'}</span>
    </div>
  )
}

// ── Support Queue ────────────────────────────────────────────────────────────
const SUPPORT_CATEGORIES = ['bug', 'account', 'billing', 'feature_request', 'usability', 'other']
const SUPPORT_PRIORITIES = ['low', 'normal', 'high', 'urgent']
const SUPPORT_STATUSES = ['open', 'in_progress', 'waiting', 'resolved', 'closed']

const SUPPORT_LABELS = {
  bug: 'Bug',
  account: 'Account',
  billing: 'Billing',
  feature_request: 'Feature request',
  usability: 'Usability',
  other: 'Other',
  low: 'Low',
  normal: 'Normal',
  high: 'High',
  urgent: 'Urgent',
  open: 'Open',
  in_progress: 'In progress',
  waiting: 'Waiting',
  resolved: 'Resolved',
  closed: 'Closed',
}

const supportLabel = (key) =>
  SUPPORT_LABELS[key] || String(key || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

const PRIORITY_BADGE = {
  urgent: 'bg-red-500/15 text-red-200',
  high: 'bg-orange-500/15 text-orange-200',
  normal: 'bg-slate-500/15 text-slate-300',
  low: 'bg-slate-500/10 text-slate-400',
}

const STATUS_BADGE = {
  open: 'bg-amber-500/15 text-amber-200',
  in_progress: 'bg-sky-500/15 text-sky-200',
  waiting: 'bg-violet-500/15 text-violet-200',
  resolved: 'bg-emerald-500/15 text-emerald-200',
  closed: 'bg-slate-500/15 text-slate-400',
}

// Full timestamp for the detail drawer; falls back to the raw value, or an em-dash.
const formatFullTime = (iso) => {
  if (!iso) return '—'
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return String(iso)
  return parsed.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

// ── Activation controls (read-only, env/deployment-gated) ────────────────────
// These surface real posture but are NEVER toggles. Each carries an explicit lock
// label and a read-only "View activation checklist" modal. Nothing here calls
// Stripe / Railway / Vercel or changes any env var or flag.
const LOCK_BADGE_STYLES = {
  'Env-controlled': 'bg-sky-500/15 text-sky-200',
  'Activation locked': 'bg-red-500/15 text-red-200',
  'Requires deployment change': 'bg-amber-500/15 text-amber-200',
  Dormant: 'bg-slate-500/15 text-slate-300',
}

const ACTIVATION_CONTROLS = [
  { key: 'saas', name: 'SaaS mode', lock: 'Env-controlled', state: (o) => (o?.multi_tenant_enabled ? 'Enabled' : 'Disabled') },
  { key: 'stripe', name: 'Stripe mode', lock: 'Dormant', state: (o, s) => s?.mode || 'Unknown' },
  { key: 'billing', name: 'Billing', lock: 'Activation locked', state: (o, s) => (s?.billing_enabled ? 'On' : 'Off') },
  { key: 'checkout', name: 'Checkout', lock: 'Requires deployment change', state: (o, s) => (s?.checkout_enabled ? 'On' : 'Off') },
  { key: 'portal', name: 'Customer Portal', lock: 'Requires deployment change', state: (o, s) => (s?.portal_enabled ? 'On' : 'Off') },
  { key: 'webhooks', name: 'Webhooks', lock: 'Requires deployment change', state: (o, s) => (s?.webhooks_enabled ? 'On' : 'Off') },
]

const ACTIVATION_CHECKLISTS = {
  saas: {
    title: 'SaaS / multi-tenant mode',
    lock: 'Env-controlled',
    summary: 'Multi-tenant mode is controlled entirely by a deployment environment flag.',
    steps: [
      'Confirm tenant isolation has been validated in staging (org wall tests green).',
      'Set MULTI_TENANT_ENABLED=true in the backend deployment environment.',
      'Redeploy the backend so the flag is read at startup.',
      'Verify org scoping end-to-end before inviting external organizations.',
    ],
  },
  stripe: {
    title: 'Stripe mode',
    lock: 'Dormant',
    summary: 'Stripe is connected but intentionally dormant. No SDK calls are made from this shell.',
    steps: [
      'Confirm the plan catalog and price IDs are finalized.',
      'Provision live Stripe keys in the deployment environment (never in the app).',
      'Move billing out of dormant mode only after Checkout, Portal, and webhooks are ready.',
    ],
  },
  billing: {
    title: 'Billing',
    lock: 'Activation locked',
    summary: 'Billing stays off until activation flags are explicitly enabled outside this shell.',
    steps: [
      'Finalize the plan limits and pricing helper values.',
      'Enable the billing activation flag in the deployment environment.',
      'Redeploy and verify plan enforcement runs in warning mode first.',
    ],
  },
  checkout: {
    title: 'Checkout',
    lock: 'Requires deployment change',
    summary: 'Checkout session creation requires live Stripe keys and a deployment change.',
    steps: [
      'Confirm live Stripe keys and price IDs are configured in the environment.',
      'Enable the Checkout activation flag in the deployment environment.',
      'Redeploy the backend and smoke-test a Checkout session in test mode first.',
    ],
  },
  portal: {
    title: 'Customer Portal',
    lock: 'Requires deployment change',
    summary: 'The Stripe customer portal requires configured billing and a deployment change.',
    steps: [
      'Configure the Stripe Billing customer portal settings in the Stripe dashboard.',
      'Enable the Portal activation flag in the deployment environment.',
      'Redeploy and verify the portal link resolves for a test customer.',
    ],
  },
  webhooks: {
    title: 'Webhooks',
    lock: 'Requires deployment change',
    summary: 'Webhook handling requires a signing secret and a deployment change.',
    steps: [
      'Create the webhook endpoint in the Stripe dashboard and copy its signing secret.',
      'Set the webhook signing secret in the deployment environment.',
      'Enable the webhooks activation flag and redeploy, then send a test event.',
    ],
  },
}

function SupportTicketRow({ ticket, onPatch, onOpen }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)

  const patch = async (body) => {
    setBusy(true)
    setSaved(false)
    try {
      await onPatch(ticket.id, body)
      setSaved(true)
    } finally {
      setBusy(false)
    }
  }

  const submitNote = async (event) => {
    event.preventDefault()
    const trimmed = note.trim()
    if (!trimmed) return
    await patch({ internal_notes: trimmed })
    setNote('')
  }

  return (
    <li className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={() => onOpen?.(ticket.id)}
            aria-label={`Open ticket ${ticket.id}: ${ticket.subject}`}
            className="group flex w-full items-center gap-1.5 text-left font-medium text-white transition hover:text-amber-200"
          >
            <span className="truncate">{ticket.subject}</span>
            <ChevronRight className="h-4 w-4 shrink-0 text-slate-500 transition group-hover:text-amber-200" />
          </button>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span className="rounded-full bg-white/[0.06] px-2 py-0.5">{supportLabel(ticket.category)}</span>
            <span className={`rounded-full px-2 py-0.5 ${PRIORITY_BADGE[ticket.priority] || PRIORITY_BADGE.normal}`}>
              {supportLabel(ticket.priority)}
            </span>
            <span className="text-slate-500">#{ticket.id}</span>
            {ticket.assigned_to ? <span className="text-slate-500">→ {ticket.assigned_to}</span> : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor={`status-${ticket.id}`}>Status</label>
          <select
            id={`status-${ticket.id}`}
            aria-label={`Status for ticket ${ticket.id}`}
            value={ticket.status}
            disabled={busy}
            onChange={(event) => patch({ status: event.target.value })}
            className="rounded-xl border border-white/10 bg-black/30 px-2 py-1 text-xs text-white"
          >
            {SUPPORT_STATUSES.map((value) => (
              <option key={value} value={value}>{supportLabel(value)}</option>
            ))}
          </select>
          <label className="sr-only" htmlFor={`priority-${ticket.id}`}>Priority</label>
          <select
            id={`priority-${ticket.id}`}
            aria-label={`Priority for ticket ${ticket.id}`}
            value={ticket.priority}
            disabled={busy}
            onChange={(event) => patch({ priority: event.target.value })}
            className="rounded-xl border border-white/10 bg-black/30 px-2 py-1 text-xs text-white"
          >
            {SUPPORT_PRIORITIES.map((value) => (
              <option key={value} value={value}>{supportLabel(value)}</option>
            ))}
          </select>
        </div>
      </div>
      <form onSubmit={submitNote} className="mt-3 flex items-center gap-2">
        <input
          type="text"
          value={note}
          disabled={busy}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Add internal note (owner-only)"
          aria-label={`Internal note for ticket ${ticket.id}`}
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-1.5 text-xs text-white placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={busy || !note.trim()}
          className="shrink-0 rounded-xl border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-white transition hover:bg-white/[0.1] disabled:opacity-40"
        >
          Save note
        </button>
        {saved ? <span className="shrink-0 text-xs text-emerald-300">Saved</span> : null}
      </form>
    </li>
  )
}

function SupportQueue({ summary, onPatch, onOpen }) {
  const tickets = summary?.recent_tickets || []
  const total = summary?.total_tickets ?? 0
  const open = summary?.open_tickets ?? 0
  const highPriority = summary?.high_priority_tickets ?? 0

  const statusRows = SUPPORT_STATUSES
    .map((key) => ({ key, label: supportLabel(key), value: summary?.by_status?.[key] ?? 0 }))
    .filter((row) => row.value > 0)
  const categoryRows = SUPPORT_CATEGORIES
    .map((key) => ({ key, label: supportLabel(key), value: summary?.by_category?.[key] ?? 0 }))
    .filter((row) => row.value > 0)

  const hasTickets = total > 0

  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 backdrop-blur">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Service</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Support Queue</h2>
        </div>
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/30 to-teal-500/20 text-white">
          <LifeBuoy className="h-5 w-5" />
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500"><Inbox className="h-4 w-4" /> Total</p>
          <p className="mt-2 text-2xl font-semibold text-white">{formatNumber(total)}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500"><LifeBuoy className="h-4 w-4" /> Open</p>
          <p className="mt-2 text-2xl font-semibold text-white">{formatNumber(open)}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500"><AlertTriangle className="h-4 w-4" /> High / urgent</p>
          <p className="mt-2 text-2xl font-semibold text-white">{formatNumber(highPriority)}</p>
        </div>
      </div>

      {hasTickets ? (
        <div className="mt-5 grid gap-6 lg:grid-cols-[1fr,1.4fr]">
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">By status</p>
              <CountRows rows={statusRows} emptyLabel="No status data yet" />
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">By category</p>
              <CountRows rows={categoryRows} emptyLabel="No category data yet" />
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">Recent tickets</p>
            <ul className="space-y-2">
              {tickets.map((ticket) => (
                <SupportTicketRow key={ticket.id} ticket={ticket} onPatch={onPatch} onOpen={onOpen} />
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="mt-5">
          <EmptyHint>No support tickets yet</EmptyHint>
        </div>
      )}

      <p className="mt-4 text-xs text-slate-500">
        Tickets are issue reports only — they never store client names, notes, documents, or message content.
        Internal notes and assignments are owner-only and never visible to customers.
      </p>
    </section>
  )
}

// ── Inline toast (owner action feedback) ─────────────────────────────────────
function Toast({ toast }) {
  if (!toast) return null
  const success = toast.type === 'success'
  const Icon = success ? CheckCircle2 : AlertTriangle
  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-[70] flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm shadow-xl shadow-black/30 ${
        success
          ? 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100'
          : 'border-red-400/30 bg-red-500/15 text-red-100'
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span>{toast.message}</span>
    </div>
  )
}

// ── Ticket detail drawer (owner-only) ────────────────────────────────────────
// The ONLY place full description + internal notes are shown. Fetches the single
// ticket on open, exposes status / priority / internal-note controls, and reports
// loading / success / error explicitly. PHI warning stays visible throughout.
function DetailField({ label, children }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <div className="mt-1 text-sm text-white">{children}</div>
    </div>
  )
}

function TicketDetailDrawer({ ticketId, onClose, onPatch }) {
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [priority, setPriority] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null) // { type, message }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setFeedback(null)
    apiCall(`/api/owner/support/tickets/${ticketId}`)
      .then((data) => {
        if (cancelled) return
        const t = data?.ticket || data
        setTicket(t)
        setStatus(t?.status || '')
        setPriority(t?.priority || '')
        setNote('')
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Failed to load ticket detail.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [ticketId])

  // Close on Escape for keyboard users.
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const save = async () => {
    if (!ticket) return
    const body = {}
    if (status && status !== ticket.status) body.status = status
    if (priority && priority !== ticket.priority) body.priority = priority
    const trimmedNote = note.trim()
    if (trimmedNote) body.internal_notes = trimmedNote
    if (Object.keys(body).length === 0) {
      setFeedback({ type: 'error', message: 'No changes to save.' })
      return
    }
    setSaving(true)
    setFeedback(null)
    try {
      const res = await onPatch(ticket.id, body)
      const updated = res?.ticket
      if (updated) {
        setTicket(updated)
        setStatus(updated.status)
        setPriority(updated.priority)
      }
      setNote('')
      setFeedback({ type: 'success', message: 'Changes saved.' })
    } catch (err) {
      setFeedback({ type: 'error', message: err?.message || 'Save failed. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <button
        type="button"
        aria-label="Close ticket detail"
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="ticket-detail-title"
        className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-white/10 bg-slate-950 shadow-2xl shadow-black/50"
      >
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Support ticket</p>
            <h2 id="ticket-detail-title" className="mt-1 text-lg font-semibold text-white">
              {ticket ? `#${ticket.id}` : `#${ticketId}`} detail
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-xl border border-white/10 bg-white/[0.04] p-1.5 text-slate-300 transition hover:bg-white/[0.1]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-5 px-5 py-5">
          {loading ? (
            <p className="text-sm text-slate-400">Loading ticket…</p>
          ) : error ? (
            <p role="status" className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </p>
          ) : ticket ? (
            <>
              <DetailField label="Subject">
                <span className="font-medium">{ticket.subject}</span>
              </DetailField>

              <div className="grid grid-cols-2 gap-4">
                <DetailField label="Category">{supportLabel(ticket.category)}</DetailField>
                <DetailField label="Priority">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs ${PRIORITY_BADGE[ticket.priority] || PRIORITY_BADGE.normal}`}>
                    {supportLabel(ticket.priority)}
                  </span>
                </DetailField>
                <DetailField label="Status">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[ticket.status] || STATUS_BADGE.open}`}>
                    {supportLabel(ticket.status)}
                  </span>
                </DetailField>
                <DetailField label="Assigned to">{ticket.assigned_to || '—'}</DetailField>
                <DetailField label="Submitted by">{ticket.submitted_by_email || '—'}</DetailField>
                <DetailField label="Org">{ticket.org_id || '—'}</DetailField>
                <DetailField label="Created">{formatFullTime(ticket.created_at)}</DetailField>
                <DetailField label="Updated">{formatFullTime(ticket.updated_at)}</DetailField>
                <DetailField label="Resolved">{formatFullTime(ticket.resolved_at)}</DetailField>
              </div>

              <DetailField label="Description">
                <p className="whitespace-pre-wrap rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200">
                  {ticket.description || '—'}
                </p>
              </DetailField>

              <DetailField label="Internal notes (owner-only)">
                <p className="whitespace-pre-wrap rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200">
                  {ticket.internal_notes || 'No internal notes yet.'}
                </p>
              </DetailField>

              <div className="flex items-start gap-2 rounded-xl border border-amber-400/30 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-100">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>Do not store client names, PHI, notes, documents, or protected content here.</p>
              </div>

              {/* Owner controls */}
              <div className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Owner controls</p>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-sm">
                    <span className="mb-1 block text-slate-300">Status</span>
                    <select
                      aria-label="Detail status"
                      value={status}
                      disabled={saving}
                      onChange={(event) => setStatus(event.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                    >
                      {SUPPORT_STATUSES.map((value) => (
                        <option key={value} value={value}>{supportLabel(value)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm">
                    <span className="mb-1 block text-slate-300">Priority</span>
                    <select
                      aria-label="Detail priority"
                      value={priority}
                      disabled={saving}
                      onChange={(event) => setPriority(event.target.value)}
                      className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                    >
                      {SUPPORT_PRIORITIES.map((value) => (
                        <option key={value} value={value}>{supportLabel(value)}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="block text-sm">
                  <span className="mb-1 block text-slate-300">Add / update internal note</span>
                  <textarea
                    aria-label="Detail internal note"
                    value={note}
                    disabled={saving}
                    rows={3}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Owner-only triage note (no client names or PHI)"
                    className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder:text-slate-500"
                  />
                </label>

                {feedback ? (
                  <p
                    role="status"
                    className={`rounded-xl border px-3 py-2 text-sm ${
                      feedback.type === 'success'
                        ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                        : 'border-red-400/30 bg-red-500/10 text-red-100'
                    }`}
                  >
                    {feedback.message}
                  </p>
                ) : null}

                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : 'Save changes'}
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-400">Ticket not found.</p>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Activation checklist modal (read-only) ───────────────────────────────────
function ActivationChecklistModal({ controlKey, onClose }) {
  const checklist = ACTIVATION_CHECKLISTS[controlKey]

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!checklist) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
      <button
        type="button"
        aria-label="Close activation checklist"
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="activation-checklist-title"
        className="relative w-full max-w-lg overflow-hidden rounded-[28px] border border-white/10 bg-slate-950 shadow-2xl shadow-black/50"
      >
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-6 py-4">
          <div>
            <p className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-slate-500">
              <ClipboardList className="h-4 w-4" /> Activation checklist
            </p>
            <h2 id="activation-checklist-title" className="mt-1 text-lg font-semibold text-white">
              {checklist.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-xl border border-white/10 bg-white/[0.04] p-1.5 text-slate-300 transition hover:bg-white/[0.1]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs ${LOCK_BADGE_STYLES[checklist.lock] || 'bg-slate-500/15 text-slate-300'}`}>
              <Lock className="h-3 w-3" /> {checklist.lock}
            </span>
          </div>
          <p className="text-sm text-slate-300">{checklist.summary}</p>
          <ol className="space-y-2">
            {checklist.steps.map((step, idx) => (
              <li key={idx} className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-slate-200">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/[0.08] text-xs font-semibold text-white">{idx + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <div className="flex items-start gap-2 rounded-xl border border-sky-400/30 bg-sky-500/10 px-4 py-3 text-xs text-sky-100">
            <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>This is a read-only checklist. Nothing is activated, toggled, or changed here — activation happens through deployment environment changes outside this shell.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Activation controls section ──────────────────────────────────────────────
function ActivationControls({ overview, stripe, onViewChecklist }) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 backdrop-blur">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Posture</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Activation Controls</h2>
        </div>
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-400/30 to-slate-200/10 text-white">
          <Lock className="h-5 w-5" />
        </span>
      </div>

      <p className="mb-4 text-sm text-slate-400">
        These are status views, not toggles. SaaS mode is env-controlled; Stripe stays dormant; billing,
        Checkout, Portal, and webhooks each require an explicit deployment change. Nothing here is activated from this shell.
      </p>

      <ul className="space-y-2">
        {ACTIVATION_CONTROLS.map((control) => (
          <li
            key={control.key}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3"
          >
            <div className="min-w-0">
              <p className="font-medium text-white">{control.name}</p>
              <p className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-slate-400">State: <span className="text-slate-200">{control.state(overview, stripe)}</span></span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${LOCK_BADGE_STYLES[control.lock] || 'bg-slate-500/15 text-slate-300'}`}>
                  <Lock className="h-3 w-3" /> {control.lock}
                </span>
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled
                title="Activation locked — change the deployment environment to enable"
                aria-label={`Request activation for ${control.name} (locked)`}
                className="cursor-not-allowed rounded-xl border border-white/10 bg-white/[0.02] px-3 py-1.5 text-xs text-slate-500"
              >
                Request activation
              </button>
              <button
                type="button"
                onClick={() => onViewChecklist(control.key)}
                aria-label={`View activation checklist for ${control.name}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs text-white transition hover:bg-white/[0.1]"
              >
                <ClipboardList className="h-3.5 w-3.5" /> View activation checklist
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function OwnerCockpit() {
  const [overview, setOverview] = useState(null)
  const [orgs, setOrgs] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [support, setSupport] = useState(null)
  const [supportRefresh, setSupportRefresh] = useState(0)
  const [openTicketId, setOpenTicketId] = useState(null)
  const [checklistKey, setChecklistKey] = useState(null)
  const [toast, setToast] = useState(null)
  const [windowSel, setWindowSel] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Transient owner-action toast; auto-dismisses. Identity changes on each push
  // so the timer resets for back-to-back actions.
  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(timer)
  }, [toast])

  const pushToast = (message, type = 'success') => setToast({ id: Date.now(), message, type })

  // Platform overview + org roster: point-in-time, loaded once on mount.
  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [overviewData, orgData] = await Promise.all([
          apiCall('/api/super-admin/overview'),
          apiCall('/api/super-admin/organizations'),
        ])
        if (!cancelled) {
          setOverview(overviewData)
          setOrgs(orgData.organizations || [])
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load owner cockpit data.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  // Analytics summary: refetched whenever the time window changes. Additive —
  // a failure never blocks the rest of the cockpit.
  useEffect(() => {
    let cancelled = false
    apiCall(`/api/owner/analytics/summary?window=${encodeURIComponent(windowSel)}`)
      .then((data) => {
        if (!cancelled) setAnalytics(data)
      })
      .catch(() => {
        if (!cancelled) setAnalytics(null)
      })
    return () => {
      cancelled = true
    }
  }, [windowSel])

  // Support queue summary: refetched after any ticket mutation. Additive — a
  // failure never blocks the rest of the cockpit (renders the empty state).
  useEffect(() => {
    let cancelled = false
    apiCall('/api/owner/support/summary')
      .then((data) => {
        if (!cancelled) setSupport(data)
      })
      .catch(() => {
        if (!cancelled) setSupport(null)
      })
    return () => {
      cancelled = true
    }
  }, [supportRefresh])

  const patchSupportTicket = async (ticketId, patch) => {
    try {
      const res = await apiCall(`/api/owner/support/tickets/${ticketId}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      })
      setSupportRefresh((n) => n + 1)
      pushToast('Ticket updated', 'success')
      return res
    } catch (err) {
      pushToast(err?.message || 'Update failed', 'error')
      throw err
    }
  }

  const orgSummary = useMemo(() => {
    const active = orgs.filter((org) => org.status !== 'suspended').length
    const suspended = orgs.filter((org) => org.status === 'suspended').length
    return { active, suspended }
  }, [orgs])

  const analyticsRows = useMemo(() => {
    const planRows = Object.entries(analytics?.plan_breakdown || {})
      .sort((a, b) => b[1] - a[1])
      .map(([code, count]) => ({ key: code, label: moduleLabel(code), value: count }))
    const statusRows = Object.entries(analytics?.billing_status_breakdown || {})
      .sort((a, b) => b[1] - a[1])
      .map(([status, count]) => ({ key: status, label: moduleLabel(status), value: count }))
    const topModules = (analytics?.top_modules || []).map((m) => ({
      key: m.module,
      label: moduleLabel(m.module),
      value: m.count,
    }))
    const leastModules = (analytics?.least_used_modules || []).map((m) => ({
      key: m.module,
      label: moduleLabel(m.module),
      value: m.count,
    }))
    const marketingRows = Object.entries(analytics?.marketing_source_breakdown || {})
      .sort((a, b) => b[1] - a[1])
      .map(([source, count]) => ({ key: source, label: source, value: count }))
    // Source / medium / campaign breakdowns for the attribution detail.
    const attribution = analytics?.marketing_attribution || {}
    const attributionGroups = ['source', 'medium', 'campaign'].map((dim) => ({
      key: dim,
      label: ATTRIBUTION_LABELS[dim],
      rows: Object.entries(attribution[dim] || {})
        .sort((a, b) => b[1] - a[1])
        .map(([value, count]) => ({ key: `${dim}:${value}`, label: value, value: count })),
    }))
    // Recent activity: counts per day (oldest→newest for a readable left-to-right bar).
    const activityByDay = [...(analytics?.recent_activity || [])]
      .sort((a, b) => String(a.day).localeCompare(String(b.day)))
    const recentEvents = (analytics?.recent_events || []).map((evt, idx) => ({
      key: `${evt.created_at || idx}-${idx}`,
      eventLabel: eventTypeLabel(evt.event_type),
      moduleLabel: evt.module ? moduleLabel(evt.module) : '—',
      time: formatEventTime(evt.created_at),
    }))
    return {
      planRows,
      statusRows,
      topModules,
      leastModules,
      marketingRows,
      attributionGroups,
      activityByDay,
      recentEvents,
    }
  }, [analytics])

  const hasUsageData = (analytics?.total_events ?? 0) > 0
  const hasMarketingData = analyticsRows.marketingRows.length > 0
  const estimatedMrr = analytics?.estimated_mrr
  const totalEvents = analytics?.total_events ?? 0
  const adReadiness = analytics?.ad_readiness

  const stripe = overview?.stripe
  const panel = 'rounded-[28px] border border-white/10 bg-slate-950/70 p-6 shadow-xl shadow-black/20 backdrop-blur'

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(251,146,60,0.16),_transparent_28%),linear-gradient(135deg,_#020617_0%,_#0f172a_45%,_#111827_100%)] px-4 py-8 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="overflow-hidden rounded-[32px] border border-white/10 bg-slate-950/80 shadow-2xl shadow-black/30">
          <div className="grid gap-6 px-6 py-8 lg:grid-cols-[1.6fr,0.9fr] lg:px-8">
            <div className="relative">
              <div className="absolute -left-10 top-0 h-40 w-40 rounded-full bg-orange-500/10 blur-3xl" />
              <div className="absolute left-40 top-12 h-28 w-28 rounded-full bg-emerald-500/10 blur-3xl" />
              <div className="relative">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-500/10 px-3 py-1 text-xs uppercase tracking-[0.28em] text-amber-100">
                  <Flame className="h-3.5 w-3.5" />
                  Internal use only
                </div>
                <h1 className="text-4xl font-semibold tracking-tight text-white sm:text-5xl">Ember HQ</h1>
                <p className="mt-3 text-lg text-slate-300">Owner cockpit for SaaS operations</p>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
                  Separate from customer workspaces. This shell is for company-level visibility across platform analytics,
                  billing readiness, support, system status, and internal operations. Domain-ready later, internal route today.
                </p>
              </div>
            </div>

            <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Control posture</p>
              <div className="mt-4 space-y-3 text-sm text-slate-300">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <span>SaaS mode</span>
                  <span className="font-medium text-white">{overview?.multi_tenant_enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  <span>Stripe mode</span>
                  <span className={stripe?.mode === 'active' ? 'font-medium text-emerald-300' : 'font-medium text-amber-200'}>
                    {stripe?.mode || 'Unknown'}
                  </span>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-slate-400">
                  Billing remains dormant until the activation flags are explicitly enabled. No Checkout, Portal, or webhook work is activated here.
                </div>
              </div>
            </div>
          </div>
        </section>

        {error ? (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        <div className="flex flex-col gap-3 rounded-[24px] border border-white/10 bg-slate-950/60 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/[0.05] text-slate-300">
              <BarChart3 className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-medium text-white">{formatNumber(totalEvents)} tracked events</p>
              <p className="text-xs text-slate-400">Usage, marketing, and activity below reflect the selected window.</p>
            </div>
          </div>
          <div className="inline-flex items-center gap-1 rounded-2xl border border-white/10 bg-black/20 p-1" role="group" aria-label="Time window">
            {WINDOW_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setWindowSel(opt.value)}
                aria-pressed={windowSel === opt.value}
                className={`rounded-xl px-3 py-1.5 text-sm transition ${
                  windowSel === opt.value
                    ? 'bg-amber-500/20 text-amber-100'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard icon={Building2} label="Organizations" value={analytics?.total_orgs ?? overview?.total_orgs ?? '—'} hint={`${analytics?.active_orgs ?? orgSummary.active} active, ${analytics?.suspended_orgs ?? orgSummary.suspended} suspended`} />
          <MetricCard icon={Users} label="Users" value={analytics?.total_users ?? overview?.total_users ?? '—'} hint={`${analytics?.active_users ?? overview?.active_users ?? 0} active users`} />
          <MetricCard icon={ShieldCheck} label="Clients" value={analytics?.total_clients ?? overview?.total_clients ?? '—'} hint="Read-only platform total" />
          <MetricCard icon={DollarSign} label="Estimated MRR" value={formatCurrency(estimatedMrr)} hint="From internal plan fields — not Stripe" />
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <SectionCard icon={Layers} title="Plan Breakdown" eyebrow="Revenue mix" accent="from-amber-500/30 to-orange-500/20">
            <CountRows rows={analyticsRows.planRows} emptyLabel="No plan data yet" />
            <p className="mt-4 text-sm text-slate-400">
              Estimated MRR <span className="font-semibold text-white">{formatCurrency(estimatedMrr)}</span> from internal plan fields only. Stripe is dormant and never queried.
            </p>
          </SectionCard>

          <SectionCard icon={CreditCard} title="Billing Status" eyebrow="Lifecycle" accent="from-emerald-500/30 to-teal-500/20">
            <CountRows rows={analyticsRows.statusRows} emptyLabel="No billing status data yet" />
          </SectionCard>

          <SectionCard icon={TrendingUp} title="Top Used Modules" eyebrow="Product usage" accent="from-cyan-500/30 to-blue-500/20">
            {hasUsageData ? (
              <CountRows rows={analyticsRows.topModules} emptyLabel="No usage data yet" />
            ) : (
              <EmptyHint>No usage data yet</EmptyHint>
            )}
          </SectionCard>

          <SectionCard icon={TrendingDown} title="Least Used Modules" eyebrow="Coverage gaps" accent="from-slate-400/30 to-slate-200/10">
            {hasUsageData ? (
              <CountRows rows={analyticsRows.leastModules} emptyLabel="No usage data yet" />
            ) : (
              <EmptyHint>No usage data yet</EmptyHint>
            )}
          </SectionCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <SectionCard icon={Clock} title="Event Counts by Day" eyebrow="Recent activity" accent="from-indigo-500/30 to-violet-500/20">
            {analyticsRows.activityByDay.length > 0 ? (
              <DayActivity rows={analyticsRows.activityByDay} />
            ) : (
              <EmptyHint>No activity recorded in this window yet</EmptyHint>
            )}
          </SectionCard>

          <SectionCard icon={MousePointerClick} title="Latest Events" eyebrow="Module views" accent="from-cyan-500/30 to-blue-500/20">
            {analyticsRows.recentEvents.length > 0 ? (
              <ul className="space-y-2">
                {analyticsRows.recentEvents.map((evt) => (
                  <li
                    key={evt.key}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm"
                  >
                    <span className="min-w-0">
                      <span className="font-medium text-white">{evt.moduleLabel}</span>
                      <span className="ml-2 text-slate-400">{evt.eventLabel}</span>
                    </span>
                    <span className="shrink-0 text-xs text-slate-500">{evt.time}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyHint>No events recorded in this window yet</EmptyHint>
            )}
            <p className="mt-4 text-xs text-slate-500">
              Activity is safe-by-design: only event type, module, and time are shown — never client names, notes, documents, or message content.
            </p>
          </SectionCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <SectionCard icon={Activity} title="Platform Overview" eyebrow="Operations" accent="from-cyan-500/30 to-blue-500/20">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Platform scope</p>
                <p className="mt-2 text-lg font-semibold text-white">{overview?.total_orgs ?? '—'} organizations</p>
                <p className="mt-1 text-sm text-slate-400">{overview?.total_users ?? '—'} users and {overview?.total_clients ?? '—'} clients tracked</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">HQ route readiness</p>
                <p className="mt-2 text-lg font-semibold text-white">Ready for `/owner` now</p>
                <p className="mt-1 text-sm text-slate-400">Future HQ domain can point at this same cockpit without a separate deployment.</p>
              </div>
            </div>
          </SectionCard>

          <SectionCard icon={Building2} title="Organizations / Customers" eyebrow="Commercial" accent="from-violet-500/30 to-fuchsia-500/20">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Active organizations</p>
                <p className="mt-2 text-2xl font-semibold text-white">{orgSummary.active}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Suspended organizations</p>
                <p className="mt-2 text-2xl font-semibold text-white">{orgSummary.suspended}</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-slate-400">
              Customer operations stay read-only here. Use Super Admin for organization-level review and manual controls.
            </p>
          </SectionCard>

          <SectionCard icon={CreditCard} title="Billing & Stripe" eyebrow="Revenue" accent="from-amber-500/30 to-orange-500/20">
            {stripe ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <span className="text-slate-300">Stripe readiness</span>
                  <span className={stripe.mode === 'active' ? 'rounded-full bg-emerald-500/15 px-2.5 py-1 text-sm text-emerald-200' : 'rounded-full bg-amber-500/15 px-2.5 py-1 text-sm text-amber-200'}>
                    {stripe.mode}
                  </span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <StripeFlag label="Billing enabled" value={stripe.billing_enabled} />
                  <StripeFlag label="Checkout enabled" value={stripe.checkout_enabled} />
                  <StripeFlag label="Portal enabled" value={stripe.portal_enabled} />
                  <StripeFlag label="Webhooks enabled" value={stripe.webhooks_enabled} />
                </div>
                <p className="text-sm text-slate-400">
                  Stripe connected: {stripe.stripe_connected ? 'Yes' : 'No'}. Billing is dormant until the activation flags are turned on outside this shell.
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Stripe readiness is unavailable.</p>
            )}
          </SectionCard>

          <SectionCard icon={Megaphone} title="Marketing & Ads" eyebrow="Growth" accent="from-pink-500/30 to-rose-500/20">
            {hasMarketingData ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-400">Tracked visits by UTM attribution</p>
                {analyticsRows.attributionGroups.map((group) =>
                  group.rows.length > 0 ? (
                    <div key={group.key}>
                      <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">{group.label}</p>
                      <CountRows rows={group.rows} emptyLabel={`No ${group.label.toLowerCase()} data yet`} />
                    </div>
                  ) : null
                )}
              </div>
            ) : (
              <EmptyHint>Marketing attribution will appear after tracked visits</EmptyHint>
            )}
            <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
              <p className="text-xs text-slate-400">
                Test attribution by appending UTM params to any HQ link, e.g.
              </p>
              <code className="mt-1 block break-all text-xs text-amber-200">{UTM_TEST_URL}</code>
            </div>
          </SectionCard>

          <SectionCard icon={Target} title="Landing & Ad Readiness" eyebrow="Acquisition" accent="from-rose-500/30 to-pink-500/20">
            <PlaceholderRows
              rows={[
                { label: 'Landing page visits', value: formatNumber(adReadiness?.landing_page_visits) },
                { label: 'Campaign conversions', value: formatNumber(adReadiness?.campaign_conversions) },
                { label: 'Cost per signup', value: formatCurrency(adReadiness?.cost_per_signup) },
                { label: 'Ad spend', value: formatCurrency(adReadiness?.ad_spend) },
              ]}
            />
            <p className="mt-4 text-sm text-slate-400">
              Placeholders until an ad/landing data source is connected. No numbers are estimated or fabricated — each stays blank until real data exists.
            </p>
          </SectionCard>

          <SectionCard icon={Server} title="Dev / System" eyebrow="Engineering" accent="from-sky-500/30 to-cyan-500/20">
            <div className="space-y-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Backend health</p>
                <a
                  href={`${API_BASE_URL || ''}/api/health`}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-2 text-sm text-cyan-300 hover:text-cyan-200"
                >
                  Open health endpoint
                  <ArrowRight className="h-4 w-4" />
                </a>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Tenant model</p>
                <p className="mt-2 text-sm text-white">{overview?.multi_tenant_enabled ? 'Multi-tenant mode is enabled.' : 'Single-tenant mode remains in place.'}</p>
              </div>
            </div>
          </SectionCard>

          <SectionCard icon={Globe} title="Internal Team" eyebrow="People" accent="from-slate-400/30 to-slate-200/10">
            <p className="text-sm text-slate-300">Coming next: internal team roles</p>
            <p className="mt-3 text-sm text-slate-400">Owner-side staffing, accountability lanes, and internal permissions will land here when the model is ready.</p>
          </SectionCard>
        </section>

        <ActivationControls overview={overview} stripe={stripe} onViewChecklist={setChecklistKey} />

        <SupportQueue summary={support} onPatch={patchSupportTicket} onOpen={setOpenTicketId} />

        <div className={panel}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-white">Need org-level intervention?</p>
              <p className="mt-1 text-sm text-slate-400">Super Admin remains the separate workspace for direct organization review and manual billing/status controls.</p>
            </div>
            <Link
              to="/super-admin"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-white transition hover:bg-white/[0.08]"
            >
              Open Super Admin
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {loading ? <p className="text-sm text-slate-500">Loading owner cockpit data...</p> : null}
      </div>

      {openTicketId != null ? (
        <TicketDetailDrawer
          ticketId={openTicketId}
          onClose={() => setOpenTicketId(null)}
          onPatch={patchSupportTicket}
        />
      ) : null}

      {checklistKey ? (
        <ActivationChecklistModal controlKey={checklistKey} onClose={() => setChecklistKey(null)} />
      ) : null}

      <Toast toast={toast} />
    </div>
  )
}

export default OwnerCockpit
