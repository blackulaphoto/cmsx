import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  GitMerge,
  Info,
  ShieldAlert,
  SplitSquareVertical,
  XCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import TrustScoreBadge from '../components/TrustScoreBadge'
import { soberLivingDirectoryApi } from '../utils/soberLivingDirectory'

const diffStatusStyles = {
  same: 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100',
  existing_empty: 'border-cyan-400/20 bg-cyan-500/10 text-cyan-100',
  imported_empty: 'border-slate-400/20 bg-slate-500/10 text-slate-200',
  conflict: 'border-red-400/30 bg-red-500/15 text-red-100',
}

const formatLabel = (value) => String(value || '').replaceAll('_', ' ')

const formatValue = (value) => {
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'Missing'
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  if (value === null || value === undefined || value === '') {
    return 'Missing'
  }
  return String(value)
}

function SoberLivingDirectoryReview() {
  const [items, setItems] = useState([])
  const [duplicateCandidates, setDuplicateCandidates] = useState([])
  const [rawRecords, setRawRecords] = useState([])
  const [rawRecordDetails, setRawRecordDetails] = useState({})
  const [rawReviewNotes, setRawReviewNotes] = useState({})
  const [expandedRawRecordId, setExpandedRawRecordId] = useState('')
  const [loadingRawRecordId, setLoadingRawRecordId] = useState('')
  const [approvedRawTargets, setApprovedRawTargets] = useState({})
  const [candidateDetails, setCandidateDetails] = useState({})
  const [selectedImportedFields, setSelectedImportedFields] = useState({})
  const [expandedCandidateId, setExpandedCandidateId] = useState('')
  const [loadingCandidateId, setLoadingCandidateId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadQueue = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await soberLivingDirectoryApi.getReviewQueue()
      setItems(data.listings || [])
      setDuplicateCandidates(data.duplicate_candidates || [])
      setRawRecords(data.raw_records || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQueue()
  }, [])

  const updateStatus = async (listingId, status) => {
    try {
      await soberLivingDirectoryApi.updateListing(listingId, { status })
      toast.success(`Listing moved to ${status.replaceAll('_', ' ')}`)
      await loadQueue()
    } catch (err) {
      toast.error(err.message || 'Failed to update listing')
    }
  }

  const loadCandidateDetail = async (candidateId) => {
    if (candidateDetails[candidateId]) {
      setExpandedCandidateId((current) => (current === candidateId ? '' : candidateId))
      return
    }

    setLoadingCandidateId(candidateId)
    try {
      const detail = await soberLivingDirectoryApi.getDuplicateCandidate(candidateId)
      setCandidateDetails((current) => ({ ...current, [candidateId]: detail }))
      setExpandedCandidateId(candidateId)
    } catch (err) {
      toast.error(err.message || 'Failed to load duplicate candidate detail')
    } finally {
      setLoadingCandidateId('')
    }
  }

  const toggleSelectedField = (candidateId, field) => {
    setSelectedImportedFields((current) => {
      const existing = new Set(current[candidateId] || [])
      if (existing.has(field)) {
        existing.delete(field)
      } else {
        existing.add(field)
      }
      return {
        ...current,
        [candidateId]: Array.from(existing),
      }
    })
  }

  const resolveDuplicate = async (candidateId, action, useSelectedFields = false) => {
    try {
      if (action === 'merge') {
        const selectedFields = useSelectedFields ? (selectedImportedFields[candidateId] || []) : []
        await soberLivingDirectoryApi.mergeDuplicateCandidate(candidateId, {
          resolution_notes: useSelectedFields ? 'Merged with reviewer-selected imported fields' : 'Merged with safe duplicate defaults',
          selected_imported_fields: selectedFields,
        })
      } else if (action === 'separate') {
        await soberLivingDirectoryApi.keepDuplicateCandidateSeparate(candidateId, { resolution_notes: 'Approved as separate listing from duplicate review queue' })
      } else {
        await soberLivingDirectoryApi.rejectDuplicateCandidate(candidateId, { resolution_notes: 'Rejected duplicate import candidate' })
      }
      toast.success('Duplicate review updated')
      setExpandedCandidateId('')
      setCandidateDetails((current) => {
        const next = { ...current }
        delete next[candidateId]
        return next
      })
      setSelectedImportedFields((current) => {
        const next = { ...current }
        delete next[candidateId]
        return next
      })
      await loadQueue()
    } catch (err) {
      toast.error(err.message || 'Failed to resolve duplicate candidate')
    }
  }

  const markVerified = async (listingId) => {
    try {
      await soberLivingDirectoryApi.verifyListing(listingId, {
        verification_method: 'manual_review',
        result_notes: 'Verified from review queue',
      })
      toast.success('Listing verified')
      await loadQueue()
    } catch (err) {
      toast.error(err.message || 'Failed to verify listing')
    }
  }

  const loadRawRecordDetail = async (rawId) => {
    if (rawRecordDetails[rawId]) {
      setExpandedRawRecordId((current) => (current === rawId ? '' : rawId))
      return
    }

    setLoadingRawRecordId(rawId)
    try {
      const detail = await soberLivingDirectoryApi.getRawRecord(rawId)
      setRawRecordDetails((current) => ({ ...current, [rawId]: detail }))
      setExpandedRawRecordId(rawId)
    } catch (err) {
      toast.error(err.message || 'Failed to load raw record detail')
    } finally {
      setLoadingRawRecordId('')
    }
  }

  const approveRawRecord = async (rawId, force = false) => {
    try {
      const payload = {
        review_notes: rawReviewNotes[rawId] || '',
        force,
      }
      const result = await soberLivingDirectoryApi.approveRawRecord(rawId, payload)
      if (result.listing?.listing_id) {
        setApprovedRawTargets((current) => ({ ...current, [rawId]: result.listing }))
      }
      toast.success('Raw record promoted into the directory review flow')
      setExpandedRawRecordId('')
      await loadQueue()
    } catch (err) {
      toast.error(err.message || 'Failed to approve raw record')
    }
  }

  const rejectRawRecord = async (rawId) => {
    try {
      await soberLivingDirectoryApi.rejectRawRecord(rawId, { review_notes: rawReviewNotes[rawId] || '' })
      toast.success('Raw record rejected')
      setExpandedRawRecordId('')
      await loadQueue()
    } catch (err) {
      toast.error(err.message || 'Failed to reject raw record')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <p className="text-sm uppercase tracking-[0.3em] text-amber-300">Review Workflow</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Sober Living Directory Review</h1>
          <p className="mt-2 text-sm text-slate-300">
            Review pending, stale, and cautionary listings before they become trusted referral options.
          </p>
        </section>

        {loading ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-slate-300">Loading review queue...</section>
        ) : error ? (
          <section className="rounded-[2rem] border border-red-400/30 bg-red-500/10 p-10 text-center text-red-100">
            Failed to load review queue: {error}
          </section>
        ) : items.length === 0 ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-slate-300">
            No listings currently require review.
          </section>
        ) : (
          <section className="space-y-4">
            {items.map((item) => (
              <article key={item.listing_id} className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-xl font-semibold text-white">{item.name}</h2>
                      <TrustScoreBadge score={item.trust_score} status={item.status} />
                    </div>
                    <p className="text-sm text-slate-300">{item.city}, {item.state}</p>
                    <p className="text-sm text-slate-400">Phone: {item.phone || 'Missing'} | Certification: {item.certification_status || 'Unknown'}</p>
                    <div className="flex flex-wrap gap-2">
                      {item.missing_verification_fields?.length ? (
                        <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/15 px-3 py-1 text-xs text-amber-100">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Missing: {item.missing_verification_fields.join(', ')}
                        </span>
                      ) : null}
                      {item.is_stale ? (
                        <span className="rounded-full border border-orange-400/30 bg-orange-500/15 px-3 py-1 text-xs text-orange-100">
                          Stale record
                        </span>
                      ) : null}
                      {item.source_urls_json?.length ? (
                        <span className="rounded-full border border-cyan-400/30 bg-cyan-500/15 px-3 py-1 text-xs text-cyan-100">
                          {item.source_urls_json.length} source link{item.source_urls_json.length === 1 ? '' : 's'}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => updateStatus(item.listing_id, 'approved')} className="rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400">
                      Approve
                    </button>
                    <button onClick={() => markVerified(item.listing_id)} className="inline-flex items-center gap-2 rounded-2xl border border-emerald-400/30 bg-emerald-500/15 px-4 py-3 text-sm font-medium text-emerald-100 hover:bg-emerald-500/25">
                      <CheckCircle2 className="h-4 w-4" />
                      Mark Verified
                    </button>
                    <button onClick={() => updateStatus(item.listing_id, 'do_not_refer')} className="inline-flex items-center gap-2 rounded-2xl border border-red-400/30 bg-red-500/15 px-4 py-3 text-sm font-medium text-red-100 hover:bg-red-500/25">
                      <ShieldAlert className="h-4 w-4" />
                      Do Not Refer
                    </button>
                    <button onClick={() => updateStatus(item.listing_id, 'archived')} className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10">
                      <Archive className="h-4 w-4" />
                      Archive
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </section>
        )}

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Duplicate Review</p>
              <h2 className="mt-2 text-2xl font-bold text-white">Possible Duplicate Candidates</h2>
              <p className="mt-2 text-sm text-slate-300">
                Compare imported raw records against existing directory listings before merging or creating a separate listing.
              </p>
            </div>
            <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
              {duplicateCandidates.length} open candidate{duplicateCandidates.length === 1 ? '' : 's'}
            </div>
          </div>

          {duplicateCandidates.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
              No duplicate candidates are waiting for review.
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {duplicateCandidates.map((candidate) => {
                const detail = candidateDetails[candidate.candidate_id]
                const selectedFields = selectedImportedFields[candidate.candidate_id] || []
                const isExpanded = expandedCandidateId === candidate.candidate_id

                return (
                  <article key={candidate.candidate_id} className="rounded-[2rem] border border-white/10 bg-slate-950/35 p-5">
                    <div className="grid gap-5 xl:grid-cols-[1fr_1fr_auto]">
                      <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Imported Candidate</p>
                        <h3 className="mt-2 text-lg font-semibold text-white">{candidate.proposed_name || candidate.extracted_json?.name || 'Unnamed candidate'}</h3>
                        <div className="mt-3 space-y-1 text-sm text-slate-300">
                          <p>City: {candidate.extracted_json?.city || 'Unknown'}</p>
                          <p>Phone: {candidate.extracted_json?.phone || 'Missing'}</p>
                          <p>Website: {candidate.extracted_json?.website || 'Missing'}</p>
                          <p>Population: {candidate.extracted_json?.population_served || 'Unknown'}</p>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-amber-400/20 bg-amber-500/5 p-4">
                        <p className="text-xs uppercase tracking-[0.2em] text-amber-200">Existing Listing</p>
                        <h3 className="mt-2 text-lg font-semibold text-white">{candidate.existing_name}</h3>
                        <div className="mt-3 space-y-1 text-sm text-slate-300">
                          <p>City: {candidate.existing_city || 'Unknown'}, {candidate.existing_state || ''}</p>
                          <p>Phone: {candidate.existing_phone || 'Missing'}</p>
                          <p>Website: {candidate.existing_website || 'Missing'}</p>
                          <p>Population: {candidate.existing_population_served || 'Unknown'}</p>
                          <p>Status: {candidate.existing_status?.replaceAll('_', ' ') || 'Unknown'}</p>
                        </div>
                      </div>

                      <div className="flex flex-col gap-3">
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Confidence</p>
                          <p className="mt-2 text-2xl font-semibold text-white">{candidate.confidence_score}</p>
                          <p className="mt-2 text-xs text-slate-400">
                            {candidate.match_reasons_json?.length ? candidate.match_reasons_json.join(', ').replaceAll('_', ' ') : 'possible duplicate'}
                          </p>
                        </div>
                        <button
                          onClick={() => loadCandidateDetail(candidate.candidate_id)}
                          className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10"
                        >
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          Review Diff
                        </button>
                        <button onClick={() => resolveDuplicate(candidate.candidate_id, 'merge')} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400">
                          <GitMerge className="h-4 w-4" />
                          Merge Safely
                        </button>
                        <button onClick={() => resolveDuplicate(candidate.candidate_id, 'separate')} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm font-medium text-cyan-100 hover:bg-cyan-500/25">
                          <SplitSquareVertical className="h-4 w-4" />
                          Keep Separate
                        </button>
                        <button onClick={() => resolveDuplicate(candidate.candidate_id, 'reject')} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-red-400/30 bg-red-500/15 px-4 py-3 text-sm font-medium text-red-100 hover:bg-red-500/25">
                          <ShieldAlert className="h-4 w-4" />
                          Reject
                        </button>
                      </div>
                    </div>

                    {loadingCandidateId === candidate.candidate_id ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        Loading duplicate comparison...
                      </div>
                    ) : null}

                    {isExpanded && detail ? (
                      <div className="mt-4 rounded-[1.5rem] border border-white/10 bg-slate-950/40 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <h4 className="text-lg font-semibold text-white">Field-by-field comparison</h4>
                            <p className="mt-1 text-sm text-slate-400">
                              Match reasons: {(detail.match_reasons || []).join(', ').replaceAll('_', ' ') || 'possible duplicate'}
                            </p>
                          </div>
                          <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white">
                            Confidence {detail.confidence_score}
                          </div>
                        </div>

                        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                          {detail.field_diff?.map((fieldDiff) => {
                            const canSelectImported = fieldDiff.status === 'conflict'
                            const isChecked = selectedFields.includes(fieldDiff.field)
                            return (
                              <div
                                key={fieldDiff.field}
                                className={`rounded-2xl border p-4 ${diffStatusStyles[fieldDiff.status] || 'border-white/10 bg-white/5 text-white'}`}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <p className="text-xs uppercase tracking-[0.2em] opacity-80">{formatLabel(fieldDiff.field)}</p>
                                    <p className="mt-2 text-xs opacity-75">Recommended: {formatLabel(fieldDiff.recommended_action)}</p>
                                  </div>
                                  <span className="rounded-full border border-current/25 px-2 py-1 text-[11px] uppercase tracking-[0.18em]">
                                    {formatLabel(fieldDiff.status)}
                                  </span>
                                </div>
                                <div className="mt-4 space-y-3 text-sm">
                                  <div>
                                    <p className="text-xs uppercase tracking-[0.15em] opacity-70">Existing</p>
                                    <p className="mt-1 break-words">{formatValue(fieldDiff.existing_value)}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs uppercase tracking-[0.15em] opacity-70">Imported</p>
                                    <p className="mt-1 break-words">{formatValue(fieldDiff.imported_value)}</p>
                                  </div>
                                </div>
                                {canSelectImported ? (
                                  <label className="mt-4 flex items-center gap-2 text-xs font-medium">
                                    <input
                                      type="checkbox"
                                      checked={isChecked}
                                      onChange={() => toggleSelectedField(candidate.candidate_id, fieldDiff.field)}
                                    />
                                    Apply imported value for {formatLabel(fieldDiff.field)}
                                  </label>
                                ) : null}
                              </div>
                            )
                          })}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <button
                            onClick={() => resolveDuplicate(candidate.candidate_id, 'merge')}
                            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
                          >
                            <GitMerge className="h-4 w-4" />
                            Merge Safely
                          </button>
                          <button
                            onClick={() => resolveDuplicate(candidate.candidate_id, 'merge', true)}
                            disabled={selectedFields.length === 0}
                            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 hover:bg-amber-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <GitMerge className="h-4 w-4" />
                            Merge Selected Fields
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>
          )}
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-fuchsia-300">Raw Discovery</p>
              <h2 className="mt-2 text-2xl font-bold text-white">Raw Discovery Records</h2>
              <p className="mt-2 text-sm text-slate-300">
                Discovery runs can only create reviewable raw records. Nothing here is auto-published.
              </p>
            </div>
            <div className="rounded-full border border-white/10 bg-slate-950/40 px-4 py-2 text-sm text-white">
              {rawRecords.length} raw record{rawRecords.length === 1 ? '' : 's'}
            </div>
          </div>

          {rawRecords.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-6 text-center text-slate-300">
              No raw discovery records currently need review.
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {rawRecords.map((record) => {
                const detail = rawRecordDetails[record.raw_id]
                const isExpanded = expandedRawRecordId === record.raw_id
                const hasOpenDuplicate = (record.duplicate_candidate_count || 0) > 0
                const approvedTarget = approvedRawTargets[record.raw_id]
                return (
                  <article key={record.raw_id} className="rounded-[2rem] border border-white/10 bg-slate-950/35 p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-3">
                          <h3 className="text-lg font-semibold text-white">{record.raw_name || record.extracted_json?.name || 'Unnamed raw record'}</h3>
                          <span className="rounded-full border border-fuchsia-400/30 bg-fuchsia-500/15 px-3 py-1 text-xs text-fuchsia-100">
                            {formatLabel(record.review_status)}
                          </span>
                          {hasOpenDuplicate ? (
                            <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/15 px-3 py-1 text-xs text-amber-100">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              {record.duplicate_candidate_count} duplicate candidate{record.duplicate_candidate_count === 1 ? '' : 's'}
                            </span>
                          ) : null}
                        </div>
                        <p className="text-sm text-slate-300">
                          {record.raw_address || record.extracted_json?.address || 'Missing address'} | {(record.extracted_json?.city || 'Unknown city')}, {(record.extracted_json?.state || 'Unknown state')}
                        </p>
                        <p className="text-sm text-slate-400">
                          Phone: {record.raw_phone || record.extracted_json?.phone || 'Missing'} | Website: {record.raw_website || record.extracted_json?.website || 'Missing'}
                        </p>
                        <p className="text-xs text-slate-500">
                          Source: {record.source_name || 'Unknown source'} | Run: {record.run_id || 'Manual/import'} | Discovered: {record.discovered_at || 'Unknown'}
                        </p>
                        {record.missing_required_fields?.length ? (
                          <p className="text-xs text-red-200">
                            Missing required fields: {record.missing_required_fields.join(', ')}
                          </p>
                        ) : null}
                        {approvedTarget ? (
                          <Link className="text-sm text-cyan-200 underline underline-offset-4" to={`/sober-living-directory/${approvedTarget.listing_id}`}>
                            Open new listing {approvedTarget.name || approvedTarget.listing_id}
                          </Link>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => loadRawRecordDetail(record.raw_id)}
                          className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-white hover:bg-white/10"
                        >
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          View Details
                        </button>
                        <button
                          onClick={() => approveRawRecord(record.raw_id)}
                          disabled={hasOpenDuplicate || Boolean(record.missing_required_fields?.length)}
                          className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Approve Into Directory
                        </button>
                        <button
                          onClick={() => rejectRawRecord(record.raw_id)}
                          className="inline-flex items-center gap-2 rounded-2xl border border-red-400/30 bg-red-500/15 px-4 py-3 text-sm font-medium text-red-100 hover:bg-red-500/25"
                        >
                          <XCircle className="h-4 w-4" />
                          Reject
                        </button>
                        {hasOpenDuplicate ? (
                          <button
                            onClick={() => {
                              const candidate = duplicateCandidates.find((item) => item.raw_id === record.raw_id)
                              if (candidate) {
                                loadCandidateDetail(candidate.candidate_id)
                                setExpandedRawRecordId('')
                              }
                            }}
                            className="inline-flex items-center gap-2 rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 hover:bg-amber-500/25"
                          >
                            <GitMerge className="h-4 w-4" />
                            Resolve Duplicate
                          </button>
                        ) : null}
                      </div>
                    </div>

                    {loadingRawRecordId === record.raw_id ? (
                      <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                        Loading raw record detail...
                      </div>
                    ) : null}

                    {isExpanded && detail ? (
                      <div className="mt-4 rounded-[1.5rem] border border-white/10 bg-slate-950/40 p-4">
                        <div className="grid gap-4 lg:grid-cols-2">
                          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Original Raw Fields</p>
                            <div className="mt-3 space-y-2 text-sm text-slate-200">
                              <p>Name: {detail.original_raw_fields?.raw_name || 'Missing'}</p>
                              <p>Address: {detail.original_raw_fields?.raw_address || 'Missing'}</p>
                              <p>Phone: {detail.original_raw_fields?.raw_phone || 'Missing'}</p>
                              <p>Email: {detail.original_raw_fields?.raw_email || 'Missing'}</p>
                              <p>Website: {detail.original_raw_fields?.raw_website || 'Missing'}</p>
                            </div>
                          </div>
                          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/5 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200">Normalized Preview</p>
                            <div className="mt-3 space-y-2 text-sm text-slate-100">
                              <p>Name: {detail.normalized_preview_fields?.name || 'Missing'}</p>
                              <p>City/State: {detail.normalized_preview_fields?.city || 'Missing'}, {detail.normalized_preview_fields?.state || 'Missing'}</p>
                              <p>Phone: {detail.normalized_preview_fields?.phone || 'Missing'}</p>
                              <p>Website: {detail.normalized_preview_fields?.website || 'Missing'}</p>
                              <p>Population: {detail.normalized_preview_fields?.population_served || 'Missing'}</p>
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 lg:grid-cols-2">
                          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Source and Run</p>
                            <div className="mt-3 space-y-2 text-sm text-slate-200">
                              <p>Source: {detail.source?.source_name || 'Unknown source'}</p>
                              <p>Source Type: {detail.source?.source_type || 'Unknown'}</p>
                              <p>Run ID: {detail.discovery_run?.run_id || detail.raw_record?.run_id || 'None'}</p>
                              <p>Run Status: {detail.discovery_run?.status || 'N/A'}</p>
                            </div>
                          </div>
                          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Review Notes</p>
                            <textarea
                              rows={4}
                              value={rawReviewNotes[record.raw_id] ?? detail.raw_record?.review_notes ?? ''}
                              onChange={(event) => setRawReviewNotes((current) => ({ ...current, [record.raw_id]: event.target.value }))}
                              className="mt-3 w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
                            />
                          </div>
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          {detail.missing_required_fields?.length ? (
                            <span className="inline-flex items-center gap-2 rounded-full border border-red-400/30 bg-red-500/15 px-3 py-2 text-xs text-red-100">
                              <Info className="h-3.5 w-3.5" />
                              Missing required fields: {detail.missing_required_fields.join(', ')}
                            </span>
                          ) : null}
                          {detail.duplicate_candidates?.length ? (
                            <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-500/15 px-3 py-2 text-xs text-amber-100">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              Duplicate candidate must be resolved before normal approval
                            </span>
                          ) : null}
                        </div>

                        <div className="mt-4 flex flex-wrap gap-3">
                          <button
                            onClick={() => approveRawRecord(record.raw_id)}
                            disabled={Boolean(detail.duplicate_candidates?.length) || Boolean(detail.missing_required_fields?.length)}
                            className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <CheckCircle2 className="h-4 w-4" />
                            Approve Into Pending Review
                          </button>
                          {detail.duplicate_candidates?.length ? (
                            <button
                              onClick={() => approveRawRecord(record.raw_id, true)}
                              disabled={Boolean(detail.missing_required_fields?.length)}
                              className="inline-flex items-center gap-2 rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 hover:bg-amber-500/25 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              <AlertTriangle className="h-4 w-4" />
                              Force Approve
                            </button>
                          ) : null}
                          <button
                            onClick={() => rejectRawRecord(record.raw_id)}
                            className="inline-flex items-center gap-2 rounded-2xl border border-red-400/30 bg-red-500/15 px-4 py-3 text-sm font-medium text-red-100 hover:bg-red-500/25"
                          >
                            <XCircle className="h-4 w-4" />
                            Reject Raw Record
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default SoberLivingDirectoryReview
