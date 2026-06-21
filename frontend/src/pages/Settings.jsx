import { Link } from 'react-router-dom'
import { User, Building2, Users, Server, CreditCard, Lock, ChevronRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

function SectionLink({ to, icon: Icon, title, desc }) {
  return (
    <Link to={to} className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-5 transition-colors hover:border-white/25 hover:bg-white/10">
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600">
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-gray-400">{desc}</p>
      </div>
      <ChevronRight className="h-5 w-5 flex-shrink-0 text-gray-500" />
    </Link>
  )
}

function PlaceholderSection({ icon: Icon, title, desc }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5 opacity-70">
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-white/10">
        <Icon className="h-5 w-5 text-gray-300" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-gray-200">{title}</p>
        <p className="text-sm text-gray-400">{desc}</p>
      </div>
      <span className="flex-shrink-0 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-gray-400">Coming later</span>
    </div>
  )
}

function Settings() {
  const { profile, multiTenantEnabled } = useAuth()
  const p = profile || {}
  const isAdmin = p.role === 'admin'

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-gray-300">Manage your account and organization.</p>
        </div>

        <div className="grid gap-3">
          <SectionLink to="/profile" icon={User} title="Account" desc="Your profile, role, and account status." />
          <SectionLink to="/profile" icon={Building2} title="Organization" desc={`Organization: ${p.org_id || '—'}`} />
          {isAdmin ? (
            <SectionLink to="/team" icon={Users} title="Team Management" desc="Invite staff, assign roles, manage your team." />
          ) : null}
          {isAdmin ? (
            <SectionLink to="/supervisor-dashboard" icon={Server} title="SaaS / System Status" desc={`SaaS mode: ${multiTenantEnabled ? 'ON' : 'OFF'} · view the system status card.`} />
          ) : (
            <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-5">
              <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-white/10"><Server className="h-5 w-5 text-gray-300" /></span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">SaaS / System Status</p>
                <p className="text-sm text-gray-400">SaaS mode: {multiTenantEnabled ? 'ON' : 'OFF'}</p>
              </div>
            </div>
          )}
          <SectionLink to="/billing" icon={CreditCard} title="Billing" desc="Plan, usage, and limits. Billing foundation active — payments not connected yet." />
          <PlaceholderSection icon={Lock} title="Security" desc="Password, sessions, and account protection." />
        </div>
      </div>
    </div>
  )
}

export default Settings
