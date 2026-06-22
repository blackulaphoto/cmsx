import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LifeBuoy, LayoutDashboard, Users, UserCog, Sparkles, Mail, Bug, CheckCircle2, AlertTriangle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiCall } from '../api/config'

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

const TICKET_CATEGORIES = [
  { value: 'bug', label: 'Bug / something broken' },
  { value: 'account', label: 'Account / login' },
  { value: 'billing', label: 'Billing question' },
  { value: 'feature_request', label: 'Feature request' },
  { value: 'usability', label: 'Usability / confusing' },
  { value: 'other', label: 'Other' },
]

const TICKET_PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

const SUBJECT_MAX = 200
const DESCRIPTION_MAX = 5000

function ReportIssueForm() {
  const [category, setCategory] = useState('bug')
  const [priority, setPriority] = useState('normal')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [state, setState] = useState('idle') // idle | submitting | success | error
  const [message, setMessage] = useState('')

  const submitting = state === 'submitting'

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmedSubject = subject.trim()
    const trimmedDescription = description.trim()
    if (!trimmedSubject || !trimmedDescription) {
      setState('error')
      setMessage('Please add a short subject and a description.')
      return
    }
    setState('submitting')
    setMessage('')
    try {
      await apiCall('/api/support/tickets', {
        method: 'POST',
        body: JSON.stringify({
          category,
          priority,
          subject: trimmedSubject.slice(0, SUBJECT_MAX),
          description: trimmedDescription.slice(0, DESCRIPTION_MAX),
        }),
      })
      setState('success')
      setMessage('Thanks — your ticket was submitted. Our team will follow up.')
      setSubject('')
      setDescription('')
      setPriority('normal')
      setCategory('bug')
    } catch (err) {
      setState('error')
      setMessage(err?.message || 'Something went wrong submitting your ticket. Please try again.')
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-semibold"><Bug className="h-5 w-5 text-gray-300" /> Report an issue</h2>
      <p className="text-sm text-gray-400">Bugs, account or billing questions, feature requests — tell us what you need.</p>

      <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
        <p>
          Please <strong>do not include client names, PHI, case notes, documents, or any protected client details</strong>.
          Describe the issue in general terms only.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-gray-300">Category</span>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              disabled={submitting}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-white"
            >
              {TICKET_CATEGORIES.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-gray-300">Priority</span>
            <select
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
              disabled={submitting}
              className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-white"
            >
              {TICKET_PRIORITIES.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="block text-sm">
          <span className="mb-1 block text-gray-300">Subject</span>
          <input
            type="text"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            disabled={submitting}
            maxLength={SUBJECT_MAX}
            placeholder="Short summary (no client names)"
            className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-white placeholder:text-gray-500"
          />
        </label>

        <label className="block text-sm">
          <span className="mb-1 block text-gray-300">Description</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={submitting}
            maxLength={DESCRIPTION_MAX}
            rows={5}
            placeholder="What happened, what you expected, and steps to reproduce — in general terms only."
            className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-white placeholder:text-gray-500"
          />
        </label>

        {message ? (
          <p
            role="status"
            className={`rounded-xl border px-4 py-3 text-sm ${
              state === 'success'
                ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                : 'border-red-400/30 bg-red-500/10 text-red-100'
            }`}
          >
            {message}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-green-600 px-5 py-2.5 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? 'Submitting…' : 'Submit ticket'}
        </button>
      </form>
    </div>
  )
}

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

        <ReportIssueForm />

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <p className="flex items-center gap-2 font-semibold text-gray-200"><Mail className="h-5 w-5 text-gray-300" /> Contact support</p>
          <p className="mt-1 text-sm text-gray-400">Submitting a ticket above is the fastest way to reach us. A direct email channel is coming later.</p>
        </div>
      </div>
    </div>
  )
}

export default Support
