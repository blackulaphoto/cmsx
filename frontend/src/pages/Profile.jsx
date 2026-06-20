import { User, ShieldCheck, Building2, Contact, Mail, ToggleRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const roleLabel = (role) => (role === 'admin' ? 'Admin' : role === 'case_manager' ? 'Case manager' : role || '—')
const orgRoleLabel = (r) => (r === 'org_admin' ? 'Organization admin' : r === 'member' ? 'Member' : r || '—')

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/5 py-3 last:border-0">
      <span className="flex items-center gap-2 text-gray-400">
        {Icon ? <Icon className="h-4 w-4 text-gray-500" /> : null}
        {label}
      </span>
      <span className="max-w-[60%] truncate text-right font-medium text-gray-100">{value}</span>
    </div>
  )
}

function Profile() {
  const { profile, multiTenantEnabled } = useAuth()
  const p = profile || {}

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-2xl space-y-6">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-r from-purple-500 to-pink-500">
            <User className="h-6 w-6" />
          </span>
          <div className="min-w-0">
            <h1 className="text-3xl font-bold">{p.full_name || 'My Profile'}</h1>
            <p className="truncate text-gray-300">{p.email || 'Signed-in user'}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
          <h2 className="mb-2 text-lg font-semibold">Account details</h2>
          <Row icon={Mail} label="Email" value={p.email || '—'} />
          <Row icon={ShieldCheck} label="App role" value={roleLabel(p.role)} />
          <Row icon={ShieldCheck} label="Organization role" value={orgRoleLabel(p.org_role)} />
          <Row icon={Building2} label="Organization" value={p.org_id || '—'} />
          <Row icon={Contact} label="Case manager ID" value={p.case_manager_id || '—'} />
          <Row icon={ToggleRight} label="SaaS mode" value={multiTenantEnabled ? 'ON' : 'OFF'} />
          <Row icon={ShieldCheck} label="Account status" value={p.is_active === false ? 'Disabled' : 'Active'} />
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-gray-400 backdrop-blur-xl">
          Editing your profile is coming later. For now this page is read-only.
        </div>
      </div>
    </div>
  )
}

export default Profile
