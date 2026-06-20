import { Link } from 'react-router-dom'
import { LifeBuoy, LayoutDashboard, Users, UserCog, Sparkles, Mail, Bug, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const CHECKLIST = [
  'Review your caseload in Case Management.',
  'Check Smart Daily for today’s priorities.',
  'Use the AI Assistant (bottom-right) to research resources and draft documents.',
  'Admins: invite your team from Team Management.',
]

const AI_TIPS = [
  'Ask “list my current clients” to see your caseload.',
  'Ask “who has court next week?” for upcoming dates.',
  'Ask it to draft a document or research a resource.',
]

function QuickLink({ to, icon: Icon, label }) {
  return (
    <Link to={to} className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 transition-colors hover:border-white/25 hover:bg-white/10">
      <Icon className="h-5 w-5 text-cyan-300" />
      <span className="font-medium">{label}</span>
    </Link>
  )
}

function Support() {
  const { profile } = useAuth()
  const isAdmin = profile?.role === 'admin'

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-r from-emerald-500 to-green-600">
            <LifeBuoy className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-3xl font-bold">Help &amp; Support</h1>
            <p className="text-gray-300">Quick help to get the most out of Ember.</p>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
          <h2 className="mb-4 text-lg font-semibold">How to get started</h2>
          <ul className="space-y-3">
            {CHECKLIST.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-gray-200">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
          <h2 className="mb-4 text-lg font-semibold">Jump to</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <QuickLink to="/" icon={LayoutDashboard} label="Dashboard" />
            <QuickLink to="/case-management" icon={Users} label="Case Management" />
            {isAdmin ? <QuickLink to="/team" icon={UserCog} label="Team Management" /> : null}
            <QuickLink to="/smart-dashboard" icon={Sparkles} label="Smart Daily" />
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold"><Sparkles className="h-5 w-5 text-purple-300" /> AI Assistant tips</h2>
          <ul className="space-y-2 text-sm text-gray-300">
            {AI_TIPS.map((tip) => <li key={tip}>• {tip}</li>)}
          </ul>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <p className="flex items-center gap-2 font-semibold text-gray-200"><Mail className="h-5 w-5 text-gray-300" /> Contact support</p>
            <p className="mt-1 text-sm text-gray-400">A support contact channel is coming later.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <p className="flex items-center gap-2 font-semibold text-gray-200"><Bug className="h-5 w-5 text-gray-300" /> Report an issue</p>
            <p className="mt-1 text-sm text-gray-400">Issue reporting is coming later.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Support
