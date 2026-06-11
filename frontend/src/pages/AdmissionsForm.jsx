import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ClipboardCheck,
  Loader2,
  AlertTriangle,
  Save,
  CheckCircle2,
  XCircle,
  Paperclip,
  Upload,
  Trash2,
  Download,
  ShieldCheck,
  ShieldAlert,
  Shield,
  MessageSquare,
  Calendar,
} from 'lucide-react'
import { apiFetch, apiUrl } from '../api/config'
import AdmissionFormRenderer from '../components/admissions/AdmissionFormRenderer'

// ── Validation ────────────────────────────────────────────────────────────────

function validate(template, responseData) {
  if (!template) return {}
  const errors = {}
  for (const group of template.grouped_fields || []) {
    for (const field of group.fields || []) {
      if (!field.required) continue
      const v = responseData[field.name]
      let invalid = false
      if (field.type === 'checkbox') {
        invalid = !v
      } else if (field.type === 'checkbox_group') {
        invalid = !Array.isArray(v) || v.length === 0
      } else if (field.type === 'yesno') {
        const norm = v === true ? 'yes' : v === false ? 'no' : (v || '')
        invalid = norm !== 'yes' && norm !== 'no'
      } else {
        invalid = v === undefined || v === null || (typeof v === 'string' && v.trim() === '')
      }
      if (invalid) errors[field.name] = `${field.label} is required`
    }
  }
  return errors
}

// ── Attachment panel ──────────────────────────────────────────────────────────

