import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldCheck,
  ExternalLink,
  Paperclip,
  AlertTriangle,
  Upload,
  FileText,
  Download,
  Plus,
  Printer,
  Ban,
  Pencil,
} from 'lucide-react'
import { apiFetch } from '../api/config'

/**
 * RoiConsentTracker — Client ROI / Releases area (dedicated client tab).
 *
 * Three clearly separated layers, most specific first:
 *
 *  1. Client ROI Records — the real ongoing system (Phase 1). Structured,
 *     multiple-per-client release-of-information records backed by
 *     /api/clients/:id/roi-records. Create/list/edit, generate a printable
 *     ROI form, upload a signed copy, revoke (history preserved).
 *
 *  2. Uploaded Signed ROIs — a fallback for scanned/external signed files
 *     stored as plain client documents (doc_type = "roi"). No structured
 *     metadata; the signed file is authoritative.
 *
 *  3. Packet consent forms — read-only status from the single Admissions
 *     packet artifact. Separate from client-level ROI records.
 *
 * Workflow tracker only. It does not guarantee HIPAA / 42 CFR Part 2
 * compliance and does not replace review of the signed authorization.
 */

const COMPLIANCE_NOTICE =
  'This tool supports workflow review only. It does not guarantee HIPAA or 42 CFR Part 2 ' +
  'compliance and does not replace review of the signed authorization.'

const INFO_OPTIONS = [
  'Attendance',
  'Diagnosis',
  'Treatment plan',
  'Progress notes',
  'Medications',
  'Drug test results',
  'Billing information',
  'Discharge summary',
  'Other',
]

const PURPOSE_OPTIONS = [
  'Continuity of care',
  'Insurance/payment',
  'Court/legal',
  'Probation/parole',
  'Family involvement',
  'Other',
]

const RELATIONSHIP_OPTIONS = [
  'Family',
  'Spouse',
  'Probation/parole',
  'Court',
  'Provider',
  'Employer',
  'Sober living',
  'Insurance',
  'Other',
]

const METHOD_OPTIONS = ['Verbal', 'Paper copy', 'Fax', 'Secure email/portal', 'Other']

