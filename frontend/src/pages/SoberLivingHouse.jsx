import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, BedDouble, Users, Plus, RefreshCw,
  Home, Phone, Mail, User, AlertCircle, ChevronDown, ChevronRight,
  DollarSign, ClipboardList, Beaker, ShieldAlert, Building2,
  CheckCircle2, Circle, CheckSquare, Square, X, Edit3,
  Receipt, TrendingDown, LayoutDashboard, CalendarDays,
  ListChecks, Footprints, Moon, Clock, CheckCheck,
  AlertTriangle, Ban,
} from 'lucide-react'
import toast from 'react-hot-toast'
import BedMap from '../components/BedMap'
import {
  slApi,
  BED_STATUS_COLORS, BED_STATUS_LABELS, BED_STATUS_OPTIONS,
  DISCHARGE_REASON_OPTIONS, INCIDENT_TYPES, PAYMENT_METHODS,
  CERTIFICATION_OPTIONS, PAYMENT_TYPE_OPTIONS,
  formatDate, formatCurrency,
} from '../utils/soberLiving'

const TABS = [
  { id: 'dashboard',   label: 'Dashboard',   icon: LayoutDashboard },
  { id: 'overview',    label: 'Overview',    icon: Building2 },
  { id: 'bedmap',      label: 'Bed Map',     icon: BedDouble },
  { id: 'residents',   label: 'Residents',   icon: Users },
  { id: 'compliance',  label: 'Compliance',  icon: ClipboardList },
  { id: 'ua',          label: 'UA Tests',    icon: Beaker },
  { id: 'incidents',   label: 'Incidents',   icon: ShieldAlert },
  { id: 'rent',        label: 'Rent',        icon: DollarSign },
  { id: 'meetings',    label: 'Meetings',    icon: CalendarDays },
  { id: 'chores',      label: 'Chores',      icon: ListChecks },
  { id: 'passes',      label: 'Passes',      icon: Footprints },
  { id: 'curfew',      label: 'Curfew',      icon: Moon },
]

const MEETING_TYPES   = ['house', 'aa', 'na', 'clinical', 'staff', 'other']
const PASS_TYPES      = ['day', 'overnight', 'weekend', 'extended']
const CURFEW_STATUSES = ['present', 'absent', 'on_pass', 'unexcused']
const RECURRENCE_OPTIONS = ['once', 'daily', 'weekly', 'biweekly', 'monthly']

const todayStr = () => new Date().toISOString().slice(0, 10)

// Compliance checklist field definitions
const CHECKLIST_FIELDS = [
  { key: 'house_rules_signed',               label: 'House Rules Signed',                hasDate: true },
  { key: 'photo_id_on_file',                 label: 'Photo ID on File',                  hasDate: false },
  { key: 'emergency_contact_on_file',        label: 'Emergency Contact on File',          hasDate: false },
  { key: 'intake_form_complete',             label: 'Intake Form Complete',               hasDate: false },
  { key: 'consent_to_coordinate_care',       label: 'Consent to Coordinate Care',         hasDate: false },
  { key: 'medication_policy_signed',         label: 'Medication Policy Signed',           hasDate: false },
  { key: 'ua_policy_signed',                 label: 'UA Policy Signed',                   hasDate: false },
  { key: 'financial_agreement_signed',       label: 'Financial Agreement Signed',         hasDate: false },
  { key: 'grievance_policy_acknowledged',    label: 'Grievance Policy Acknowledged',      hasDate: false },
  { key: 'good_neighbor_policy_acknowledged',label: 'Good Neighbor Policy Acknowledged',  hasDate: false },
  { key: 'release_of_information_on_file',   label: 'Release of Information on File',     hasDate: false },
]

const BOOL_KEYS = CHECKLIST_FIELDS.map((f) => f.key)

const UA_RESULTS = ['negative', 'positive', 'dilute', 'refused', 'not_completed']

const CHARGE_TYPES = ['rent', 'late_fee', 'deposit', 'damage', 'other']

const SEVERITY_COLORS = {
  critical: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  high:     'bg-orange-500/20 text-orange-300 border-orange-500/30',
  medium:   'bg-amber-500/20 text-amber-300 border-amber-500/30',
  low:      'bg-slate-500/20 text-slate-300 border-slate-500/30',
}

