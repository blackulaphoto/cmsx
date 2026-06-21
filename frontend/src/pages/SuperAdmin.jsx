import { useEffect, useState } from 'react'
import { ShieldAlert, Building2, Users, Activity, Search, X, Ban, RotateCcw, ExternalLink, CreditCard } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiCall, API_BASE_URL } from '../api/config'
import { listPlans, BILLING_STATUSES, formatPrice } from '../utils/plans'

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur-xl">
      <div className="mb-3 flex items-center justify-between">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600">
          <Icon className="h-5 w-5" />
        </span>
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="text-sm text-gray-400">{label}</p>
    </div>
  )
}

function SuperAdmin() {
  const [overview, setOverview] = useState(null)
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState(null)
  const [detailBusy, setDetailBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [users, setUsers] = useState([])
  const [searching, setSearching] = useState(false)
  const [billingDraft, setBillingDraft] = useState({ plan_code: '', billing_status: '' })
  const [billingBusy, setBillingBusy] = useState(false)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [o, list] = await Promise.all([
        apiCall('/api/super-admin/overview'),
        apiCall('/api/super-admin/organizations'),
      ])
      setOverview(o)
      setOrgs(list.organizations || [])
    } catch (err) {
      setError(err?.message || 'Failed to load super-admin data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openDetail = async (orgId) => {
    setDetailBusy(true)
    try {
      const d = await apiCall(`/api/super-admin/organizations/${orgId}`)
      setDetail(d)
      setBillingDraft({
        plan_code: d?.billing?.plan_code || '',
        billing_status: d?.billing?.billing_status || '',
      })
    } catch (err) {
      toast.error(err?.message || 'Failed to load organization.')
    } finally {
      setDetailBusy(false)
    }
  }

  const saveBilling = async (orgId) => {
    setBillingBusy(true)
    try {
      await apiCall(`/api/super-admin/organizations/${orgId}/billing`, {
        method: 'POST',
        body: JSON.stringify({
          plan_code: billingDraft.plan_code || undefined,
          billing_status: billingDraft.billing_status || undefined,
        }),
      })
      toast.success('Billing updated')
      await load()
      await openDetail(orgId)
    } catch (err) {
      toast.error(err?.message || 'Could not update billing.')
    } finally {
      setBillingBusy(false)
    }
  }

  const setStatus = async (orgId, action) => {
    try {
      await apiCall(`/api/super-admin/organizations/${orgId}/${action}`, {
        method: 'POST',
        body: action === 'suspend' ? JSON.stringify({ confirm: false }) : undefined,
      })
      toast.success(action === 'suspend' ? 'Organization suspended' : 'Organization restored')
      await load()
      await openDetail(orgId)
    } catch (err) {
      toast.error(err?.message || `Could not ${action} organization.`)
    }
  }

  const runSearch = async (e) => {
    e.preventDefault()
    setSearching(true)
    try {
      const data = await apiCall(`/api/super-admin/users?q=${encodeURIComponent(query.trim())}`)
      setUsers(data.users || [])
    } catch (err) {
      toast.error(err?.message || 'Search failed.')
    } finally {
      setSearching(false)
    }
  }

  const panel = 'rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl'

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-r from-rose-500 to-red-600">
            <ShieldAlert className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-3xl font-bold">Super Admin</h1>
            <p className="text-gray-300">Platform owner command center. Internal use only.</p>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        {/* Platform status */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard icon={Activity} label={`SaaS mode: ${overview?.multi_tenant_enabled ? 'ON' : 'OFF'}`} value={overview?.multi_tenant_enabled ? 'ON' : 'OFF'} />
          <StatCard icon={Building2} label="Organizations" value={overview?.total_orgs ?? '—'} />
          <StatCard icon={Users} label="Users" value={overview?.total_users ?? '—'} />
          <StatCard icon={Users} label="Clients" value={overview?.total_clients ?? '—'} />
        </div>
        <a href={`${API_BASE_URL || ''}/api/health`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-cyan-300 hover:text-cyan-200">
          Backend health <ExternalLink className="h-3.5 w-3.5" />
        </a>

        {/* Organizations table */}
        <div className={panel}>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><Building2 className="h-5 w-5" /> Organizations</h2>
          {loading ? (
            <p className="text-gray-400">Loading…</p>
          ) : orgs.length === 0 ? (
            <p className="text-gray-400">No organizations yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-gray-400">
                  <tr className="border-b border-white/10">
                    <th className="py-2 pr-3">Name</th>
                    <th className="py-2 pr-3">Type</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Plan</th>
                    <th className="py-2 pr-3">Billing</th>
                    <th className="py-2 pr-3">Users</th>
                    <th className="py-2 pr-3">Clients</th>
                    <th className="py-2 pr-3">Created</th>
                    <th className="py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {orgs.map((o) => (
                    <tr key={o.org_id} className="border-b border-white/5">
                      <td className="py-2 pr-3">
                        <div className="font-medium">{o.name}</div>
                        <div className="font-mono text-xs text-gray-500">{o.org_id}</div>
                      </td>
                      <td className="py-2 pr-3 text-gray-300">{o.org_type || '—'}</td>
                      <td className="py-2 pr-3">
                        <span className={o.status === 'suspended' ? 'text-amber-300' : 'text-emerald-300'}>{o.status}</span>
                      </td>
                      <td className="py-2 pr-3 text-gray-300">
                        {o.plan_code || '—'}
                        {o.limit_status?.over_limit ? <span className="ml-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-200">over</span> : null}
                      </td>
                      <td className="py-2 pr-3 text-gray-300">{o.billing_status || '—'}</td>
                      <td className="py-2 pr-3">{o.user_count}</td>
                      <td className="py-2 pr-3">{o.client_count}</td>
                      <td className="py-2 pr-3 text-gray-400">{(o.created_at || '').slice(0, 10) || '—'}</td>
                      <td className="py-2">
                        <button onClick={() => openDetail(o.org_id)} className="rounded bg-white/10 px-3 py-1.5 text-xs hover:bg-white/20">View</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* User search */}
        <div className={panel}>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><Search className="h-5 w-5" /> User lookup</h2>
          <form onSubmit={runSearch} className="flex gap-2">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by email or name"
              className="flex-1 rounded-lg bg-slate-800 px-4 py-2.5 outline-none focus:ring-2 focus:ring-cyan-500" />
            <button type="submit" disabled={searching} className="rounded-lg bg-cyan-500 px-5 py-2.5 font-medium text-slate-950 disabled:opacity-50">
              {searching ? 'Searching…' : 'Search'}
            </button>
          </form>
          {users.length > 0 ? (
            <div className="mt-4 space-y-2">
              {users.map((u) => (
                <div key={u.email} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-black/10 px-4 py-2.5 text-sm">
                  <div><span className="font-medium">{u.full_name || u.email}</span> <span className="text-gray-400">· {u.email}</span></div>
                  <div className="text-gray-400">{u.org_role} · {u.role} · <span className={u.is_active ? 'text-emerald-300' : 'text-amber-300'}>{u.is_active ? 'active' : 'disabled'}</span></div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {/* Billing — internal model is live; live payments (Stripe) are not connected */}
        <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10"><CreditCard className="h-5 w-5 text-gray-300" /></span>
          <div className="flex-1">
            <p className="font-semibold text-gray-200">Billing</p>
            <p className="text-sm text-gray-400">Plan &amp; billing status per org are shown in the table and editable in each org&apos;s detail drawer.</p>
          </div>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-gray-400">Payments not connected</span>
        </div>
      </div>

      {/* Org detail drawer */}
      {detail ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={() => setDetail(null)}>
          <div className="h-full w-full max-w-md overflow-y-auto bg-slate-950 p-6 text-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-xl font-bold">{detail.organization?.name}</h3>
                <p className="font-mono text-xs text-gray-500">{detail.organization?.org_id}</p>
              </div>
              <button onClick={() => setDetail(null)} className="rounded p-1 hover:bg-white/10"><X className="h-5 w-5" /></button>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-lg font-bold">{detail.staff?.length ?? 0}</p><p className="text-xs text-gray-400">Staff</p></div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-lg font-bold">{detail.pending_invites ?? 0}</p><p className="text-xs text-gray-400">Pending invites</p></div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-3"><p className="text-lg font-bold">{detail.client_count ?? 0}</p><p className="text-xs text-gray-400">Clients</p></div>
            </div>
            <p className="mt-4 text-sm">Status: <span className={detail.organization?.status === 'suspended' ? 'text-amber-300' : 'text-emerald-300'}>{detail.organization?.status}</span></p>

            <div className="mt-4">
              {detail.organization?.status === 'suspended' ? (
                <button disabled={detailBusy} onClick={() => setStatus(detail.organization.org_id, 'restore')} className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2 text-sm text-emerald-200 hover:bg-emerald-500/30">
                  <RotateCcw className="h-4 w-4" /> Restore access
                </button>
              ) : (
                <button disabled={detailBusy} onClick={() => setStatus(detail.organization.org_id, 'suspend')} className="inline-flex items-center gap-2 rounded-lg bg-red-500/20 px-4 py-2 text-sm text-red-200 hover:bg-red-500/30">
                  <Ban className="h-4 w-4" /> Suspend access
                </button>
              )}
            </div>

            {/* Billing — internal model only, no Stripe. Manual override for comped/testing. */}
            <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-cyan-300" />
                <h4 className="font-semibold">Billing</h4>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-gray-400">Plan</p><p className="font-medium">{detail.billing?.plan?.display_name || detail.billing?.plan_code || '—'}</p></div>
                <div><p className="text-gray-400">Status</p><p className="font-medium capitalize">{(detail.billing?.billing_status || '—').replace('_', ' ')}</p></div>
                <div><p className="text-gray-400">Est. price</p><p className="font-medium">{formatPrice(detail.billing?.estimated_monthly_price)}</p></div>
                <div><p className="text-gray-400">Active users</p><p className="font-medium">{detail.billing?.usage?.active_users ?? 0}</p></div>
              </div>
              <p className="mt-2 text-xs text-gray-400">AI usage tracking: Coming later</p>
              {detail.billing?.limit_status?.over_limit ? (
                <p className="mt-2 rounded-lg bg-amber-500/15 px-3 py-1.5 text-xs text-amber-200">Over plan limit (clients or users)</p>
              ) : null}

              <div className="mt-4 grid gap-2">
                <label className="text-xs text-gray-400">Plan
                  <select value={billingDraft.plan_code} onChange={(e) => setBillingDraft((d) => ({ ...d, plan_code: e.target.value }))}
                    className="mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-cyan-500">
                    {listPlans().map((pl) => <option key={pl.plan_code} value={pl.plan_code}>{pl.display_name}</option>)}
                  </select>
                </label>
                <label className="text-xs text-gray-400">Billing status
                  <select value={billingDraft.billing_status} onChange={(e) => setBillingDraft((d) => ({ ...d, billing_status: e.target.value }))}
                    className="mt-1 w-full rounded-lg bg-slate-800 px-3 py-2 text-sm capitalize outline-none focus:ring-2 focus:ring-cyan-500">
                    {BILLING_STATUSES.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                  </select>
                </label>
                <button disabled={billingBusy} onClick={() => saveBilling(detail.organization.org_id)}
                  className="mt-1 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">
                  {billingBusy ? 'Saving…' : 'Save billing (comped/testing)'}
                </button>
              </div>
              <p className="mt-2 text-xs text-gray-500">Manual override only. Stripe is not connected — no payment is created.</p>
            </div>

            <h4 className="mt-6 mb-2 font-semibold">Staff</h4>
            <div className="space-y-2">
              {(detail.staff || []).map((s) => (
                <div key={s.firebase_uid} className="rounded-lg border border-white/10 bg-black/10 px-3 py-2 text-sm">
                  <span className="font-medium">{s.full_name || s.email}</span>
                  <span className="text-gray-400"> · {s.org_role} · {s.is_active ? 'active' : 'disabled'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default SuperAdmin