// Structured ROI record status → badge. Status is derived server-side.
const ROI_STATUS_META = {
  draft: { label: 'Draft', cls: 'bg-gray-500/20 text-gray-300 border-gray-500/40' },
  needs_signature: {
    label: 'Needs signature',
    cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  },
  active: { label: 'Active', cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  expired: { label: 'Expired', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
  revoked: { label: 'Revoked', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
}

const roiStatusMeta = (status) =>
  ROI_STATUS_META[status] || {
    label: status || 'Unknown',
    cls: 'bg-gray-500/20 text-gray-300 border-gray-500/40',
  }

// Display "type" derived from the form's stable key (structured data, not free text).
const TYPE_BY_KEY = {
  roi: 'ROI',
  hipaa_npp: 'Privacy notice',
  treatment_consent: 'Treatment consent',
  telehealth_consent: 'Telehealth/media consent',
  personal_rights: 'Other consent',
  program_rules: 'Other consent',
}

const deriveType = (formKey = '') => {
  if (TYPE_BY_KEY[formKey]) return TYPE_BY_KEY[formKey]
  const key = String(formKey).toLowerCase()
  if (key.includes('roi') || key.includes('release')) return 'ROI'
  if (key.includes('hipaa') || key.includes('npp') || key.includes('privacy')) return 'Privacy notice'
  if (key.includes('telehealth') || key.includes('media')) return 'Telehealth/media consent'
  if (key.includes('treatment')) return 'Treatment consent'
  return 'Other consent'
}

// Map the existing persisted packet form status to a tracker badge.
const STATUS_META = {
  Completed: { label: 'Active', cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' },
  'Not Started': { label: 'Missing', cls: 'bg-gray-500/20 text-gray-300 border-gray-500/40' },
  Expired: { label: 'Expired', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
  Revoked: { label: 'Revoked', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
  'Needs Signature': { label: 'Pending signature', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  'In Progress': { label: 'In progress', cls: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
  'Missing Attachment': { label: 'Missing attachment', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
  'Staff Review Needed': { label: 'Staff review needed', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
}

const statusMeta = (status) =>
  STATUS_META[status] || { label: status || 'Unknown', cls: 'bg-gray-500/20 text-gray-300 border-gray-500/40' }

const isConsentForm = (form) =>
  String(form?.category || '').toLowerCase().includes('consent')

const isRoiDoc = (doc) =>
  String(doc?.doc_type || '').toLowerCase() === 'roi'

const formatDate = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

const isPastDate = (value) => {
  if (!value) return false
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return false
  return d.getTime() < Date.now()
}

const EMPTY_ROI_FORM = {
  authorized_party: '',
  relationship_type: '',
  party_address: '',
  party_contact: '',
  purpose: '',
  info_to_release: [],
  release_method: '',
  effective_date: '',
  expiration_date: '',
  revocable: true,
}

const RoiConsentTracker = ({ clientId, onRoiRecordsChange }) => {
  const [forms, setForms] = useState([])
  const [sharedProfile, setSharedProfile] = useState({})
  const [loading, setLoading] = useState(true)
  const [hasPacket, setHasPacket] = useState(false)

  // Uploaded signed ROI documents (doc_type = "roi" client documents).
  const [roiDocs, setRoiDocs] = useState([])
  const [docsRefresh, setDocsRefresh] = useState(0)

  // Structured client ROI records (the real ongoing system).
  const [roiRecords, setRoiRecords] = useState([])
  const [recordsLoading, setRecordsLoading] = useState(true)
  const [recordsRefresh, setRecordsRefresh] = useState(0)
  const [showRoiForm, setShowRoiForm] = useState(false)
  const [editingRoiId, setEditingRoiId] = useState(null)
  const [roiForm, setRoiForm] = useState(EMPTY_ROI_FORM)
  const [savingRoi, setSavingRoi] = useState(false)
  const [roiError, setRoiError] = useState('')
  const [busyRoiId, setBusyRoiId] = useState(null)

  // Upload flow state (uploaded signed ROIs fallback).
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadParty, setUploadParty] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  // Load packet-derived consent forms.
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      if (!clientId) return
      setLoading(true)
      try {
        const res = await apiFetch(`/api/admissions/packets/${clientId}`)
        if (!res.ok) {
          if (!cancelled) {
            setHasPacket(false)
            setForms([])
          }
          return
        }
        const data = await res.json()
        const packet = data?.packet
        if (!cancelled) {
          setHasPacket(Boolean(packet))
          setForms((packet?.forms || []).filter(isConsentForm))
          setSharedProfile(packet?.shared_profile || {})
        }
      } catch (e) {
        if (!cancelled) {
          setHasPacket(false)
          setForms([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [clientId])

  // Load uploaded signed ROI documents from the existing client-documents store.
  useEffect(() => {
    let cancelled = false
    const loadDocs = async () => {
      if (!clientId) return
      try {
        const res = await apiFetch(`/api/clients/${clientId}/documents`)
        if (!res.ok) return
        const data = await res.json()
        if (cancelled) return
        setRoiDocs((data?.documents || []).filter(isRoiDoc))
      } catch (e) {
        // Uploaded ROIs are optional; the tracker still works from packet data.
      }
    }
    loadDocs()
    return () => {
      cancelled = true
    }
  }, [clientId, docsRefresh])

  // Load structured client ROI records.
  useEffect(() => {
    let cancelled = false
    const loadRecords = async () => {
      if (!clientId) return
      setRecordsLoading(true)
      try {
        const res = await apiFetch(`/api/clients/${clientId}/roi-records`)
        if (!res.ok) {
          if (!cancelled) setRoiRecords([])
          return
        }
        const data = await res.json()
        if (!cancelled) setRoiRecords(data?.roi_records || [])
      } catch (e) {
        if (!cancelled) setRoiRecords([])
      } finally {
        if (!cancelled) setRecordsLoading(false)
      }
    }
    loadRecords()
    return () => {
      cancelled = true
    }
  }, [clientId, recordsRefresh])

  useEffect(() => {
    if (typeof onRoiRecordsChange === 'function') {
      onRoiRecordsChange(roiRecords)
    }
  }, [onRoiRecordsChange, roiRecords])

  const docViewUrl = (doc) => {
    if (doc?.file_path) return `/api/clients/${clientId}/documents/${doc.doc_id}/view`
    if (doc?.url) return doc.url
    return null
  }

  const linkedDocUrl = (record) =>
    record?.linked_document_id
      ? `/api/clients/${clientId}/documents/${record.linked_document_id}/view`
      : null

  // ── ROI record handlers ─────────────────────────────────────────────────────
  const openCreateForm = () => {
    setEditingRoiId(null)
    setRoiForm(EMPTY_ROI_FORM)
    setRoiError('')
    setShowRoiForm(true)
  }

  const openEditForm = (record) => {
    setEditingRoiId(record.roi_id)
    setRoiForm({
      authorized_party: record.authorized_party || '',
      relationship_type: record.relationship_type || '',
      party_address: record.party_address || '',
      party_contact: record.party_contact || '',
      purpose: record.purpose || '',
      info_to_release: Array.isArray(record.info_to_release) ? record.info_to_release : [],
      release_method: record.release_method || '',
      effective_date: record.effective_date || '',
      expiration_date: record.expiration_date || '',
      revocable: record.revocable !== false,
    })
    setRoiError('')
    setShowRoiForm(true)
  }

  const closeForm = () => {
    setShowRoiForm(false)
    setEditingRoiId(null)
    setRoiForm(EMPTY_ROI_FORM)
    setRoiError('')
  }

  const toggleInfo = (option) => {
    setRoiForm((prev) => {
      const has = prev.info_to_release.includes(option)
      return {
        ...prev,
        info_to_release: has
          ? prev.info_to_release.filter((o) => o !== option)
          : [...prev.info_to_release, option],
      }
    })
  }

  const handleSaveRoi = async () => {
    if (!roiForm.authorized_party.trim()) {
      setRoiError('Authorized party is required.')
      return
    }
    setSavingRoi(true)
    setRoiError('')
    try {
      const url = editingRoiId
        ? `/api/clients/${clientId}/roi-records/${editingRoiId}`
        : `/api/clients/${clientId}/roi-records`
      const res = await apiFetch(url, {
        method: editingRoiId ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(roiForm),
      })
      if (!res.ok) throw new Error('save failed')
      closeForm()
      setRecordsRefresh((n) => n + 1)
    } catch (e) {
      setRoiError('Could not save ROI record. Please try again.')
    } finally {
      setSavingRoi(false)
    }
  }

  const handleRevoke = async (record) => {
    setBusyRoiId(record.roi_id)
    try {
      const res = await apiFetch(`/api/clients/${clientId}/roi-records/${record.roi_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ revoked: true }),
      })
      if (res.ok) setRecordsRefresh((n) => n + 1)
    } catch (e) {
      // Non-fatal; the list reload would surface the unchanged state.
    } finally {
      setBusyRoiId(null)
    }
  }

  const handleGenerate = async (record) => {
    setBusyRoiId(record.roi_id)
    try {
      const res = await apiFetch(
        `/api/clients/${clientId}/roi-records/${record.roi_id}/generate-document`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error('generate failed')
      const data = await res.json()
      setRecordsRefresh((n) => n + 1)
      setDocsRefresh((n) => n + 1)
      if (data?.view_url && typeof window !== 'undefined') {
        window.open(data.view_url, '_blank', 'noopener,noreferrer')
      }
    } catch (e) {
      // Non-fatal; surface nothing destructive.
    } finally {
      setBusyRoiId(null)
    }
  }

  const handleUploadSigned = async (record, file) => {
    if (!file) return
    setBusyRoiId(record.roi_id)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await apiFetch(
        `/api/clients/${clientId}/roi-records/${record.roi_id}/upload-signed-document`,
        { method: 'POST', body: fd }
      )
      if (res.ok) {
        setRecordsRefresh((n) => n + 1)
        setDocsRefresh((n) => n + 1)
      }
    } catch (e) {
      // Non-fatal.
    } finally {
      setBusyRoiId(null)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) {
      setUploadError('Choose a signed ROI file to upload.')
      return
    }
    setUploading(true)
    setUploadError('')
    try {
      const party = uploadParty.trim()
      const title = `ROI — ${party || uploadFile.name}`
      const fd = new FormData()
      fd.append('title', title)
      fd.append('doc_type', 'roi')
      fd.append('file', uploadFile)
      const res = await apiFetch(`/api/clients/${clientId}/documents`, {
        method: 'POST',
        body: fd,
      })
      if (!res.ok) throw new Error('upload failed')
      setShowUpload(false)
      setUploadFile(null)
      setUploadParty('')
      setDocsRefresh((n) => n + 1)
    } catch (e) {
      setUploadError('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const helper = (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-300 shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="text-amber-100 font-medium">
            Review active ROI/consent status before disclosing client information to courts,
            probation, family, employers, providers, or other collateral contacts.
          </p>
          <p className="text-amber-200/70 mt-1">
            This is a workflow tracker, not legal advice or a guarantee of HIPAA / 42 CFR Part 2
            compliance. It does not replace a signed ROI/consent document or approve any disclosure.
          </p>
        </div>
      </div>
    </div>
  )

  const hasPacketForms = hasPacket && forms.length > 0
  const hasRoiDocs = roiDocs.length > 0
  const hasRoiRecords = roiRecords.length > 0

  const header = (
    <div className="flex items-center gap-3 mb-2">
      <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
        <ShieldCheck className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-2xl font-bold text-white">ROI / Releases</h3>
      {hasRoiRecords && (
        <span className="px-3 py-1 bg-emerald-500/20 rounded-full text-emerald-300 text-sm">
          {roiRecords.length} {roiRecords.length === 1 ? 'record' : 'records'}
        </span>
      )}
    </div>
  )

  // ── ROI record create/edit form ─────────────────────────────────────────────
  const roiFormBlock = (
    <div className="mb-5 p-5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-4">
      <div className="flex items-center justify-between">
        <h5 className="text-base font-semibold text-white">
          {editingRoiId ? 'Edit ROI record' : 'New ROI record'}
        </h5>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-300 mb-1">Authorized party *</label>
          <input
            type="text"
            aria-label="Authorized party"
            value={roiForm.authorized_party}
            onChange={(e) => setRoiForm((p) => ({ ...p, authorized_party: e.target.value }))}
            placeholder="e.g. County Probation, Mother (Jane Doe), Employer"
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/60"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Relationship type</label>
          <select
            aria-label="Relationship type"
            value={roiForm.relationship_type}
            onChange={(e) => setRoiForm((p) => ({ ...p, relationship_type: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500/60"
          >
            <option value="" className="bg-slate-800 text-white">
              Select…
            </option>
            {RELATIONSHIP_OPTIONS.map((o) => (
              <option key={o} value={o} className="bg-slate-800 text-white">
                {o}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Address</label>
          <textarea
            aria-label="Party address"
            value={roiForm.party_address}
            onChange={(e) => setRoiForm((p) => ({ ...p, party_address: e.target.value }))}
            rows={2}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/60"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Contact (phone / email)</label>
          <input
            type="text"
            aria-label="Party contact"
            value={roiForm.party_contact}
            onChange={(e) => setRoiForm((p) => ({ ...p, party_contact: e.target.value }))}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/60"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Purpose</label>
          <select
            aria-label="Purpose"
            value={roiForm.purpose}
            onChange={(e) => setRoiForm((p) => ({ ...p, purpose: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500/60"
          >
            <option value="" className="bg-slate-800 text-white">
              Select…
            </option>
            {PURPOSE_OPTIONS.map((o) => (
              <option key={o} value={o} className="bg-slate-800 text-white">
                {o}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Method of release</label>
          <select
            aria-label="Release method"
            value={roiForm.release_method}
            onChange={(e) => setRoiForm((p) => ({ ...p, release_method: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500/60"
          >
            <option value="" className="bg-slate-800 text-white">
              Select…
            </option>
            {METHOD_OPTIONS.map((o) => (
              <option key={o} value={o} className="bg-slate-800 text-white">
                {o}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Effective date</label>
          <input
            type="date"
            aria-label="Effective date"
            value={roiForm.effective_date}
            onChange={(e) => setRoiForm((p) => ({ ...p, effective_date: e.target.value }))}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500/60"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-300 mb-1">Expiration date</label>
          <input
            type="date"
            aria-label="Expiration date"
            value={roiForm.expiration_date}
            onChange={(e) => setRoiForm((p) => ({ ...p, expiration_date: e.target.value }))}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500/60"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-300 mb-2">Information to release</label>
        <div className="flex flex-wrap gap-2">
          {INFO_OPTIONS.map((option) => {
            const active = roiForm.info_to_release.includes(option)
            return (
              <button
                key={option}
                type="button"
                onClick={() => toggleInfo(option)}
                className={`px-3 py-1.5 rounded-full text-xs border transition-all ${
                  active
                    ? 'bg-emerald-500/20 text-emerald-200 border-emerald-500/50'
                    : 'bg-white/5 text-gray-300 border-white/15 hover:border-white/30'
                }`}
              >
                {option}
              </button>
            )
          })}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-200">
        <input
          type="checkbox"
          checked={roiForm.revocable}
          onChange={(e) => setRoiForm((p) => ({ ...p, revocable: e.target.checked }))}
          className="h-4 w-4 rounded border-white/30 bg-white/10"
        />
        Revocable in writing
      </label>

      {roiError && <p className="text-sm text-red-300">{roiError}</p>}

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSaveRoi}
          disabled={savingRoi}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {savingRoi ? 'Saving…' : editingRoiId ? 'Save changes' : 'Create ROI record'}
        </button>
        <button
          type="button"
          onClick={closeForm}
          className="px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-sm hover:bg-white/15"
        >
          Cancel
        </button>
      </div>
    </div>
  )

  // ── Client ROI records section (primary) ────────────────────────────────────
  const recordsSection = (
    <div>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <h4 className="text-lg font-semibold text-white">Client ROI Records</h4>
          <p className="text-xs text-gray-500">
            Structured releases of information — many per client (family, probation, court,
            providers, employers, sober living, insurance, etc.)
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateForm}
          className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-medium hover:scale-105 transition-all text-sm"
        >
          <Plus className="h-4 w-4" />
          Create New ROI
        </button>
      </div>

      {showRoiForm && roiFormBlock}

      {recordsLoading ? (
        <div className="p-4 text-sm text-gray-400">Loading ROI records…</div>
      ) : hasRoiRecords ? (
        <div className="grid grid-cols-1 gap-4">
          {roiRecords.map((record) => {
            const meta = roiStatusMeta(record.status)
            const linkUrl = linkedDocUrl(record)
            const info = Array.isArray(record.info_to_release) ? record.info_to_release : []
            const busy = busyRoiId === record.roi_id
            const canRevoke =
              record.revocable !== false && !record.revoked && record.status !== 'revoked'
            return (
              <div
                key={record.roi_id}
                className="p-5 bg-gradient-to-br from-white/10 to-white/5 rounded-xl border border-white/15 hover:border-emerald-500/40 transition-all"
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-white truncate">
                        {record.authorized_party || 'Authorized party'}
                      </h4>
                      {record.relationship_type && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-white/10 text-gray-300 border border-white/15">
                          {record.relationship_type}
                        </span>
                      )}
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${meta.cls}`}>
                        {meta.label}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-x-6 gap-y-1 mt-2 text-xs text-gray-400">
                      {record.purpose && (
                        <span>
                          <span className="text-gray-500">Purpose:</span> {record.purpose}
                        </span>
                      )}
                      {record.release_method && (
                        <span>
                          <span className="text-gray-500">Method:</span> {record.release_method}
                        </span>
                      )}
                      {record.effective_date && (
                        <span>Effective: {formatDate(record.effective_date)}</span>
                      )}
                      {record.expiration_date && (
                        <span className={isPastDate(record.expiration_date) ? 'text-amber-300' : ''}>
                          Expires: {formatDate(record.expiration_date)}
                        </span>
                      )}
                      <span>Revocable: {record.revocable !== false ? 'Yes' : 'No'}</span>
                      {record.revoked && <span className="text-red-300">Revoked: Yes</span>}
                    </div>

                    {info.length > 0 && (
                      <p className="text-xs text-gray-400 mt-2">
                        <span className="text-gray-500">Information scope:</span> {info.join(', ')}
                      </p>
                    )}

                    {linkUrl && (
                      <a
                        href={linkUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 mt-3 text-sm text-emerald-300 hover:underline"
                      >
                        <Download className="h-4 w-4" />
                        View linked document
                      </a>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 mt-4">
                  <button
                    type="button"
                    onClick={() => openEditForm(record)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-xs hover:bg-white/15"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Open / Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGenerate(record)}
                    disabled={busy}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-xs hover:bg-emerald-500/20 hover:text-emerald-200 disabled:opacity-50"
                  >
                    <Printer className="h-3.5 w-3.5" />
                    Generate Printable ROI Form
                  </button>
                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-xs hover:bg-white/15 cursor-pointer">
                    <Upload className="h-3.5 w-3.5" />
                    Upload Signed Copy
                    <input
                      type="file"
                      aria-label={`Upload signed copy for ${record.authorized_party || 'ROI'}`}
                      className="hidden"
                      disabled={busy}
                      onChange={(e) => handleUploadSigned(record, e.target.files?.[0] || null)}
                    />
                  </label>
                  {canRevoke && (
                    <button
                      type="button"
                      onClick={() => handleRevoke(record)}
                      disabled={busy}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 border border-red-500/30 text-red-300 rounded-lg text-xs hover:bg-red-500/20 disabled:opacity-50"
                    >
                      <Ban className="h-3.5 w-3.5" />
                      Revoke
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-white/10 bg-white/5 text-sm text-gray-400">
          No structured ROI records yet. Use “Create New ROI” to add a release of information for
          family, spouse, probation/parole, court, providers, employers, sober living, insurance,
          or other collateral contacts.
        </div>
      )}
    </div>
  )

  // ── Packet consent forms section ────────────────────────────────────────────
  const packetSection = (
    <div>
      <div className="flex items-center justify-between gap-3 mb-3">
        <h4 className="text-lg font-semibold text-white">Packet consent forms</h4>
        <span className="text-xs text-gray-500">From the Admissions packet</span>
      </div>
      {hasPacketForms ? (
        <div className="grid grid-cols-1 gap-4">
          {forms.map((form) => {
            const meta = statusMeta(form.status)
            const type = deriveType(form.form_key)
            const signedDate = formatDate(form.completed_at || form.signed_at)
            const expDate = formatDate(form.expires_at)
            const expiredFlag =
              isPastDate(form.expires_at) && !['Expired', 'Revoked'].includes(form.status)
            const recipient =
              type === 'ROI' ? String(sharedProfile?.roi_contact_name || '').trim() : ''
            const hasAttachment = Number(form.attachment_count || 0) > 0
            return (
              <div
                key={form.form_key}
                className="p-5 bg-gradient-to-br from-white/10 to-white/5 rounded-xl border border-white/15 hover:border-emerald-500/40 transition-all"
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-white truncate">{form.form_name}</h4>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-white/10 text-gray-300 border border-white/15">
                        {type}
                      </span>
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${meta.cls}`}>
                        {meta.label}
                      </span>
                    </div>

                    {recipient && (
                      <p className="text-sm text-gray-300 mt-2">
                        <span className="text-gray-500">Authorized party:</span> {recipient}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-x-6 gap-y-1 mt-2 text-xs text-gray-400">
                      <span>Source: Admissions packet</span>
                      <span>Revocable: {form.allow_revocation ? 'Yes' : 'No'}</span>
                      {form.status === 'Revoked' && <span className="text-red-300">Revoked: Yes</span>}
                      {signedDate && <span>Signed/completed: {signedDate}</span>}
                      {expDate && (
                        <span className={expiredFlag ? 'text-amber-300' : ''}>
                          Expires: {expDate}
                          {expiredFlag ? ' (past expiration date)' : ''}
                        </span>
                      )}
                      {hasAttachment && (
                        <span className="inline-flex items-center gap-1 text-emerald-300">
                          <Paperclip className="h-3 w-3" /> Attachment on file
                        </span>
                      )}
                    </div>
                  </div>

                  <Link
                    to={`/admissions/${clientId}/forms/${form.form_key}`}
                    className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-xl hover:bg-emerald-500/20 hover:text-emerald-200 transition-all text-sm"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Open
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-white/10 bg-white/5 text-sm text-gray-400">
          No admissions-packet consent forms on file for this client yet.{' '}
          <Link to={`/admissions/${clientId}`} className="text-emerald-300 hover:underline">
            Open Admissions Packet
          </Link>
        </div>
      )}
    </div>
  )

  // ── Uploaded signed ROIs section (fallback) ─────────────────────────────────
  const uploadedSection = (
    <div>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <h4 className="text-lg font-semibold text-white">Uploaded Signed ROIs</h4>
          <p className="text-xs text-gray-500">
            Fallback for scanned/external signed files stored as client documents
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setUploadError('')
            setShowUpload((s) => !s)
          }}
          className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-xl font-medium hover:bg-white/15 transition-all text-sm"
        >
          <Upload className="h-4 w-4" />
          Upload Signed ROI
        </button>
      </div>

      <p className="text-xs text-gray-400 mb-3">
        Uploaded ROI files are stored as client documents and carry no structured status,
        expiration, or revocation. Review the signed document before disclosing information. This
        tracker does not guarantee HIPAA or 42 CFR Part 2 compliance.
      </p>

      {showUpload && (
        <div className="mb-4 p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-3">
          <div>
            <label className="block text-xs text-gray-300 mb-1">
              Authorized party / label (optional)
            </label>
            <input
              type="text"
              value={uploadParty}
              onChange={(e) => setUploadParty(e.target.value)}
              placeholder="e.g. County Probation, Mother (Jane Doe), Employer"
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/60"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-300 mb-1">Signed ROI file</label>
            <input
              type="file"
              aria-label="Signed ROI file"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white hover:file:bg-emerald-500"
            />
          </div>
          {uploadError && <p className="text-sm text-red-300">{uploadError}</p>}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleUpload}
              disabled={uploading}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {uploading ? 'Uploading…' : 'Upload signed ROI document'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowUpload(false)
                setUploadError('')
              }}
              className="px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-lg text-sm hover:bg-white/15"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {hasRoiDocs ? (
        <div className="grid grid-cols-1 gap-4">
          {roiDocs.map((doc) => {
            const viewUrl = docViewUrl(doc)
            const created = formatDate(doc.created_at)
            return (
              <div
                key={doc.doc_id}
                className="p-5 bg-gradient-to-br from-white/10 to-white/5 rounded-xl border border-white/15 hover:border-emerald-500/40 transition-all"
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-white truncate">{doc.title || 'Signed ROI'}</h4>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                        Signed ROI document
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-6 gap-y-1 mt-2 text-xs text-gray-400">
                      <span>Source: Client document</span>
                      {doc.file_name && (
                        <span className="inline-flex items-center gap-1">
                          <FileText className="h-3 w-3" /> {doc.file_name}
                        </span>
                      )}
                      {created && <span>Uploaded: {created}</span>}
                    </div>
                  </div>

                  {viewUrl ? (
                    <a
                      href={viewUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-white/10 border border-white/20 text-gray-200 rounded-xl hover:bg-emerald-500/20 hover:text-emerald-200 transition-all text-sm"
                    >
                      <Download className="h-4 w-4" />
                      Download Signed ROI
                    </a>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="p-4 rounded-xl border border-white/10 bg-white/5 text-sm text-gray-400">
          No uploaded signed ROIs yet. Use “Upload Signed ROI” to add a signed release of
          information file (family, spouse, probation/parole, court, provider, employer, sober
          living, etc.).
        </div>
      )}
    </div>
  )

  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-emerald-500/10">
      {header}
      <p className="text-sm text-gray-400 mb-3">
        Releases of information and consents for this client — structured ROI records (the ongoing
        system), plus a signed-file upload fallback and read-only admissions-packet consent status.
      </p>
      <p className="text-xs text-gray-500 mb-5">{COMPLIANCE_NOTICE}</p>

      <div className="mb-6">{helper}</div>

      <div className="space-y-8">
        {recordsSection}
        {loading ? (
          <div className="text-center py-8 text-gray-400">Loading consent records…</div>
        ) : (
          <>
            {packetSection}
            {uploadedSection}
          </>
        )}
      </div>
    </div>
  )
}

export default RoiConsentTracker
