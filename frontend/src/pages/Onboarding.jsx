import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { Building2, User, Users, ArrowLeft, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { apiCall } from '../api/config'

const ORG_TYPES = [
  { value: 'treatment_center', label: 'Treatment center' },
  { value: 'sober_living', label: 'Sober living' },
  { value: 'case_management_agency', label: 'Case management agency' },
  { value: 'independent_provider', label: 'Independent provider' },
  { value: 'other', label: 'Other' },
]

function Onboarding() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { profile, needsOnboarding, refreshProfile } = useAuth()

  // A team invite link (/onboarding?invite=TOKEN) deep-links into the join view
  // with the code prefilled, so Brandon can test the flow without email sending.
  const invitedToken = searchParams.get('invite') || ''

  const [view, setView] = useState(invitedToken ? 'join' : 'choose') // choose | create | join
  const [busy, setBusy] = useState('') // '', 'individual', 'create', 'join'
  const [error, setError] = useState('')

  const [orgName, setOrgName] = useState('')
  const [orgType, setOrgType] = useState(ORG_TYPES[0].value)
  const [inviteToken, setInviteToken] = useState(invitedToken)

  // Configured users never see onboarding (and this avoids a redirect loop the
  // moment setup completes and needsOnboarding flips to false).
  if (profile && !needsOnboarding) {
    return <Navigate to="/" replace />
  }

  const finish = async () => {
    await refreshProfile()
    toast.success('Workspace ready')
    navigate('/', { replace: true })
  }

  const submit = async (kind, endpoint, body) => {
    setError('')
    setBusy(kind)
    try {
      await apiCall(endpoint, {
        method: 'POST',
        body: body ? JSON.stringify(body) : undefined,
      })
      await finish()
    } catch (err) {
      setError(err?.message || 'Something went wrong. Please try again.')
    } finally {
      setBusy('')
    }
  }

  const chooseIndividual = () => submit('individual', '/api/auth/onboarding/individual')
  const submitCreate = (e) => {
    e.preventDefault()
    if (!orgName.trim()) {
      setError('Please enter an organization name.')
      return
    }
    submit('create', '/api/auth/onboarding/organization', { name: orgName.trim(), org_type: orgType })
  }
  const submitJoin = (e) => {
    e.preventDefault()
    if (!inviteToken.trim()) {
      setError('Please enter your invite code.')
      return
    }
    submit('join', '/api/auth/onboarding/join', { token: inviteToken.trim() })
  }

  const card = 'rounded-2xl border border-white/10 bg-white/5 p-6 text-left transition-all duration-200 hover:border-white/25 hover:bg-white/10 disabled:opacity-50'

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-4 py-12 text-white">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Welcome to Ember</h1>
          <p className="mt-2 text-gray-300">
            Let’s set up your workspace. You can change details later.
          </p>
        </div>

        {error ? (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        {view === 'choose' && (
          <div className="grid gap-4">
            <button type="button" className={card} onClick={chooseIndividual} disabled={Boolean(busy)}>
              <div className="flex items-start gap-4">
                <div className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 p-3">
                  {busy === 'individual' ? <Loader2 className="h-6 w-6 animate-spin" /> : <User className="h-6 w-6" />}
                </div>
                <div>
                  <p className="text-lg font-semibold">Individual workspace</p>
                  <p className="mt-1 text-sm text-gray-400">
                    Just you. We’ll set up a personal workspace and take you straight in.
                  </p>
                </div>
              </div>
            </button>

            <button type="button" className={card} onClick={() => { setError(''); setView('create') }} disabled={Boolean(busy)}>
              <div className="flex items-start gap-4">
                <div className="rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 p-3">
                  <Building2 className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-lg font-semibold">Create an organization</p>
                  <p className="mt-1 text-sm text-gray-400">
                    Set up an org for your team. You’ll be its admin.
                  </p>
                </div>
              </div>
            </button>

            <button type="button" className={card} onClick={() => { setError(''); setView('join') }} disabled={Boolean(busy)}>
              <div className="flex items-start gap-4">
                <div className="rounded-xl bg-gradient-to-r from-emerald-500 to-green-600 p-3">
                  <Users className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-lg font-semibold">Join an organization</p>
                  <p className="mt-1 text-sm text-gray-400">
                    Have an invite code from your team? Enter it to join.
                  </p>
                </div>
              </div>
            </button>
          </div>
        )}

        {view === 'create' && (
          <form onSubmit={submitCreate} className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <BackButton onClick={() => { setError(''); setView('choose') }} />
            <h2 className="text-xl font-semibold">Create an organization</h2>
            <label className="mt-5 block text-sm text-gray-300">Organization name</label>
            <input
              className="mt-2 w-full rounded-lg bg-slate-800 px-4 py-3 outline-none focus:ring-2 focus:ring-cyan-500"
              placeholder="e.g. Pacific Recovery Center"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              maxLength={120}
              autoFocus
            />
            <label className="mt-4 block text-sm text-gray-300">Organization type</label>
            <select
              className="mt-2 w-full rounded-lg bg-slate-800 px-4 py-3 outline-none focus:ring-2 focus:ring-cyan-500"
              value={orgType}
              onChange={(e) => setOrgType(e.target.value)}
            >
              {ORG_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={Boolean(busy)}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 py-3 font-medium text-slate-950 disabled:opacity-50"
            >
              {busy === 'create' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {busy === 'create' ? 'Creating…' : 'Create organization'}
            </button>
          </form>
        )}

        {view === 'join' && (
          <form onSubmit={submitJoin} className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <BackButton onClick={() => { setError(''); setView('choose') }} />
            <h2 className="text-xl font-semibold">Join an organization</h2>
            <p className="mt-2 text-sm text-gray-400">
              Enter the invite code your organization admin shared with you.
            </p>
            <label className="mt-5 block text-sm text-gray-300">Invite code</label>
            <input
              className="mt-2 w-full rounded-lg bg-slate-800 px-4 py-3 font-mono outline-none focus:ring-2 focus:ring-cyan-500"
              placeholder="Paste your invite code"
              value={inviteToken}
              onChange={(e) => setInviteToken(e.target.value)}
              maxLength={200}
              autoFocus
            />
            <button
              type="submit"
              disabled={Boolean(busy)}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-3 font-medium text-slate-950 disabled:opacity-50"
            >
              {busy === 'join' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {busy === 'join' ? 'Joining…' : 'Join organization'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

function BackButton({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-4 inline-flex items-center gap-1 text-sm text-gray-300 hover:text-white"
    >
      <ArrowLeft className="h-4 w-4" /> Back
    </button>
  )
}

export default Onboarding
