import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PauseCircle, Play, Plus, RefreshCw, TimerReset, Workflow } from 'lucide-react'
import toast from 'react-hot-toast'
import { soberLivingDirectoryApi } from '../utils/soberLivingDirectory'

const defaultSourceForm = {
  source_name: '',
  source_type: 'manual',
  base_url: '',
  trust_level: 'medium',
  supports_api: false,
  supports_scraping: false,
  requires_manual_review: true,
  is_active: true,
}

const defaultJobForm = {
  source_id: '',
  job_name: '',
  job_type: 'manual_test',
  target_city: '',
  target_state: 'CA',
  query: '',
  is_active: true,
}

const allowedSourceTypes = [
  'spreadsheet_import',
  'certification_directory',
  'public_directory',
  'manual',
  'other',
]

const allowedJobTypes = [
  'manual_test',
  'scheduled_source_check',
  'city_search',
  'reverification_check',
  'import_recheck',
]

const allowedScheduleFrequencies = [
  'manual_only',
  'daily',
  'weekly',
  'monthly',
  'custom_hours',
]

const blockedReasonLabels = {
  job_inactive: 'Job is inactive',
  schedule_disabled: 'Schedule is disabled',
  manual_only: 'Manual-only jobs are never due automatically',
  source_inactive: 'Source is inactive',
  source_bypasses_review: 'Source bypasses manual review',
  auto_disabled_after_failures: 'Schedule auto-disabled after too many failures',
  run_locked: 'Run is currently locked',
  max_runs_per_day_reached: 'Maximum scheduled runs reached for today',
  not_due: 'Job is not due yet',
}

const buildScheduleForm = (job = {}) => ({
  schedule_enabled: Boolean(job.schedule_enabled),
  schedule_frequency: job.schedule_frequency || 'manual_only',
  schedule_interval_hours: job.schedule_interval_hours ?? '',
  max_runs_per_day: job.max_runs_per_day ?? 1,
  schedule_timezone: job.schedule_timezone || 'America/Los_Angeles',
  auto_disable_after_failures: job.auto_disable_after_failures ?? 3,
})

const uniqById = (items = [], idKey) => {
  if (!Array.isArray(items)) {
    return []
  }
  const seen = new Set()
  return items.filter((item) => {
    if (!item || typeof item !== 'object') {
      return false
    }
    const id = item?.[idKey]
    if (!id || seen.has(id)) {
      return false
    }
    seen.add(id)
    return true
  })
}

const humanizeToken = (value, fallback = 'Unknown') => {
  if (typeof value !== 'string' || !value.trim()) {
    return fallback
  }
  return value.replaceAll('_', ' ')
}

