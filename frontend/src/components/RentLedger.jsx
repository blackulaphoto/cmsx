import { useEffect, useState } from 'react'
import { DollarSign, Plus, Receipt, AlertCircle, Ban } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  slApi,
  PAYMENT_FREQUENCIES, PAYMENT_METHODS, PAYMENT_STATUS_COLORS,
  formatCurrency, formatDate,
} from '../utils/soberLiving'

/**
 * RentLedger — full rent panel for a single active stay.
 * Props:
 *   stayId       : string
 *   residentId   : string
 *   houseId      : string
 *   residentName : string  — display name only
 */
export default function RentLedger({ stayId, residentId, houseId, residentName }) {
  const [ledger, setLedger] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(null) // 'set-agreement' | 'add-payment'
  const [saving, setSaving] = useState(false)

  const today = new Date().toISOString().slice(0, 10)

  const [agForm, setAgForm] = useState({
    rent_amount: '',
    frequency: 'monthly',
    due_day: '',
    payment_method: '',
    notes: '',
  })

  const [pmtForm, setPmtForm] = useState({
    amount: '',
    payment_date: today,
    period_start: '',
    period_end: '',
    payment_method: '',
    reference_number: '',
    notes: '',
  })

  const load = async () => {
    setLoading(true)
    try {
      const data = await slApi.getLedger(stayId)
      setLedger(data)
      if (data.agreement) {
        setAgForm({
          rent_amount: data.agreement.rent_amount ?? '',
          frequency: data.agreement.frequency ?? 'monthly',
          due_day: data.agreement.due_day ?? '',
          payment_method: data.agreement.payment_method ?? '',
          notes: data.agreement.notes ?? '',
        })
      }
    } catch {
      toast.error('Failed to load rent ledger')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [stayId])

  const handleSaveAgreement = async (e) => {
    e.preventDefault()
    if (!agForm.rent_amount || Number(agForm.rent_amount) <= 0) return toast.error('Enter a valid rent amount')
    setSaving(true)
    try {
      const payload = {
        ...agForm,
        rent_amount: parseFloat(agForm.rent_amount),
        due_day: agForm.due_day ? parseInt(agForm.due_day) : null,
      }
      if (ledger?.agreement) {
        await slApi.updateRentAgreement(ledger.agreement.agreement_id, payload)
      } else {
        await slApi.createRentAgreement({ ...payload, stay_id: stayId, resident_id: residentId, house_id: houseId })
      }
      toast.success('Rent agreement saved')
      setModal(null)
      load()
    } catch {
      toast.error('Failed to save rent agreement')
    } finally {
      setSaving(false)
    }
  }

  const handleRecordPayment = async (e) => {
    e.preventDefault()
    if (!ledger?.agreement) return toast.error('Set a rent agreement first')
    if (!pmtForm.amount || Number(pmtForm.amount) <= 0) return toast.error('Enter a valid amount')
    setSaving(true)
    try {
      await slApi.createPayment({
        ...pmtForm,
        amount: parseFloat(pmtForm.amount),
        agreement_id: ledger.agreement.agreement_id,
        stay_id: stayId,
        resident_id: residentId,
        house_id: houseId,
      })
      toast.success('Payment recorded')
      setModal(null)
      setPmtForm({ amount: '', payment_date: today, period_start: '', period_end: '', payment_method: '', reference_number: '', notes: '' })
      load()
    } catch {
      toast.error('Failed to record payment')
    } finally {
      setSaving(false)
    }
  }

  const handleVoid = async (paymentId) => {
    if (!window.confirm('Void this payment? This cannot be undone.')) return
    try {
      await slApi.voidPayment(paymentId)
      toast.success('Payment voided')
      load()
    } catch {
      toast.error('Failed to void payment')
    }
  }

  if (loading) return <div className="text-center py-6 text-slate-400 text-sm">Loading ledger...</div>

  const agreement = ledger?.agreement
  const payments = ledger?.payments || []
  const totalPaid = ledger?.total_paid ?? 0

  return (
    <div className="space-y-5">
      {/* Agreement Card */}
      <div className="bg-slate-700/40 border border-slate-600/40 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <DollarSign size={14} className="text-emerald-400" />
            Rent Agreement
          </h4>
          <button
            onClick={() => setModal('set-agreement')}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs transition-colors"
          >
            <Plus size={11} />
            {agreement ? 'Edit' : 'Set Agreement'}
          </button>
        </div>

        {agreement ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-xs text-slate-500">Amount</p>
              <p className="text-base font-bold text-emerald-300">{formatCurrency(agreement.rent_amount)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Frequency</p>
              <p className="text-sm text-white capitalize">{agreement.frequency}</p>
            </div>
            {agreement.due_day && (
              <div>
                <p className="text-xs text-slate-500">Due Day</p>
                <p className="text-sm text-white">Day {agreement.due_day}</p>
              </div>
            )}
            {agreement.payment_method && (
              <div>
                <p className="text-xs text-slate-500">Default Method</p>
                <p className="text-sm text-white">{agreement.payment_method}</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">No rent agreement set yet.</p>
        )}
      </div>

      {/* Balance Summary */}
      {agreement && (
        <div className="flex items-center gap-4 px-1">
          <div>
            <p className="text-xs text-slate-500">Total Paid</p>
            <p className="text-lg font-bold text-emerald-300">{formatCurrency(totalPaid)}</p>
          </div>
        </div>
      )}

      {/* Payment History */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <Receipt size={14} className="text-indigo-400" />
            Payment History
          </h4>
          {agreement && (
            <button
              onClick={() => setModal('add-payment')}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 text-xs transition-colors"
            >
              <Plus size={11} />
              Record Payment
            </button>
          )}
        </div>

        {payments.length === 0 ? (
          <p className="text-sm text-slate-500">No payments recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {payments.map((p) => {
              const colors = PAYMENT_STATUS_COLORS[p.status] || PAYMENT_STATUS_COLORS.posted
              return (
                <div
                  key={p.payment_id}
                  className={`flex items-start justify-between rounded-lg border px-4 py-3 ${colors.bg} ${colors.border}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-sm font-semibold ${colors.text}`}>
                        {formatCurrency(p.amount)}
                      </span>
                      <span className="text-xs text-slate-400">{formatDate(p.payment_date)}</span>
                      {p.payment_method && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-slate-600/40 text-slate-300">
                          {p.payment_method}
                        </span>
                      )}
                      {p.status === 'voided' && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          Voided
                        </span>
                      )}
                    </div>
                    {(p.period_start || p.period_end) && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        Period: {formatDate(p.period_start)} – {formatDate(p.period_end)}
                      </p>
                    )}
                    {p.reference_number && (
                      <p className="text-xs text-slate-500">Ref: {p.reference_number}</p>
                    )}
                    {p.notes && <p className="text-xs text-slate-500 mt-0.5 truncate">{p.notes}</p>}
                  </div>
                  {p.status === 'posted' && (
                    <button
                      onClick={() => handleVoid(p.payment_id)}
                      title="Void payment"
                      className="ml-3 p-1.5 rounded hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-colors shrink-0"
                    >
                      <Ban size={13} />
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* =============== MODALS =============== */}

      {/* Set / Edit Rent Agreement */}
      {modal === 'set-agreement' && (
        <LedgerModal title={agreement ? 'Edit Rent Agreement' : 'Set Rent Agreement'} onClose={() => setModal(null)}>
          <form onSubmit={handleSaveAgreement} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Rent Amount *</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                  <input
                    type="number" step="0.01" min="0"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg pl-7 pr-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={agForm.rent_amount}
                    onChange={(e) => setAgForm({ ...agForm, rent_amount: e.target.value })}
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Frequency</label>
                <select
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  value={agForm.frequency}
                  onChange={(e) => setAgForm({ ...agForm, frequency: e.target.value })}
                >
                  {PAYMENT_FREQUENCIES.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Due Day (1–31)</label>
                <input
                  type="number" min="1" max="31"
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  value={agForm.due_day}
                  onChange={(e) => setAgForm({ ...agForm, due_day: e.target.value })}
                  placeholder="e.g. 1, 15"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Default Payment Method</label>
                <select
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  value={agForm.payment_method}
                  onChange={(e) => setAgForm({ ...agForm, payment_method: e.target.value })}
                >
                  <option value="">None</option>
                  {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea
                className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 resize-none"
                rows={2}
                value={agForm.notes}
                onChange={(e) => setAgForm({ ...agForm, notes: e.target.value })}
              />
            </div>
            <LedgerFooter onCancel={() => setModal(null)} saving={saving} label={agreement ? 'Update Agreement' : 'Create Agreement'} />
          </form>
        </LedgerModal>
      )}

      {/* Record Payment */}
      {modal === 'add-payment' && (
        <LedgerModal title="Record Payment" onClose={() => setModal(null)}>
          <form onSubmit={handleRecordPayment} className="space-y-4">
            {agreement && (
              <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-700/30 rounded-lg px-3 py-2">
                <AlertCircle size={12} />
                Agreement: {formatCurrency(agreement.rent_amount)} / {agreement.frequency}
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Amount *</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                  <input
                    type="number" step="0.01" min="0"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg pl-7 pr-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                    value={pmtForm.amount}
                    onChange={(e) => setPmtForm({ ...pmtForm, amount: e.target.value })}
                    placeholder={agreement ? String(agreement.rent_amount) : '0.00'}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Payment Date</label>
                <input
                  type="date"
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={pmtForm.payment_date}
                  onChange={(e) => setPmtForm({ ...pmtForm, payment_date: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Period Start</label>
                <input
                  type="date"
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={pmtForm.period_start}
                  onChange={(e) => setPmtForm({ ...pmtForm, period_start: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Period End</label>
                <input
                  type="date"
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={pmtForm.period_end}
                  onChange={(e) => setPmtForm({ ...pmtForm, period_end: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Payment Method</label>
                <select
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={pmtForm.payment_method}
                  onChange={(e) => setPmtForm({ ...pmtForm, payment_method: e.target.value })}
                >
                  <option value="">Select...</option>
                  {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Reference / Check #</label>
                <input
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={pmtForm.reference_number}
                  onChange={(e) => setPmtForm({ ...pmtForm, reference_number: e.target.value })}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea
                className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
                rows={2}
                value={pmtForm.notes}
                onChange={(e) => setPmtForm({ ...pmtForm, notes: e.target.value })}
              />
            </div>
            <LedgerFooter onCancel={() => setModal(null)} saving={saving} label="Record Payment" />
          </form>
        </LedgerModal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Internal modal shell (smaller, scrollable)
// ---------------------------------------------------------------------------

function LedgerModal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-700 shrink-0">
          <h3 className="font-semibold text-white text-sm">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div className="p-4 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function LedgerFooter({ onCancel, saving, label }) {
  return (
    <div className="flex justify-end gap-3 pt-1">
      <button type="button" onClick={onCancel} className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
        Cancel
      </button>
      <button type="submit" disabled={saving} className="px-3 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium disabled:opacity-50">
        {saving ? 'Saving...' : label}
      </button>
    </div>
  )
}
