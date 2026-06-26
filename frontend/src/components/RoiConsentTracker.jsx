import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck, ExternalLink, Paperclip, AlertTriangle } from 'lucide-react'
import { apiFetch } from '../api/config'

/**
 * RoiConsentTracker
 *
 * A read-only, workflow-tracking view of a client's ROI / consent documents.
 * It does NOT create or persist any new data — it derives its rows entirely
 * from the existing Admissions packet (GET /api/admissions/packets/:clientId),
 * which already stores per-form status, expiration, revocation, signed dates,
 * and attachment counts.
 *
 * This is a workflow tracker only. It is not legal advice and does not
 * guarantee HIPAA / 42 CFR Part 2 compliance, and it never replaces a signed
 * ROI/consent document or auto-approves a disclosure.
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

  const header = (
    <div className="flex items-center gap-3 mb-2">
      <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
        <ShieldCheck className="h-6 w-6 text-white" />
      </div>
      <h3 className="text-2xl font-bold text-white">ROI / Consent Tracker</h3>
      {hasPacket && (
        <span className="px-3 py-1 bg-emerald-500/20 rounded-full text-emerald-300 text-sm">
          {forms.length} {forms.length === 1 ? 'record' : 'records'}
        </span>
      )}
    </div>
  )

  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-emerald-500/10">
      {header}
      <p className="text-sm text-gray-400 mb-5">
        Releases of information and consents on file from this client's admissions packet, with
        status, expiration, and revocation.
      </p>

      <div className="mb-6">{helper}</div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading consent records…</div>
      ) : !hasPacket || forms.length === 0 ? (
        <div className="text-center py-12 bg-gradient-to-br from-emerald-500/10 to-teal-500/10 rounded-xl border border-emerald-500/20">
          <ShieldCheck className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
          <h4 className="text-lg font-medium text-white mb-2">No ROI / consent records yet</h4>
          <p className="text-emerald-200/80 mb-4 px-6">
            Start or complete an admissions packet to begin tracking releases of information and
            consents for this client.
          </p>
          <Link
            to={`/admissions/${clientId}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-xl font-medium hover:scale-105 transition-all"
          >
            Open Admissions Packet
          </Link>
        </div>
      ) : (
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
      )}
    </div>
  )
}

export default RoiConsentTracker
