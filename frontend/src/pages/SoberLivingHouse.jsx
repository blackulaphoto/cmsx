import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, BedDouble, Users, Plus, RefreshCw,
  Home, Phone, Mail, User, AlertCircle, ChevronDown, ChevronRight,
  DollarSign, ClipboardList, Beaker, ShieldAlert, Building2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import BedMap from '../components/BedMap'
import {
  slApi,
  BED_STATUS_COLORS, BED_STATUS_LABELS, BED_STATUS_OPTIONS,
  DISCHARGE_REASON_OPTIONS, INCIDENT_TYPES, PAYMENT_METHODS,
  formatDate, formatCurrency,
} from '../utils/soberLiving'

const TABS = [
  { id: 'overview',    label: 'Overview',    icon: Building2 },
  { id: 'bedmap',      label: 'Bed Map',     icon: BedDouble },
  { id: 'residents',   label: 'Residents',   icon: Users },
  { id: 'compliance',  label: 'Compliance',  icon: ClipboardList },
  { id: 'ua',          label: 'UA Tests',    icon: Beaker },
  { id: 'incidents',   label: 'Incidents',   icon: ShieldAlert },
  { id: 'rent',        label: 'Rent',        icon: DollarSign },
]

export default function SoberLivingHouse() {
  const { houseId } = useParams()
  const navigate    = useNavigate()

  const [tab, setTab]             = useState('overview')
  const [house, setHouse]         = useState(null)
  const [beds, setBeds]           = useState([])
  const [rooms, setRooms]         = useState([])
  const [residents, setResidents] = useState([])
  const [allResidents, setAllResidents] = useState([])
  const [incidents, setIncidents] = useState([])
  const [uaTests, setUATests]     = useState([])
  const [rentSummary, setRentSummary] = useState(null)
  const [loading, setLoading]     = useState(true)

  const [modal, setModal]         = useState(null)
  const [selectedBed, setSelectedBed]   = useState(null)
  const [expandedStay, setExpandedStay] = useState(null)
  const [ledgerData, setLedgerData]     = useState({})
  const [saving, setSaving]       = useState(false)

  // Forms
  const [roomForm, setRoomForm]     = useState({ room_name: '', floor: '', room_type: '', max_occupancy: 1, notes: '' })
  const [bedForm, setBedForm]       = useState({ bed_label: '', room_id: '', bed_status: 'available', notes: '' })
  const [residentForm, setResidentForm] = useState({
    first_name: '', last_name: '', phone: '', email: '',
    date_of_birth: '', sobriety_date: '',
    emergency_contact_name: '', emergency_contact_phone: '', emergency_contact_relationship: '',
    primary_substance: '', notes: '',
  })
  const [assignForm, setAssignForm] = useState({ resident_id: '', bed_id: '', move_in_date: '', case_manager_name: '', referral_source: '' })
  const [dischargeForm, setDischargeForm] = useState({ actual_move_out_date: '', move_out_reason: '', discharge_destination: '' })
  const [incidentForm, setIncidentForm] = useState({ incident_date: '', incident_type: '', severity: '', description: '', reported_by_name: '', location_in_house: '', response_taken: '' })
  const [uaForm, setUAForm] = useState({ test_date: '', result: '', administered_by_name: '', stay_id: '', resident_id: '', notes: '' })
  const [paymentForm, setPaymentForm] = useState({ stay_id: '', resident_id: '', amount: '', payment_method: 'Cash', payment_for_month: '', received_by: '', notes: '' })

  const load = async () => {
    setLoading(true)
    try {
      const [h, b, r, res, allRes] = await Promise.all([
        slApi.getHouse(houseId),
        slApi.listBeds(houseId),
        slApi.listRooms(houseId),
        slApi.listResidents(houseId),
        slApi.listAllResidents(),
      ])
      setHouse(h)
      setBeds(Array.isArray(b) ? b : [])
      setRooms(Array.isArray(r) ? r : [])
      setResidents(Array.isArray(res) ? res : [])
      setAllResidents(Array.isArray(allRes) ? allRes : [])
    } catch {
      toast.error('Failed to load house data')
    } finally {
      setLoading(false)
    }
  }

  const loadTabData = async (t) => {
    try {
      if (t === 'incidents') {
        const data = await slApi.listIncidents(houseId)
        setIncidents(Array.isArray(data) ? data : [])
      }
      if (t === 'ua') {
        const data = await slApi.listUATests(houseId)
        setUATests(Array.isArray(data) ? data : [])
      }
      if (t === 'rent') {
        const data = await slApi.getRentSummary(houseId)
        setRentSummary(data)
      }
    } catch {}
  }

  useEffect(() => { load() }, [houseId])
  useEffect(() => { loadTabData(tab) }, [tab])

  const loadLedger = async (stayId) => {
    if (ledgerData[stayId]) return
    try {
      const data = await slApi.getLedger(stayId)
      setLedgerData((prev) => ({ ...prev, [stayId]: data }))
    } catch {}
  }

  const handleTabChange = (t) => {
    setTab(t)
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleAddRoom = async (e) => {
    e.preventDefault()
    if (!roomForm.room_name.trim()) return toast.error('Room name required')
    setSaving(true)
    try {
      await slApi.createRoom(houseId, { ...roomForm, max_occupancy: parseInt(roomForm.max_occupancy) || 1 })
      toast.success('Room added')
      setModal(null)
      setRoomForm({ room_name: '', floor: '', room_type: '', max_occupancy: 1, notes: '' })
      load()
    } catch (err) { toast.error(err.message || 'Failed to add room') }
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
      setBedForm({ bed_label: '', room_id: '', bed_status: 'available', notes: '' })
      load()
    } catch (err) { toast.error(err.message || 'Failed to add bed') }
    finally { setSaving(false) }
  }

  const handleAddResident = async (e) => {
    e.preventDefault()
    if (!residentForm.first_name.trim() || !residentForm.last_name.trim()) return toast.error('Name required')
    setSaving(true)
    try {
      await slApi.createResident(residentForm)
      toast.success('Resident created')
      setModal(null)
      setResidentForm({
        first_name: '', last_name: '', phone: '', email: '',
        date_of_birth: '', sobriety_date: '',
        emergency_contact_name: '', emergency_contact_phone: '', emergency_contact_relationship: '',
        primary_substance: '', notes: '',
      })
      const allRes = await slApi.listAllResidents()
      setAllResidents(Array.isArray(allRes) ? allRes : [])
    } catch (err) { toast.error(err.message || 'Failed to create resident') }
    finally { setSaving(false) }
  }

  const handleAssign = async (e) => {
    e.preventDefault()
    if (!assignForm.resident_id) return toast.error('Select a resident')
    if (!assignForm.move_in_date) return toast.error('Move-in date required')
    setSaving(true)
    try {
      await slApi.createStay({
        resident_id:  assignForm.resident_id,
        house_id:     houseId,
        bed_id:       assignForm.bed_id || null,
        move_in_date: assignForm.move_in_date,
        case_manager_name: assignForm.case_manager_name || null,
        referral_source:   assignForm.referral_source || null,
      })
      toast.success('Stay created')
      setModal(null)
      setAssignForm({ resident_id: '', bed_id: '', move_in_date: '', case_manager_name: '', referral_source: '' })
      load()
    } catch (err) { toast.error(err.message || 'Failed to assign bed') }
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
      setDischargeForm({ actual_move_out_date: '', move_out_reason: '', discharge_destination: '' })
      load()
    } catch (err) { toast.error(err.message || 'Failed to discharge') }
    finally { setSaving(false) }
  }

  const handleUpdateBedStatus = async (bedId, status) => {
    try {
      await slApi.updateBed(bedId, { bed_status: status })
      toast.success('Bed status updated')
      setModal(null)
      load()
    } catch (err) { toast.error(err.message || 'Failed to update bed') }
  }

  const handleBedClick = (bed) => {
    setSelectedBed(bed)
    setModal('bed-detail')
  }

  const handleAddIncident = async (e) => {
    e.preventDefault()
    if (!incidentForm.incident_date || !incidentForm.incident_type) return toast.error('Date and type required')
    setSaving(true)
    try {
      await slApi.createIncident({ ...incidentForm, house_id: houseId })
      toast.success('Incident logged')
      setModal(null)
      setIncidentForm({ incident_date: '', incident_type: '', severity: '', description: '', reported_by_name: '', location_in_house: '', response_taken: '' })
      const data = await slApi.listIncidents(houseId)
      setIncidents(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to log incident') }
    finally { setSaving(false) }
  }

  const handleAddUATest = async (e) => {
    e.preventDefault()
    if (!uaForm.test_date || !uaForm.stay_id) return toast.error('Date and stay required')
    setSaving(true)
    try {
      await slApi.createUATest({ ...uaForm, house_id: houseId })
      toast.success('UA test logged')
      setModal(null)
      setUAForm({ test_date: '', result: '', administered_by_name: '', stay_id: '', resident_id: '', notes: '' })
      const data = await slApi.listUATests(houseId)
      setUATests(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to log UA test') }
    finally { setSaving(false) }
  }

  const handleAddPayment = async (e) => {
    e.preventDefault()
    if (!paymentForm.stay_id || !paymentForm.amount) return toast.error('Stay and amount required')
    setSaving(true)
    try {
      const resident = residents.find((r) => r.stay_id === paymentForm.stay_id)
      await slApi.createPayment({
        ...paymentForm,
        house_id:    houseId,
        resident_id: resident?.resident_id || paymentForm.resident_id,
        amount:      parseFloat(paymentForm.amount),
      })
      toast.success('Payment recorded')
      setModal(null)
      setPaymentForm({ stay_id: '', resident_id: '', amount: '', payment_method: 'Cash', payment_for_month: '', received_by: '', notes: '' })
      const data = await slApi.getRentSummary(houseId)
      setRentSummary(data)
      // Clear cached ledgers so they reload fresh
      setLedgerData({})
    } catch (err) { toast.error(err.message || 'Failed to record payment') }
    finally { setSaving(false) }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400">Loading...</div>
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
      <div className="flex items-start gap-4 mb-6">
        <button
          onClick={() => navigate('/sober-living')}
          className="mt-1 p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors shrink-0"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex-1">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">{house.house_name}</h1>
              {(house.city || house.address) && (
                <p className="text-sm text-slate-400 mt-0.5">
                  {house.address && `${house.address}, `}{house.city}{house.state && `, ${house.state}`}{house.zip_code && ` ${house.zip_code}`}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-500">
                {house.house_manager_phone && <span className="flex items-center gap-1"><Phone size={11} />{house.house_manager_phone}</span>}
                {house.house_manager_email && <span className="flex items-center gap-1"><Mail size={11} />{house.house_manager_email}</span>}
                {house.house_manager_name  && <span className="flex items-center gap-1"><User size={11} />{house.house_manager_name}</span>}
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={load} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-400 text-xs">
                <RefreshCw size={12} /> Refresh
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

      {/* Bed count summary bar */}
      <div className="flex gap-5 mb-6 flex-wrap">
        {[
          { key: 'available',   label: 'Available',   color: 'text-emerald-300' },
          { key: 'occupied',    label: 'Occupied',    color: 'text-rose-300'    },
          { key: 'reserved',    label: 'Reserved',    color: 'text-amber-300'   },
          { key: 'maintenance', label: 'Maintenance', color: 'text-slate-400'   },
        ].map(({ key, label, color }) => (counts[key] ?? 0) > 0 && (
          <div key={key} className={`text-sm ${color}`}>
            <span className="font-bold">{counts[key]}</span> {label}
          </div>
        ))}
        <div className="text-sm text-slate-500">
          <span className="font-bold">{counts.total ?? 0}</span> Total Beds
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-800/40 border border-slate-700/50 rounded-xl p-1 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => handleTabChange(id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm whitespace-nowrap transition-all ${
              tab === id
                ? 'bg-indigo-500 text-white font-medium'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/40'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview'   && <TabOverview house={house} counts={counts} residents={residents} />}
      {tab === 'bedmap'     && <TabBedMap beds={beds} onBedClick={handleBedClick} />}
      {tab === 'residents'  && (
        <TabResidents
          residents={residents}
          expandedStay={expandedStay}
          setExpandedStay={(stayId) => {
            setExpandedStay(stayId)
            if (stayId) loadLedger(stayId)
          }}
          ledgerData={ledgerData}
          onAddResident={() => setModal('add-resident')}
          onAssign={() => setModal('assign-bed')}
        />
      )}
      {tab === 'compliance' && <TabCompliance residents={residents} />}
      {tab === 'ua'         && <TabUA uaTests={uaTests} residents={residents} onAdd={() => setModal('add-ua')} />}
      {tab === 'incidents'  && <TabIncidents incidents={incidents} onAdd={() => setModal('add-incident')} />}
      {tab === 'rent'       && (
        <TabRent
          rentSummary={rentSummary}
          residents={residents}
          ledgerData={ledgerData}
          loadLedger={loadLedger}
          onAddPayment={() => setModal('add-payment')}
        />
      )}

      {/* ========================= MODALS ========================= */}

      {modal === 'add-room' && (
        <Modal title="Add Room" onClose={() => setModal(null)}>
          <form onSubmit={handleAddRoom} className="space-y-4">
            <Field label="Room Name *">
              <TInput value={roomForm.room_name} onChange={(e) => setRoomForm({ ...roomForm, room_name: e.target.value })} placeholder="Room 1, Upstairs West, etc." />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Floor">
                <TInput value={roomForm.floor} onChange={(e) => setRoomForm({ ...roomForm, floor: e.target.value })} placeholder="1st" />
              </Field>
              <Field label="Max Occupancy">
                <TInput type="number" min="1" value={roomForm.max_occupancy} onChange={(e) => setRoomForm({ ...roomForm, max_occupancy: e.target.value })} />
              </Field>
            </div>
            <Field label="Room Type">
              <TInput value={roomForm.room_type} onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })} placeholder="private, shared, etc." />
            </Field>
            <Field label="Notes">
              <TArea value={roomForm.notes} onChange={(e) => setRoomForm({ ...roomForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Add Room" />
          </form>
        </Modal>
      )}

      {modal === 'add-bed' && (
        <Modal title="Add Bed" onClose={() => setModal(null)}>
          <form onSubmit={handleAddBed} className="space-y-4">
            <Field label="Room *">
              <TSelect value={bedForm.room_id} onChange={(e) => setBedForm({ ...bedForm, room_id: e.target.value })}>
                <option value="">Select room...</option>
                {rooms.map((r) => (
                  <option key={r.room_id} value={r.room_id}>
                    {r.room_name}{r.floor ? ` (${r.floor})` : ''}
                  </option>
                ))}
              </TSelect>
            </Field>
            <Field label="Bed Label *">
              <TInput value={bedForm.bed_label} onChange={(e) => setBedForm({ ...bedForm, bed_label: e.target.value })} placeholder="Bed A, Top Bunk, etc." />
            </Field>
            <Field label="Initial Status">
              <TSelect value={bedForm.bed_status} onChange={(e) => setBedForm({ ...bedForm, bed_status: e.target.value })}>
                {BED_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </TSelect>
            </Field>
            <Field label="Notes">
              <TArea value={bedForm.notes} onChange={(e) => setBedForm({ ...bedForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Add Bed" />
          </form>
        </Modal>
      )}

      {modal === 'add-resident' && (
        <Modal title="Add Resident" onClose={() => setModal(null)}>
          <form onSubmit={handleAddResident} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="First Name *">
                <TInput value={residentForm.first_name} onChange={(e) => setResidentForm({ ...residentForm, first_name: e.target.value })} />
              </Field>
              <Field label="Last Name *">
                <TInput value={residentForm.last_name} onChange={(e) => setResidentForm({ ...residentForm, last_name: e.target.value })} />
              </Field>
              <Field label="Phone">
                <TInput value={residentForm.phone} onChange={(e) => setResidentForm({ ...residentForm, phone: e.target.value })} />
              </Field>
              <Field label="Email">
                <TInput value={residentForm.email} onChange={(e) => setResidentForm({ ...residentForm, email: e.target.value })} />
              </Field>
              <Field label="Date of Birth">
                <TInput type="date" value={residentForm.date_of_birth} onChange={(e) => setResidentForm({ ...residentForm, date_of_birth: e.target.value })} />
              </Field>
              <Field label="Sobriety Date">
                <TInput type="date" value={residentForm.sobriety_date} onChange={(e) => setResidentForm({ ...residentForm, sobriety_date: e.target.value })} />
              </Field>
              <Field label="Primary Substance">
                <TInput value={residentForm.primary_substance} onChange={(e) => setResidentForm({ ...residentForm, primary_substance: e.target.value })} placeholder="Alcohol, Opioids, etc." />
              </Field>
              <Field label="Emergency Contact">
                <TInput value={residentForm.emergency_contact_name} onChange={(e) => setResidentForm({ ...residentForm, emergency_contact_name: e.target.value })} placeholder="Name" />
              </Field>
              <Field label="Emergency Phone">
                <TInput value={residentForm.emergency_contact_phone} onChange={(e) => setResidentForm({ ...residentForm, emergency_contact_phone: e.target.value })} />
              </Field>
              <Field label="Relationship">
                <TInput value={residentForm.emergency_contact_relationship} onChange={(e) => setResidentForm({ ...residentForm, emergency_contact_relationship: e.target.value })} placeholder="Parent, Spouse, etc." />
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={residentForm.notes} onChange={(e) => setResidentForm({ ...residentForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Add Resident" />
          </form>
        </Modal>
      )}

      {modal === 'assign-bed' && (
        <Modal title="Assign Stay" onClose={() => setModal(null)}>
          <form onSubmit={handleAssign} className="space-y-4">
            <Field label="Resident *">
              <TSelect value={assignForm.resident_id} onChange={(e) => setAssignForm({ ...assignForm, resident_id: e.target.value })}>
                <option value="">Select resident...</option>
                {allResidents.map((r) => (
                  <option key={r.resident_id} value={r.resident_id}>
                    {r.first_name} {r.last_name}
                  </option>
                ))}
              </TSelect>
              {allResidents.length === 0 && (
                <p className="text-xs text-slate-500 mt-1">No residents found — add a resident first.</p>
              )}
            </Field>
            <Field label="Bed (optional)">
              <TSelect value={assignForm.bed_id} onChange={(e) => setAssignForm({ ...assignForm, bed_id: e.target.value })}>
                <option value="">No specific bed</option>
                {beds.filter((b) => b.bed_status === 'available').map((b) => (
                  <option key={b.bed_id} value={b.bed_id}>
                    {b.room_name ? `${b.room_name} / ` : ''}{b.bed_label}
                  </option>
                ))}
              </TSelect>
            </Field>
            <Field label="Move-in Date *">
              <TInput type="date" value={assignForm.move_in_date} onChange={(e) => setAssignForm({ ...assignForm, move_in_date: e.target.value })} />
            </Field>
            <Field label="Case Manager">
              <TInput value={assignForm.case_manager_name} onChange={(e) => setAssignForm({ ...assignForm, case_manager_name: e.target.value })} />
            </Field>
            <Field label="Referral Source">
              <TInput value={assignForm.referral_source} onChange={(e) => setAssignForm({ ...assignForm, referral_source: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Create Stay" />
          </form>
        </Modal>
      )}

      {modal === 'bed-detail' && selectedBed && (
        <Modal title={`Bed: ${selectedBed.bed_label}`} onClose={() => setModal(null)}>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded-full text-xs border ${BED_STATUS_COLORS[selectedBed.bed_status]?.bg} ${BED_STATUS_COLORS[selectedBed.bed_status]?.text} ${BED_STATUS_COLORS[selectedBed.bed_status]?.border}`}>
                {BED_STATUS_LABELS[selectedBed.bed_status] || selectedBed.bed_status}
              </span>
              {selectedBed.room_name && <span className="text-xs text-slate-400">{selectedBed.room_name}</span>}
            </div>

            {selectedBed.bed_status === 'occupied' && selectedBed.first_name && (
              <div className="bg-slate-700/40 rounded-lg p-3 text-sm">
                <p className="text-white font-medium">{selectedBed.first_name} {selectedBed.last_name}</p>
                <p className="text-slate-400 text-xs mt-1">Active stay</p>
              </div>
            )}

            {selectedBed.notes && <p className="text-xs text-slate-400">{selectedBed.notes}</p>}

            <div>
              <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-2">Change Status</p>
              <div className="grid grid-cols-2 gap-2">
                {BED_STATUS_OPTIONS.filter((o) => o.value !== selectedBed.bed_status).map((o) => (
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

            {selectedBed.bed_status === 'occupied' && selectedBed.stay_id && (
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

      {modal === 'discharge' && selectedBed && (
        <Modal title="Discharge Resident" onClose={() => setModal('bed-detail')}>
          <form onSubmit={handleDischarge} className="space-y-4">
            <Field label="Move-out Date">
              <TInput type="date" value={dischargeForm.actual_move_out_date} onChange={(e) => setDischargeForm({ ...dischargeForm, actual_move_out_date: e.target.value })} />
            </Field>
            <Field label="Reason">
              <TSelect value={dischargeForm.move_out_reason} onChange={(e) => setDischargeForm({ ...dischargeForm, move_out_reason: e.target.value })}>
                <option value="">Select reason...</option>
                {DISCHARGE_REASON_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </TSelect>
            </Field>
            <Field label="Discharge Destination">
              <TInput value={dischargeForm.discharge_destination} onChange={(e) => setDischargeForm({ ...dischargeForm, discharge_destination: e.target.value })} placeholder="Family home, permanent housing, etc." />
            </Field>
            <MFooter onCancel={() => setModal('bed-detail')} saving={saving} label="Confirm Discharge" submitClass="bg-rose-500 hover:bg-rose-600" />
          </form>
        </Modal>
      )}

      {modal === 'add-incident' && (
        <Modal title="Log Incident" onClose={() => setModal(null)}>
          <form onSubmit={handleAddIncident} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Date *">
                <TInput type="date" value={incidentForm.incident_date} onChange={(e) => setIncidentForm({ ...incidentForm, incident_date: e.target.value })} />
              </Field>
              <Field label="Type *">
                <TSelect value={incidentForm.incident_type} onChange={(e) => setIncidentForm({ ...incidentForm, incident_type: e.target.value })}>
                  <option value="">Select...</option>
                  {INCIDENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </TSelect>
              </Field>
              <Field label="Severity">
                <TSelect value={incidentForm.severity} onChange={(e) => setIncidentForm({ ...incidentForm, severity: e.target.value })}>
                  <option value="">Select...</option>
                  {['low','medium','high','critical'].map((s) => <option key={s} value={s}>{s}</option>)}
                </TSelect>
              </Field>
              <Field label="Location in House">
                <TInput value={incidentForm.location_in_house} onChange={(e) => setIncidentForm({ ...incidentForm, location_in_house: e.target.value })} />
              </Field>
              <Field label="Reported By">
                <TInput value={incidentForm.reported_by_name} onChange={(e) => setIncidentForm({ ...incidentForm, reported_by_name: e.target.value })} />
              </Field>
            </div>
            <Field label="Description">
              <TArea rows={3} value={incidentForm.description} onChange={(e) => setIncidentForm({ ...incidentForm, description: e.target.value })} />
            </Field>
            <Field label="Response Taken">
              <TArea rows={2} value={incidentForm.response_taken} onChange={(e) => setIncidentForm({ ...incidentForm, response_taken: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Log Incident" />
          </form>
        </Modal>
      )}

      {modal === 'add-ua' && (
        <Modal title="Log UA Test" onClose={() => setModal(null)}>
          <form onSubmit={handleAddUATest} className="space-y-4">
            <Field label="Resident Stay *">
              <TSelect value={uaForm.stay_id} onChange={(e) => {
                const res = residents.find((r) => r.stay_id === e.target.value)
                setUAForm({ ...uaForm, stay_id: e.target.value, resident_id: res?.resident_id || '' })
              }}>
                <option value="">Select resident...</option>
                {residents.map((r) => (
                  <option key={r.stay_id} value={r.stay_id}>{r.first_name} {r.last_name}</option>
                ))}
              </TSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Test Date *">
                <TInput type="date" value={uaForm.test_date} onChange={(e) => setUAForm({ ...uaForm, test_date: e.target.value })} />
              </Field>
              <Field label="Result">
                <TSelect value={uaForm.result} onChange={(e) => setUAForm({ ...uaForm, result: e.target.value })}>
                  <option value="">Select...</option>
                  {['negative','positive','dilute','refused','not_completed'].map((r) => (
                    <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
                  ))}
                </TSelect>
              </Field>
              <Field label="Administered By">
                <TInput value={uaForm.administered_by_name} onChange={(e) => setUAForm({ ...uaForm, administered_by_name: e.target.value })} />
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={uaForm.notes} onChange={(e) => setUAForm({ ...uaForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Log Test" />
          </form>
        </Modal>
      )}

      {modal === 'add-payment' && (
        <Modal title="Record Payment" onClose={() => setModal(null)}>
          <form onSubmit={handleAddPayment} className="space-y-4">
            <Field label="Resident Stay *">
              <TSelect value={paymentForm.stay_id} onChange={(e) => {
                const res = residents.find((r) => r.stay_id === e.target.value)
                setPaymentForm({ ...paymentForm, stay_id: e.target.value, resident_id: res?.resident_id || '' })
              }}>
                <option value="">Select resident...</option>
                {residents.map((r) => (
                  <option key={r.stay_id} value={r.stay_id}>{r.first_name} {r.last_name}</option>
                ))}
              </TSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Amount ($) *">
                <TInput type="number" min="0" step="0.01" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} />
              </Field>
              <Field label="Method">
                <TSelect value={paymentForm.payment_method} onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}>
                  {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                </TSelect>
              </Field>
              <Field label="For Month (YYYY-MM)">
                <TInput value={paymentForm.payment_for_month} onChange={(e) => setPaymentForm({ ...paymentForm, payment_for_month: e.target.value })} placeholder="2026-06" />
              </Field>
              <Field label="Received By">
                <TInput value={paymentForm.received_by} onChange={(e) => setPaymentForm({ ...paymentForm, received_by: e.target.value })} />
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={paymentForm.notes} onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Record Payment" submitClass="bg-emerald-500 hover:bg-emerald-600" />
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab panels
// ---------------------------------------------------------------------------

function TabOverview({ house, counts, residents }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">House Details</h3>
        <dl className="space-y-2 text-sm">
          {[
            ['Type', house.house_type],
            ['Certification', house.certification_level],
            ['Affiliated Program', house.affiliated_clinical_program],
            ['Monthly Rent', house.monthly_rent ? `$${Number(house.monthly_rent).toLocaleString()}` : null],
            ['House Rules Version', house.house_rules_version],
          ].filter(([, v]) => v).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <dt className="text-slate-400">{k}</dt>
              <dd className="text-white text-right">{v}</dd>
            </div>
          ))}
          {house.notes && (
            <div className="pt-2 border-t border-slate-700/50">
              <dt className="text-slate-400 mb-1">Notes</dt>
              <dd className="text-slate-300">{house.notes}</dd>
            </div>
          )}
        </dl>
      </div>

      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Capacity</h3>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Total Beds',   value: counts.total ?? 0,       color: 'text-white'        },
            { label: 'Available',    value: counts.available ?? 0,   color: 'text-emerald-300'  },
            { label: 'Occupied',     value: counts.occupied ?? 0,    color: 'text-rose-300'     },
            { label: 'Reserved',     value: counts.reserved ?? 0,    color: 'text-amber-300'    },
            { label: 'Maintenance',  value: counts.maintenance ?? 0, color: 'text-slate-400'    },
            { label: 'Active Stays', value: residents.length,        color: 'text-indigo-300'   },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-slate-700/30 rounded-lg p-3">
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-slate-400 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function TabBedMap({ beds, onBedClick }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <BedMap beds={beds} onBedClick={onBedClick} />
    </div>
  )
}

function TabResidents({ residents, expandedStay, setExpandedStay, ledgerData, onAddResident, onAssign }) {
  if (residents.length === 0) {
    return (
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-10 text-center">
        <Users size={36} className="mx-auto text-slate-600 mb-3" />
        <p className="text-slate-400 mb-4">No active residents in this house.</p>
        <div className="flex justify-center gap-2">
          <button onClick={onAddResident} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">Add Resident</button>
          <button onClick={onAssign} className="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm">Assign Stay</button>
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {residents.map((r) => {
        const isOpen = expandedStay === r.stay_id
        const ledger = ledgerData[r.stay_id]
        return (
          <div key={r.resident_id} className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            <button
              onClick={() => setExpandedStay(isOpen ? null : r.stay_id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/20 transition-colors text-left"
            >
              <div className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                  <User size={14} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{r.first_name} {r.last_name}</p>
                  <p className="text-xs text-slate-400">
                    {r.room_name ? `${r.room_name}` : ''}
                    {r.bed_label ? ` / ${r.bed_label}` : ''}
                    {r.move_in_date ? ` · In since ${formatDate(r.move_in_date)}` : ''}
                    {r.phone ? ` · ${r.phone}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-3">
                <span className="text-xs text-slate-500 flex items-center gap-1"><DollarSign size={11} /> Ledger</span>
                {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
              </div>
            </button>

            {isOpen && (
              <div className="border-t border-slate-700/50 px-4 py-4 bg-slate-800/40">
                {!ledger ? (
                  <p className="text-sm text-slate-400">Loading ledger...</p>
                ) : (
                  <div>
                    <div className="flex gap-4 mb-4 flex-wrap">
                      <div className="bg-slate-700/40 rounded-lg px-4 py-2">
                        <div className="text-xs text-slate-400">Total Charged</div>
                        <div className="text-lg font-bold text-white">{formatCurrency(ledger.total_charged)}</div>
                      </div>
                      <div className="bg-slate-700/40 rounded-lg px-4 py-2">
                        <div className="text-xs text-slate-400">Total Paid</div>
                        <div className="text-lg font-bold text-emerald-300">{formatCurrency(ledger.total_paid)}</div>
                      </div>
                      <div className="bg-slate-700/40 rounded-lg px-4 py-2">
                        <div className="text-xs text-slate-400">Balance</div>
                        <div className={`text-lg font-bold ${(ledger.balance ?? 0) > 0 ? 'text-rose-300' : 'text-emerald-300'}`}>
                          {formatCurrency(ledger.balance)}
                        </div>
                      </div>
                    </div>
                    {ledger.payments.length === 0 ? (
                      <p className="text-xs text-slate-500">No payments recorded yet.</p>
                    ) : (
                      <div className="space-y-1">
                        {ledger.payments.map((p) => (
                          <div key={p.payment_id} className="flex items-center justify-between text-xs text-slate-300 bg-slate-700/30 rounded px-3 py-2">
                            <span>{formatDate(p.payment_date)} — {p.payment_method || 'Unknown'}</span>
                            <span className="text-emerald-300 font-medium">{formatCurrency(p.amount)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function TabCompliance({ residents }) {
  if (residents.length === 0) {
    return <EmptyTab message="No active residents — compliance tracking requires at least one active stay." />
  }
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
      <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
        <ClipboardList size={16} className="text-indigo-400" />
        Document Compliance
      </h3>
      <div className="space-y-3">
        {residents.map((r) => (
          <div key={r.resident_id} className="bg-slate-700/30 rounded-lg p-4">
            <p className="font-medium text-white text-sm mb-2">{r.first_name} {r.last_name}</p>
            <p className="text-xs text-slate-400">
              Compliance checklist UI coming in next phase. Stay ID: <code className="text-indigo-300">{r.stay_id?.slice(0, 8)}…</code>
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

function TabUA({ uaTests, residents, onAdd }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Beaker size={16} className="text-indigo-400" />
          UA Tests ({uaTests.length})
        </h3>
        {residents.length > 0 && (
          <button onClick={onAdd} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
            <Plus size={12} /> Log Test
          </button>
        )}
      </div>
      {uaTests.length === 0 ? (
        <EmptyTab message="No UA tests logged yet." />
      ) : (
        <div className="space-y-2">
          {uaTests.map((t) => (
            <div key={t.test_id} className="bg-slate-700/30 rounded-lg px-4 py-3 flex items-center justify-between text-sm">
              <div>
                <p className="text-white font-medium">{formatDate(t.test_date)}</p>
                <p className="text-xs text-slate-400">{t.administered_by_name || 'Unknown administrator'}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full border ${
                t.result === 'negative' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' :
                t.result === 'positive' ? 'bg-rose-500/10 text-rose-300 border-rose-500/30' :
                'bg-amber-500/10 text-amber-300 border-amber-500/30'
              }`}>
                {t.result?.replace(/_/g, ' ') || 'Pending'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TabIncidents({ incidents, onAdd }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <ShieldAlert size={16} className="text-indigo-400" />
          Incidents ({incidents.length})
        </h3>
        <button onClick={onAdd} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
          <Plus size={12} /> Log Incident
        </button>
      </div>
      {incidents.length === 0 ? (
        <EmptyTab message="No incidents logged." />
      ) : (
        <div className="space-y-2">
          {incidents.map((inc) => (
            <div key={inc.incident_id} className="bg-slate-700/30 rounded-lg px-4 py-3 text-sm">
              <div className="flex items-center justify-between mb-1">
                <p className="text-white font-medium">{inc.incident_type.replace(/_/g, ' ')}</p>
                <span className="text-xs text-slate-400">{formatDate(inc.incident_date)}</span>
              </div>
              {inc.description && <p className="text-xs text-slate-400 truncate">{inc.description}</p>}
              {inc.severity && (
                <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${
                  inc.severity === 'critical' ? 'bg-rose-500/20 text-rose-300' :
                  inc.severity === 'high'     ? 'bg-orange-500/20 text-orange-300' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                  {inc.severity}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TabRent({ rentSummary, residents, ledgerData, loadLedger, onAddPayment }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <DollarSign size={16} className="text-indigo-400" />
          Rent Summary
        </h3>
        {residents.length > 0 && (
          <button onClick={onAddPayment} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium">
            <Plus size={12} /> Record Payment
          </button>
        )}
      </div>
      {!rentSummary || rentSummary.residents.length === 0 ? (
        <EmptyTab message="No active residents with rent data." />
      ) : (
        <div className="space-y-3">
          {rentSummary.residents.map((r) => (
            <div key={r.resident_id} className="bg-slate-700/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="font-medium text-white text-sm">{r.first_name} {r.last_name}</p>
                <div className="flex gap-3 text-xs">
                  <span className="text-slate-400">Charged: <span className="text-white">{formatCurrency(r.total_charged)}</span></span>
                  <span className="text-slate-400">Paid: <span className="text-emerald-300">{formatCurrency(r.total_paid)}</span></span>
                </div>
              </div>
              <button
                onClick={() => loadLedger(r.stay_id)}
                className="text-xs text-indigo-400 hover:text-indigo-300"
              >
                {ledgerData[r.stay_id] ? 'Ledger loaded ✓' : 'Load full ledger →'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function EmptyTab({ message }) {
  return (
    <div className="text-center py-10 text-slate-400 text-sm">{message}</div>
  )
}

// ---------------------------------------------------------------------------
// Shared modal components
// ---------------------------------------------------------------------------

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-slate-700 shrink-0">
          <h2 className="font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  )
}

function MFooter({ onCancel, saving, label, submitClass = 'bg-indigo-500 hover:bg-indigo-600' }) {
  return (
    <div className="flex justify-end gap-3 pt-1">
      <button type="button" onClick={onCancel} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
        Cancel
      </button>
      <button type="submit" disabled={saving} className={`px-4 py-2 rounded-lg ${submitClass} text-white text-sm font-medium disabled:opacity-50`}>
        {saving ? 'Saving...' : label}
      </button>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      {children}
    </div>
  )
}

function TInput({ value, onChange, placeholder, type = 'text', maxLength, min, step }) {
  return (
    <input
      type={type} value={value} onChange={onChange} placeholder={placeholder}
      maxLength={maxLength} min={min} step={step}
      className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
    />
  )
}

function TSelect({ value, onChange, children }) {
  return (
    <select
      value={value} onChange={onChange}
      className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
    >
      {children}
    </select>
  )
}

function TArea({ value, onChange, rows = 2 }) {
  return (
    <textarea
      value={value} onChange={onChange} rows={rows}
      className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
    />
  )
}