function SoberLivingDirectoryDiscovery() {
  const [sources, setSources] = useState([])
  const [jobs, setJobs] = useState([])
  const [runs, setRuns] = useState([])
  const [schedulerPreview, setSchedulerPreview] = useState([])
  const [schedulerStatus, setSchedulerStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creatingSource, setCreatingSource] = useState(false)
  const [creatingJob, setCreatingJob] = useState(false)
  const [savingScheduleJobId, setSavingScheduleJobId] = useState('')
  const [sourceForm, setSourceForm] = useState(defaultSourceForm)
  const [jobForm, setJobForm] = useState(defaultJobForm)
  const [scheduleForms, setScheduleForms] = useState({})
  const [runningJobId, setRunningJobId] = useState('')
  const [schedulerAction, setSchedulerAction] = useState('')
  const [runSummaries, setRunSummaries] = useState({})

  const safeSources = Array.isArray(sources) ? sources.filter(Boolean) : []
  const safeJobs = Array.isArray(jobs) ? jobs.filter(Boolean) : []
  const safeRuns = Array.isArray(runs) ? runs.filter(Boolean) : []
  const safeSchedulerPreview = Array.isArray(schedulerPreview) ? schedulerPreview.filter(Boolean) : []

  const sourceNames = useMemo(
    () => Object.fromEntries(safeSources.map((source) => [source.source_id, source.source_name])),
    [safeSources]
  )

  const previewByJobId = useMemo(
    () => Object.fromEntries(safeSchedulerPreview.map((item) => [item.job_id, item])),
    [safeSchedulerPreview]
  )

  const loadDiscoveryData = async () => {
    setLoading(true)
    setError('')
    try {
      const [sourcesResponse, jobsResponse, runsResponse, previewResponse, statusResponse] = await Promise.all([
        soberLivingDirectoryApi.listSources(),
        soberLivingDirectoryApi.listDiscoveryJobs(),
        soberLivingDirectoryApi.listDiscoveryRuns(),
        soberLivingDirectoryApi.listSchedulerPreview(),
        soberLivingDirectoryApi.getSchedulerStatus(),
      ])
      const loadedSources = uniqById(sourcesResponse.sources || [], 'source_id')
      const loadedJobs = uniqById(jobsResponse.jobs || [], 'job_id')
      setSources(loadedSources)
      setJobs(loadedJobs)
      setRuns(uniqById(runsResponse.runs || [], 'run_id'))
      setSchedulerPreview(uniqById(previewResponse.jobs || [], 'job_id'))
      setSchedulerStatus(statusResponse.scheduler || null)
      setScheduleForms((current) => {
        const next = { ...current }
        loadedJobs.forEach((job) => {
          next[job.job_id] = current[job.job_id] || buildScheduleForm(job)
        })
        return next
      })
      setJobForm((current) => ({
        ...current,
        source_id: current.source_id || loadedSources[0]?.source_id || '',
      }))
    } catch (err) {
      setError(err.message || 'Failed to load discovery controls')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDiscoveryData()
  }, [])

  const handleCreateSource = async (event) => {
    event.preventDefault()
    if (!sourceForm.source_name.trim()) {
      toast.error('Source name is required')
      return
    }
    setCreatingSource(true)
    try {
      const response = await soberLivingDirectoryApi.createSource({
        ...sourceForm,
        source_name: sourceForm.source_name.trim(),
        base_url: sourceForm.base_url.trim() || null,
      })
      const createdSource = response.source
      toast.success('Discovery source created')
      setSourceForm(defaultSourceForm)
      setSources((current) => [createdSource, ...current])
      setJobForm((current) => ({
        ...current,
        source_id: current.source_id || createdSource.source_id,
      }))
    } catch (err) {
      toast.error(err.message || 'Failed to create source')
    } finally {
      setCreatingSource(false)
    }
  }

  const handleCreateJob = async (event) => {
    event.preventDefault()
    if (!jobForm.source_id) {
      toast.error('Select a source for the discovery job')
      return
    }
    if (!jobForm.job_name.trim()) {
      toast.error('Job name is required')
      return
    }
    setCreatingJob(true)
    try {
      const response = await soberLivingDirectoryApi.createDiscoveryJob({
        ...jobForm,
        job_name: jobForm.job_name.trim(),
        target_city: jobForm.target_city.trim() || null,
        target_state: jobForm.target_state.trim().toUpperCase() || null,
        query: jobForm.query.trim() || null,
      })
      toast.success('Discovery job created')
      setJobs((current) => [response.job, ...current])
      setScheduleForms((current) => ({
        ...current,
        [response.job.job_id]: buildScheduleForm(response.job),
      }))
      setJobForm((current) => ({
        ...defaultJobForm,
        source_id: current.source_id,
      }))
      await loadDiscoveryData()
    } catch (err) {
      toast.error(err.message || 'Failed to create discovery job')
    } finally {
      setCreatingJob(false)
    }
  }

  const handleRunDiscovery = async (jobId) => {
    setRunningJobId(jobId)
    try {
      const response = await soberLivingDirectoryApi.runDiscoveryJob(jobId)
      const run = response.run
      setRunSummaries((current) => ({ ...current, [jobId]: run }))
      toast.success(`Discovery run completed with ${run.raw_records_created} raw record${run.raw_records_created === 1 ? '' : 's'}`)
      await loadDiscoveryData()
    } catch (err) {
      const message = err.message || 'Discovery run failed'
      setRunSummaries((current) => ({
        ...current,
        [jobId]: {
          status: 'failed',
          error_message: message,
          records_found: 0,
          raw_records_created: 0,
          duplicates_detected: 0,
          errors_count: 1,
        },
      }))
      toast.error(message)
    } finally {
      setRunningJobId('')
    }
  }

  const handleSchedulerAction = async (action) => {
    setSchedulerAction(action)
    try {
      let response
      if (action === 'start') {
        response = await soberLivingDirectoryApi.startSchedulerWorker()
        toast.success('Scheduler worker started')
      } else if (action === 'stop') {
        response = await soberLivingDirectoryApi.stopSchedulerWorker()
        toast.success('Scheduler worker stopped')
      } else {
        response = await soberLivingDirectoryApi.runSchedulerOnce()
        const summary = response.scheduler?.last_cycle_summary || {}
        toast.success(
          `Scheduler poll checked ${summary.checked_jobs ?? 0} jobs and executed ${summary.executed_jobs ?? 0}`
        )
      }
      setSchedulerStatus(response.scheduler || null)
      await loadDiscoveryData()
    } catch (err) {
      toast.error(err.message || 'Scheduler action failed')
    } finally {
      setSchedulerAction('')
    }
  }

  const updateScheduleForm = (jobId, field, value) => {
    setScheduleForms((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || buildScheduleForm(jobs.find((job) => job.job_id === jobId))),
        [field]: value,
      },
    }))
  }

  const handleSaveSchedule = async (jobId) => {
    const form = scheduleForms[jobId] || buildScheduleForm(jobs.find((job) => job.job_id === jobId))
    if (form.schedule_frequency === 'custom_hours' && !Number(form.schedule_interval_hours)) {
      toast.error('Custom hours schedules require an interval greater than 0')
      return
    }
    setSavingScheduleJobId(jobId)
    try {
      await soberLivingDirectoryApi.updateDiscoveryJobSchedule(jobId, {
        schedule_enabled: Boolean(form.schedule_enabled),
        schedule_frequency: form.schedule_frequency || 'manual_only',
        schedule_interval_hours: form.schedule_frequency === 'custom_hours' ? Number(form.schedule_interval_hours) : null,
        max_runs_per_day: Number(form.max_runs_per_day) || 1,
        schedule_timezone: form.schedule_timezone || 'America/Los_Angeles',
        auto_disable_after_failures: Number(form.auto_disable_after_failures) || 3,
      })
      toast.success('Schedule settings saved')
      await loadDiscoveryData()
    } catch (err) {
      toast.error(err.message || 'Failed to save schedule settings')
    } finally {
      setSavingScheduleJobId('')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-slate-950/40">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-fuchsia-300">Discovery Control</p>
              <h1 className="mt-2 text-3xl font-bold text-white">Sober Living Discovery</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Manage discovery sources, define manual discovery jobs, configure future-safe scheduling, and route all results into the existing review workflow.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/sober-living-directory"
                className="rounded-2xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/25"
              >
                Sober Directory
              </Link>
              <Link
                to="/sober-living-directory/review"
                className="rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-500/25"
              >
                Open Review Queue
              </Link>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-amber-400/30 bg-amber-500/10 p-6 text-amber-100">
          <p className="text-sm uppercase tracking-[0.3em] text-amber-200">Scheduling Foundation</p>
          <h2 className="mt-2 text-2xl font-bold text-white">Controlled Worker</h2>
          <p className="mt-2 text-sm">
            Scheduling remains disabled by default. Starting the worker here enables bounded polling for due jobs, but all discovery results still stay in raw review and nothing is auto-published or auto-merged.
          </p>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Review Integration</p>
              <h2 className="mt-2 text-2xl font-bold text-white">Review Links</h2>
              <p className="mt-2 text-sm text-slate-300">
                Discovery runs never publish directly. Review raw records and duplicates before anything becomes a trusted directory listing.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to="/sober-living-directory/review" className="rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
                Review Raw Records
              </Link>
              <Link to="/sober-living-directory/review" className="rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 hover:bg-amber-500/25">
                Resolve Duplicates
              </Link>
              <Link to="/sober-living-directory/review" className="rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400">
                Open Review Queue
              </Link>
            </div>
          </div>
        </section>

        {loading ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-slate-300">Loading discovery controls...</section>
        ) : error ? (
          <section className="rounded-[2rem] border border-red-400/30 bg-red-500/10 p-10 text-center text-red-100">
            Failed to load discovery controls: {error}
          </section>
        ) : (
          <>
            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-fuchsia-300">Scheduler Worker</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Runtime Controls</h2>
                  <p className="mt-2 text-sm text-slate-300">
                    The worker is off by default. Use these controls to start or stop bounded polling, or run one scheduler cycle without leaving the page.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => handleSchedulerAction('start')}
                    disabled={schedulerAction !== '' || schedulerStatus?.running}
                    className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Play className="h-4 w-4" />
                    {schedulerAction === 'start' ? 'Starting...' : 'Start Worker'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSchedulerAction('stop')}
                    disabled={schedulerAction !== '' || !schedulerStatus?.running}
                    className="inline-flex items-center gap-2 rounded-2xl border border-red-400/30 bg-red-500/15 px-4 py-3 text-sm font-semibold text-red-100 transition hover:bg-red-500/25 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <PauseCircle className="h-4 w-4" />
                    {schedulerAction === 'stop' ? 'Stopping...' : 'Stop Worker'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSchedulerAction('tick')}
                    disabled={schedulerAction !== ''}
                    className="inline-flex items-center gap-2 rounded-2xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-500/25 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <TimerReset className="h-4 w-4" />
                    {schedulerAction === 'tick' ? 'Polling...' : 'Poll Once'}
                  </button>
                </div>
              </div>

              <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_1fr]">
                <article className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-lg font-semibold text-white">Worker Status</h3>
                    <Pill color={schedulerStatus?.running ? 'emerald' : 'slate'}>
                      {schedulerStatus?.running ? 'running' : 'stopped'}
                    </Pill>
                    <Pill color={schedulerStatus?.autostart_enabled ? 'amber' : 'slate'}>
                      {schedulerStatus?.autostart_enabled ? 'autostart enabled' : 'autostart disabled'}
                    </Pill>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2 text-sm text-slate-300">
                    <p>Poll interval: {schedulerStatus?.poll_interval_seconds ?? 'Unknown'} seconds</p>
                    <p>Max jobs per cycle: {schedulerStatus?.max_jobs_per_cycle ?? 'Unknown'}</p>
                    <p>Started: {schedulerStatus?.started_at || 'Never'}</p>
                    <p>Stopped: {schedulerStatus?.stopped_at || 'Not stopped yet'}</p>
                    <p>Last poll: {schedulerStatus?.last_poll_at || 'Never'}</p>
                    <p>Active job: {schedulerStatus?.current_job_name || 'None'}</p>
                  </div>
                  <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                    {schedulerStatus?.warning || 'Scheduler worker is controlled manually from this page.'}
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                  <h3 className="text-lg font-semibold text-white">Last Cycle Summary</h3>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <StatCard label="Checked" value={schedulerStatus?.last_cycle_summary?.checked_jobs ?? 0} />
                    <StatCard label="Due" value={schedulerStatus?.last_cycle_summary?.due_jobs ?? 0} />
                    <StatCard label="Executed" value={schedulerStatus?.last_cycle_summary?.executed_jobs ?? 0} />
                    <StatCard label="Failed" value={schedulerStatus?.last_cycle_summary?.failed_jobs ?? 0} danger={Boolean(schedulerStatus?.last_cycle_summary?.failed_jobs)} />
                  </div>
                  <div className="mt-4 space-y-1 text-sm text-slate-300">
                    <p>Trigger: {schedulerStatus?.last_cycle_summary?.trigger || 'None yet'}</p>
                    <p>Cycle started: {schedulerStatus?.last_cycle_started_at || 'Never'}</p>
                    <p>Cycle finished: {schedulerStatus?.last_cycle_finished_at || 'Never'}</p>
                  </div>
                </article>
              </div>
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Source Registry</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Discovery Sources</h2>
                </div>
                <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
                  {safeSources.length} source{safeSources.length === 1 ? '' : 's'}
                </div>
              </div>

              <form className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={handleCreateSource}>
                <Input label="Source Name" value={sourceForm.source_name} onChange={(value) => setSourceForm((current) => ({ ...current, source_name: value }))} />
                <Select label="Source Type" value={sourceForm.source_type} onChange={(value) => setSourceForm((current) => ({ ...current, source_type: value }))} options={allowedSourceTypes} />
                <Input label="Base URL" value={sourceForm.base_url} onChange={(value) => setSourceForm((current) => ({ ...current, base_url: value }))} />
                <Select label="Trust Level" value={sourceForm.trust_level} onChange={(value) => setSourceForm((current) => ({ ...current, trust_level: value }))} options={['high', 'medium', 'low']} />
                <Toggle label="Supports API" checked={sourceForm.supports_api} onChange={(value) => setSourceForm((current) => ({ ...current, supports_api: value }))} />
                <Toggle label="Supports Scraping" checked={sourceForm.supports_scraping} onChange={(value) => setSourceForm((current) => ({ ...current, supports_scraping: value }))} />
                <Toggle label="Requires Manual Review" checked={sourceForm.requires_manual_review} onChange={(value) => setSourceForm((current) => ({ ...current, requires_manual_review: value }))} />
                <Toggle label="Active" checked={sourceForm.is_active} onChange={(value) => setSourceForm((current) => ({ ...current, is_active: value }))} />
                <div className="md:col-span-2 xl:col-span-4 flex justify-end">
                  <button type="submit" disabled={creatingSource} className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60">
                    <Plus className="h-4 w-4" />
                    {creatingSource ? 'Creating Source...' : 'Create Source'}
                  </button>
                </div>
              </form>

              {safeSources.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
                  No discovery sources configured yet.
                </div>
              ) : (
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  {safeSources.map((source) => (
                    <article key={source.source_id} className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-semibold text-white">{source.source_name}</h3>
                            <Pill color={source.is_active ? 'emerald' : 'slate'}>{source.is_active ? 'active' : 'inactive'}</Pill>
                            <Pill color={source.trust_level === 'high' ? 'cyan' : source.trust_level === 'medium' ? 'amber' : 'slate'}>
                              {source.trust_level} trust
                            </Pill>
                          </div>
                          <p className="mt-2 text-sm text-slate-300">{humanizeToken(source.source_type)}</p>
                          <p className="mt-1 break-all text-xs text-slate-400">{source.base_url || 'No base URL configured'}</p>
                          <p className="mt-2 text-xs text-slate-500">Last checked: {source.last_checked_at || 'Never'}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                          <p>API: {source.supports_api ? 'Yes' : 'No'}</p>
                          <p>Scraping: {source.supports_scraping ? 'Yes' : 'No'}</p>
                          <p>Manual review: {source.requires_manual_review ? 'Yes' : 'No'}</p>
                        </div>
                      </div>
                      {(source.source_type === 'certification_directory' || source.source_name?.toLowerCase().includes('oxford')) ? (
                        <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                          <p>Manual run only. Results are stored as raw review records and are not published automatically.</p>
                          <p className="mt-2">Connector parses visible public search-page cards only; results may be incomplete.</p>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-violet-300">Scheduler Preview</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Scheduling Eligibility Preview</h2>
                  <p className="mt-2 text-sm text-slate-300">
                    This preview evaluates which jobs would be due or blocked if a scheduler worker existed. It does not execute anything.
                  </p>
                </div>
                <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
                  {safeSchedulerPreview.length} preview item{safeSchedulerPreview.length === 1 ? '' : 's'}
                </div>
              </div>

              {safeSchedulerPreview.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
                  No discovery jobs are available for scheduler preview yet.
                </div>
              ) : (
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  {safeSchedulerPreview.map((preview) => (
                    <article key={preview.job_id} className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold text-white">{preview.job_name}</h3>
                        <Pill color={preview.schedule_enabled ? 'emerald' : 'slate'}>
                          {preview.schedule_enabled ? 'schedule enabled' : 'schedule disabled'}
                        </Pill>
                        <Pill color={preview.due ? 'amber' : 'slate'}>
                          {preview.due ? 'due' : 'not due'}
                        </Pill>
                        <Pill color={preview.can_run ? 'emerald' : 'red'}>
                          {preview.can_run ? 'can run' : 'blocked'}
                        </Pill>
                      </div>
                      <div className="mt-3 space-y-1 text-sm text-slate-300">
                        <p>Source: {preview.source_name || sourceNames[preview.source_id] || 'Unknown source'}</p>
                        <p>Frequency: {humanizeToken(preview.schedule_frequency || 'manual_only')}</p>
                        <p>Next scheduled run: {preview.next_scheduled_run_at || 'Not scheduled'}</p>
                        <p>Last scheduled run: {preview.last_scheduled_run_at || 'Never'}</p>
                        <p>Last run status: {preview.last_run_status || 'None'}</p>
                        <p>Consecutive failures: {preview.consecutive_failures ?? 0}</p>
                      </div>
                      {!preview.can_run ? (
                        <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-100">
                          {blockedReasonLabels[preview.blocked_reason] || preview.blocked_reason || 'Blocked'}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Discovery Jobs</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Manual Discovery Runs</h2>
                </div>
                <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
                  {safeJobs.length} job{safeJobs.length === 1 ? '' : 's'}
                </div>
              </div>

              <form className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={handleCreateJob}>
                <Select label="Source" value={jobForm.source_id} onChange={(value) => setJobForm((current) => ({ ...current, source_id: value }))} options={safeSources.map((source) => ({ value: source.source_id, label: source.source_name }))} />
                <Input label="Job Name" value={jobForm.job_name} onChange={(value) => setJobForm((current) => ({ ...current, job_name: value }))} />
                <Select label="Job Type" value={jobForm.job_type} onChange={(value) => setJobForm((current) => ({ ...current, job_type: value }))} options={allowedJobTypes} />
                <Input label="Query" value={jobForm.query} onChange={(value) => setJobForm((current) => ({ ...current, query: value }))} />
                <Input label="Target City" value={jobForm.target_city} onChange={(value) => setJobForm((current) => ({ ...current, target_city: value }))} />
                <Input label="Target State" value={jobForm.target_state} onChange={(value) => setJobForm((current) => ({ ...current, target_state: value }))} />
                <Toggle label="Active" checked={jobForm.is_active} onChange={(value) => setJobForm((current) => ({ ...current, is_active: value }))} />
                <div className="flex items-end">
                  <button type="submit" disabled={creatingJob} className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60">
                    <Plus className="h-4 w-4" />
                    {creatingJob ? 'Creating Job...' : 'Create Job'}
                  </button>
                </div>
              </form>

              {safeJobs.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
                  No discovery jobs configured yet.
                </div>
              ) : (
                <div className="mt-5 space-y-4">
                  {safeJobs.map((job) => {
                    const summary = runSummaries[job.job_id]
                    const sourceName = job.source_name || sourceNames[job.source_id] || 'Unknown source'
                    const preview = previewByJobId[job.job_id]
                    const scheduleForm = scheduleForms[job.job_id] || buildScheduleForm(job)
                    return (
                      <article key={job.job_id} className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="text-lg font-semibold text-white">{job.job_name}</h3>
                              <Pill color={job.is_active ? 'emerald' : 'slate'}>{job.is_active ? 'active' : 'inactive'}</Pill>
                              <Pill color={scheduleForm.schedule_enabled ? 'cyan' : 'slate'}>
                                {scheduleForm.schedule_enabled ? 'schedule enabled' : 'manual only'}
                              </Pill>
                            </div>
                            <p className="text-sm text-slate-300">{sourceName} | {humanizeToken(job.job_type)}</p>
                            <p className="text-sm text-slate-400">
                              Target: {job.target_city || 'Any city'}, {job.target_state || 'Any state'} | Query: {job.query || 'None'}
                            </p>
                            <p className="text-xs text-slate-500">
                              Last run: {job.last_run_at || 'Never'} | Last scheduled run: {job.last_scheduled_run_at || 'Never'}
                            </p>
                            <p className="text-xs text-slate-500">
                              Next scheduled run: {job.next_scheduled_run_at || 'Not scheduled'} | Failures: {job.consecutive_failures ?? 0}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-3">
                            <button type="button" onClick={() => handleRunDiscovery(job.job_id)} disabled={runningJobId === job.job_id} className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60">
                              <Play className="h-4 w-4" />
                              {runningJobId === job.job_id ? 'Running...' : 'Run Discovery'}
                            </button>
                            <Link to="/sober-living-directory/review" className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
                              <Workflow className="h-4 w-4" />
                              Review Queue
                            </Link>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
                          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Schedule Controls</p>
                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                              <Toggle label="Enable Schedule" checked={Boolean(scheduleForm.schedule_enabled)} onChange={(value) => updateScheduleForm(job.job_id, 'schedule_enabled', value)} />
                              <Select label="Frequency" value={scheduleForm.schedule_frequency} onChange={(value) => updateScheduleForm(job.job_id, 'schedule_frequency', value)} options={allowedScheduleFrequencies} />
                              <Input label="Interval Hours" type="number" value={scheduleForm.schedule_interval_hours} onChange={(value) => updateScheduleForm(job.job_id, 'schedule_interval_hours', value)} />
                              <Input label="Max Runs / Day" type="number" value={scheduleForm.max_runs_per_day} onChange={(value) => updateScheduleForm(job.job_id, 'max_runs_per_day', value)} />
                              <Input label="Timezone" value={scheduleForm.schedule_timezone} onChange={(value) => updateScheduleForm(job.job_id, 'schedule_timezone', value)} />
                              <Input label="Auto Disable After Failures" type="number" value={scheduleForm.auto_disable_after_failures} onChange={(value) => updateScheduleForm(job.job_id, 'auto_disable_after_failures', value)} />
                            </div>
                            <div className="mt-4 flex justify-end">
                              <button type="button" onClick={() => handleSaveSchedule(job.job_id)} disabled={savingScheduleJobId === job.job_id} className="rounded-2xl bg-violet-500 px-4 py-3 text-sm font-semibold text-white hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-60">
                                {savingScheduleJobId === job.job_id ? 'Saving Schedule...' : 'Save Schedule Settings'}
                              </button>
                            </div>
                          </div>

                          <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Scheduler Preview</p>
                            <div className="mt-3 space-y-2 text-sm text-slate-200">
                              <p>Due: {preview?.due ? 'Yes' : 'No'}</p>
                              <p>Can run: {preview?.can_run ? 'Yes' : 'No'}</p>
                              <p>Reason: {preview?.can_run ? 'Eligible' : (blockedReasonLabels[preview?.blocked_reason] || preview?.blocked_reason || 'Blocked')}</p>
                              <p>Max runs / day: {preview?.max_runs_per_day ?? job.max_runs_per_day ?? 1}</p>
                              <p>Scheduled runs today: {preview?.scheduled_runs_today ?? 0}</p>
                              <p>Last run status: {preview?.last_run_status || 'None'}</p>
                            </div>
                          </div>
                        </div>

                        {summary ? (
                          <div className={`mt-4 rounded-2xl border p-4 text-sm ${summary.status === 'failed' ? 'border-red-400/30 bg-red-500/10 text-red-100' : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100'}`}>
                            <div className="flex flex-wrap gap-4">
                              <span>Records found: {summary.records_found ?? 0}</span>
                              <span>Raw created: {summary.raw_records_created ?? 0}</span>
                              <span>Duplicates: {summary.duplicates_detected ?? 0}</span>
                              <span>Errors: {summary.errors_count ?? 0}</span>
                            </div>
                            {summary.error_message ? <p className="mt-2">{summary.error_message}</p> : null}
                          </div>
                        ) : null}
                      </article>
                    )
                  })}
                </div>
              )}
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-amber-300">Run History</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Recent Discovery Runs</h2>
                </div>
                <button type="button" onClick={loadDiscoveryData} className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
                  <RefreshCw className="h-4 w-4" />
                  Refresh
                </button>
              </div>

              {safeRuns.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
                  No discovery runs have been recorded yet.
                </div>
              ) : (
                <div className="mt-5 space-y-4">
                  {safeRuns.map((run) => (
                    <article key={run.run_id} className="rounded-[1.5rem] border border-white/10 bg-slate-950/35 p-5">
                      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-semibold text-white">{run.job_name || 'Unknown job'}</h3>
                            <Pill color={run.status === 'completed' ? 'emerald' : run.status === 'failed' ? 'red' : 'amber'}>
                              {run.status}
                            </Pill>
                            <Pill color={run.trigger_type === 'scheduled' ? 'violet' : 'slate'}>
                              {run.trigger_type || 'manual'}
                            </Pill>
                          </div>
                          <p className="text-sm text-slate-300">Run ID: {run.run_id}</p>
                          <p className="text-sm text-slate-400">
                            Source: {run.source_name || sourceNames[run.source_id] || 'Unknown source'}
                          </p>
                          <p className="text-xs text-slate-500">
                            Started: {run.started_at || 'Unknown'} | Finished: {run.finished_at || 'In progress'}
                          </p>
                        </div>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                          <StatCard label="Found" value={run.records_found ?? 0} />
                          <StatCard label="Raw" value={run.raw_records_created ?? 0} />
                          <StatCard label="Duplicates" value={run.duplicates_detected ?? 0} />
                          <StatCard label="Errors" value={run.errors_count ?? 0} danger={Boolean(run.errors_count)} />
                        </div>
                      </div>
                      {run.error_message ? (
                        <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
                          Error: {run.error_message}
                        </div>
                      ) : null}
                      {run.notes ? (
                        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                          {run.notes}
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
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

function Select({ label, value, onChange, options = [] }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      >
        <option value="">Select...</option>
        {options.map((option) => {
          const valueToUse = typeof option === 'string' ? option : option.value
          const labelToUse = typeof option === 'string' ? option.replaceAll('_', ' ') : option.label
          return (
            <option key={valueToUse} value={valueToUse}>
              {labelToUse}
            </option>
          )
        })}
      </select>
    </label>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border-white/20 bg-slate-900"
      />
    </label>
  )
}

function StatCard({ label, value, danger = false }) {
  return (
    <div className={`rounded-2xl border px-4 py-3 text-center ${danger ? 'border-red-400/30 bg-red-500/10' : 'border-white/10 bg-white/5'}`}>
      <p className="text-xs uppercase tracking-[0.15em] text-slate-400">{label}</p>
      <p className={`mt-2 text-xl font-semibold ${danger ? 'text-red-100' : 'text-white'}`}>{value}</p>
    </div>
  )
}

function Pill({ children, color = 'slate' }) {
  const colorMap = {
    slate: 'border-slate-400/20 bg-slate-500/10 text-slate-200',
    emerald: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100',
    amber: 'border-amber-400/30 bg-amber-500/15 text-amber-100',
    cyan: 'border-cyan-400/30 bg-cyan-500/15 text-cyan-100',
    red: 'border-red-400/30 bg-red-500/15 text-red-100',
    violet: 'border-violet-400/30 bg-violet-500/15 text-violet-100',
  }
  return (
    <span className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.18em] ${colorMap[color] || colorMap.slate}`}>
      {children}
    </span>
  )
}

export default SoberLivingDirectoryDiscovery
