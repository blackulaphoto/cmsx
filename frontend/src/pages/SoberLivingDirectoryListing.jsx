import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Archive, CheckCircle2, ClipboardList, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import TrustScoreBadge from '../components/TrustScoreBadge'
import {
  buildListingPayload,
  defaultListingForm,
  mapListingToForm,
  soberLivingDirectoryApi,
} from '../utils/soberLivingDirectory'

const statusOptions = ['pending_review', 'approved', 'needs_reverification', 'use_caution', 'do_not_refer', 'archived']

function SoberLivingDirectoryListing() {
  const { listingId } = useParams()
  const [listing, setListing] = useState(null)
  const [formState, setFormState] = useState(defaultListingForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [taskState, setTaskState] = useState({
    task_type: 'call_to_verify',
    priority: 'medium',
    assigned_to: '',
    due_date: '',
    result_notes: '',
  })
  const [updatingTaskId, setUpdatingTaskId] = useState('')

  const loadListing = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await soberLivingDirectoryApi.getListing(listingId)
      setListing(data.listing)
      setFormState(mapListingToForm(data.listing))
    } catch (err) {
      setListing(null)
      setError(err.message || 'Failed to load listing')
      toast.error(err.message || 'Failed to load listing')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadListing()
  }, [listingId])

  const handleSave = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const data = await soberLivingDirectoryApi.updateListing(listingId, buildListingPayload(formState))
      setListing(data.listing)
      setFormState(mapListingToForm(data.listing))
      toast.success('Listing updated')
    } catch (err) {
      toast.error(err.message || 'Failed to update listing')
    } finally {
      setSaving(false)
    }
  }

  const handleVerify = async () => {
    try {
      const data = await soberLivingDirectoryApi.verifyListing(listingId, {
        verification_method: formState.verification_method || 'manual_review',
        result_notes: 'Verified from listing detail page',
      })
      setListing(data.listing)
      setFormState(mapListingToForm(data.listing))
      toast.success('Listing marked verified')
    } catch (err) {
      toast.error(err.message || 'Failed to verify listing')
    }
  }

  const handleArchive = async () => {
    try {
      const data = await soberLivingDirectoryApi.archiveListing(listingId)
      setListing(data.listing)
      setFormState(mapListingToForm(data.listing))
      toast.success('Listing archived')
    } catch (err) {
      toast.error(err.message || 'Failed to archive listing')
    }
  }

  const handleCreateTask = async (event) => {
    event.preventDefault()
    try {
      const data = await soberLivingDirectoryApi.createTask({
        listing_id: listingId,
        ...taskState,
        status: 'open',
      })
      toast.success(`Verification task created: ${data.task.task_id}`)
      setTaskState({
        task_type: 'call_to_verify',
        priority: 'medium',
        assigned_to: '',
        due_date: '',
        result_notes: '',
      })
      await loadListing()
    } catch (err) {
      toast.error(err.message || 'Failed to create task')
    }
  }

  const handleUpdateTask = async (taskId, updates) => {
    setUpdatingTaskId(taskId)
    try {
      await soberLivingDirectoryApi.updateTask(taskId, updates)
      toast.success('Task updated')
      await loadListing()
    } catch (err) {
      toast.error(err.message || 'Failed to update task')
    } finally {
      setUpdatingTaskId('')
    }
  }

  if (loading) {
    return <PageShell>Loading listing...</PageShell>
  }

  if (!listing) {
    return <PageShell>{error || 'Listing not found.'}</PageShell>
  }

  return (
    <PageShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link to="/sober-living-directory" className="inline-flex items-center gap-2 text-sm text-cyan-200 hover:text-cyan-100">
              <ArrowLeft className="h-4 w-4" />
              Back to Directory
            </Link>
            <h1 className="mt-3 text-3xl font-bold text-white">{listing.name}</h1>
            <p className="mt-1 text-sm text-slate-300">{listing.city}, {listing.state}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <TrustScoreBadge score={listing.trust_score} status={listing.status} />
            <button onClick={handleVerify} className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Mark Verified
            </button>
            <button onClick={handleArchive} className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
              <Archive className="h-4 w-4" />
              Archive
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold text-white">Listing Details</h2>
            <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={handleSave}>
              <Input label="Name" value={formState.name} onChange={(value) => setFormState((prev) => ({ ...prev, name: value }))} />
              <Input label="Operator Name" value={formState.operator_name} onChange={(value) => setFormState((prev) => ({ ...prev, operator_name: value }))} />
              <Input label="Phone" value={formState.phone} onChange={(value) => setFormState((prev) => ({ ...prev, phone: value }))} />
              <Input label="Email" value={formState.email} onChange={(value) => setFormState((prev) => ({ ...prev, email: value }))} />
              <Input label="Website" value={formState.website} onChange={(value) => setFormState((prev) => ({ ...prev, website: value }))} />
              <Input label="Address" value={formState.address} onChange={(value) => setFormState((prev) => ({ ...prev, address: value }))} />
              <Input label="City" value={formState.city} onChange={(value) => setFormState((prev) => ({ ...prev, city: value }))} />
              <Input label="State" value={formState.state} onChange={(value) => setFormState((prev) => ({ ...prev, state: value }))} />
              <Input label="ZIP Code" value={formState.zip_code} onChange={(value) => setFormState((prev) => ({ ...prev, zip_code: value }))} />
              <Input label="Neighborhood" value={formState.neighborhood} onChange={(value) => setFormState((prev) => ({ ...prev, neighborhood: value }))} />
              <Input label="Population Served" value={formState.population_served} onChange={(value) => setFormState((prev) => ({ ...prev, population_served: value }))} />
              <Input label="House Type" value={formState.house_type} onChange={(value) => setFormState((prev) => ({ ...prev, house_type: value }))} />
              <Input label="Certification Status" value={formState.certification_status} onChange={(value) => setFormState((prev) => ({ ...prev, certification_status: value }))} />
              <Input label="Certification Body" value={formState.certification_body} onChange={(value) => setFormState((prev) => ({ ...prev, certification_body: value }))} />
              <Input label="Verification Method" value={formState.verification_method} onChange={(value) => setFormState((prev) => ({ ...prev, verification_method: value }))} />
              <Select label="Status" value={formState.status} onChange={(value) => setFormState((prev) => ({ ...prev, status: value }))} options={statusOptions} />
              <Input label="Rent Min" value={formState.monthly_rent_min} onChange={(value) => setFormState((prev) => ({ ...prev, monthly_rent_min: value }))} type="number" />
              <Input label="Rent Max" value={formState.monthly_rent_max} onChange={(value) => setFormState((prev) => ({ ...prev, monthly_rent_max: value }))} type="number" />
              <Toggle label="Accepts MAT" checked={Boolean(formState.accepts_mat)} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_mat: value }))} />
              <Toggle label="Accepts Probation / Parole" checked={Boolean(formState.accepts_probation_parole)} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_probation_parole: value }))} />
              <Toggle label="Accepts Insurance" checked={Boolean(formState.accepts_insurance)} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_insurance: value }))} />
              <Toggle label="Deposit Required" checked={Boolean(formState.deposit_required)} onChange={(value) => setFormState((prev) => ({ ...prev, deposit_required: value }))} />
              <Toggle label="Pets Allowed" checked={Boolean(formState.pets_allowed)} onChange={(value) => setFormState((prev) => ({ ...prev, pets_allowed: value }))} />
              <TextArea label="Notes" value={formState.notes} onChange={(value) => setFormState((prev) => ({ ...prev, notes: value }))} className="md:col-span-2" />
              <TextArea
                label="Internal Referral Notes"
                value={formState.internal_referral_notes}
                onChange={(value) => setFormState((prev) => ({ ...prev, internal_referral_notes: value }))}
                className="md:col-span-2"
              />
              <div className="md:col-span-2 flex justify-end">
                <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60">
                  <Save className="h-4 w-4" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </section>

          <section className="space-y-6">
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold text-white">Verification Health</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-300">
                <p>Last verified: {listing.last_verified_date ? new Date(listing.last_verified_date).toLocaleString() : 'Not verified'}</p>
                <p>Missing verification fields: {listing.missing_verification_fields?.length ? listing.missing_verification_fields.join(', ') : 'None'}</p>
                <p>Stale record: {listing.is_stale ? 'Yes' : 'No'}</p>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold text-white">Create Verification Task</h2>
              <form className="mt-4 space-y-4" onSubmit={handleCreateTask}>
                <Input label="Task Type" value={taskState.task_type} onChange={(value) => setTaskState((prev) => ({ ...prev, task_type: value }))} />
                <Select label="Priority" value={taskState.priority} onChange={(value) => setTaskState((prev) => ({ ...prev, priority: value }))} options={['low', 'medium', 'high']} />
                <Input label="Assigned To" value={taskState.assigned_to} onChange={(value) => setTaskState((prev) => ({ ...prev, assigned_to: value }))} />
                <Input label="Due Date" type="date" value={taskState.due_date} onChange={(value) => setTaskState((prev) => ({ ...prev, due_date: value }))} />
                <TextArea label="Task Notes" value={taskState.result_notes} onChange={(value) => setTaskState((prev) => ({ ...prev, result_notes: value }))} />
                <button type="submit" className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
                  <ClipboardList className="h-4 w-4" />
                  Create Task
                </button>
              </form>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold text-white">Verification Tasks</h2>
              <div className="mt-4 space-y-3">
                {listing.verification_tasks?.length ? listing.verification_tasks.map((task) => (
                  <div key={task.task_id} className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-white">{task.task_type.replaceAll('_', ' ')}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          Priority: {task.priority} • Assigned: {task.assigned_to || 'Unassigned'}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          Due: {task.due_date || 'None'} • Status: {task.status}
                        </p>
                        {task.result_notes ? <p className="mt-2 text-sm text-slate-300">{task.result_notes}</p> : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={updatingTaskId === task.task_id || task.status === 'completed'}
                          onClick={() => handleUpdateTask(task.task_id, { status: 'completed' })}
                          className="rounded-xl border border-emerald-400/30 bg-emerald-500/15 px-3 py-2 text-xs font-medium text-emerald-100 hover:bg-emerald-500/25 disabled:opacity-50"
                        >
                          Mark Completed
                        </button>
                        <button
                          type="button"
                          disabled={updatingTaskId === task.task_id || task.status === 'skipped'}
                          onClick={() => handleUpdateTask(task.task_id, { status: 'skipped' })}
                          className="rounded-xl border border-amber-400/30 bg-amber-500/15 px-3 py-2 text-xs font-medium text-amber-100 hover:bg-amber-500/25 disabled:opacity-50"
                        >
                          Skip
                        </button>
                        <button
                          type="button"
                          disabled={updatingTaskId === task.task_id || task.status === 'open'}
                          onClick={() => handleUpdateTask(task.task_id, { status: 'open' })}
                          className="rounded-xl border border-white/15 px-3 py-2 text-xs font-medium text-white hover:bg-white/10 disabled:opacity-50"
                        >
                          Reopen
                        </button>
                      </div>
                    </div>
                  </div>
                )) : <p className="text-sm text-slate-400">No verification tasks yet.</p>}
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <h2 className="text-xl font-semibold text-white">Recent Change Log</h2>
              <div className="mt-4 space-y-3">
                {listing.change_log?.length ? listing.change_log.slice(0, 6).map((change) => (
                  <div key={change.change_id} className="rounded-2xl border border-white/10 bg-slate-950/40 p-3 text-sm text-slate-300">
                    <p className="font-medium text-white">{change.change_type.replaceAll('_', ' ')}</p>
                    <p className="mt-1 text-xs text-slate-400">{new Date(change.detected_at).toLocaleString()}</p>
                    {change.new_value ? <p className="mt-2 break-words text-xs text-slate-300">{change.new_value}</p> : null}
                  </div>
                )) : <p className="text-sm text-slate-400">No changes logged yet.</p>}
              </div>
            </div>
          </section>
        </div>
      </div>
    </PageShell>
  )
}

function PageShell({ children }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">{children}</div>
    </div>
  )
}

function Input({ label, value, onChange, type = 'text' }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      />
    </label>
  )
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50">
        {options.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll('_', ' ')}
          </option>
        ))}
      </select>
    </label>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 rounded border-white/20 bg-slate-900" />
    </label>
  )
}

function TextArea({ label, value, onChange, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={4} className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50" />
    </label>
  )
}

export default SoberLivingDirectoryListing
