import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home, Plus, RefreshCw, Building2, BedDouble, Users, Activity, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  slApi,
  HOUSE_TYPE_OPTIONS,
  CERTIFICATION_OPTIONS,
  PAYMENT_TYPE_OPTIONS,
  ACCEPTS_INSURANCE_OPTIONS,
  occupancyColor,
} from '../utils/soberLiving'

const emptyForm = () => ({
  house_name: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  house_manager_name: '',
  house_manager_phone: '',
  house_manager_email: '',
  house_type: 'any',
  total_beds: '',
  monthly_rent: '',
  certification_level: 'unknown',
  certification_notes: '',
  affiliated_clinical_program: '',
  payment_type: 'unknown',
  accepts_insurance: 'unknown',
  insurance_plans_accepted: '',
  funding_notes: '',
  requires_clinical_program: 0,
  billing_contact_name: '',
  billing_contact_phone: '',
  billing_contact_email: '',
  notes: '',
})

export default function SoberLiving() {
  const navigate = useNavigate()
  const [summary, setSummary]     = useState(null)
  const [houses, setHouses]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [showAdd, setShowAdd]     = useState(false)
  const [form, setForm]           = useState(emptyForm())
  const [saving, setSaving]       = useState(false)
  const [showPayment, setShowPayment] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [sum, houseList] = await Promise.all([
        slApi.getSummary(),
        slApi.listHouses(),
      ])
      setSummary(sum)
      setHouses(Array.isArray(houseList) ? houseList : [])
    } catch (err) {
      setError(err.message || 'Failed to load sober living data')
      toast.error('Failed to load sober living data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!form.house_name.trim()) return toast.error('House name is required')
    setSaving(true)
    try {
      const payload = { ...form }
      if (payload.total_beds !== '') payload.total_beds = parseInt(payload.total_beds) || 0
      else delete payload.total_beds
      if (payload.monthly_rent !== '') payload.monthly_rent = parseFloat(payload.monthly_rent) || null
      else delete payload.monthly_rent
      await slApi.createHouse(payload)
      toast.success('House added')
      setShowAdd(false)
      setForm(emptyForm())
      setShowPayment(false)
      load()
    } catch (err) {
      toast.error(err.message || 'Failed to add house')
    } finally {
      setSaving(false)
    }
  }

  const field = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const check = (key) => (e) => setForm({ ...form, [key]: e.target.checked ? 1 : 0 })

  const s = summary || {}
  const totalHouses      = Number(s.total_houses      ?? 0)
  const configuredBeds   = Number(s.configured_beds   ?? s.total_beds ?? 0)
  const plannedCapacity  = Number(s.planned_capacity  ?? 0)
  const occupiedBeds     = Number(s.occupied_beds     ?? 0)
  const availableBeds    = Number(s.available_beds    ?? 0)
  const occupancyRate    = Number(s.occupancy_rate    ?? 0)

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <Home size={24} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Sober Living</h1>
            <p className="text-sm text-slate-400">Operations &amp; Bed Management</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-sm transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium transition-colors"
          >
            <Plus size={14} />
            Add House
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Building2} label="Houses" value={loading ? '—' : totalHouses} />
        <StatCard
          icon={BedDouble}
          label="Configured Beds"
          value={loading ? '—' : configuredBeds}
          sub={loading ? null : plannedCapacity > configuredBeds
            ? `${plannedCapacity} planned capacity`
            : plannedCapacity > 0 ? `${plannedCapacity} planned` : null}
        />
        <StatCard
          icon={Users}
          label="Occupied"
          value={loading ? '—' : occupiedBeds}
          sub={loading ? null : `${availableBeds} available`}
        />
        <StatCard
          icon={Activity}
          label="Occupancy Rate"
          value={
            loading ? '—' : (
              <span className={occupancyColor(occupancyRate)}>
                {occupancyRate.toFixed(1)}%
              </span>
            )
          }
          sub={loading ? null : 'based on configured beds'}
        />
      </div>

      {/* Error state */}
      {error && !loading && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 mb-6 text-rose-300 text-sm">
          {error} —{' '}
          <button onClick={load} className="underline hover:text-rose-200">retry</button>
        </div>
      )}

      {/* House list */}
      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading...</div>
      ) : houses.length === 0 ? (
        <div className="text-center py-16">
          <Home size={40} className="mx-auto text-slate-600 mb-3" />
          <p className="text-slate-400 mb-4">No houses added yet.</p>
          <button
            onClick={() => setShowAdd(true)}
            className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium"
          >
            Add your first house
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {houses.map((house) => {
            const counts       = house.bed_counts || {}
            const configured   = counts.configured ?? counts.total ?? 0
            const planned      = counts.planned_capacity ?? 0
            const occ          = counts.occupied ?? 0
            const avail        = counts.available ?? 0
            const incomplete   = counts.setup_incomplete ?? (planned > configured)
            const toConfig     = counts.beds_to_configure ?? Math.max(0, planned - configured)
            const rate         = configured > 0 ? Math.round((occ / configured) * 100) : 0
            const payType      = house.payment_type && house.payment_type !== 'unknown'
              ? PAYMENT_TYPE_OPTIONS.find(o => o.value === house.payment_type)?.label || house.payment_type
              : null

            return (
              <button
                key={house.house_id}
                onClick={() => navigate(`/sober-living/${house.house_id}`)}
                className="text-left bg-slate-800/60 border border-slate-700/50 hover:border-emerald-500/40 rounded-xl p-5 transition-all hover:shadow-lg group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white group-hover:text-emerald-300 transition-colors">
                      {house.house_name}
                    </h3>
                    {(house.city || house.state) && (
                      <p className="text-sm text-slate-400 mt-0.5">
                        {house.city}{house.state ? `, ${house.state}` : ''}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      house.is_active
                        ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                        : 'bg-slate-600/20 text-slate-400 border-slate-600/30'
                    }`}>
                      {house.is_active ? 'active' : 'inactive'}
                    </span>
                    {payType && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                        {payType}
                      </span>
                    )}
                  </div>
                </div>

                {house.house_manager_name && (
                  <p className="text-xs text-slate-500 mb-3">Manager: {house.house_manager_name}</p>
                )}

                {/* Bed summary */}
                <div className="flex items-center gap-4 text-sm mb-2">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-slate-300">{avail} available</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                    <span className="text-slate-300">{occ} occupied</span>
                  </div>
                  {(counts.reserved ?? 0) > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />
                      <span className="text-slate-300">{counts.reserved} reserved</span>
                    </div>
                  )}
                </div>

                {/* Configured vs planned line */}
                <p className="text-xs text-slate-500 mb-2">
                  {configured} bed{configured !== 1 ? 's' : ''} configured
                  {planned > 0 ? ` · ${planned} planned` : ''}
                </p>

                {/* Setup incomplete warning */}
                {incomplete && toConfig > 0 && (
                  <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-2 py-1 mb-2">
                    <AlertTriangle size={12} />
                    {toConfig} bed{toConfig !== 1 ? 's' : ''} not yet configured
                  </div>
                )}

                {configured > 0 && (
                  <div className="mt-1">
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>Occupancy</span>
                      <span className={occupancyColor(rate)}>{rate}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-500 transition-all"
                        style={{ width: `${rate}%` }}
                      />
                    </div>
                  </div>
                )}

                {configured === 0 && (
                  <p className="text-xs text-slate-600 mt-1">No bed records — add beds in house detail</p>
                )}
              </button>
            )
          })}
        </div>
      )}

      {/* Add House Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-5 border-b border-slate-700 shrink-0">
              <h2 className="font-semibold text-white">Add New House</h2>
              <button onClick={() => { setShowAdd(false); setShowPayment(false) }} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleAdd} className="p-5 space-y-5 overflow-y-auto">

              {/* Basic Info */}
              <Section title="Basic Info">
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <Label>House Name *</Label>
                    <Input value={form.house_name} onChange={field('house_name')} placeholder="e.g. Oak Street Recovery House" />
                  </div>
                  <div>
                    <Label>Address</Label>
                    <Input value={form.address} onChange={field('address')} />
                  </div>
                  <div>
                    <Label>City</Label>
                    <Input value={form.city} onChange={field('city')} />
                  </div>
                  <div>
                    <Label>State</Label>
                    <Input value={form.state} onChange={field('state')} maxLength={2} placeholder="CA" />
                  </div>
                  <div>
                    <Label>ZIP</Label>
                    <Input value={form.zip_code} onChange={field('zip_code')} />
                  </div>
                </div>
              </Section>

              {/* Management */}
              <Section title="House Management">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Manager Name</Label>
                    <Input value={form.house_manager_name} onChange={field('house_manager_name')} />
                  </div>
                  <div>
                    <Label>Manager Phone</Label>
                    <Input value={form.house_manager_phone} onChange={field('house_manager_phone')} />
                  </div>
                  <div className="col-span-2">
                    <Label>Manager Email</Label>
                    <Input value={form.house_manager_email} onChange={field('house_manager_email')} />
                  </div>
                </div>
              </Section>

              {/* Capacity & Type */}
              <Section title="Capacity &amp; Type">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>House Type</Label>
                    <Select value={form.house_type} onChange={field('house_type')}>
                      {HOUSE_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </Select>
                  </div>
                  <div>
                    <Label>Planned Capacity</Label>
                    <Input type="number" min="0" value={form.total_beds} onChange={field('total_beds')} placeholder="0" />
                    <p className="text-xs text-slate-500 mt-1">Target bed count. Actual availability comes from configured bed records.</p>
                  </div>
                  <div>
                    <Label>Monthly Rent ($)</Label>
                    <Input type="number" min="0" step="0.01" value={form.monthly_rent} onChange={field('monthly_rent')} placeholder="0.00" />
                  </div>
                  <div>
                    <Label>Affiliated Clinical Program</Label>
                    <Input value={form.affiliated_clinical_program} onChange={field('affiliated_clinical_program')} />
                  </div>
                </div>
              </Section>

              {/* Certification */}
              <Section title="Certification">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Certification Level</Label>
                    <Select value={form.certification_level} onChange={field('certification_level')}>
                      {CERTIFICATION_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </Select>
                  </div>
                  <div>
                    <Label>Certification Notes</Label>
                    <Input value={form.certification_notes} onChange={field('certification_notes')} placeholder="NARR Level 2, Cert # 12345..." />
                  </div>
                </div>
              </Section>

              {/* Payment & Funding */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowPayment(p => !p)}
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-3"
                >
                  <span className={`transition-transform ${showPayment ? 'rotate-90' : ''}`}>▶</span>
                  Payment &amp; Funding {showPayment ? '' : '(optional)'}
                </button>
                {showPayment && (
                  <div className="grid grid-cols-2 gap-3 pl-4 border-l-2 border-slate-700">
                    <div>
                      <Label>Payment Type</Label>
                      <Select value={form.payment_type} onChange={field('payment_type')}>
                        {PAYMENT_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </Select>
                    </div>
                    <div>
                      <Label>Accepts Insurance</Label>
                      <Select value={form.accepts_insurance} onChange={field('accepts_insurance')}>
                        {ACCEPTS_INSURANCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </Select>
                    </div>
                    <div className="col-span-2">
                      <Label>Insurance Plans Accepted</Label>
                      <Input value={form.insurance_plans_accepted} onChange={field('insurance_plans_accepted')} placeholder="Medi-Cal, Blue Cross PPO..." />
                    </div>
                    <div className="col-span-2">
                      <Label>Funding Notes</Label>
                      <Input value={form.funding_notes} onChange={field('funding_notes')} placeholder="DHCS voucher, county contract..." />
                    </div>
                    <div className="col-span-2">
                      <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.requires_clinical_program === 1}
                          onChange={check('requires_clinical_program')}
                          className="rounded border-slate-600"
                        />
                        Requires enrollment in a clinical program
                      </label>
                    </div>
                    <div>
                      <Label>Billing Contact Name</Label>
                      <Input value={form.billing_contact_name} onChange={field('billing_contact_name')} />
                    </div>
                    <div>
                      <Label>Billing Contact Phone</Label>
                      <Input value={form.billing_contact_phone} onChange={field('billing_contact_phone')} />
                    </div>
                    <div className="col-span-2">
                      <Label>Billing Contact Email</Label>
                      <Input value={form.billing_contact_email} onChange={field('billing_contact_email')} />
                    </div>
                  </div>
                )}
              </div>

              {/* Notes */}
              <div>
                <Label>Notes</Label>
                <textarea
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 resize-none"
                  rows={2}
                  value={form.notes}
                  onChange={field('notes')}
                />
              </div>

              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => { setShowAdd(false); setShowPayment(false) }} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-50">
                  {saving ? 'Saving...' : 'Add House'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">{title}</h3>
      {children}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-lg bg-indigo-500/10">
          <Icon size={18} className="text-indigo-400" />
        </div>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}

function Label({ children }) {
  return <label className="block text-xs text-slate-400 mb-1">{children}</label>
}

function Input({ value, onChange, placeholder, maxLength, type = 'text', min, step }) {
  return (
    <input
      type={type}
      className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      maxLength={maxLength}
      min={min}
      step={step}
    />
  )
}

function Select({ value, onChange, children }) {
  return (
    <select
      className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
      value={value}
      onChange={onChange}
    >
      {children}
    </select>
  )
}
