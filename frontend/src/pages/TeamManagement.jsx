import { useEffect, useState } from 'react'
import { UserPlus, Mail, Copy, RefreshCw, X, Trash2, Loader2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiCall } from '../api/config'

// Only the two roles the backend actually enforces are selectable. Supervisor /
// Viewer are shown as disabled "coming soon" so the UI maps 1:1 to real perms.
const ROLE_OPTIONS = [
  { value: 'org_admin', label: 'Admin' },
  { value: 'member', label: 'Case manager' },
]
const COMING_SOON_ROLES = ['Supervisor', 'Viewer (read-only)']

const roleLabel = (orgRole) => (orgRole === 'org_admin' ? 'Admin' : 'Case manager')

function inviteLink(token) {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/onboarding?invite=${encodeURIComponent(token)}`
}

function TeamManagement() {
  const [staff, setStaff] = useState([])
  const [invites, setInvites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('member')
  const [inviting, setInviting] = useState(false)
  const [busyId, setBusyId] = useState('')
  const [lastInvite, setLastInvite] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [s, i] = await Promise.all([
        apiCall('/api/team/staff'),
        apiCall('/api/team/invites'),
      ])
      setStaff(s.staff || [])
      setInvites(i.invites || [])
    } catch (err) {
      setError(err?.message || 'Failed to load team data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const createInvite = async (e) => {
    e.preventDefault()
    if (!email.trim()) {
      setError('Enter an email address to invite.')
      return
    }
    setInviting(true)
    setError('')
    try {
      // Body carries only the selected role — never org_id/org_role authority.
      const data = await apiCall('/api/team/invites', {
        method: 'POST',
        body: JSON.stringify({ email: email.trim(), role, name: name.trim() || undefined }),
      })
      setLastInvite(data.invite)
      setEmail('')
      setName('')
      toast.success('Invite created')
      await load()
    } catch (err) {
      setError(err?.message || 'Could not create invite.')
    } finally {
      setInviting(false)
    }
  }

  const copyLink = async (token) => {
    try {
      await navigator.clipboard.writeText(inviteLink(token))
      toast.success('Invite link copied')
    } catch {
      toast.error('Copy failed — select the code manually')
    }
  }

  const inviteAction = async (id, action) => {
    setBusyId(id + action)
    try {
      await apiCall(`/api/team/invites/${id}/${action}`, { method: 'POST' })
      toast.success(action === 'cancel' ? 'Invite cancelled' : 'Invite resent')
      await load()
    } catch (err) {
      toast.error(err?.message || `Could not ${action} invite.`)
    } finally {
      setBusyId('')
    }
  }

  const removeStaff = async (uid) => {
    setBusyId(uid + 'remove')
    try {
      await apiCall(`/api/team/staff/${uid}/remove`, { method: 'POST' })
      toast.success('Access removed')
      await load()
    } catch (err) {
      toast.error(err?.message || 'Could not remove staff member.')
    } finally {
      setBusyId('')
    }
  }

  const changeRole = async (uid, newRole) => {
    setBusyId(uid + 'role')
    try {
      await apiCall(`/api/team/staff/${uid}/role`, { method: 'POST', body: JSON.stringify({ role: newRole }) })
      toast.success('Role updated')
      await load()
    } catch (err) {
      toast.error(err?.message || 'Could not update role.')
    } finally {
      setBusyId('')
    }
  }

  const panel = 'rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl'

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center gap-3">
          <Users className="h-7 w-7 text-cyan-300" />
          <div>
            <h1 className="text-3xl font-bold">Team Management</h1>
            <p className="text-gray-300">Invite staff, assign roles, and manage your organization’s team.</p>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        {/* Invite form */}
        <div className={panel}>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><UserPlus className="h-5 w-5" /> Invite a team member</h2>
          <form onSubmit={createInvite} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <div>
              <label className="block text-sm text-gray-300">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com"
                className="mt-1 w-full rounded-lg bg-slate-800 px-4 py-2.5 outline-none focus:ring-2 focus:ring-cyan-500" />
            </div>
            <div>
              <label className="block text-sm text-gray-300">Name (optional)</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name"
                className="mt-1 w-full rounded-lg bg-slate-800 px-4 py-2.5 outline-none focus:ring-2 focus:ring-cyan-500" />
            </div>
            <div>
              <label className="block text-sm text-gray-300">Role</label>
              <select value={role} onChange={(e) => setRole(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-800 px-4 py-2.5 outline-none focus:ring-2 focus:ring-cyan-500">
                {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                {COMING_SOON_ROLES.map((r) => <option key={r} disabled>{r} (coming soon)</option>)}
              </select>
            </div>
            <button type="submit" disabled={inviting}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-500 px-5 py-2.5 font-medium text-slate-950 disabled:opacity-50 sm:col-span-3">
              {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              {inviting ? 'Creating…' : 'Create invite'}
            </button>
          </form>

          {lastInvite ? (
            <div className="mt-4 rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-4 text-sm">
              <p className="font-medium text-cyan-100">Invite created for {lastInvite.email}.</p>
              <p className="mt-1 text-cyan-200">Share this link (email sending is not configured yet):</p>
              <div className="mt-2 flex items-center gap-2">
                <code className="flex-1 truncate rounded bg-black/30 px-3 py-2 font-mono text-xs text-gray-100">{inviteLink(lastInvite.token)}</code>
                <button onClick={() => copyLink(lastInvite.token)} className="inline-flex items-center gap-1 rounded bg-white/10 px-3 py-2 hover:bg-white/20">
                  <Copy className="h-4 w-4" /> Copy
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {/* Pending invites */}
        <div className={panel}>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><Mail className="h-5 w-5" /> Pending invites</h2>
          {loading ? (
            <p className="text-gray-400">Loading…</p>
          ) : invites.length === 0 ? (
            <p className="text-gray-400">No pending invites. Invite a teammate above to get started.</p>
          ) : (
            <div className="space-y-3">
              {invites.map((inv) => (
                <div key={inv.invite_id} className="flex flex-col gap-3 rounded-xl border border-white/10 bg-black/10 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium">{inv.email}</p>
                    <p className="text-sm text-gray-400">
                      {roleLabel(inv.org_role)} · {inv.status} · expires {(inv.expires_at || '').slice(0, 10) || '—'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button onClick={() => copyLink(inv.token)} className="inline-flex items-center gap-1 rounded bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"><Copy className="h-4 w-4" /> Copy link</button>
                    <button disabled={busyId === inv.invite_id + 'resend'} onClick={() => inviteAction(inv.invite_id, 'resend')} className="inline-flex items-center gap-1 rounded bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20 disabled:opacity-50"><RefreshCw className="h-4 w-4" /> Resend</button>
                    <button disabled={busyId === inv.invite_id + 'cancel'} onClick={() => inviteAction(inv.invite_id, 'cancel')} className="inline-flex items-center gap-1 rounded bg-red-500/20 px-3 py-1.5 text-sm text-red-200 hover:bg-red-500/30 disabled:opacity-50"><X className="h-4 w-4" /> Cancel</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active staff */}
        <div className={panel}>
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><Users className="h-5 w-5" /> Team members</h2>
          {loading ? (
            <p className="text-gray-400">Loading…</p>
          ) : staff.length === 0 ? (
            <p className="text-gray-400">No team members invited yet.</p>
          ) : (
            <div className="space-y-3">
              {staff.map((s) => (
                <div key={s.firebase_uid} className="flex flex-col gap-3 rounded-xl border border-white/10 bg-black/10 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium">{s.full_name || s.email}</p>
                    <p className="text-sm text-gray-400">{s.email} · <span className={s.is_active ? 'text-emerald-300' : 'text-amber-300'}>{s.status}</span></p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={s.org_role === 'org_admin' ? 'org_admin' : 'member'}
                      disabled={!s.is_active || busyId === s.firebase_uid + 'role'}
                      onChange={(e) => changeRole(s.firebase_uid, e.target.value)}
                      className="rounded bg-slate-800 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50">
                      {ROLE_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                    <button
                      disabled={!s.is_active || busyId === s.firebase_uid + 'remove'}
                      onClick={() => removeStaff(s.firebase_uid)}
                      className="inline-flex items-center gap-1 rounded bg-red-500/20 px-3 py-1.5 text-sm text-red-200 hover:bg-red-500/30 disabled:opacity-50">
                      <Trash2 className="h-4 w-4" /> {s.is_active ? 'Remove' : 'Removed'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TeamManagement
