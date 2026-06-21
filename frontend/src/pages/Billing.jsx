import { useEffect, useState } from 'react'
import { CreditCard, Users, UserCircle, Sparkles, Info, Check } from 'lucide-react'
import { apiCall } from '../api/config'
import { formatPrice } from '../utils/plans'

const STATUS_STYLES = {
  trialing: 'bg-blue-500/15 text-blue-200 border-blue-400/30',
  active: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/30',
  past_due: 'bg-amber-500/15 text-amber-200 border-amber-400/30',
  cancelled: 'bg-gray-500/15 text-gray-300 border-gray-400/30',
  comped: 'bg-purple-500/15 text-purple-200 border-purple-400/30',
  disabled: 'bg-red-500/15 text-red-200 border-red-400/30',
}

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.cancelled
  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${cls}`}>
      {String(status || '—').replace('_', ' ')}
    </span>
  )
}

function UsageBar({ icon: Icon, label, used, limit, over, hint }) {
  const hasLimit = limit !== null && limit !== undefined
  const pct = hasLimit && limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-5 w-5 text-cyan-300" />
        <span className="font-semibold">{label}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold">{used}</span>
        <span className="text-gray-400">/ {hasLimit ? limit : 'unlimited'}</span>
        {over ? (
          <span className="ml-auto rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs text-amber-200">Over limit</span>
        ) : null}
      </div>
      {hasLimit ? (
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div className={`h-full rounded-full ${over ? 'bg-amber-400' : 'bg-gradient-to-r from-cyan-500 to-blue-600'}`} style={{ width: `${pct}%` }} />
        </div>
      ) : null}
      {hint ? <p className="mt-2 text-xs text-gray-400">{hint}</p> : null}
    </div>
  )
}

function Billing() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const body = await apiCall('/api/billing/status')
        if (active) setData(body)
      } catch (err) {
        if (active) setError(err?.message || 'Failed to load billing.')
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => { active = false }
  }, [])

  const panel = 'rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl'
  const plan = data?.plan || {}
  const usage = data?.usage || {}
  const limit = data?.limit_status || {}
  const trialDate = data?.trial_ends_at ? String(data.trial_ends_at).slice(0, 10) : null

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600">
            <CreditCard className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-3xl font-bold">Billing &amp; Plan</h1>
            <p className="text-gray-300">Your plan, usage, and limits. Billing foundation active — payments not connected yet.</p>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        {loading ? (
          <p className="text-gray-400">Loading billing…</p>
        ) : data ? (
          <>
            {/* Current plan */}
            <div className={panel}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-gray-400">Current plan</p>
                  <h2 className="text-2xl font-bold">{plan.display_name || '—'}</h2>
                  <p className="text-gray-300">{plan.intended_for}</p>
                </div>
                <div className="text-right">
                  <StatusBadge status={data.billing_status} />
                  <p className="mt-2 text-2xl font-bold">{formatPrice(data.estimated_monthly_price)}</p>
                  <p className="text-xs text-gray-400">estimated · {plan.price_label}</p>
                </div>
              </div>
              {trialDate ? (
                <div className="mt-4 flex items-center gap-2 rounded-xl border border-blue-400/20 bg-blue-500/10 px-4 py-2.5 text-sm text-blue-100">
                  <Info className="h-4 w-4" /> Trial ends {trialDate}
                </div>
              ) : null}
            </div>

            {/* Usage */}
            <div className="grid gap-4 sm:grid-cols-3">
              <UsageBar icon={UserCircle} label="Staff users" used={usage.active_users ?? 0} limit={limit.users?.limit ?? null}
                over={limit.users?.over_limit} hint={`${plan.included_users ?? '—'} included${limit.users?.extra_billable ? ' · extra seats billable' : ''}`} />
              <UsageBar icon={Users} label="Active clients" used={usage.active_clients ?? 0} limit={limit.clients?.limit ?? null}
                over={limit.clients?.over_limit} />
              <UsageBar icon={Sparkles} label="AI usage" used={usage.ai_usage_placeholder ?? 0} limit={null}
                hint={`Limit: ${plan.ai_limit_label || '—'} (placeholder)`} />
            </div>

            {/* Actions — all disabled while Stripe is not connected */}
            <div className={panel}>
              <h3 className="mb-1 text-lg font-semibold">Manage subscription</h3>
              <p className="mb-4 text-sm text-gray-400">Stripe billing connection is coming soon. These actions are disabled for now.</p>
              <div className="flex flex-wrap gap-3">
                <button disabled title="Stripe connection coming soon"
                  className="cursor-not-allowed rounded-lg bg-white/10 px-5 py-2.5 font-medium text-gray-300 opacity-60">
                  Start trial
                </button>
                <button disabled title="Stripe connection coming soon"
                  className="cursor-not-allowed rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 font-medium opacity-50">
                  Upgrade plan
                </button>
                <button disabled title="Stripe connection coming soon"
                  className="cursor-not-allowed rounded-lg bg-white/10 px-5 py-2.5 font-medium text-gray-300 opacity-60">
                  Manage billing
                </button>
              </div>
              <p className="mt-3 text-xs text-gray-500">Payments are disabled in this phase — no card is collected and no Stripe checkout is created.</p>
            </div>

            {/* Plan catalog */}
            <div className={panel}>
              <h3 className="mb-4 text-lg font-semibold">Plans</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {(data.plans || []).map((pl) => {
                  const current = pl.plan_code === data.plan_code
                  return (
                    <div key={pl.plan_code} className={`rounded-2xl border p-4 ${current ? 'border-cyan-400/50 bg-cyan-500/10' : 'border-white/10 bg-white/5'}`}>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{pl.display_name}</span>
                        {current ? <span className="flex items-center gap-1 text-xs text-cyan-300"><Check className="h-3.5 w-3.5" /> Current</span> : null}
                      </div>
                      <p className="mt-1 text-lg font-bold">{pl.price_label}</p>
                      <ul className="mt-2 space-y-1 text-sm text-gray-300">
                        <li>{pl.included_users ?? 'Custom'} included {pl.included_users === 1 ? 'user' : 'users'}{pl.extra_user_price ? ` · +$${pl.extra_user_price}/extra` : ''}</li>
                        <li>{pl.max_active_clients ?? 'Unlimited'} active clients</li>
                        <li className="text-gray-400">AI: {pl.ai_limit_label}</li>
                      </ul>
                      {data.recommended_plan === pl.plan_code && !current ? (
                        <p className="mt-2 text-xs text-emerald-300">Recommended for your team size</p>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

export default Billing
