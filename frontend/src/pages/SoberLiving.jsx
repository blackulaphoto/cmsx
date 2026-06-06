import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Home, Plus, RefreshCw, Building2, BedDouble, Users, Activity } from 'lucide-react'
import toast from 'react-hot-toast'
import { slApi, GENDER_POLICY_OPTIONS, occupancyColor } from '../utils/soberLiving'

const emptyHouseForm = () => ({
  name: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  phone: '',
  email: '',
  manager_name: '',
  gender_policy: 'any',
  notes: '',
  status: 'active',
})

export default function SoberLiving() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [houses, setHouses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddHouse, setShowAddHouse] = useState(false)
  const [form, setForm] = useState(emptyHouseForm())
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [sum, houseList] = await Promise.all([slApi.getSummary(), slApi.listHouses()])
      setSummary(sum)
      setHouses(Array.isArray(houseList) ? houseList : [])
    } catch (err) {
      toast.error('Failed to load sober living data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAddHouse = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return toast.error('House name is required')
    setSaving(true)
    try {
      await slApi.createHouse(form)
      toast.success('House added')
      setShowAddHouse(false)
      setForm(emptyHouseForm())
      load()
    } catch {
      toast.error('Failed to add house')
    } finally {
      setSaving(false)
    }
  }

  const StatCard = ({ icon: Icon, label, value, sub }) => (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-lg bg-indigo-500/10">
          <Icon size={18} className="text-indigo-400" />
        </div>
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value ?? '—'}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )

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
            onClick={() => setShowAddHouse(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium transition-colors"
          >
            <Plus size={14} />
            Add House
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon={Building2} label="Houses" value={summary.total_houses} />
          <StatCard icon={BedDouble} label="Total Beds" value={summary.total_beds} />
          <StatCard icon={Users} label="Occupied" value={summary.occupied_beds} sub={`${summary.available_beds} available`} />
          <StatCard
            icon={Activity}
            label="Occupancy Rate"
            value={
              <span className={occupancyColor(summary.occupancy_rate)}>
                {summary.occupancy_rate}%
              </span>
            }
          />
        </div>
      )}

      {/* House List */}
      {loading ? (
        <div className="text-center py-16 text-slate-400">Loading...</div>
      ) : houses.length === 0 ? (
        <div className="text-center py-16">
          <Home size={40} className="mx-auto text-slate-600 mb-3" />
          <p className="text-slate-400">No houses added yet.</p>
          <button
            onClick={() => setShowAddHouse(true)}
            className="mt-4 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium"
          >
            Add your first house
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {houses.map((house) => {
            const counts = house.bed_counts || {}
            const rate = counts.total > 0
              ? Math.round((counts.occupied / counts.total) * 100)
              : 0
            return (
              <button
                key={house.house_id}
                onClick={() => navigate(`/sober-living/${house.house_id}`)}
                className="text-left bg-slate-800/60 border border-slate-700/50 hover:border-emerald-500/40 rounded-xl p-5 transition-all hover:shadow-lg"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white">{house.name}</h3>
                    {house.city && (
                      <p className="text-sm text-slate-400 mt-0.5">
                        {house.city}{house.state ? `, ${house.state}` : ''}
                      </p>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    house.status === 'active'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                      : 'bg-slate-600/20 text-slate-400 border-slate-600/30'
                  }`}>
                    {house.status}
                  </span>
                </div>

                {house.manager_name && (
                  <p className="text-xs text-slate-500 mb-3">Manager: {house.manager_name}</p>
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
                  {counts.reserved > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-400" />
                      <span className="text-slate-300">{counts.reserved} reserved</span>
                    </div>
                  )}
                </div>

                {counts.total > 0 && (
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
              </button>
            )
          })}
        </div>
      )}

      {/* Add House Modal */}
      {showAddHouse && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-slate-700">
              <h2 className="font-semibold text-white">Add New House</h2>
              <button onClick={() => setShowAddHouse(false)} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleAddHouse} className="p-5 space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">House Name *</label>
                <input
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Recovery House North"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Address</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">City</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.city}
                    onChange={(e) => setForm({ ...form, city: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">State</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.state}
                    onChange={(e) => setForm({ ...form, state: e.target.value })}
                    maxLength={2}
                    placeholder="CA"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">ZIP</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.zip_code}
                    onChange={(e) => setForm({ ...form, zip_code: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Phone</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Manager Name</label>
                  <input
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                    value={form.manager_name}
                    onChange={(e) => setForm({ ...form, manager_name: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Gender Policy</label>
                <select
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500"
                  value={form.gender_policy}
                  onChange={(e) => setForm({ ...form, gender_policy: e.target.value })}
                >
                  {GENDER_POLICY_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Notes</label>
                <textarea
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-emerald-500 resize-none"
                  rows={2}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
              <div className="flex justify-end gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setShowAddHouse(false)}
                  className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
                >
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
