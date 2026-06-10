import { useState, useEffect } from 'react'
import {
  DollarSign, ShieldCheck, ArrowLeftRight, CreditCard,
  FileText, LogOut, ChevronDown, Loader2, CheckCircle2,
  AlertTriangle, Save,
} from 'lucide-react'
import { apiFetch } from '../../api/config'

// ── Shared input styles ───────────────────────────────────────────────────────

const baseInput = [
  'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white',
  'placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-cyan-500/50',
  'focus:border-cyan-500/40 transition-colors [color-scheme:dark]',
].join(' ')

// ── Sub-components ────────────────────────────────────────────────────────────

function FieldLabel({ children }) {
  return (
    <label className="block text-xs font-medium text-gray-400 mb-1">{children}</label>
  )
}

function SectionCard({ title, icon: Icon, open, onToggle, children }) {
  return (
    <div className="border border-white/8 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 text-cyan-400" />
          <span className="text-sm font-medium text-gray-200">{title}</span>
        </div>
        <ChevronDown
          className={`h-3.5 w-3.5 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-3 space-y-3 border-t border-white/8 bg-white/2">
          {children}
        </div>
      )}
    </div>
  )
}

function Sel({ label, value, onChange, options }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className={baseInput + ' appearance-none'}
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </div>
  )
}

function Txt({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={baseInput}
      />
    </div>
  )
}

function Area({ label, value, onChange, placeholder, rows = 2 }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <textarea
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={baseInput + ' resize-y min-h-[60px]'}
      />
    </div>
  )
}

function Chk({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={!!checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-600 bg-white/10 text-cyan-500 focus:ring-cyan-500/30 cursor-pointer"
      />
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function FinancialCoordinationPanel({ clientId }) {
  const [form, setForm] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedFlash, setSavedFlash] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [saveError, setSaveError] = useState(null)
  const [collapsed, setCollapsed] = useState(true)
  const [open, setOpen] = useState({
    billing: true,
    insurance: false,
    cob: false,
    payment: false,
    std_fmla: false,
    discharge: false,
  })

  useEffect(() => {
    if (!clientId) return
    setLoading(true)
    apiFetch(`/api/admissions/packets/${clientId}/financial-coordination`)
      .then((r) => r.json())
      .then((d) => setForm(d.financial_coordination || {}))
      .catch(() => setLoadError('Failed to load financial coordination data.'))
      .finally(() => setLoading(false))
  }, [clientId])

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const tog = (key) => setOpen((prev) => ({ ...prev, [key]: !prev[key] }))

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      const res = await apiFetch(
        `/api/admissions/packets/${clientId}/financial-coordination`,
        { method: 'PUT', body: JSON.stringify(form) }
      )
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || 'Save failed')
      }
      const d = await res.json()
      setForm(d.financial_coordination || form)
      setSavedFlash(true)
      setTimeout(() => setSavedFlash(false), 2000)
    } catch (e) {
      setSaveError(e.message || 'Failed to save.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/3 overflow-hidden">
      {/* Panel header */}
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/4 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <DollarSign className="h-4 w-4 text-cyan-400" />
          <span className="text-sm font-semibold text-white">Financial Coordination</span>
          <span className="text-xs text-gray-600 hidden sm:inline">
            Billing · Insurance · COB · Payment · STD/FMLA · Discharge
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
        />
      </button>

      {!collapsed && (
        <div className="px-5 pb-5 border-t border-white/8 pt-4 space-y-3">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Loading…
            </div>
          ) : loadError ? (
            <div className="flex items-center gap-2 text-xs text-red-400 py-2">
              <AlertTriangle className="h-3.5 w-3.5" />
              {loadError}
            </div>
          ) : (
            <>
              {/* A. Billing Explanation */}
              <SectionCard
                title="Billing Explanation"
                icon={DollarSign}
                open={open.billing}
                onToggle={() => tog('billing')}
              >
                <Sel
                  label="Billing explained to client"
                  value={form.billing_explained_status}
                  onChange={(v) => set('billing_explained_status', v)}
                  options={[
                    ['Not Started', 'Not Started'],
                    ['Explained', 'Explained'],
                    ['Needs Follow-up', 'Needs Follow-up'],
                  ]}
                />
                <Txt
                  label="Date explained"
                  value={form.billing_explained_date}
                  onChange={(v) => set('billing_explained_date', v)}
                  type="date"
                />
                <Area
                  label="Notes"
                  value={form.billing_notes}
                  onChange={(v) => set('billing_notes', v)}
                  placeholder="Billing explanation notes…"
                />
              </SectionCard>

              {/* B. Insurance Verification */}
              <SectionCard
                title="Insurance Verification"
                icon={ShieldCheck}
                open={open.insurance}
                onToggle={() => tog('insurance')}
              >
                <Sel
                  label="Verification status"
                  value={form.insurance_verification_status}
                  onChange={(v) => set('insurance_verification_status', v)}
                  options={[
                    ['Not Started', 'Not Started'],
                    ['Pending', 'Pending'],
                    ['Verified', 'Verified'],
                    ['Issue Found', 'Issue Found'],
                  ]}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Txt label="Payer type" value={form.primary_payer_type} onChange={(v) => set('primary_payer_type', v)} placeholder="Medi-Cal, Medicare…" />
                  <Txt label="Plan name" value={form.primary_plan_name} onChange={(v) => set('primary_plan_name', v)} placeholder="Plan name" />
                  <Txt label="Member ID" value={form.primary_member_id} onChange={(v) => set('primary_member_id', v)} placeholder="Member ID" />
                  <Txt label="Verification date" value={form.verification_date} onChange={(v) => set('verification_date', v)} type="date" />
                  <Txt label="Rep name" value={form.verification_rep_name} onChange={(v) => set('verification_rep_name', v)} placeholder="Rep name" />
                  <Txt label="Reference number" value={form.verification_reference_number} onChange={(v) => set('verification_reference_number', v)} placeholder="Ref #" />
                  <Txt label="Deductible" value={form.deductible} onChange={(v) => set('deductible', v)} placeholder="$" />
                  <Txt label="Copay" value={form.copay} onChange={(v) => set('copay', v)} placeholder="$" />
                  <Txt label="Coinsurance" value={form.coinsurance} onChange={(v) => set('coinsurance', v)} placeholder="%" />
                  <Txt label="Out-of-pocket max" value={form.out_of_pocket_max} onChange={(v) => set('out_of_pocket_max', v)} placeholder="$" />
                </div>
                <Sel
                  label="Prior authorization required"
                  value={form.auth_required}
                  onChange={(v) => set('auth_required', v)}
                  options={[
                    ['Unknown', 'Unknown'],
                    ['Yes', 'Yes'],
                    ['No', 'No'],
                    ['Pending', 'Pending'],
                  ]}
                />
              </SectionCard>

              {/* C. COB */}
              <SectionCard
                title="Coordination of Benefits (COB)"
                icon={ArrowLeftRight}
                open={open.cob}
                onToggle={() => tog('cob')}
              >
                <Sel
                  label="COB status"
                  value={form.cob_status}
                  onChange={(v) => set('cob_status', v)}
                  options={[
                    ['Not Needed', 'Not Needed'],
                    ['Needs Review', 'Needs Review'],
                    ['Client Must Call', 'Client Must Call'],
                    ['Pending', 'Pending'],
                    ['Resolved', 'Resolved'],
                  ]}
                />
                <div className="space-y-2 pt-1">
                  <Chk label="COB issue identified" checked={form.cob_issue_identified} onChange={(v) => set('cob_issue_identified', v)} />
                  <Chk label="Follow-up needed" checked={form.cob_followup_needed} onChange={(v) => set('cob_followup_needed', v)} />
                </div>
                <Area label="Notes" value={form.cob_notes} onChange={(v) => set('cob_notes', v)} placeholder="COB details…" />
              </SectionCard>

              {/* D. Payment Plan */}
              <SectionCard
                title="Payment Plan"
                icon={CreditCard}
                open={open.payment}
                onToggle={() => tog('payment')}
              >
                <Sel
                  label="Payment plan status"
                  value={form.payment_plan_status}
                  onChange={(v) => set('payment_plan_status', v)}
                  options={[
                    ['Not Needed', 'Not Needed'],
                    ['Needed', 'Needed'],
                    ['Pending', 'Pending'],
                    ['Active', 'Active'],
                    ['Completed', 'Completed'],
                    ['Escalated', 'Escalated'],
                  ]}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Txt label="Arrangement type" value={form.payment_arrangement_type} onChange={(v) => set('payment_arrangement_type', v)} placeholder="Self-pay, installment…" />
                  <Txt label="Amount" value={form.payment_amount} onChange={(v) => set('payment_amount', v)} placeholder="$" />
                  <Txt label="Due date" value={form.payment_due_date} onChange={(v) => set('payment_due_date', v)} type="date" />
                </div>
                <Area label="Notes" value={form.payment_notes} onChange={(v) => set('payment_notes', v)} placeholder="Payment notes…" />
              </SectionCard>

              {/* E. STD / FMLA */}
              <SectionCard
                title="STD / FMLA Screening"
                icon={FileText}
                open={open.std_fmla}
                onToggle={() => tog('std_fmla')}
              >
                <div className="grid grid-cols-2 gap-3">
                  <Sel
                    label="STD needed"
                    value={form.std_needed}
                    onChange={(v) => set('std_needed', v)}
                    options={[['Unknown', 'Unknown'], ['Yes', 'Yes'], ['No', 'No']]}
                  />
                  <Sel
                    label="STD status"
                    value={form.std_status}
                    onChange={(v) => set('std_status', v)}
                    options={[
                      ['Not Started', 'Not Started'],
                      ['Pending Client Info', 'Pending Client Info'],
                      ['Submitted', 'Submitted'],
                      ['Approved', 'Approved'],
                      ['Denied', 'Denied'],
                      ['Not Applicable', 'Not Applicable'],
                    ]}
                  />
                </div>
                <Area label="STD notes" value={form.std_notes} onChange={(v) => set('std_notes', v)} placeholder="STD details…" />
                <div className="grid grid-cols-2 gap-3">
                  <Sel
                    label="FMLA needed"
                    value={form.fmla_needed}
                    onChange={(v) => set('fmla_needed', v)}
                    options={[['Unknown', 'Unknown'], ['Yes', 'Yes'], ['No', 'No']]}
                  />
                  <Txt
                    label="Linked FMLA case ID"
                    value={form.linked_fmla_case_id}
                    onChange={(v) => set('linked_fmla_case_id', v)}
                    placeholder="FMLA case reference"
                  />
                </div>
              </SectionCard>

              {/* F. Discharge Starter */}
              <SectionCard
                title="Discharge Planning"
                icon={LogOut}
                open={open.discharge}
                onToggle={() => tog('discharge')}
              >
                <Chk
                  label="Discharge planning started"
                  checked={form.discharge_planning_started}
                  onChange={(v) => set('discharge_planning_started', v)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Txt
                    label="Expected discharge destination"
                    value={form.discharge_destination}
                    onChange={(v) => set('discharge_destination', v)}
                    placeholder="Home, sober living, family…"
                  />
                  <Txt
                    label="Transportation plan"
                    value={form.transportation_plan}
                    onChange={(v) => set('transportation_plan', v)}
                    placeholder="Bus, family, rideshare…"
                  />
                </div>
                <div className="pt-1 space-y-2">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Follow-up needed at discharge
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <Chk label="Sober living" checked={form.sober_living_needed} onChange={(v) => set('sober_living_needed', v)} />
                    <Chk label="PCP / dental / psychiatry" checked={form.pcp_dental_psych_needed} onChange={(v) => set('pcp_dental_psych_needed', v)} />
                    <Chk label="Legal / probation" checked={form.legal_probation_followup_needed} onChange={(v) => set('legal_probation_followup_needed', v)} />
                    <Chk label="Benefits" checked={form.benefits_followup_needed} onChange={(v) => set('benefits_followup_needed', v)} />
                    <Chk label="Employment / resume" checked={form.employment_resume_needed} onChange={(v) => set('employment_resume_needed', v)} />
                  </div>
                </div>
                <Area
                  label="Discharge notes"
                  value={form.discharge_notes}
                  onChange={(v) => set('discharge_notes', v)}
                  placeholder="Discharge planning notes…"
                />
              </SectionCard>

              {/* Save */}
              {saveError && (
                <div className="flex items-center gap-2 text-xs text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {saveError}
                </div>
              )}
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-cyan-500/12 border border-cyan-500/20 text-cyan-300 text-sm hover:bg-cyan-500/20 disabled:opacity-50 transition-colors"
              >
                {saving ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…</>
                ) : savedFlash ? (
                  <><CheckCircle2 className="h-3.5 w-3.5" /> Saved</>
                ) : (
                  <><Save className="h-3.5 w-3.5" /> Save Financial Coordination</>
                )}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
