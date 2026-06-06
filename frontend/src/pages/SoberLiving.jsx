import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home, Plus, RefreshCw, Building2, BedDouble, Users, Activity } from 'lucide-react'
import toast from 'react-hot-toast'
import { slApi, HOUSE_TYPE_OPTIONS, occupancyColor } from '../utils/soberLiving'

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
  certification_level: '',
  affiliated_clinical_program: '',
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
      load()
    } catch (err) {
      toast.error(err.message || 'Failed to add house')
    } finally {
      setSaving(false)
    }
  }

  const field = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  // Summary values always default to 0, never undefined/null
  const s = summary || {}
  const totalHouses    = Number(s.total_houses   ?? 0)
  const totalBeds      = Number(s.total_beds     ?? 0)
  const occupiedBeds   = Number(s.occupied_beds  ?? 0)
  const availableBeds  = Number(s.available_beds ?? 0)
  const occupancyRate  = Number(s.occupancy_rate ?? 0)

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

      {/* Summary Cards — always show, never undefined */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Building2} label="Houses"       value={loading ? '—' : totalHouses} />
        <StatCard icon={BedDouble} label="Total Beds"   value={loading ? '—' : totalBeds} />
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
            const counts = house.bed_counts || {}
            const total = counts.total || 0
            const occ   = counts.occupied || 0
            const rate  = total > 0 ? Math.round((occ / total) * 100) : 0
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
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    house.is_active
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : 'bg-slate-600/20 text-slate-400 border-slate-600/30'
                  }`}>
                    {house.is_active ? 'active' : 'inactive'}
                  </span>
                </div>

                {house.house_manager_name && (
                  <p className="text-xs text-slate-500 mb-3">Manager: {house.house_manager_name}</p>
                )}

                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-slate-300">{counts.available ?? 0} open</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                    <span className="text-slate-300">{counts.occupied ?? 0} occupied</span>
                  </div>
                  {(counts.reserved ?? 0) > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />
                      <span className="text-slate-300">{counts.reserved} reserved</span>
                    </div>
                  )}
                </div>

                {total > 0 && (
                  <div className="mt-3">
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

                {total === 0 && (
                  <p className="text-xs text-slate-600 mt-3">No beds configured</p>
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
              <button onClick={() => setShowAdd(false)} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleAdd} className="p-5 space-y-4 overflow-y-auto">
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
                <div>
                  <Label>Manager Name</Label>
                  <Input value={form.house_manager_name} onChange={field('house_manager_name')} />
                </div>
                <div>
                  <Label>Manager Phone</Label>
                  <Input value={form.house_manager_phone} onChange={field('house_manager_phone')} />
                </div>
                <div>
                  <Label>Manager Email</Label>
                  <Input value={form.house_manager_email} onChange={field('house_manager_email')} />
                </div>
                <div>
                  <Label>House Type</Label>
                  <Select value={form.house_type} onChange={field('house_type')}>
                    {HOUSE_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </Select>
                </div>
                <div>
                  <Label>Total Beds (approx.)</Label>
                  <Input type="number" min="0" value={form.total_beds} onChange={field('total_beds')} placeholder="0" />
                </div>
                <div>
                  <Label>Monthly Rent ($)</Label>
                  <Input type="number" min="0" step="0.01" value={form.monthly_rent} onChange={field('monthly_rent')} placeholder="0.00" />
                </div>
                <div>
                  <Label>Certification Level</Label>
                  <Input value={form.certification_level} onChange={field('certification_level')} placeholder="NARR Level 2, etc." />
                </div>
                <div className="col-span-2">
                  <Label>Affiliated Clinical Program</Label>
                  <Input value={form.affiliated_clinical_program} onChange={field('affiliated_clinical_program')} />
                </div>
                <div className="col-span-2">
                  <Label>Notes</Label>
                  <textarea
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 resize-none"
                    rows={2}
                    value={form.notes}
                    onChange={field('notes')}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-1">
                <button type="button" onClick={() => setShowAdd(false)} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
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
