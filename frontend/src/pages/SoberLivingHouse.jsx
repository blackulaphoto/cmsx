import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, BedDouble, Users, Plus, RefreshCw,
  Home, Phone, Mail, User, AlertCircle, ChevronDown, ChevronRight, DollarSign
} from 'lucide-react'
import toast from 'react-hot-toast'
import BedMap from '../components/BedMap'
import RentLedger from '../components/RentLedger'
import {
  slApi,
  BED_STATUS_COLORS, BED_STATUS_LABELS, BED_STATUS_OPTIONS,
  DISCHARGE_REASON_OPTIONS, formatMoveInDate,
} from '../utils/soberLiving'

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

const FieldLabel = ({ children }) => (
  <label className="block text-xs text-slate-400 mb-1">{children}</label>
)

const TextInput = ({ value, onChange, placeholder, maxLength }) => (
  <input
    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
    value={value}
    onChange={onChange}
    placeholder={placeholder}
    maxLength={maxLength}
  />
)

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function SoberLivingHouse() {
  const { houseId } = useParams()
  const navigate = useNavigate()

  const [house, setHouse] = useState(null)
  const [beds, setBeds] = useState([])
  const [rooms, setRooms] = useState([])
  const [residents, setResidents] = useState([])
  const [loading, setLoading] = useState(true)

  // Modal states
  const [modal, setModal] = useState(null) // 'add-room' | 'add-bed' | 'add-resident' | 'assign-bed' | 'bed-detail' | 'discharge'
  const [expandedResident, setExpandedResident] = useState(null) // resident_id with rent ledger open

  // Forms
  const [roomForm, setRoomForm] = useState({ room_number: '', floor: '', notes: '' })
  const [bedForm, setBedForm] = useState({ bed_label: '', room_id: '', status: 'available', notes: '' })
  const [residentForm, setResidentForm] = useState({
    first_name: '', last_name: '', phone: '', email: '', gender: '',
    date_of_birth: '', sobriety_date: '', emergency_contact_name: '',
    emergency_contact_phone: '', notes: '',
  })
  const [assignForm, setAssignForm] = useState({ resident_id: '', bed_id: '', move_in_date: '' })
  const [dischargeForm, setDischargeForm] = useState({ discharge_reason: '', discharge_notes: '', move_out_date: '' })
  const [selectedBed, setSelectedBed] = useState(null)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [h, b, r, res] = await Promise.all([
        slApi.getHouse(houseId),
        slApi.listBeds(houseId),
        slApi.listRooms(houseId),
        slApi.listResidents(houseId),
      ])
      setHouse(h)
      setBeds(Array.isArray(b) ? b : [])
      setRooms(Array.isArray(r) ? r : [])
      setResidents(Array.isArray(res) ? res : [])
    } catch {
      toast.error('Failed to load house data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [houseId])

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleAddRoom = async (e) => {
    e.preventDefault()
    if (!roomForm.room_number.trim()) return toast.error('Room number required')
    setSaving(true)
    try {
      await slApi.createRoom(houseId, roomForm)
      toast.success('Room added')
      setModal(null)
      setRoomForm({ room_number: '', floor: '', notes: '' })
      load()
    } catch { toast.error('Failed to add room') }
    finally { setSaving(false) }
  }

  const handleAddBed = async (e) => {
    e.preventDefault()
    if (!bedForm.bed_label.trim()) return toast.error('Bed label required')
    if (!bedForm.room_id) return toast.error('Select a room')
    setSaving(true)
    try {
      await slApi.createBed(houseId, bedForm)
      toast.success('Bed added')
      setModal(null)
      setBedForm({ bed_label: '', room_id: '', status: 'available', notes: '' })
      load()
    } catch { toast.error('Failed to add bed') }
    finally { setSaving(false) }
  }

  const handleAddResident = async (e) => {
    e.preventDefault()
    if (!residentForm.first_name.trim() || !residentForm.last_name.trim()) return toast.error('Name required')
    setSaving(true)
    try {
      await slApi.createResident(residentForm)
      toast.success('Resident added')
      setModal(null)
      setResidentForm({
        first_name: '', last_name: '', phone: '', email: '', gender: '',
        date_of_birth: '', sobriety_date: '', emergency_contact_name: '',
        emergency_contact_phone: '', notes: '',
      })
      load()
    } catch { toast.error('Failed to add resident') }
    finally { setSaving(false) }
  }

  const handleAssignBed = async (e) => {
    e.preventDefault()
    if (!assignForm.resident_id) return toast.error('Select a resident')
    if (!assignForm.move_in_date) return toast.error('Move-in date required')
    setSaving(true)
    try {
      await slApi.createStay({
        resident_id: assignForm.resident_id,
        house_id: houseId,
        bed_id: assignForm.bed_id || null,
        move_in_date: assignForm.move_in_date,
      })
      toast.success('Stay created')
      setModal(null)
      setAssignForm({ resident_id: '', bed_id: '', move_in_date: '' })
      load()
    } catch (err) {
      toast.error(err?.message || 'Failed to assign bed')
    }
    finally { setSaving(false) }
  }

  const handleDischarge = async (e) => {
    e.preventDefault()
    if (!selectedBed?.stay_id) return
    setSaving(true)
    try {
      await slApi.dischargeStay(selectedBed.stay_id, dischargeForm)
      toast.success('Resident discharged')
      setModal(null)
      setSelectedBed(null)
      setDischargeForm({ discharge_reason: '', discharge_notes: '', move_out_date: '' })
      load()
    } catch { toast.error('Failed to discharge') }
    finally { setSaving(false) }
  }

  const handleBedClick = (bed) => {
    setSelectedBed(bed)
    setModal('bed-detail')
  }

  const handleUpdateBedStatus = async (bedId, status) => {
    try {
      await slApi.updateBed(bedId, { status })
      toast.success('Bed status updated')
      load()
      setModal(null)
    } catch { toast.error('Failed to update bed') }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400">
        Loading...
      </div>
    )
  }

  if (!house) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-3 text-slate-400">
        <AlertCircle size={32} />
        <p>House not found.</p>
        <button onClick={() => navigate('/sober-living')} className="text-indigo-400 hover:underline text-sm">
          Back to Sober Living
        </button>
      </div>
    )
  }

  const counts = house.bed_counts || {}

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">
      {/* Header */}
      <div className="flex items-start gap-4 mb-8">
        <button
          onClick={() => navigate('/sober-living')}
          className="mt-1 p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">{house.name}</h1>
              {(house.city || house.address) && (
                <p className="text-sm text-slate-400 mt-0.5">
                  {house.address && `${house.address}, `}{house.city}{house.state && `, ${house.state}`} {house.zip_code}
                </p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                {house.phone && <span className="flex items-center gap-1"><Phone size={11} />{house.phone}</span>}
                {house.email && <span className="flex items-center gap-1"><Mail size={11} />{house.email}</span>}
                {house.manager_name && <span className="flex items-center gap-1"><User size={11} />{house.manager_name}</span>}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap justify-end">
              <button onClick={load} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 text-xs transition-colors">
                <RefreshCw size={12} />
                Refresh
              </button>
              <button onClick={() => setModal('add-room')} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs">
                <Plus size={12} /> Room
              </button>
              <button onClick={() => setModal('add-bed')} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs">
                <BedDouble size={12} /> Bed
              </button>
              <button onClick={() => setModal('add-resident')} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 text-xs">
                <User size={12} /> Resident
              </button>
              <button onClick={() => setModal('assign-bed')} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
                <Home size={12} /> Assign Stay
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bed Count Bar */}
      <div className="flex gap-4 mb-8 flex-wrap">
        {[
          { key: 'available', label: 'Available', color: 'text-emerald-300' },
          { key: 'occupied', label: 'Occupied', color: 'text-rose-300' },
          { key: 'reserved', label: 'Reserved', color: 'text-amber-300' },
          { key: 'maintenance', label: 'Maintenance', color: 'text-slate-400' },
        ].map(({ key, label, color }) => counts[key] > 0 && (
          <div key={key} className={`text-sm ${color}`}>
            <span className="font-bold">{counts[key]}</span> {label}
          </div>
        ))}
        <div className="text-sm text-slate-500">
          <span className="font-bold">{counts.total ?? 0}</span> Total Beds
        </div>
      </div>

      {/* Bed Map */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5 mb-8">
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          <BedDouble size={16} className="text-indigo-400" />
          Bed Map
        </h2>
        <BedMap beds={beds} onBedClick={handleBedClick} />
      </div>

      {/* Residents & Rent */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Users size={16} className="text-indigo-400" />
          Current Residents ({residents.length})
        </h2>
        {residents.length === 0 ? (
          <p className="text-sm text-slate-400">No active residents.</p>
        ) : (
          <div className="space-y-2">
            {residents.map((r) => {
              const isOpen = expandedResident === r.resident_id
              return (
                <div key={r.resident_id} className="border border-slate-700/60 rounded-xl overflow-hidden">
                  {/* Resident header row */}
                  <button
                    onClick={() => setExpandedResident(isOpen ? null : r.resident_id)}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/20 transition-colors text-left"
                  >
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                        <User size={14} className="text-indigo-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-white">{r.first_name} {r.last_name}</p>
                        <p className="text-xs text-slate-400">
                          {r.room_number ? `Room ${r.room_number}` : ''}
                          {r.bed_label ? ` / ${r.bed_label}` : ''}
                          {r.move_in_date ? ` · In since ${formatMoveInDate(r.move_in_date)}` : ''}
                          {r.phone ? ` · ${r.phone}` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-3">
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <DollarSign size={11} />
                        Rent
                      </span>
                      {isOpen
                        ? <ChevronDown size={14} className="text-slate-400" />
                        : <ChevronRight size={14} className="text-slate-400" />
                      }
                    </div>
                  </button>

                  {/* Expanded: RentLedger */}
                  {isOpen && r.stay_id && (
                    <div className="border-t border-slate-700/50 px-4 py-4 bg-slate-800/40">
                      <RentLedger
                        stayId={r.stay_id}
                        residentId={r.resident_id}
                        houseId={houseId}
                        residentName={`${r.first_name} ${r.last_name}`}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ============================= MODALS ============================= */}

      {/* Add Room */}
      {modal === 'add-room' && (
        <Modal title="Add Room" onClose={() => setModal(null)}>
          <form onSubmit={handleAddRoom} className="space-y-4">
            <div>
              <FieldLabel>Room Number *</FieldLabel>
              <TextInput value={roomForm.room_number} onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })} placeholder="101" />
            </div>
            <div>
              <FieldLabel>Floor</FieldLabel>
              <TextInput value={roomForm.floor} onChange={(e) => setRoomForm({ ...roomForm, floor: e.target.value })} placeholder="1st" />
            </div>
            <div>
              <FieldLabel>Notes</FieldLabel>
              <textarea className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none" rows={2} value={roomForm.notes} onChange={(e) => setRoomForm({ ...roomForm, notes: e.target.value })} />
            </div>
            <ModalFooter onCancel={() => setModal(null)} saving={saving} label="Add Room" />
          </form>
        </Modal>
      )}

      {/* Add Bed */}
      {modal === 'add-bed' && (
        <Modal title="Add Bed" onClose={() => setModal(null)}>
          <form onSubmit={handleAddBed} className="space-y-4">
            <div>
              <FieldLabel>Room *</FieldLabel>
              <select className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={bedForm.room_id} onChange={(e) => setBedForm({ ...bedForm, room_id: e.target.value })}>
                <option value="">Select room...</option>
                {rooms.map((r) => <option key={r.room_id} value={r.room_id}>Room {r.room_number}{r.floor ? ` (${r.floor})` : ''}</option>)}
              </select>
            </div>
            <div>
              <FieldLabel>Bed Label *</FieldLabel>
              <TextInput value={bedForm.bed_label} onChange={(e) => setBedForm({ ...bedForm, bed_label: e.target.value })} placeholder="Bed A, Top Bunk, etc." />
            </div>
            <div>
              <FieldLabel>Initial Status</FieldLabel>
              <select className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={bedForm.status} onChange={(e) => setBedForm({ ...bedForm, status: e.target.value })}>
                {BED_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <FieldLabel>Notes</FieldLabel>
              <textarea className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none" rows={2} value={bedForm.notes} onChange={(e) => setBedForm({ ...bedForm, notes: e.target.value })} />
            </div>
            <ModalFooter onCancel={() => setModal(null)} saving={saving} label="Add Bed" />
          </form>
        </Modal>
      )}

      {/* Add Resident */}
      {modal === 'add-resident' && (
        <Modal title="Add Resident" onClose={() => setModal(null)}>
          <form onSubmit={handleAddResident} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <FieldLabel>First Name *</FieldLabel>
                <TextInput value={residentForm.first_name} onChange={(e) => setResidentForm({ ...residentForm, first_name: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Last Name *</FieldLabel>
                <TextInput value={residentForm.last_name} onChange={(e) => setResidentForm({ ...residentForm, last_name: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Phone</FieldLabel>
                <TextInput value={residentForm.phone} onChange={(e) => setResidentForm({ ...residentForm, phone: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Email</FieldLabel>
                <TextInput value={residentForm.email} onChange={(e) => setResidentForm({ ...residentForm, email: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Date of Birth</FieldLabel>
                <input type="date" className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={residentForm.date_of_birth} onChange={(e) => setResidentForm({ ...residentForm, date_of_birth: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Sobriety Date</FieldLabel>
                <input type="date" className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={residentForm.sobriety_date} onChange={(e) => setResidentForm({ ...residentForm, sobriety_date: e.target.value })} />
              </div>
              <div>
                <FieldLabel>Emergency Contact</FieldLabel>
                <TextInput value={residentForm.emergency_contact_name} onChange={(e) => setResidentForm({ ...residentForm, emergency_contact_name: e.target.value })} placeholder="Name" />
              </div>
              <div>
                <FieldLabel>Emergency Phone</FieldLabel>
                <TextInput value={residentForm.emergency_contact_phone} onChange={(e) => setResidentForm({ ...residentForm, emergency_contact_phone: e.target.value })} />
              </div>
            </div>
            <div>
              <FieldLabel>Notes</FieldLabel>
              <textarea className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none" rows={2} value={residentForm.notes} onChange={(e) => setResidentForm({ ...residentForm, notes: e.target.value })} />
            </div>
            <ModalFooter onCancel={() => setModal(null)} saving={saving} label="Add Resident" />
          </form>
        </Modal>
      )}

      {/* Assign Stay */}
      {modal === 'assign-bed' && (
        <Modal title="Assign Stay" onClose={() => setModal(null)}>
          <form onSubmit={handleAssignBed} className="space-y-4">
            <div>
              <FieldLabel>Resident *</FieldLabel>
              <select className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={assignForm.resident_id} onChange={(e) => setAssignForm({ ...assignForm, resident_id: e.target.value })}>
                <option value="">Select resident...</option>
                {/* Show all residents from store, not just current house residents */}
                {beds.filter((b) => b.status === 'occupied').map((b) => null)}
                {/* We show unassigned residents — those without an active stay on this house */}
                {residents.length === 0 && <option disabled>Add a resident first</option>}
                {residents.map((r) => <option key={r.resident_id} value={r.resident_id}>{r.first_name} {r.last_name}</option>)}
              </select>
            </div>
            <div>
              <FieldLabel>Bed (optional)</FieldLabel>
              <select className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={assignForm.bed_id} onChange={(e) => setAssignForm({ ...assignForm, bed_id: e.target.value })}>
                <option value="">No specific bed</option>
                {beds.filter((b) => b.status === 'available').map((b) => (
                  <option key={b.bed_id} value={b.bed_id}>
                    {b.room_number ? `Room ${b.room_number} / ` : ''}{b.bed_label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <FieldLabel>Move-in Date *</FieldLabel>
              <input type="date" className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={assignForm.move_in_date} onChange={(e) => setAssignForm({ ...assignForm, move_in_date: e.target.value })} />
            </div>
            <ModalFooter onCancel={() => setModal(null)} saving={saving} label="Create Stay" />
          </form>
        </Modal>
      )}

      {/* Bed Detail */}
      {modal === 'bed-detail' && selectedBed && (
        <Modal title={`Bed: ${selectedBed.bed_label}`} onClose={() => setModal(null)}>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded-full text-xs border ${BED_STATUS_COLORS[selectedBed.status]?.bg} ${BED_STATUS_COLORS[selectedBed.status]?.text} ${BED_STATUS_COLORS[selectedBed.status]?.border}`}>
                {BED_STATUS_LABELS[selectedBed.status] || selectedBed.status}
              </span>
              {selectedBed.room_number && <span className="text-xs text-slate-400">Room {selectedBed.room_number}</span>}
            </div>

            {selectedBed.status === 'occupied' && selectedBed.first_name && (
              <div className="bg-slate-700/40 rounded-lg p-3 text-sm">
                <p className="text-white font-medium">{selectedBed.first_name} {selectedBed.last_name}</p>
                <p className="text-slate-400 text-xs mt-1">Active stay</p>
              </div>
            )}

            {selectedBed.notes && (
              <p className="text-xs text-slate-400">{selectedBed.notes}</p>
            )}

            <div className="space-y-2">
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">Change Status</p>
              <div className="grid grid-cols-2 gap-2">
                {BED_STATUS_OPTIONS.filter((o) => o.value !== selectedBed.status).map((o) => (
                  <button
                    key={o.value}
                    onClick={() => handleUpdateBedStatus(selectedBed.bed_id, o.value)}
                    className={`px-3 py-2 rounded-lg text-xs border transition-all ${BED_STATUS_COLORS[o.value]?.bg} ${BED_STATUS_COLORS[o.value]?.text} ${BED_STATUS_COLORS[o.value]?.border} hover:opacity-80`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>

            {selectedBed.status === 'occupied' && selectedBed.stay_id && (
              <button
                onClick={() => setModal('discharge')}
                className="w-full px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 text-rose-300 text-sm"
              >
                Discharge Resident
              </button>
            )}
          </div>
        </Modal>
      )}

      {/* Discharge */}
      {modal === 'discharge' && selectedBed && (
        <Modal title="Discharge Resident" onClose={() => setModal('bed-detail')}>
          <form onSubmit={handleDischarge} className="space-y-4">
            <div>
              <FieldLabel>Move-out Date</FieldLabel>
              <input type="date" className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={dischargeForm.move_out_date} onChange={(e) => setDischargeForm({ ...dischargeForm, move_out_date: e.target.value })} />
            </div>
            <div>
              <FieldLabel>Discharge Reason</FieldLabel>
              <select className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500" value={dischargeForm.discharge_reason} onChange={(e) => setDischargeForm({ ...dischargeForm, discharge_reason: e.target.value })}>
                <option value="">Select reason...</option>
                {DISCHARGE_REASON_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <FieldLabel>Notes</FieldLabel>
              <textarea className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none" rows={2} value={dischargeForm.discharge_notes} onChange={(e) => setDischargeForm({ ...dischargeForm, discharge_notes: e.target.value })} />
            </div>
            <ModalFooter onCancel={() => setModal('bed-detail')} saving={saving} label="Confirm Discharge" submitClassName="bg-rose-500 hover:bg-rose-600" />
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared modal shell
// ---------------------------------------------------------------------------

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-slate-700 shrink-0">
          <h2 className="font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

function ModalFooter({ onCancel, saving, label, submitClassName = 'bg-indigo-500 hover:bg-indigo-600' }) {
  return (
    <div className="flex justify-end gap-3 pt-1">
      <button type="button" onClick={onCancel} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
        Cancel
      </button>
      <button type="submit" disabled={saving} className={`px-4 py-2 rounded-lg ${submitClassName} text-white text-sm font-medium disabled:opacity-50`}>
        {saving ? 'Saving...' : label}
      </button>
    </div>
  )
}
