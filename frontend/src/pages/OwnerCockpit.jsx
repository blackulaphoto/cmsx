import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Building2,
  CreditCard,
  DollarSign,
  Flame,
  Globe,
  Layers,
  LifeBuoy,
  Megaphone,
  Server,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react'
import { apiCall, API_BASE_URL } from '../api/config'

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

function StripeFlag({ label, value }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
      <span className="text-slate-300">{label}</span>
      <span className={value ? 'text-emerald-300' : 'text-amber-200'}>{value ? 'On' : 'Off'}</span>
    </div>
  )
}

function OwnerCockpit() {
  const [overview, setOverview] = useState(null)
  const [orgs, setOrgs] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const [overviewData, orgData, analyticsData] = await Promise.all([
          apiCall('/api/super-admin/overview'),
          apiCall('/api/super-admin/organizations'),
          // Analytics is additive — never let it fail the whole cockpit load.
          apiCall('/api/owner/analytics/summary').catch(() => null),
        ])
        if (!cancelled) {
          setOverview(overviewData)
          setOrgs(orgData.organizations || [])
          setAnalytics(analyticsData)
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
    return { planRows, statusRows, topModules, leastModules, marketingRows }
  }, [analytics])

  const hasUsageData = (analytics?.total_events ?? 0) > 0
  const estimatedMrr = analytics?.estimated_mrr

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
            {analyticsRows.marketingRows.length > 0 ? (
              <>
                <p className="mb-3 text-sm text-slate-400">Tracked visits by source (UTM attribution)</p>
                <CountRows rows={analyticsRows.marketingRows} emptyLabel="No marketing source data yet" />
              </>
            ) : (
              <EmptyHint>Marketing attribution will appear after tracked visits</EmptyHint>
            )}
          </SectionCard>

          <SectionCard icon={LifeBuoy} title="Support" eyebrow="Service" accent="from-emerald-500/30 to-teal-500/20">
            <p className="text-sm text-slate-300">Coming next: support queue</p>
            <p className="mt-3 text-sm text-slate-400">Customer help workflows and escalation status are intentionally left as placeholders until the queue model exists.</p>
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
    </div>
  )
}

export default OwnerCockpit
