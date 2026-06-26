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
} from 'lucide-react'
import { apiFetch } from '../api/config'

/**
 * RoiConsentTracker
 *
 * A workflow-tracking view of a client's ROI / consent documents. It has two
 * distinct, clearly separated sections:
 *
 *  1. Packet consent forms — derived (read-only) from the existing Admissions
 *     packet (GET /api/admissions/packets/:clientId), which already stores
 *     per-form status, expiration, revocation, signed dates, and attachments.
 *
 *  2. Uploaded signed ROIs — actual signed files a case manager uploads as
 *     client documents (doc_type = "roi") via the existing client-documents
 *     API. These are the source of truth and are downloadable. A client can
 *     have many of them (family, spouse, probation/parole, court, provider,
 *     employer, sober living, etc.).
 *
 * This is a workflow tracker only. It is not legal advice and does not
 * guarantee HIPAA / 42 CFR Part 2 compliance, and it never replaces a signed
 * ROI/consent document or auto-approves a disclosure. Uploaded ROI files carry
 * no structured/compliance metadata — they are stored as plain client
 * documents and the signed file itself remains authoritative.
 */

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

// Map the existing persisted form status to a tracker badge.
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

const RoiConsentTracker = ({ clientId }) => {
  const [forms, setForms] = useState([])
  const [sharedProfile, setSharedProfile] = useState({})
  const [loading, setLoading] = useState(true)
  const [hasPacket, setHasPacket] = useState(false)

  // Uploaded signed ROI documents (doc_type = "roi" client documents).
  const [roiDocs, setRoiDocs] = useState([])
  const [docsRefresh, setDocsRefresh] = useState(0)

  // Upload flow state.
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

  const docViewUrl = (doc) => {
    if (doc?.file_path) return `/api/clients/${clientId}/documents/${doc.doc_id}/view`
    if (doc?.url) return doc.url
    return null
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

  const header = (
    <div className="flex items-center gap-3 mb-2">
      <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
        <ShieldCheck className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-2xl font-bold text-white">ROI / Consent Tracker</h3>
      {(hasPacketForms || hasRoiDocs) && (
        <span className="px-3 py-1 bg-emerald-500/20 rounded-full text-emerald-300 text-sm">
          {forms.length + roiDocs.length}{' '}
          {forms.length + roiDocs.length === 1 ? 'record' : 'records'}
        </span>
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

  // ── Uploaded signed ROIs section ────────────────────────────────────────────
  const uploadedSection = (
    <div>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div>
          <h4 className="text-lg font-semibold text-white">Uploaded Signed ROIs</h4>
          <p className="text-xs text-gray-500">Signed ROI files stored as client documents</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setUploadError('')
            setShowUpload((s) => !s)
          }}
          className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-medium hover:scale-105 transition-all text-sm"
        >
          <Upload className="h-4 w-4" />
          Upload Signed ROI
        </button>
      </div>

      <p className="text-xs text-gray-400 mb-3">
        Uploaded ROI files are stored as client documents. Review the signed document before
        disclosing information. This tracker does not guarantee HIPAA or 42 CFR Part 2 compliance.
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
      <p className="text-sm text-gray-400 mb-5">
        Releases of information and consents for this client — packet consent forms from the
        admissions packet, plus signed ROI files uploaded as client documents.
      </p>

      <div className="mb-6">{helper}</div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading consent records…</div>
      ) : !hasPacketForms && !hasRoiDocs ? (
        <div className="text-center py-12 bg-gradient-to-br from-emerald-500/10 to-teal-500/10 rounded-xl border border-emerald-500/20">
          <ShieldCheck className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
          <h4 className="text-lg font-medium text-white mb-2">No ROI / consent records yet</h4>
          <p className="text-emerald-200/80 mb-4 px-6">
            Start or complete an admissions packet, or upload a signed ROI document, to begin
            tracking releases of information and consents for this client.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link
              to={`/admissions/${clientId}`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-medium hover:scale-105 transition-all"
            >
              Open Admissions Packet
            </Link>
            <button
              type="button"
              onClick={() => {
                setUploadError('')
                setShowUpload(true)
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/10 border border-white/20 text-gray-200 rounded-xl font-medium hover:bg-white/15 transition-all"
            >
              <Upload className="h-4 w-4" />
              Upload Signed ROI
            </button>
          </div>
          {showUpload && <div className="mt-6 text-left">{uploadedSection}</div>}
        </div>
      ) : (
        <div className="space-y-8">
          {packetSection}
          {uploadedSection}
        </div>
      )}
    </div>
  )
}

export default RoiConsentTracker