function AttachmentsPanel({ packetId, formKey }) {
  const [attachments, setAttachments] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const fileRef = useRef(null)

  const loadAttachments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiFetch(
        `/api/admissions/packets/${packetId}/forms/${formKey}/attachments`
      )
      if (res.ok) {
        const d = await res.json()
        setAttachments(d.attachments || [])
      }
    } catch {
      // non-fatal
    } finally {
      setLoading(false)
    }
  }, [packetId, formKey])

  useEffect(() => {
    if (packetId && formKey) loadAttachments()
  }, [loadAttachments])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await apiFetch(
        `/api/admissions/packets/${packetId}/forms/${formKey}/attachments`,
        { method: 'POST', body: formData, timeoutMs: 30000 }
      )
      const d = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(d.detail || 'Upload failed')
      setAttachments((prev) => [...prev, d.attachment])
    } catch (err) {
      setUploadError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleDelete = async (id, fileName) => {
    if (!window.confirm(`Remove "${fileName}"?`)) return
    setDeletingId(id)
    try {
      const res = await apiFetch(`/api/admissions/attachments/${id}`, { method: 'DELETE' })
      if (res.ok) {
        setAttachments((prev) => prev.filter((a) => a.id !== id))
      }
    } catch {
      // non-fatal
    } finally {
      setDeletingId(null)
    }
  }

  const handleDownload = async (att) => {
    try {
      const res = await apiFetch(`/api/admissions/attachments/${att.id}/download`, {
        timeoutMs: 30000,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Download failed (${res.status})`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = att.file_name
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 150)
    } catch (err) {
      console.error('[AdmissionsForm] attachment download failed:', err)
      alert(`Could not download "${att.file_name}": ${err.message}`)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/8 bg-white/3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Paperclip className="h-4 w-4 text-sky-400" />
          <h3 className="text-sm font-semibold text-sky-200">Attachments</h3>
          {attachments.length > 0 && (
            <span className="text-xs text-gray-500">({attachments.length})</span>
          )}
        </div>
        <label className={[
          'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs cursor-pointer transition-colors',
          uploading
            ? 'text-gray-500 border border-white/8 bg-white/3 cursor-not-allowed'
            : 'text-gray-300 border border-white/12 bg-white/5 hover:bg-white/10 hover:text-white',
        ].join(' ')}>
          {uploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
          {uploading ? 'Uploading…' : 'Upload'}
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            disabled={uploading}
            accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.tiff,.txt,.csv"
            onChange={handleUpload}
          />
        </label>
      </div>

      <div className="px-5 py-4 space-y-3">
        {uploadError && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300">
            <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
            {uploadError}
            <button onClick={() => setUploadError(null)} className="ml-auto text-red-400">
              <XCircle className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading attachments…
          </div>
        ) : attachments.length === 0 ? (
          <p className="text-xs text-gray-500">No attachments yet. Upload documents, images, or PDFs (max 10 MB).</p>
        ) : (
          attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/4 border border-white/8 hover:bg-white/6 transition-colors"
            >
              <Paperclip className="h-3.5 w-3.5 text-sky-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-200 truncate">{att.file_name}</p>
                <p className="text-xs text-gray-500">
                  {formatSize(att.file_size)}
                  {att.created_at && ` · ${new Date(att.created_at).toLocaleDateString()}`}
                  {att.uploaded_by && ` · ${att.uploaded_by}`}
                </p>
              </div>
              <button
                onClick={() => handleDownload(att)}
                className="p-1 text-gray-500 hover:text-cyan-300 transition-colors flex-shrink-0"
                title="Download"
              >
                <Download className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => handleDelete(att.id, att.file_name)}
                disabled={deletingId === att.id}
                className="p-1 text-gray-600 hover:text-red-400 transition-colors flex-shrink-0 disabled:opacity-40"
                title="Remove"
              >
                {deletingId === att.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Staff review panel ────────────────────────────────────────────────────────

const REVIEW_CONFIG = {
  'Not Reviewed': { icon: Shield, color: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/20' },
  'Needs Correction': { icon: ShieldAlert, color: 'text-amber-300', bg: 'bg-amber-500/10 border-amber-500/20' },
  'Approved': { icon: ShieldCheck, color: 'text-emerald-300', bg: 'bg-emerald-500/10 border-emerald-500/20' },
}

function StaffReviewPanel({ packetId, formKey, initialStatus, initialNotes, onSaved }) {
  const [reviewStatus, setReviewStatus] = useState(initialStatus || 'Not Reviewed')
  const [reviewNotes, setReviewNotes] = useState(initialNotes || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  const cfg = REVIEW_CONFIG[reviewStatus] || REVIEW_CONFIG['Not Reviewed']
  const Icon = cfg.icon

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    setError(null)
    try {
      const res = await apiFetch(
        `/api/admissions/packets/${packetId}/forms/${formKey}/review`,
        {
          method: 'PATCH',
          body: JSON.stringify({ review_status: reviewStatus, review_notes: reviewNotes }),
        }
      )
      const d = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(d.detail || 'Save failed')
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
      if (onSaved) onSaved(d.form)
    } catch (err) {
      setError(err.message || 'Failed to save review')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-white/8 bg-white/3 flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-purple-200">Staff Review</h3>
        <span className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${cfg.bg} ${cfg.color}`}>
          <Icon className="h-3 w-3" />
          {reviewStatus}
        </span>
      </div>

      <div className="px-5 py-4 space-y-4">
        {error && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300">
            <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Status selector */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">Review Status</label>
          <div className="flex flex-wrap gap-2">
            {Object.entries(REVIEW_CONFIG).map(([status, conf]) => {
              const StatusIcon = conf.icon
              return (
                <button
                  key={status}
                  onClick={() => setReviewStatus(status)}
                  className={[
                    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-colors',
                    reviewStatus === status
                      ? `${conf.bg} ${conf.color} font-medium`
                      : 'bg-white/4 border-white/10 text-gray-400 hover:bg-white/8',
                  ].join(' ')}
                >
                  <StatusIcon className="h-3 w-3" />
                  {status}
                </button>
              )
            })}
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            Review Notes <span className="text-gray-600">(internal)</span>
          </label>
          <textarea
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            rows={3}
            placeholder="Observations, corrections needed, or approval notes…"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-purple-500/40 focus:border-purple-500/30 resize-y transition-colors"
          />
        </div>

        {/* Save button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors bg-purple-600/30 border border-purple-500/30 text-purple-200 hover:bg-purple-600/40"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : saved ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {saving ? 'Saving…' : saved ? 'Saved' : 'Save Review'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main form page ────────────────────────────────────────────────────────────

export default function AdmissionsForm() {
  const { client_id, form_key } = useParams()
  const navigate = useNavigate()

  const [packet, setPacket] = useState(null)
  const [template, setTemplate] = useState(null)
  const [responseData, setResponseData] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [validationErrors, setValidationErrors] = useState({})

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [packetRes, templateRes] = await Promise.all([
        apiFetch(`/api/admissions/packets/${client_id}`),
        apiFetch(`/api/admissions/templates/${form_key}`),
      ])

      if (!packetRes.ok) {
        const d = await packetRes.json().catch(() => ({}))
        throw new Error(d.detail || `Failed to load packet (${packetRes.status})`)
      }
      if (!templateRes.ok) {
        const d = await templateRes.json().catch(() => ({}))
        throw new Error(d.detail || `Form template not found: ${form_key}`)
      }

      const packetData = await packetRes.json()
      const templateData = await templateRes.json()
      setPacket(packetData.packet)
      setTemplate(templateData.template)

      const responseRes = await apiFetch(
        `/api/admissions/packets/${packetData.packet.id}/forms/${form_key}/response`
      )
      if (responseRes.ok) {
        const rd = await responseRes.json()
        setResponseData(rd.response?.response_data || {})
      }
    } catch (err) {
      setError(err.message || 'Failed to load form.')
    } finally {
      setLoading(false)
    }
  }, [client_id, form_key])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleFieldChange = (fieldName, val) => {
    setResponseData((prev) => ({ ...prev, [fieldName]: val }))
    if (validationErrors[fieldName]) {
      setValidationErrors((prev) => {
        const next = { ...prev }
        delete next[fieldName]
        return next
      })
    }
  }

  const handleSaveDraft = async () => {
    if (!packet) return
    setSaving(true)
    setSaveSuccess(false)
    setError(null)
    try {
      const res = await apiFetch(
        `/api/admissions/packets/${packet.id}/forms/${form_key}/response`,
        { method: 'PUT', body: JSON.stringify({ response_data: responseData }) }
      )
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Save failed')
      }
      // Bump status to In Progress if still Not Started (also sets started_at on backend)
      const formEntry = packet.forms?.find((f) => f.form_key === form_key)
      if (formEntry?.status === 'Not Started') {
        const statusRes = await apiFetch(
          `/api/admissions/packets/${packet.id}/forms/${form_key}/status`,
          { method: 'PATCH', body: JSON.stringify({ status: 'In Progress' }) }
        )
        if (statusRes.ok) {
          const sd = await statusRes.json()
          // Update local packet forms with started_at
          setPacket((prev) => ({
            ...prev,
            forms: prev.forms.map((f) => f.form_key === form_key ? { ...f, ...sd.form } : f),
          }))
        }
      }
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2500)
    } catch (err) {
      setError(`Save failed: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleMarkComplete = async () => {
    const errors = validate(template, responseData)
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors)
      window.scrollTo({ top: 0, behavior: 'smooth' })
      setError(`${Object.keys(errors).length} required field(s) are missing.`)
      return
    }
    if (!packet) return
    setCompleting(true)
    setError(null)
    try {
      await apiFetch(
        `/api/admissions/packets/${packet.id}/forms/${form_key}/response`,
        { method: 'PUT', body: JSON.stringify({ response_data: responseData }) }
      )
      const formEntry = packet.forms?.find((f) => f.form_key === form_key)
      const nextStatus = formEntry?.requires_signature ? 'Needs Signature' : 'Completed'
      await apiFetch(
        `/api/admissions/packets/${packet.id}/forms/${form_key}/status`,
        { method: 'PATCH', body: JSON.stringify({ status: nextStatus }) }
      )
      navigate(`/admissions/${client_id}`)
    } catch (err) {
      setError(`Could not complete form: ${err.message}`)
    } finally {
      setCompleting(false)
    }
  }

  const handleReviewSaved = (updatedForm) => {
    if (updatedForm) {
      setPacket((prev) => ({
        ...prev,
        forms: prev.forms.map((f) => f.form_key === form_key ? { ...f, ...updatedForm } : f),
      }))
    }
  }

  // ── Loading / error states ─────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-gray-400">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
          <span className="text-sm">Loading form…</span>
        </div>
      </div>
    )
  }

  if (error && !template) {
    return (
      <div className="min-h-screen p-6 flex items-start justify-center pt-24">
        <div className="max-w-md w-full bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-center">
          <AlertTriangle className="h-10 w-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-300 mb-4">{error}</p>
          <Link
            to={`/admissions/${client_id}`}
            className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            ← Back to packet
          </Link>
        </div>
      </div>
    )
  }

  const formEntry = packet?.forms?.find((f) => f.form_key === form_key)
  const reviewCfg = REVIEW_CONFIG[formEntry?.review_status] || REVIEW_CONFIG['Not Reviewed']
  const ReviewIcon = reviewCfg.icon

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Back link */}
        <Link
          to={`/admissions/${client_id}`}
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {packet?.client_name || 'Packet'}
        </Link>

        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25 flex-shrink-0 mt-0.5">
            <ClipboardCheck className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold text-white">{template?.form_name}</h1>
            {template?.description && (
              <p className="text-sm text-gray-400 mt-0.5 leading-relaxed">{template.description}</p>
            )}
            <div className="flex flex-wrap items-center gap-2 mt-2">
              {template?.timing_label && (
                <span className="text-xs text-gray-500">{template.timing_label}</span>
              )}
              {formEntry?.required && (
                <span className="text-xs px-1.5 py-0.5 rounded border bg-rose-500/15 border-rose-500/25 text-rose-300">
                  Required
                </span>
              )}
              {formEntry?.status && (
                <span className="text-xs px-1.5 py-0.5 rounded border bg-white/8 border-white/10 text-gray-300">
                  {formEntry.status}
                </span>
              )}
              {formEntry?.review_status && formEntry.review_status !== 'Not Reviewed' && (
                <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded border ${reviewCfg.bg} ${reviewCfg.color}`}>
                  <ReviewIcon className="h-3 w-3" />
                  {formEntry.review_status}
                </span>
              )}
              {/* Timestamps */}
              {formEntry?.started_at && (
                <span className="inline-flex items-center gap-1 text-xs text-gray-600">
                  <Calendar className="h-3 w-3" />
                  Started {new Date(formEntry.started_at).toLocaleDateString()}
                </span>
              )}
              {formEntry?.completed_at && (
                <span className="text-xs text-emerald-500">
                  Completed {new Date(formEntry.completed_at).toLocaleDateString()}
                </span>
              )}
              {formEntry?.reviewed_at && (
                <span className="text-xs text-blue-500">
                  Reviewed {new Date(formEntry.reviewed_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-300">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 flex-shrink-0">
              <XCircle className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Form body */}
        {template && (
          <AdmissionFormRenderer
            template={template}
            responseData={responseData}
            validationErrors={validationErrors}
            onChange={handleFieldChange}
          />
        )}

        {/* Attachments panel — only for forms that allow attachments */}
        {formEntry?.allow_attachments && packet?.id && (
          <AttachmentsPanel packetId={packet.id} formKey={form_key} />
        )}

        {/* Staff review panel */}
        {packet?.id && (
          <StaffReviewPanel
            packetId={packet.id}
            formKey={form_key}
            initialStatus={formEntry?.review_status || 'Not Reviewed'}
            initialNotes={formEntry?.review_notes || ''}
            onSaved={handleReviewSaved}
          />
        )}

        {/* Actions bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 pb-8">
          <Link
            to={`/admissions/${client_id}`}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm text-gray-400 border border-white/10 hover:border-white/20 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back without saving
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSaveDraft}
              disabled={saving || completing}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-gray-200 border border-white/15 bg-white/5 hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : saveSuccess ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {saving ? 'Saving…' : saveSuccess ? 'Saved' : 'Save Draft'}
            </button>

            <button
              onClick={handleMarkComplete}
              disabled={saving || completing}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm text-white font-medium bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 transition-all"
            >
              {completing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              {completing
                ? 'Completing…'
                : formEntry?.requires_signature
                ? 'Mark Needs Signature'
                : 'Mark Complete'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