export default function SoberLivingHouse() {
  const { houseId } = useParams()
  const navigate    = useNavigate()

  const [tab, setTab]             = useState('dashboard')
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

  // Compliance state keyed by stay_id
  const [complianceData, setComplianceData] = useState({})
  const [complianceDraft, setComplianceDraft] = useState({})
  const [complianceSaving, setComplianceSaving] = useState({})

  // Incident expand/edit state
  const [expandedIncident, setExpandedIncident] = useState(null)
  const [incidentEditForm, setIncidentEditForm] = useState({})
  const [incidentSaving, setIncidentSaving] = useState(false)

  // UA expand state
  const [expandedUA, setExpandedUA] = useState(null)

  // Ledger expand state (for rent tab)
  const [expandedLedger, setExpandedLedger] = useState(null)

  // Phase 3 state
  const [dashboard, setDashboard]   = useState(null)
  const [meetings, setMeetings]     = useState([])
  const [chores, setChores]         = useState([])
  const [passes, setPasses]         = useState([])
  const [curfewChecks, setCurfewChecks] = useState([])
  const [curfewDate, setCurfewDate] = useState(todayStr())
  const [choreDate, setChoreDate]   = useState('')

  // Phase 3 forms
  const [meetingForm, setMeetingForm] = useState({
    scheduled_date: '', scheduled_time: '', meeting_type: 'house',
    topic: '', facilitator_name: '', location: '', notes: '',
  })
  const [choreForm, setChoreForm] = useState({
    chore_name: '', resident_id: '', stay_id: '', location: '',
    due_date: todayStr(), recurrence: 'once', assigned_by: '', notes: '',
  })
  const [passForm, setPassForm] = useState({
    resident_id: '', stay_id: '', pass_type: 'day', destination: '',
    leave_date: todayStr(), leave_time: '', expected_return_date: '', expected_return_time: '',
    approved_by: '', is_blackout: false, notes: '',
  })

  // Pass return form (separate, opened from pass row)
  const [selectedPass, setSelectedPass] = useState(null)
  const [returnForm, setReturnForm] = useState({ actual_return_date: todayStr(), actual_return_time: '' })

  // Quick Add Beds form
  const [quickBedForm, setQuickBedForm] = useState({ room_id: '', quantity: 1, label_prefix: '', start_number: 1, bed_status: 'available' })
  const [quickBedSaving, setQuickBedSaving] = useState(false)

  // Meeting attendance editing
  const [attendanceModal, setAttendanceModal] = useState(null) // meeting object

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
  const [incidentForm, setIncidentForm] = useState({
    incident_date: '', incident_type: '', severity: '', description: '',
    reported_by_name: '', location_in_house: '', response_taken: '',
    immediate_safety_concern: false,
  })
  const [uaForm, setUAForm] = useState({
    test_date: '', result: '', administered_by_name: '',
    stay_id: '', resident_id: '', test_type: '', test_method: '', notes: '',
  })
  const [paymentForm, setPaymentForm] = useState({
    stay_id: '', resident_id: '', amount: '', payment_method: 'Cash',
    payment_for_month: '', received_by: '', notes: '',
  })
  const [chargeForm, setChargeForm] = useState({
    stay_id: '', resident_id: '', amount: '', charge_type: 'rent',
    charge_month: '', due_date: '', notes: '',
  })

  const load = useCallback(async () => {
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
  }, [houseId])

  const loadTabData = useCallback(async (t) => {
    try {
      if (t === 'dashboard') {
        const data = await slApi.getDashboard(houseId)
        setDashboard(data)
      }
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
      if (t === 'meetings') {
        const data = await slApi.listMeetings(houseId)
        setMeetings(Array.isArray(data) ? data : [])
      }
      if (t === 'chores') {
        const data = await slApi.listChores(houseId, choreDate || undefined)
        setChores(Array.isArray(data) ? data : [])
      }
      if (t === 'passes') {
        const data = await slApi.listPasses(houseId)
        setPasses(Array.isArray(data) ? data : [])
      }
      if (t === 'curfew') {
        const data = await slApi.listCurfew(houseId, curfewDate)
        setCurfewChecks(Array.isArray(data) ? data : [])
      }
    } catch {}
  }, [houseId, curfewDate, choreDate])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadTabData(tab) }, [tab, loadTabData])

  const loadLedger = useCallback(async (stayId) => {
    if (ledgerData[stayId]) return
    try {
      const data = await slApi.getLedger(stayId)
      setLedgerData((prev) => ({ ...prev, [stayId]: data }))
    } catch {}
  }, [ledgerData])

  const reloadLedger = useCallback(async (stayId) => {
    try {
      const data = await slApi.getLedger(stayId)
      setLedgerData((prev) => ({ ...prev, [stayId]: data }))
    } catch {}
  }, [])

  const loadCompliance = useCallback(async (stayId) => {
    if (complianceData[stayId] !== undefined) return
    try {
      const data = await slApi.getCompliance(stayId)
      const checklist = data || {}
      setComplianceData((prev) => ({ ...prev, [stayId]: checklist }))
      // Initialize draft from server state
      const draft = {}
      BOOL_KEYS.forEach((k) => { draft[k] = checklist[k] ? 1 : 0 })
      draft.house_rules_signed_date = checklist.house_rules_signed_date || ''
      draft.missing_items_summary = checklist.missing_items_summary || ''
      setComplianceDraft((prev) => ({ ...prev, [stayId]: draft }))
    } catch {
      setComplianceData((prev) => ({ ...prev, [stayId]: null }))
    }
  }, [complianceData])

  const handleTabChange = (t) => setTab(t)

  // ---------------------------------------------------------------------------
  // Handlers — House management
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

  const handleQuickAddBeds = async (e) => {
    e.preventDefault()
    if (!quickBedForm.room_id) return toast.error('Select a room')
    if (!quickBedForm.quantity || quickBedForm.quantity < 1) return toast.error('Quantity must be at least 1')
    setQuickBedSaving(true)
    try {
      await slApi.bulkCreateBeds(houseId, {
        room_id:      quickBedForm.room_id,
        quantity:     parseInt(quickBedForm.quantity) || 1,
        label_prefix: quickBedForm.label_prefix || '',
        start_number: parseInt(quickBedForm.start_number) || 1,
        bed_status:   quickBedForm.bed_status,
      })
      toast.success(`${quickBedForm.quantity} bed${quickBedForm.quantity > 1 ? 's' : ''} created`)
      setModal(null)
      setQuickBedForm({ room_id: '', quantity: 1, label_prefix: '', start_number: 1, bed_status: 'available' })
      load()
    } catch (err) { toast.error(err.message || 'Failed to create beds') }
    finally { setQuickBedSaving(false) }
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
        resident_id:       assignForm.resident_id,
        house_id:          houseId,
        bed_id:            assignForm.bed_id || null,
        move_in_date:      assignForm.move_in_date,
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

  // ---------------------------------------------------------------------------
  // Handlers — Incidents
  // ---------------------------------------------------------------------------

  const handleAddIncident = async (e) => {
    e.preventDefault()
    if (!incidentForm.incident_date || !incidentForm.incident_type) return toast.error('Date and type required')
    setSaving(true)
    try {
      await slApi.createIncident({
        ...incidentForm,
        house_id: houseId,
        immediate_safety_concern: incidentForm.immediate_safety_concern ? 1 : 0,
      })
      toast.success('Incident logged')
      setModal(null)
      setIncidentForm({
        incident_date: '', incident_type: '', severity: '', description: '',
        reported_by_name: '', location_in_house: '', response_taken: '',
        immediate_safety_concern: false,
      })
      const data = await slApi.listIncidents(houseId)
      setIncidents(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to log incident') }
    finally { setSaving(false) }
  }

  const handleExpandIncident = (inc) => {
    if (expandedIncident === inc.incident_id) {
      setExpandedIncident(null)
      return
    }
    setExpandedIncident(inc.incident_id)
    setIncidentEditForm({
      response_taken:   inc.response_taken || '',
      resolution_notes: inc.resolution_notes || '',
      follow_up_required:  inc.follow_up_required ? true : false,
      follow_up_due_date:  inc.follow_up_due_date || '',
      incident_resolved:   inc.incident_resolved ? true : false,
    })
  }

  const handleUpdateIncident = async (incidentId) => {
    setIncidentSaving(true)
    try {
      const payload = {
        ...incidentEditForm,
        follow_up_required: incidentEditForm.follow_up_required ? 1 : 0,
        incident_resolved:  incidentEditForm.incident_resolved ? 1 : 0,
      }
      await slApi.updateIncident(incidentId, payload)
      toast.success('Incident updated')
      setExpandedIncident(null)
      const data = await slApi.listIncidents(houseId)
      setIncidents(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to update incident') }
    finally { setIncidentSaving(false) }
  }

  // ---------------------------------------------------------------------------
  // Handlers — UA Tests
  // ---------------------------------------------------------------------------

  const handleAddUATest = async (e) => {
    e.preventDefault()
    if (!uaForm.test_date || !uaForm.stay_id) return toast.error('Date and stay required')
    setSaving(true)
    try {
      await slApi.createUATest({ ...uaForm, house_id: houseId })
      toast.success('UA test logged')
      setModal(null)
      setUAForm({ test_date: '', result: '', administered_by_name: '', stay_id: '', resident_id: '', test_type: '', test_method: '', notes: '' })
      const data = await slApi.listUATests(houseId)
      setUATests(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to log UA test') }
    finally { setSaving(false) }
  }

  // ---------------------------------------------------------------------------
  // Handlers — Compliance
  // ---------------------------------------------------------------------------

  const handleToggleCompliance = (stayId, key) => {
    setComplianceDraft((prev) => {
      const draft = { ...(prev[stayId] || {}) }
      draft[key] = draft[key] ? 0 : 1
      return { ...prev, [stayId]: draft }
    })
  }

  const handleSaveCompliance = async (stayId) => {
    setComplianceSaving((prev) => ({ ...prev, [stayId]: true }))
    try {
      const draft = complianceDraft[stayId] || {}
      await slApi.updateCompliance(stayId, draft)
      toast.success('Checklist saved')
      // Refresh from server
      const data = await slApi.getCompliance(stayId)
      const checklist = data || {}
      setComplianceData((prev) => ({ ...prev, [stayId]: checklist }))
      const updated = {}
      BOOL_KEYS.forEach((k) => { updated[k] = checklist[k] ? 1 : 0 })
      updated.house_rules_signed_date = checklist.house_rules_signed_date || ''
      updated.missing_items_summary = checklist.missing_items_summary || ''
      setComplianceDraft((prev) => ({ ...prev, [stayId]: updated }))
    } catch (err) { toast.error(err.message || 'Failed to save checklist') }
    finally { setComplianceSaving((prev) => ({ ...prev, [stayId]: false })) }
  }

  // ---------------------------------------------------------------------------
  // Handlers — Rent
  // ---------------------------------------------------------------------------

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
      if (expandedLedger) reloadLedger(expandedLedger)
    } catch (err) { toast.error(err.message || 'Failed to record payment') }
    finally { setSaving(false) }
  }

  const handleAddCharge = async (e) => {
    e.preventDefault()
    if (!chargeForm.stay_id || !chargeForm.amount) return toast.error('Stay and amount required')
    setSaving(true)
    try {
      const resident = residents.find((r) => r.stay_id === chargeForm.stay_id)
      await slApi.createCharge({
        ...chargeForm,
        house_id:    houseId,
        resident_id: resident?.resident_id || chargeForm.resident_id,
        amount:      parseFloat(chargeForm.amount),
      })
      toast.success('Charge added')
      setModal(null)
      setChargeForm({ stay_id: '', resident_id: '', amount: '', charge_type: 'rent', charge_month: '', due_date: '', notes: '' })
      const data = await slApi.getRentSummary(houseId)
      setRentSummary(data)
      if (expandedLedger) reloadLedger(expandedLedger)
    } catch (err) { toast.error(err.message || 'Failed to add charge') }
    finally { setSaving(false) }
  }

  const handleToggleLedger = (stayId) => {
    if (expandedLedger === stayId) {
      setExpandedLedger(null)
    } else {
      setExpandedLedger(stayId)
      reloadLedger(stayId)
    }
  }

  // ---------------------------------------------------------------------------
  // Phase 3 handlers
  // ---------------------------------------------------------------------------

  const handleAddMeeting = async (e) => {
    e.preventDefault()
    if (!meetingForm.scheduled_date) return toast.error('Date required')
    setSaving(true)
    try {
      await slApi.createMeeting({ ...meetingForm, house_id: houseId })
      toast.success('Meeting scheduled')
      setModal(null)
      setMeetingForm({ scheduled_date: '', scheduled_time: '', meeting_type: 'house', topic: '', facilitator_name: '', location: '', notes: '' })
      const data = await slApi.listMeetings(houseId)
      setMeetings(Array.isArray(data) ? data : [])
      const dash = await slApi.getDashboard(houseId)
      setDashboard(dash)
    } catch (err) { toast.error(err.message || 'Failed to schedule meeting') }
    finally { setSaving(false) }
  }

  const handleMeetingStatus = async (meetingId, status) => {
    try {
      await slApi.updateMeeting(meetingId, { status })
      const data = await slApi.listMeetings(houseId)
      setMeetings(Array.isArray(data) ? data : [])
      const dash = await slApi.getDashboard(houseId)
      setDashboard(dash)
    } catch (err) { toast.error(err.message || 'Failed to update meeting') }
  }

  const handleSaveAttendance = async (meeting, attendanceJson) => {
    try {
      await slApi.updateMeeting(meeting.meeting_id, { status: 'completed', attendance_json: attendanceJson })
      toast.success('Attendance saved')
      setAttendanceModal(null)
      const data = await slApi.listMeetings(houseId)
      setMeetings(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to save attendance') }
  }

  const handleAddChore = async (e) => {
    e.preventDefault()
    if (!choreForm.chore_name.trim() || !choreForm.due_date) return toast.error('Name and date required')
    setSaving(true)
    try {
      const payload = { ...choreForm, house_id: houseId }
      if (!payload.resident_id) { delete payload.resident_id; delete payload.stay_id }
      await slApi.createChore(payload)
      toast.success('Chore assigned')
      setModal(null)
      setChoreForm({ chore_name: '', resident_id: '', stay_id: '', location: '', due_date: todayStr(), recurrence: 'once', assigned_by: '', notes: '' })
      const data = await slApi.listChores(houseId, choreDate || undefined)
      setChores(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to assign chore') }
    finally { setSaving(false) }
  }

  const handleToggleChore = async (chore) => {
    const done = !chore.completed
    try {
      await slApi.updateChore(chore.chore_id, {
        completed:    done ? 1 : 0,
        completed_at: done ? new Date().toISOString() : null,
      })
      const data = await slApi.listChores(houseId, choreDate || undefined)
      setChores(Array.isArray(data) ? data : [])
    } catch (err) { toast.error(err.message || 'Failed to update chore') }
  }

  const handleAddPass = async (e) => {
    e.preventDefault()
    if (!passForm.resident_id || !passForm.leave_date || !passForm.expected_return_date)
      return toast.error('Resident and dates required')
    setSaving(true)
    try {
      const res = residents.find((r) => r.resident_id === passForm.resident_id)
      await slApi.createPass({
        ...passForm,
        house_id:    houseId,
        stay_id:     res?.stay_id || passForm.stay_id,
        is_blackout: passForm.is_blackout ? 1 : 0,
      })
      toast.success('Pass logged')
      setModal(null)
      setPassForm({ resident_id: '', stay_id: '', pass_type: 'day', destination: '', leave_date: todayStr(), leave_time: '', expected_return_date: '', expected_return_time: '', approved_by: '', is_blackout: false, notes: '' })
      const data = await slApi.listPasses(houseId)
      setPasses(Array.isArray(data) ? data : [])
      const dash = await slApi.getDashboard(houseId)
      setDashboard(dash)
    } catch (err) { toast.error(err.message || 'Failed to log pass') }
    finally { setSaving(false) }
  }

  const handleReturnPass = async (e) => {
    e.preventDefault()
    if (!selectedPass) return
    setSaving(true)
    try {
      await slApi.updatePass(selectedPass.pass_id, {
        ...returnForm,
        status: 'returned',
      })
      toast.success('Return recorded')
      setModal(null)
      setSelectedPass(null)
      setReturnForm({ actual_return_date: todayStr(), actual_return_time: '' })
      const data = await slApi.listPasses(houseId)
      setPasses(Array.isArray(data) ? data : [])
      const dash = await slApi.getDashboard(houseId)
      setDashboard(dash)
    } catch (err) { toast.error(err.message || 'Failed to record return') }
    finally { setSaving(false) }
  }

  const handleCurfewCheck = async (resident, status) => {
    try {
      await slApi.upsertCurfew(houseId, {
        resident_id: resident.resident_id,
        stay_id:     resident.stay_id,
        status,
        check_date:  curfewDate,
      })
      const data = await slApi.listCurfew(houseId, curfewDate)
      setCurfewChecks(Array.isArray(data) ? data : [])
      const dash = await slApi.getDashboard(houseId)
      setDashboard(dash)
    } catch (err) { toast.error(err.message || 'Failed to update curfew check') }
  }

  const handleCurfewDateChange = async (date) => {
    setCurfewDate(date)
    try {
      const data = await slApi.listCurfew(houseId, date)
      setCurfewChecks(Array.isArray(data) ? data : [])
    } catch {}
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

  const counts     = house.bed_counts || {}
  const configured = counts.configured ?? counts.total ?? 0
  const planned    = counts.planned_capacity ?? 0
  const incomplete = counts.setup_incomplete ?? (planned > configured)
  const toConfig   = counts.beds_to_configure ?? Math.max(0, planned - configured)

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
      <div className="flex items-center gap-5 mb-2 flex-wrap">
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
          <span className="font-bold text-slate-300">{configured}</span> Configured
          {planned > 0 && <span> · <span className="font-bold">{planned}</span> Planned</span>}
        </div>
      </div>

      {/* Setup incomplete banner */}
      {incomplete && toConfig > 0 && (
        <div className="flex items-center justify-between gap-3 mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-2.5">
          <div className="flex items-center gap-2 text-sm text-amber-300">
            <AlertTriangle size={14} className="shrink-0" />
            <span>{toConfig} of {planned} planned beds not yet configured as records</span>
          </div>
          <button
            onClick={() => { if (rooms.length === 0) return toast.error('Add a room first'); setModal('quick-add-beds') }}
            className="flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 text-amber-300 text-xs font-medium shrink-0"
          >
            <Plus size={11} /> Generate Missing Beds
          </button>
        </div>
      )}
      {!incomplete && <div className="mb-4" />}

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
      {tab === 'dashboard'  && (
        <TabDashboard
          dashboard={dashboard}
          residents={residents}
          onTabSwitch={setTab}
          onAddPass={() => setModal('add-pass')}
          onAddChore={() => setModal('add-chore')}
        />
      )}
      {tab === 'overview'   && (
        <TabOverview
          house={house}
          counts={counts}
          residents={residents}
          rooms={rooms}
          onGenerateBeds={() => { if (rooms.length === 0) return toast.error('Add a room first'); setModal('quick-add-beds') }}
        />
      )}
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
      {tab === 'compliance' && (
        <TabCompliance
          residents={residents}
          complianceDraft={complianceDraft}
          complianceSaving={complianceSaving}
          onLoad={loadCompliance}
          onToggle={handleToggleCompliance}
          onSave={handleSaveCompliance}
          onDraftChange={(stayId, field, value) =>
            setComplianceDraft((prev) => ({
              ...prev,
              [stayId]: { ...(prev[stayId] || {}), [field]: value },
            }))
          }
        />
      )}
      {tab === 'ua' && (
        <TabUA
          uaTests={uaTests}
          residents={residents}
          expandedUA={expandedUA}
          setExpandedUA={setExpandedUA}
          onAdd={() => setModal('add-ua')}
        />
      )}
      {tab === 'incidents' && (
        <TabIncidents
          incidents={incidents}
          expandedIncident={expandedIncident}
          incidentEditForm={incidentEditForm}
          incidentSaving={incidentSaving}
          onExpand={handleExpandIncident}
          onEditChange={(field, value) => setIncidentEditForm((prev) => ({ ...prev, [field]: value }))}
          onUpdate={handleUpdateIncident}
          onAdd={() => setModal('add-incident')}
        />
      )}
      {tab === 'rent' && (
        <TabRent
          rentSummary={rentSummary}
          residents={residents}
          ledgerData={ledgerData}
          expandedLedger={expandedLedger}
          onToggleLedger={handleToggleLedger}
          onAddPayment={() => setModal('add-payment')}
          onAddCharge={() => setModal('add-charge')}
        />
      )}
      {tab === 'meetings'   && (
        <TabMeetings
          meetings={meetings}
          residents={residents}
          onAdd={() => setModal('add-meeting')}
          onStatusChange={handleMeetingStatus}
          onTakeAttendance={(m) => setAttendanceModal(m)}
        />
      )}
      {tab === 'chores'     && (
        <TabChores
          chores={chores}
          choreDate={choreDate}
          onDateChange={async (d) => {
            setChoreDate(d)
            const data = await slApi.listChores(houseId, d || undefined)
            setChores(Array.isArray(data) ? data : [])
          }}
          onAdd={() => setModal('add-chore')}
          onToggle={handleToggleChore}
        />
      )}
      {tab === 'passes'     && (
        <TabPasses
          passes={passes}
          onAdd={() => setModal('add-pass')}
          onReturn={(p) => { setSelectedPass(p); setModal('log-return') }}
        />
      )}
      {tab === 'curfew'     && (
        <TabCurfew
          residents={residents}
          curfewChecks={curfewChecks}
          curfewDate={curfewDate}
          onDateChange={handleCurfewDateChange}
          onCheck={handleCurfewCheck}
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
              <Field label="Immediate Safety Concern?">
                <label className="flex items-center gap-2 mt-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={incidentForm.immediate_safety_concern}
                    onChange={(e) => setIncidentForm({ ...incidentForm, immediate_safety_concern: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm text-slate-300">Yes</span>
                </label>
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
                  {UA_RESULTS.map((r) => (
                    <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
                  ))}
                </TSelect>
              </Field>
              <Field label="Test Type">
                <TInput value={uaForm.test_type} onChange={(e) => setUAForm({ ...uaForm, test_type: e.target.value })} placeholder="Random, Scheduled, etc." />
              </Field>
              <Field label="Test Method">
                <TInput value={uaForm.test_method} onChange={(e) => setUAForm({ ...uaForm, test_method: e.target.value })} placeholder="Dip strip, Lab send, etc." />
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

      {modal === 'add-charge' && (
        <Modal title="Add Charge" onClose={() => setModal(null)}>
          <form onSubmit={handleAddCharge} className="space-y-4">
            <Field label="Resident Stay *">
              <TSelect value={chargeForm.stay_id} onChange={(e) => {
                const res = residents.find((r) => r.stay_id === e.target.value)
                setChargeForm({ ...chargeForm, stay_id: e.target.value, resident_id: res?.resident_id || '' })
              }}>
                <option value="">Select resident...</option>
                {residents.map((r) => (
                  <option key={r.stay_id} value={r.stay_id}>{r.first_name} {r.last_name}</option>
                ))}
              </TSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Charge Type">
                <TSelect value={chargeForm.charge_type} onChange={(e) => setChargeForm({ ...chargeForm, charge_type: e.target.value })}>
                  {CHARGE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </TSelect>
              </Field>
              <Field label="Amount ($) *">
                <TInput type="number" min="0" step="0.01" value={chargeForm.amount} onChange={(e) => setChargeForm({ ...chargeForm, amount: e.target.value })} />
              </Field>
              <Field label="Charge Month (YYYY-MM)">
                <TInput value={chargeForm.charge_month} onChange={(e) => setChargeForm({ ...chargeForm, charge_month: e.target.value })} placeholder="2026-06" />
              </Field>
              <Field label="Due Date">
                <TInput type="date" value={chargeForm.due_date} onChange={(e) => setChargeForm({ ...chargeForm, due_date: e.target.value })} />
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={chargeForm.notes} onChange={(e) => setChargeForm({ ...chargeForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Add Charge" submitClass="bg-amber-500 hover:bg-amber-600" />
          </form>
        </Modal>
      )}

      {modal === 'add-meeting' && (
        <Modal title="Schedule Meeting" onClose={() => setModal(null)}>
          <form onSubmit={handleAddMeeting} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Date *">
                <TInput type="date" value={meetingForm.scheduled_date} onChange={(e) => setMeetingForm({ ...meetingForm, scheduled_date: e.target.value })} />
              </Field>
              <Field label="Time">
                <TInput type="time" value={meetingForm.scheduled_time} onChange={(e) => setMeetingForm({ ...meetingForm, scheduled_time: e.target.value })} />
              </Field>
              <Field label="Type">
                <TSelect value={meetingForm.meeting_type} onChange={(e) => setMeetingForm({ ...meetingForm, meeting_type: e.target.value })}>
                  {MEETING_TYPES.map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                </TSelect>
              </Field>
              <Field label="Location">
                <TInput value={meetingForm.location} onChange={(e) => setMeetingForm({ ...meetingForm, location: e.target.value })} placeholder="Living room, Zoom, etc." />
              </Field>
            </div>
            <Field label="Topic">
              <TInput value={meetingForm.topic} onChange={(e) => setMeetingForm({ ...meetingForm, topic: e.target.value })} placeholder="Agenda / discussion topic" />
            </Field>
            <Field label="Facilitator">
              <TInput value={meetingForm.facilitator_name} onChange={(e) => setMeetingForm({ ...meetingForm, facilitator_name: e.target.value })} />
            </Field>
            <Field label="Notes">
              <TArea value={meetingForm.notes} onChange={(e) => setMeetingForm({ ...meetingForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Schedule Meeting" />
          </form>
        </Modal>
      )}

      {modal === 'add-chore' && (
        <Modal title="Assign Chore" onClose={() => setModal(null)}>
          <form onSubmit={handleAddChore} className="space-y-4">
            <Field label="Chore *">
              <TInput value={choreForm.chore_name} onChange={(e) => setChoreForm({ ...choreForm, chore_name: e.target.value })} placeholder="Kitchen cleanup, Mop floors, etc." />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Assign To">
                <TSelect value={choreForm.resident_id} onChange={(e) => {
                  const r = residents.find((r) => r.resident_id === e.target.value)
                  setChoreForm({ ...choreForm, resident_id: e.target.value, stay_id: r?.stay_id || '' })
                }}>
                  <option value="">All residents / unassigned</option>
                  {residents.map((r) => <option key={r.resident_id} value={r.resident_id}>{r.first_name} {r.last_name}</option>)}
                </TSelect>
              </Field>
              <Field label="Due Date *">
                <TInput type="date" value={choreForm.due_date} onChange={(e) => setChoreForm({ ...choreForm, due_date: e.target.value })} />
              </Field>
              <Field label="Location in House">
                <TInput value={choreForm.location} onChange={(e) => setChoreForm({ ...choreForm, location: e.target.value })} placeholder="Kitchen, Bathroom, etc." />
              </Field>
              <Field label="Recurrence">
                <TSelect value={choreForm.recurrence} onChange={(e) => setChoreForm({ ...choreForm, recurrence: e.target.value })}>
                  {RECURRENCE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </TSelect>
              </Field>
              <Field label="Assigned By">
                <TInput value={choreForm.assigned_by} onChange={(e) => setChoreForm({ ...choreForm, assigned_by: e.target.value })} />
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={choreForm.notes} onChange={(e) => setChoreForm({ ...choreForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Assign Chore" />
          </form>
        </Modal>
      )}

      {modal === 'add-pass' && (
        <Modal title="Log Pass / Leave" onClose={() => setModal(null)}>
          <form onSubmit={handleAddPass} className="space-y-4">
            <Field label="Resident *">
              <TSelect value={passForm.resident_id} onChange={(e) => setPassForm({ ...passForm, resident_id: e.target.value })}>
                <option value="">Select resident...</option>
                {residents.map((r) => <option key={r.resident_id} value={r.resident_id}>{r.first_name} {r.last_name}</option>)}
              </TSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Pass Type">
                <TSelect value={passForm.pass_type} onChange={(e) => setPassForm({ ...passForm, pass_type: e.target.value })}>
                  {PASS_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </TSelect>
              </Field>
              <Field label="Destination">
                <TInput value={passForm.destination} onChange={(e) => setPassForm({ ...passForm, destination: e.target.value })} placeholder="Family home, Work, etc." />
              </Field>
              <Field label="Leave Date *">
                <TInput type="date" value={passForm.leave_date} onChange={(e) => setPassForm({ ...passForm, leave_date: e.target.value })} />
              </Field>
              <Field label="Leave Time">
                <TInput type="time" value={passForm.leave_time} onChange={(e) => setPassForm({ ...passForm, leave_time: e.target.value })} />
              </Field>
              <Field label="Expected Return *">
                <TInput type="date" value={passForm.expected_return_date} onChange={(e) => setPassForm({ ...passForm, expected_return_date: e.target.value })} />
              </Field>
              <Field label="Return Time">
                <TInput type="time" value={passForm.expected_return_time} onChange={(e) => setPassForm({ ...passForm, expected_return_time: e.target.value })} />
              </Field>
              <Field label="Approved By">
                <TInput value={passForm.approved_by} onChange={(e) => setPassForm({ ...passForm, approved_by: e.target.value })} />
              </Field>
              <Field label="Blackout Restriction?">
                <label className="flex items-center gap-2 mt-2 cursor-pointer">
                  <input type="checkbox" checked={passForm.is_blackout} onChange={(e) => setPassForm({ ...passForm, is_blackout: e.target.checked })} className="rounded" />
                  <span className="text-sm text-slate-300">Yes — resident on blackout</span>
                </label>
              </Field>
            </div>
            <Field label="Notes">
              <TArea value={passForm.notes} onChange={(e) => setPassForm({ ...passForm, notes: e.target.value })} />
            </Field>
            <MFooter onCancel={() => setModal(null)} saving={saving} label="Log Pass" />
          </form>
        </Modal>
      )}

      {modal === 'log-return' && selectedPass && (
        <Modal title={`Record Return — ${selectedPass.first_name} ${selectedPass.last_name}`} onClose={() => { setModal(null); setSelectedPass(null) }}>
          <form onSubmit={handleReturnPass} className="space-y-4">
            <div className="bg-slate-700/30 rounded-lg p-3 text-sm space-y-1">
              <p className="text-slate-300">Left: <span className="text-white">{formatDate(selectedPass.leave_date)}{selectedPass.leave_time ? ` at ${selectedPass.leave_time}` : ''}</span></p>
              <p className="text-slate-300">Expected back: <span className="text-white">{formatDate(selectedPass.expected_return_date)}{selectedPass.expected_return_time ? ` at ${selectedPass.expected_return_time}` : ''}</span></p>
              {selectedPass.destination && <p className="text-slate-400 text-xs">Destination: {selectedPass.destination}</p>}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Actual Return Date">
                <TInput type="date" value={returnForm.actual_return_date} onChange={(e) => setReturnForm({ ...returnForm, actual_return_date: e.target.value })} />
              </Field>
              <Field label="Actual Return Time">
                <TInput type="time" value={returnForm.actual_return_time} onChange={(e) => setReturnForm({ ...returnForm, actual_return_time: e.target.value })} />
              </Field>
            </div>
            <MFooter onCancel={() => { setModal(null); setSelectedPass(null) }} saving={saving} label="Confirm Return" submitClass="bg-emerald-500 hover:bg-emerald-600" />
          </form>
        </Modal>
      )}

      {attendanceModal && (
        <AttendanceModal
          meeting={attendanceModal}
          residents={residents}
          onSave={handleSaveAttendance}
          onClose={() => setAttendanceModal(null)}
        />
      )}

      {modal === 'quick-add-beds' && (
        <Modal title="Generate Beds" onClose={() => setModal(null)}>
          <form onSubmit={handleQuickAddBeds} className="space-y-4">
            <Field label="Room *">
              <TSelect value={quickBedForm.room_id} onChange={(e) => setQuickBedForm({ ...quickBedForm, room_id: e.target.value })}>
                <option value="">Select room...</option>
                {rooms.map((r) => (
                  <option key={r.room_id} value={r.room_id}>
                    {r.room_name}{r.floor ? ` (${r.floor})` : ''}
                  </option>
                ))}
              </TSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Quantity *">
                <TInput type="number" min="1" max="50" value={quickBedForm.quantity} onChange={(e) => setQuickBedForm({ ...quickBedForm, quantity: e.target.value })} />
              </Field>
              <Field label="Start Number">
                <TInput type="number" min="1" value={quickBedForm.start_number} onChange={(e) => setQuickBedForm({ ...quickBedForm, start_number: e.target.value })} />
              </Field>
              <Field label="Label Prefix">
                <TInput value={quickBedForm.label_prefix} onChange={(e) => setQuickBedForm({ ...quickBedForm, label_prefix: e.target.value })} placeholder="Room name used if blank" />
              </Field>
              <Field label="Initial Status">
                <TSelect value={quickBedForm.bed_status} onChange={(e) => setQuickBedForm({ ...quickBedForm, bed_status: e.target.value })}>
                  {BED_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </TSelect>
              </Field>
            </div>
            {quickBedForm.room_id && quickBedForm.quantity > 0 && (
              <div className="text-xs text-slate-400 bg-slate-700/30 rounded-lg px-3 py-2">
                Will create beds labeled: <span className="text-white">
                  {(quickBedForm.label_prefix || rooms.find(r => r.room_id === quickBedForm.room_id)?.room_name || 'Bed')} {quickBedForm.start_number || 1}
                  {quickBedForm.quantity > 1 ? ` … ${(quickBedForm.label_prefix || rooms.find(r => r.room_id === quickBedForm.room_id)?.room_name || 'Bed')} ${(parseInt(quickBedForm.start_number) || 1) + parseInt(quickBedForm.quantity) - 1}` : ''}
                </span>
              </div>
            )}
            <MFooter onCancel={() => setModal(null)} saving={quickBedSaving} label={`Create ${quickBedForm.quantity || 1} Bed${quickBedForm.quantity > 1 ? 's' : ''}`} />
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Tab panels
// ---------------------------------------------------------------------------

function TabOverview({ house, counts, residents, rooms, onGenerateBeds }) {
  const configured  = counts.configured ?? counts.total ?? 0
  const planned     = counts.planned_capacity ?? 0
  const incomplete  = counts.setup_incomplete ?? (planned > configured)
  const toConfig    = counts.beds_to_configure ?? Math.max(0, planned - configured)

  const certLabel = CERTIFICATION_OPTIONS.find(o => o.value === house.certification_level)?.label
  const payLabel  = PAYMENT_TYPE_OPTIONS.find(o => o.value === house.payment_type)?.label

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* House Details */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">House Details</h3>
        <dl className="space-y-2 text-sm">
          {[
            ['Type', house.house_type],
            ['Certification', certLabel || house.certification_level],
            ['Certification Notes', house.certification_notes],
            ['Payment Type', payLabel || house.payment_type !== 'unknown' ? payLabel : null],
            ['Accepts Insurance', house.accepts_insurance !== 'unknown' ? house.accepts_insurance : null],
            ['Insurance Plans', house.insurance_plans_accepted],
            ['Requires Clinical Program', house.requires_clinical_program ? 'Yes' : null],
            ['Affiliated Program', house.affiliated_clinical_program],
            ['Monthly Rent', house.monthly_rent ? `$${Number(house.monthly_rent).toLocaleString()}` : null],
            ['House Rules Version', house.house_rules_version],
          ].filter(([, v]) => v).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4">
              <dt className="text-slate-400 shrink-0">{k}</dt>
              <dd className="text-white text-right">{v}</dd>
            </div>
          ))}
          {house.billing_contact_name && (
            <div className="pt-2 border-t border-slate-700/50">
              <dt className="text-slate-400 mb-1 text-xs">Billing Contact</dt>
              <dd className="text-white text-sm">{house.billing_contact_name}</dd>
              {house.billing_contact_phone && <dd className="text-slate-400 text-xs">{house.billing_contact_phone}</dd>}
              {house.billing_contact_email && <dd className="text-slate-400 text-xs">{house.billing_contact_email}</dd>}
            </div>
          )}
          {house.notes && (
            <div className="pt-2 border-t border-slate-700/50">
              <dt className="text-slate-400 mb-1">Notes</dt>
              <dd className="text-slate-300">{house.notes}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Capacity */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Capacity</h3>

        {/* Setup incomplete alert */}
        {incomplete && toConfig > 0 && (
          <div className="flex items-center justify-between gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 mb-4">
            <div className="flex items-center gap-2 text-xs text-amber-300">
              <AlertTriangle size={12} className="shrink-0" />
              <span>{toConfig} bed{toConfig !== 1 ? 's' : ''} not yet configured ({configured} of {planned} planned)</span>
            </div>
            {rooms.length > 0 && (
              <button
                onClick={onGenerateBeds}
                className="flex items-center gap-1 px-2 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-medium shrink-0"
              >
                <Plus size={10} /> Generate
              </button>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Planned Capacity', value: planned || configured,  color: 'text-slate-300',   sub: 'from house settings'    },
            { label: 'Configured Beds',  value: configured,             color: 'text-white',        sub: 'actual bed records'     },
            { label: 'Available',        value: counts.available ?? 0,  color: 'text-emerald-300',  sub: null                     },
            { label: 'Occupied',         value: counts.occupied ?? 0,   color: 'text-rose-300',     sub: null                     },
            { label: 'Reserved',         value: counts.reserved ?? 0,   color: 'text-amber-300',    sub: null                     },
            { label: 'Active Stays',     value: residents.length,       color: 'text-indigo-300',   sub: null                     },
          ].map(({ label, value, color, sub }) => (
            <div key={label} className="bg-slate-700/30 rounded-lg p-3">
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-slate-400 mt-1">{label}</div>
              {sub && <div className="text-xs text-slate-600 mt-0.5">{sub}</div>}
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

// ---------------------------------------------------------------------------
// 2A: Compliance checklist tab
// ---------------------------------------------------------------------------

function TabCompliance({ residents, complianceDraft, complianceSaving, onLoad, onToggle, onSave, onDraftChange }) {
  const [expanded, setExpanded] = useState(null)

  if (residents.length === 0) {
    return <EmptyTab message="No active residents — compliance tracking requires at least one active stay." />
  }

  const handleExpand = (stayId) => {
    if (expanded === stayId) {
      setExpanded(null)
    } else {
      setExpanded(stayId)
      onLoad(stayId)
    }
  }

  return (
    <div className="space-y-2">
      {residents.map((r) => {
        const isOpen = expanded === r.stay_id
        const draft = complianceDraft[r.stay_id] || {}
        const checked = BOOL_KEYS.filter((k) => draft[k]).length
        const pct = Math.round((checked / BOOL_KEYS.length) * 100)
        const isSaving = complianceSaving[r.stay_id]

        return (
          <div key={r.stay_id} className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
            <button
              onClick={() => handleExpand(r.stay_id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/20 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                  <User size={14} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{r.first_name} {r.last_name}</p>
                  {isOpen || Object.keys(draft).length > 0 ? (
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="w-24 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${pct === 100 ? 'bg-emerald-400' : pct >= 50 ? 'bg-amber-400' : 'bg-rose-400'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{checked}/{BOOL_KEYS.length} items</span>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">Click to view checklist</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {pct === 100 && <CheckCircle2 size={16} className="text-emerald-400" />}
                {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
              </div>
            </button>

            {isOpen && (
              <div className="border-t border-slate-700/50 px-5 py-4 bg-slate-800/40">
                <div className="space-y-2 mb-4">
                  {CHECKLIST_FIELDS.map(({ key, label, hasDate }) => (
                    <div key={key}>
                      <button
                        onClick={() => onToggle(r.stay_id, key)}
                        className="flex items-center gap-3 w-full text-left py-1.5 hover:opacity-80 transition-opacity"
                      >
                        {draft[key] ? (
                          <CheckSquare size={16} className="text-emerald-400 shrink-0" />
                        ) : (
                          <Square size={16} className="text-slate-500 shrink-0" />
                        )}
                        <span className={`text-sm ${draft[key] ? 'text-white' : 'text-slate-400'}`}>{label}</span>
                      </button>
                      {hasDate && draft[key] ? (
                        <div className="ml-7 mt-1">
                          <input
                            type="date"
                            value={draft.house_rules_signed_date || ''}
                            onChange={(e) => onDraftChange(r.stay_id, 'house_rules_signed_date', e.target.value)}
                            className="bg-slate-700/50 border border-slate-600 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>

                <div className="mb-4">
                  <label className="block text-xs text-slate-400 mb-1">Missing Items / Notes</label>
                  <textarea
                    value={draft.missing_items_summary || ''}
                    onChange={(e) => onDraftChange(r.stay_id, 'missing_items_summary', e.target.value)}
                    rows={2}
                    placeholder="Note any pending items..."
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className={`text-xs font-medium ${pct === 100 ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {pct === 100 ? '✓ All items complete' : `${pct}% complete`}
                  </span>
                  <button
                    onClick={() => onSave(r.stay_id)}
                    disabled={isSaving}
                    className="px-4 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium disabled:opacity-50"
                  >
                    {isSaving ? 'Saving...' : 'Save Checklist'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 2D: UA Tests tab (improved display)
// ---------------------------------------------------------------------------

const UA_RESULT_COLORS = {
  negative:      'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  positive:      'bg-rose-500/10 text-rose-300 border-rose-500/30',
  dilute:        'bg-amber-500/10 text-amber-300 border-amber-500/30',
  refused:       'bg-orange-500/10 text-orange-300 border-orange-500/30',
  not_completed: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
}

function TabUA({ uaTests, residents, expandedUA, setExpandedUA, onAdd }) {
  const residentMap = {}
  residents.forEach((r) => { residentMap[r.resident_id] = r })

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
          {uaTests.map((t) => {
            const resident = residentMap[t.resident_id]
            const residentName = resident
              ? `${resident.first_name} ${resident.last_name}`
              : t.resident_id?.slice(0, 8) + '…'
            const isOpen = expandedUA === t.test_id
            const resultColor = UA_RESULT_COLORS[t.result] || UA_RESULT_COLORS.not_completed

            return (
              <div key={t.test_id} className="bg-slate-700/30 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedUA(isOpen ? null : t.test_id)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-700/40 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="shrink-0">
                      <p className="text-sm text-white font-medium">{formatDate(t.test_date)}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{residentName}</p>
                    </div>
                    <div className="hidden sm:flex flex-col min-w-0">
                      {t.test_type && <span className="text-xs text-slate-400 truncate">{t.test_type}</span>}
                      {t.administered_by_name && <span className="text-xs text-slate-500 truncate">by {t.administered_by_name}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className={`text-xs px-2 py-1 rounded-full border ${resultColor}`}>
                      {t.result?.replace(/_/g, ' ') || 'Pending'}
                    </span>
                    {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-600/40 px-4 py-3 bg-slate-700/20 space-y-2 text-sm">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
                      {[
                        ['Resident', residentName],
                        ['Test Date', formatDate(t.test_date)],
                        ['Test Type', t.test_type],
                        ['Test Method', t.test_method],
                        ['Administered By', t.administered_by_name],
                        ['Result', t.result?.replace(/_/g, ' ')],
                        ['Specimen Validity', t.specimen_validity],
                        ['Action Taken', t.action_taken],
                        ['Clinical Notified', t.clinical_notified ? `Yes${t.clinical_notified_at ? ' · ' + formatDate(t.clinical_notified_at) : ''}` : null],
                        ['CM Notified', t.case_manager_notified ? `Yes${t.case_manager_notified_at ? ' · ' + formatDate(t.case_manager_notified_at) : ''}` : null],
                      ].filter(([, v]) => v).map(([label, value]) => (
                        <div key={label}>
                          <span className="text-slate-500">{label}: </span>
                          <span className="text-slate-200">{value}</span>
                        </div>
                      ))}
                    </div>
                    {t.notes && (
                      <div className="pt-2 border-t border-slate-600/40">
                        <p className="text-xs text-slate-400">{t.notes}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 2B: Incidents tab with update/resolve workflow
// ---------------------------------------------------------------------------

function TabIncidents({ incidents, expandedIncident, incidentEditForm, incidentSaving, onExpand, onEditChange, onUpdate, onAdd }) {
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
          {incidents.map((inc) => {
            const isOpen = expandedIncident === inc.incident_id
            const isResolved = inc.incident_resolved

            return (
              <div key={inc.incident_id} className="bg-slate-700/30 rounded-lg overflow-hidden">
                <button
                  onClick={() => onExpand(inc)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-700/40 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {isResolved ? (
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    ) : (
                      <Circle size={16} className="text-slate-500 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-medium text-white capitalize">
                          {inc.incident_type.replace(/_/g, ' ')}
                        </p>
                        {inc.severity && (
                          <span className={`text-xs px-1.5 py-0.5 rounded border ${SEVERITY_COLORS[inc.severity] || SEVERITY_COLORS.low}`}>
                            {inc.severity}
                          </span>
                        )}
                        {inc.immediate_safety_concern ? (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            Safety concern
                          </span>
                        ) : null}
                        {isResolved && (
                          <span className="text-xs text-emerald-400">Resolved</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5 truncate">
                        {formatDate(inc.incident_date)}
                        {inc.reported_by_name ? ` · ${inc.reported_by_name}` : ''}
                        {inc.description ? ` · ${inc.description}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="shrink-0 ml-2">
                    {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-600/40 px-4 py-4 bg-slate-700/20 space-y-4">
                    {inc.description && (
                      <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Description</p>
                        <p className="text-sm text-slate-300">{inc.description}</p>
                      </div>
                    )}

                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Response Taken</label>
                      <textarea
                        value={incidentEditForm.response_taken || ''}
                        onChange={(e) => onEditChange('response_taken', e.target.value)}
                        rows={2}
                        className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
                        placeholder="Actions taken in response..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={incidentEditForm.follow_up_required || false}
                            onChange={(e) => onEditChange('follow_up_required', e.target.checked)}
                            className="rounded"
                          />
                          <span className="text-sm text-slate-300">Follow-up Required</span>
                        </label>
                      </div>
                      {incidentEditForm.follow_up_required && (
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">Follow-up Due</label>
                          <input
                            type="date"
                            value={incidentEditForm.follow_up_due_date || ''}
                            onChange={(e) => onEditChange('follow_up_due_date', e.target.value)}
                            className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                      )}
                    </div>

                    <div>
                      <label className="flex items-center gap-2 cursor-pointer mb-2">
                        <input
                          type="checkbox"
                          checked={incidentEditForm.incident_resolved || false}
                          onChange={(e) => onEditChange('incident_resolved', e.target.checked)}
                          className="rounded"
                        />
                        <span className="text-sm text-slate-300">Mark as Resolved</span>
                      </label>
                      {incidentEditForm.incident_resolved && (
                        <textarea
                          value={incidentEditForm.resolution_notes || ''}
                          onChange={(e) => onEditChange('resolution_notes', e.target.value)}
                          rows={2}
                          placeholder="Resolution notes..."
                          className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
                        />
                      )}
                    </div>

                    <div className="flex justify-end">
                      <button
                        onClick={() => onUpdate(inc.incident_id)}
                        disabled={incidentSaving}
                        className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium disabled:opacity-50"
                      >
                        <Edit3 size={13} />
                        {incidentSaving ? 'Saving...' : 'Update Incident'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 2C: Rent tab with charge creation and full ledger
// ---------------------------------------------------------------------------

function TabRent({ rentSummary, residents, ledgerData, expandedLedger, onToggleLedger, onAddPayment, onAddCharge }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <DollarSign size={16} className="text-indigo-400" />
          Rent &amp; Payments
        </h3>
        {residents.length > 0 && (
          <div className="flex gap-2">
            <button onClick={onAddCharge} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-medium">
              <Receipt size={12} /> Add Charge
            </button>
            <button onClick={onAddPayment} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium">
              <Plus size={12} /> Record Payment
            </button>
          </div>
        )}
      </div>
      {!rentSummary || rentSummary.residents.length === 0 ? (
        <EmptyTab message="No active residents with rent data." />
      ) : (
        <div className="space-y-3">
          {rentSummary.residents.map((r) => {
            const balance = (r.total_charged || 0) - (r.total_paid || 0)
            const isOpen = expandedLedger === r.stay_id
            const ledger = ledgerData[r.stay_id]

            return (
              <div key={r.resident_id} className="bg-slate-700/30 rounded-lg overflow-hidden">
                <button
                  onClick={() => onToggleLedger(r.stay_id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-700/40 transition-colors text-left"
                >
                  <div>
                    <p className="font-medium text-white text-sm">{r.first_name} {r.last_name}</p>
                    <div className="flex gap-4 mt-1 text-xs">
                      <span className="text-slate-400">Charged: <span className="text-white">{formatCurrency(r.total_charged)}</span></span>
                      <span className="text-slate-400">Paid: <span className="text-emerald-300">{formatCurrency(r.total_paid)}</span></span>
                      <span className="text-slate-400">Balance: <span className={balance > 0 ? 'text-rose-300' : 'text-emerald-300'}>{formatCurrency(balance)}</span></span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {balance > 0 && <TrendingDown size={14} className="text-rose-400" />}
                    {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-600/40 px-4 py-3 bg-slate-700/20">
                    {!ledger ? (
                      <p className="text-xs text-slate-400 py-2">Loading ledger...</p>
                    ) : (
                      <div className="space-y-3">
                        {ledger.charges.length > 0 && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">Charges</p>
                            <div className="space-y-1">
                              {ledger.charges.map((c) => (
                                <div key={c.charge_id} className="flex items-center justify-between text-xs bg-slate-700/40 rounded px-3 py-2">
                                  <div>
                                    <span className="text-slate-300 capitalize">{c.charge_type?.replace(/_/g, ' ')}</span>
                                    {c.charge_month && <span className="text-slate-500 ml-1">· {c.charge_month}</span>}
                                    {c.due_date && <span className="text-slate-500 ml-1">· due {formatDate(c.due_date)}</span>}
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                                      c.status === 'paid'   ? 'bg-emerald-500/20 text-emerald-300' :
                                      c.status === 'void'   ? 'bg-slate-500/20 text-slate-500'    :
                                      c.status === 'waived' ? 'bg-indigo-500/20 text-indigo-300'  :
                                                              'bg-amber-500/20 text-amber-300'
                                    }`}>{c.status}</span>
                                    <span className="text-white font-medium">{formatCurrency(c.amount)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {ledger.payments.length > 0 && (
                          <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">Payments</p>
                            <div className="space-y-1">
                              {ledger.payments.map((p) => (
                                <div key={p.payment_id} className="flex items-center justify-between text-xs bg-slate-700/40 rounded px-3 py-2">
                                  <div>
                                    <span className="text-slate-300">{formatDate(p.payment_date)}</span>
                                    {p.payment_method && <span className="text-slate-500 ml-1">· {p.payment_method}</span>}
                                    {p.payment_for_month && <span className="text-slate-500 ml-1">· for {p.payment_for_month}</span>}
                                    {p.received_by && <span className="text-slate-500 ml-1">· {p.received_by}</span>}
                                  </div>
                                  <span className="text-emerald-300 font-medium">{formatCurrency(p.amount)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {ledger.charges.length === 0 && ledger.payments.length === 0 && (
                          <p className="text-xs text-slate-500 py-1">No charges or payments recorded yet.</p>
                        )}

                        <div className="flex gap-3 pt-1 border-t border-slate-600/40">
                          <div className="flex gap-4 flex-1 text-xs">
                            <span className="text-slate-400">Total Charged: <span className="text-white font-medium">{formatCurrency(ledger.total_charged)}</span></span>
                            <span className="text-slate-400">Total Paid: <span className="text-emerald-300 font-medium">{formatCurrency(ledger.total_paid)}</span></span>
                            <span className="text-slate-400">Balance: <span className={`font-medium ${ledger.balance > 0 ? 'text-rose-300' : 'text-emerald-300'}`}>{formatCurrency(ledger.balance)}</span></span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3E: House manager daily dashboard
// ---------------------------------------------------------------------------

function TabDashboard({ dashboard, residents, onTabSwitch, onAddPass, onAddChore }) {
  if (!dashboard) {
    return <EmptyTab message="Loading dashboard..." />
  }

  const { curfew_checks = [], active_passes = [], open_incidents = [], todays_chores = [], upcoming_meetings = [], on_blackout = [] } = dashboard

  const curfewTotal   = residents.length
  const curfewPresent = curfew_checks.filter((c) => c.status === 'present').length
  const curfewAbsent  = curfew_checks.filter((c) => c.status === 'absent' || c.status === 'unexcused').length
  const curfewOnPass  = curfew_checks.filter((c) => c.status === 'on_pass').length
  const curfewUnchecked = curfewTotal - curfew_checks.length

  const today = dashboard.today || new Date().toISOString().slice(0, 10)
  const overduePassesList = active_passes.filter((p) => p.expected_return_date < today && p.status !== 'returned')

  return (
    <div className="space-y-5">
      {/* Curfew summary */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Moon size={16} className="text-indigo-400" /> Tonight's Curfew
          </h3>
          <button onClick={() => onTabSwitch('curfew')} className="text-xs text-indigo-400 hover:text-indigo-300">
            Take Roll Call →
          </button>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Present',   value: curfewPresent,   color: 'text-emerald-300' },
            { label: 'Absent',    value: curfewAbsent,    color: 'text-rose-300'    },
            { label: 'On Pass',   value: curfewOnPass,    color: 'text-amber-300'   },
            { label: 'Unchecked', value: curfewUnchecked, color: 'text-slate-400'   },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-slate-700/30 rounded-lg p-3 text-center">
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-slate-500 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Active passes + overdue */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Footprints size={16} className="text-indigo-400" /> Active Passes
            {overduePassesList.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {overduePassesList.length} overdue
              </span>
            )}
          </h3>
          <div className="flex gap-2">
            <button onClick={onAddPass} className="text-xs text-indigo-400 hover:text-indigo-300">+ Log Pass</button>
            <button onClick={() => onTabSwitch('passes')} className="text-xs text-slate-400 hover:text-slate-300">All →</button>
          </div>
        </div>
        {active_passes.length === 0 ? (
          <p className="text-sm text-slate-500">No active passes.</p>
        ) : (
          <div className="space-y-2">
            {active_passes.map((p) => {
              const isOverdue = p.expected_return_date < today && p.status !== 'returned'
              return (
                <div key={p.pass_id} className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm ${isOverdue ? 'bg-rose-500/10 border border-rose-500/30' : 'bg-slate-700/30'}`}>
                  <div>
                    <p className={`font-medium ${isOverdue ? 'text-rose-300' : 'text-white'}`}>
                      {p.first_name} {p.last_name}
                      {isOverdue && <span className="ml-2 text-xs text-rose-400">OVERDUE</span>}
                    </p>
                    <p className="text-xs text-slate-400">
                      Left {p.leave_date} · Expected back {p.expected_return_date}
                      {p.destination ? ` · ${p.destination}` : ''}
                    </p>
                  </div>
                  {p.is_blackout ? <Ban size={14} className="text-rose-400 shrink-0" /> : null}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Today's chores */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <ListChecks size={16} className="text-indigo-400" /> Today's Chores
            </h3>
            <div className="flex gap-2">
              <button onClick={onAddChore} className="text-xs text-indigo-400 hover:text-indigo-300">+ Add</button>
              <button onClick={() => onTabSwitch('chores')} className="text-xs text-slate-400 hover:text-slate-300">All →</button>
            </div>
          </div>
          {todays_chores.length === 0 ? (
            <p className="text-sm text-slate-500">No chores due today.</p>
          ) : (
            <div className="space-y-1.5">
              {todays_chores.map((c) => (
                <div key={c.chore_id} className="flex items-center gap-2 text-sm">
                  {c.completed
                    ? <CheckCheck size={14} className="text-emerald-400 shrink-0" />
                    : <Clock size={14} className="text-amber-400 shrink-0" />
                  }
                  <span className={c.completed ? 'text-slate-500 line-through' : 'text-slate-200'}>{c.chore_name}</span>
                  {(c.first_name || c.last_name) && (
                    <span className="text-xs text-slate-500 ml-auto">{c.first_name} {c.last_name}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming meetings */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <CalendarDays size={16} className="text-indigo-400" /> Upcoming Meetings
            </h3>
            <button onClick={() => onTabSwitch('meetings')} className="text-xs text-slate-400 hover:text-slate-300">All →</button>
          </div>
          {upcoming_meetings.length === 0 ? (
            <p className="text-sm text-slate-500">No upcoming meetings.</p>
          ) : (
            <div className="space-y-1.5">
              {upcoming_meetings.map((m) => (
                <div key={m.meeting_id} className="flex items-center justify-between text-sm bg-slate-700/30 rounded-lg px-3 py-2">
                  <div>
                    <p className="text-white font-medium">{m.scheduled_date} {m.scheduled_time && `· ${m.scheduled_time}`}</p>
                    <p className="text-xs text-slate-400 capitalize">{m.meeting_type}{m.topic ? ` · ${m.topic}` : ''}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Residents on blackout */}
      {on_blackout.length > 0 && (
        <div className="bg-slate-800/60 border border-rose-500/30 rounded-xl p-5">
          <h3 className="font-semibold text-rose-300 flex items-center gap-2 mb-3">
            <Ban size={16} /> Residents on Blackout Restriction ({on_blackout.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {on_blackout.map((r) => (
              <span key={r.resident_id} className="px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
                {r.first_name} {r.last_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Open incidents needing follow-up */}
      {open_incidents.length > 0 && (
        <div className="bg-slate-800/60 border border-amber-500/30 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-amber-300 flex items-center gap-2">
              <AlertTriangle size={16} /> Open Incidents ({open_incidents.length})
            </h3>
            <button onClick={() => onTabSwitch('incidents')} className="text-xs text-slate-400 hover:text-slate-300">View all →</button>
          </div>
          <div className="space-y-1.5">
            {open_incidents.slice(0, 5).map((inc) => (
              <div key={inc.incident_id} className="flex items-center justify-between text-sm bg-slate-700/30 rounded px-3 py-2">
                <span className="text-slate-200 capitalize">{inc.incident_type?.replace(/_/g, ' ')}</span>
                <span className="text-xs text-slate-500">{inc.incident_date}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3A: Meetings tab
// ---------------------------------------------------------------------------

const MEETING_STATUS_COLORS = {
  scheduled:  'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  completed:  'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  cancelled:  'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

function TabMeetings({ meetings, residents, onAdd, onStatusChange, onTakeAttendance }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <CalendarDays size={16} className="text-indigo-400" /> Meetings ({meetings.length})
        </h3>
        <button onClick={onAdd} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
          <Plus size={12} /> Schedule
        </button>
      </div>
      {meetings.length === 0 ? (
        <EmptyTab message="No meetings scheduled." />
      ) : (
        <div className="space-y-2">
          {meetings.map((m) => {
            const statusColor = MEETING_STATUS_COLORS[m.status] || MEETING_STATUS_COLORS.scheduled
            let attendance = []
            try { attendance = m.attendance_json ? JSON.parse(m.attendance_json) : [] } catch {}
            return (
              <div key={m.meeting_id} className="bg-slate-700/30 rounded-lg px-4 py-3">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColor}`}>
                        {m.status}
                      </span>
                      <span className="text-xs text-slate-400 uppercase tracking-wide">{m.meeting_type}</span>
                    </div>
                    <p className="text-white font-medium text-sm">
                      {m.scheduled_date}{m.scheduled_time ? ` · ${m.scheduled_time}` : ''}
                    </p>
                    {m.topic && <p className="text-xs text-slate-400 mt-0.5">{m.topic}</p>}
                    <div className="flex gap-3 mt-1 text-xs text-slate-500">
                      {m.location && <span>{m.location}</span>}
                      {m.facilitator_name && <span>Facilitator: {m.facilitator_name}</span>}
                      {attendance.length > 0 && <span>{attendance.length} attended</span>}
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {m.status === 'scheduled' && (
                      <>
                        <button
                          onClick={() => onTakeAttendance(m)}
                          className="text-xs px-2.5 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30"
                        >
                          Take Attendance
                        </button>
                        <button
                          onClick={() => onStatusChange(m.meeting_id, 'cancelled')}
                          className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-600 text-slate-400"
                        >
                          Cancel
                        </button>
                      </>
                    )}
                    {m.status === 'completed' && residents.length > 0 && (
                      <button
                        onClick={() => onTakeAttendance(m)}
                        className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-600 text-slate-400"
                      >
                        {attendance.length > 0 ? 'Edit Attendance' : 'Add Attendance'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3B: Chores tab
// ---------------------------------------------------------------------------

function TabChores({ chores, choreDate, onDateChange, onAdd, onToggle }) {
  const pending   = chores.filter((c) => !c.completed).length
  const completed = chores.filter((c) => c.completed).length

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <ListChecks size={16} className="text-indigo-400" /> Chores
          </h3>
          {chores.length > 0 && (
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">{pending} pending</span>
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">{completed} done</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={choreDate}
            onChange={(e) => onDateChange(e.target.value)}
            className="bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-indigo-500"
          />
          {choreDate && (
            <button onClick={() => onDateChange('')} className="text-xs text-slate-400 hover:text-slate-200">Clear</button>
          )}
          <button onClick={onAdd} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
            <Plus size={12} /> Assign
          </button>
        </div>
      </div>
      {chores.length === 0 ? (
        <EmptyTab message={choreDate ? `No chores for ${choreDate}.` : 'No chores logged.'} />
      ) : (
        <div className="space-y-2">
          {chores.map((c) => (
            <div key={c.chore_id} className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${c.completed ? 'bg-slate-700/20' : 'bg-slate-700/40'}`}>
              <button onClick={() => onToggle(c)} className="shrink-0 text-slate-400 hover:text-white transition-colors">
                {c.completed
                  ? <CheckSquare size={18} className="text-emerald-400" />
                  : <Square size={18} />
                }
              </button>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${c.completed ? 'text-slate-500 line-through' : 'text-white'}`}>
                  {c.chore_name}
                </p>
                <div className="flex flex-wrap gap-2 mt-0.5 text-xs text-slate-500">
                  {c.due_date && <span>Due {c.due_date}</span>}
                  {(c.first_name || c.last_name) && <span>→ {c.first_name} {c.last_name}</span>}
                  {c.location && <span>· {c.location}</span>}
                  {c.recurrence !== 'once' && c.recurrence && <span>· {c.recurrence}</span>}
                  {c.verified_by && <span>· Verified by {c.verified_by}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3C: Passes tab
// ---------------------------------------------------------------------------

const PASS_STATUS_COLORS = {
  approved: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  returned: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  revoked:  'bg-rose-500/20 text-rose-300 border-rose-500/30',
  overdue:  'bg-rose-500/20 text-rose-300 border-rose-500/30',
}

function TabPasses({ passes, onAdd, onReturn }) {
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Footprints size={16} className="text-indigo-400" /> Passes &amp; Overnight Leaves ({passes.length})
        </h3>
        <button onClick={onAdd} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-medium">
          <Plus size={12} /> Log Pass
        </button>
      </div>
      {passes.length === 0 ? (
        <EmptyTab message="No passes logged." />
      ) : (
        <div className="space-y-2">
          {passes.map((p) => {
            const isOverdue = p.expected_return_date < today && p.status === 'approved'
            const effectiveStatus = isOverdue ? 'overdue' : p.status
            const statusColor = PASS_STATUS_COLORS[effectiveStatus] || PASS_STATUS_COLORS.approved

            return (
              <div key={p.pass_id} className="bg-slate-700/30 rounded-lg px-4 py-3">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <p className="text-white font-medium text-sm">{p.first_name} {p.last_name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColor}`}>
                        {isOverdue ? 'OVERDUE' : p.status}
                      </span>
                      <span className="text-xs text-slate-500 capitalize">{p.pass_type}</span>
                      {p.is_blackout ? <Ban size={13} className="text-rose-400" /> : null}
                    </div>
                    <div className="text-xs text-slate-400 space-y-0.5">
                      <p>Left: {p.leave_date}{p.leave_time ? ` at ${p.leave_time}` : ''}</p>
                      <p>Expected back: {p.expected_return_date}{p.expected_return_time ? ` at ${p.expected_return_time}` : ''}</p>
                      {p.actual_return_date && <p className="text-emerald-400">Returned: {p.actual_return_date}{p.actual_return_time ? ` at ${p.actual_return_time}` : ''}</p>}
                      {p.destination && <p>Destination: {p.destination}</p>}
                      {p.approved_by && <p>Approved by: {p.approved_by}</p>}
                    </div>
                  </div>
                  {p.status === 'approved' && (
                    <button
                      onClick={() => onReturn(p)}
                      className="shrink-0 text-xs px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30"
                    >
                      Record Return
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3D: Curfew roll call tab
// ---------------------------------------------------------------------------

const CURFEW_STATUS_CONFIG = {
  present:   { color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', label: 'Present' },
  absent:    { color: 'bg-rose-500/20 text-rose-300 border-rose-500/30',         label: 'Absent'  },
  on_pass:   { color: 'bg-amber-500/20 text-amber-300 border-amber-500/30',      label: 'On Pass' },
  unexcused: { color: 'bg-orange-500/20 text-orange-300 border-orange-500/30',   label: 'Unexcused' },
}

function TabCurfew({ residents, curfewChecks, curfewDate, onDateChange, onCheck }) {
  const checkMap = {}
  curfewChecks.forEach((c) => { checkMap[c.resident_id] = c })

  const checkedCount   = Object.keys(checkMap).length
  const uncheckedCount = residents.length - checkedCount

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Moon size={16} className="text-indigo-400" /> Curfew Roll Call
          </h3>
          {residents.length > 0 && (
            <span className="text-xs text-slate-400">{checkedCount}/{residents.length} checked</span>
          )}
        </div>
        <input
          type="date"
          value={curfewDate}
          onChange={(e) => onDateChange(e.target.value)}
          className="bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-indigo-500"
        />
      </div>

      {uncheckedCount > 0 && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
          {uncheckedCount} resident{uncheckedCount !== 1 ? 's' : ''} not yet checked in
        </div>
      )}

      {residents.length === 0 ? (
        <EmptyTab message="No active residents to check." />
      ) : (
        <div className="space-y-2">
          {residents.map((r) => {
            const check = checkMap[r.resident_id]
            const currentStatus = check?.status || null

            return (
              <div key={r.resident_id} className="flex items-center justify-between gap-3 bg-slate-700/30 rounded-lg px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-white">{r.first_name} {r.last_name}</p>
                  {check?.checked_at && (
                    <p className="text-xs text-slate-500 mt-0.5">
                      Checked {new Date(check.checked_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      {check.checked_by ? ` by ${check.checked_by}` : ''}
                    </p>
                  )}
                </div>
                <div className="flex gap-1.5 flex-wrap justify-end">
                  {Object.entries(CURFEW_STATUS_CONFIG).map(([status, cfg]) => (
                    <button
                      key={status}
                      onClick={() => onCheck(r, status)}
                      className={`text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
                        currentStatus === status
                          ? `${cfg.color} font-medium`
                          : 'bg-slate-700/40 text-slate-500 border-slate-600 hover:border-slate-500 hover:text-slate-300'
                      }`}
                    >
                      {cfg.label}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// 3A: Attendance modal
// ---------------------------------------------------------------------------

function AttendanceModal({ meeting, residents, onSave, onClose }) {
  const [selected, setSelected] = useState(() => {
    try {
      const existing = meeting.attendance_json ? JSON.parse(meeting.attendance_json) : []
      return new Set(existing)
    } catch {
      return new Set()
    }
  })
  const [saving, setSaving] = useState(false)

  const toggle = (residentId) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(residentId)) next.delete(residentId)
      else next.add(residentId)
      return next
    })
  }

  const handleSave = async () => {
    setSaving(true)
    await onSave(meeting, JSON.stringify(Array.from(selected)))
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-slate-700">
          <div>
            <h2 className="font-semibold text-white">Take Attendance</h2>
            <p className="text-xs text-slate-400 mt-0.5">{meeting.scheduled_date}{meeting.meeting_type ? ` · ${meeting.meeting_type.toUpperCase()}` : ''}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-2 max-h-80 overflow-y-auto">
          {residents.length === 0 ? (
            <p className="text-sm text-slate-400">No residents to mark.</p>
          ) : (
            residents.map((r) => {
              const isSelected = selected.has(r.resident_id)
              return (
                <button
                  key={r.resident_id}
                  onClick={() => toggle(r.resident_id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                    isSelected ? 'bg-emerald-500/15 border border-emerald-500/30' : 'bg-slate-700/30 border border-transparent hover:bg-slate-700/50'
                  }`}
                >
                  {isSelected
                    ? <CheckSquare size={16} className="text-emerald-400 shrink-0" />
                    : <Square size={16} className="text-slate-500 shrink-0" />
                  }
                  <span className={`text-sm ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                    {r.first_name} {r.last_name}
                  </span>
                </button>
              )
            })
          )}
        </div>
        <div className="flex items-center justify-between px-5 py-4 border-t border-slate-700">
          <span className="text-xs text-slate-400">{selected.size} of {residents.length} present</span>
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Attendance'}
            </button>
          </div>
        </div>
      </div>
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
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={18} />
          </button>
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
