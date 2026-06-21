import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Building2,
  CreditCard,
  Flame,
  Globe,
  LifeBuoy,
  Megaphone,
  Server,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { apiCall, API_BASE_URL } from '../api/config'

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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  const orgSummary = useMemo(() => {
    const active = orgs.filter((org) => org.status !== 'suspended').length
    const suspended = orgs.filter((org) => org.status === 'suspended').length
    return { active, suspended }
  }, [orgs])

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
          <MetricCard icon={Building2} label="Organizations" value={overview?.total_orgs ?? '—'} hint={`${orgSummary.active} active, ${orgSummary.suspended} suspended`} />
          <MetricCard icon={Users} label="Users" value={overview?.total_users ?? '—'} hint={`${overview?.active_users ?? 0} active users in current read model`} />
          <MetricCard icon={ShieldCheck} label="Clients" value={overview?.total_clients ?? '—'} hint="Read-only platform total" />
          <MetricCard icon={Activity} label="SaaS Mode" value={overview?.multi_tenant_enabled ? 'ON' : 'OFF'} hint="Multi-tenant flag status" />
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
            <p className="text-sm text-slate-300">Coming next: campaign tracking</p>
            <p className="mt-3 text-sm text-slate-400">This shell will later hold paid acquisition, funnel reporting, and launch instrumentation.</p>
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
