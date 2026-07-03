import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Home,
  Briefcase,
  DollarSign,
  Scale,
  Building2,
  MessageSquare,
  Edit,
  Plus,
  ExternalLink,
  TrendingUp,
  Target,
  Shield,
  ShieldCheck,
  RefreshCw,
  Filter,
  Sparkles,
  Zap,
  FolderOpen,
  Upload,
  Trash2,
  Eye,
  Download,
  X,
  ClipboardList
} from 'lucide-react'
import toast from 'react-hot-toast'
import useNotes from '../hooks/useNotes'
import NoteForm from '../components/NoteForm'
import NotesList from '../components/NotesList'
import useTasks from '../hooks/useTasks'
import TaskForm from '../components/TaskForm'
import TasksList from '../components/TasksList'
import TaskViewModal from '../components/TaskViewModal'
import RoiConsentTracker from '../components/RoiConsentTracker'
import { apiFetch } from '../api/config'
import {
  fetchClientDocumentObjectUrl,
  isProtectedClientDocument,
  openClientDocument,
  downloadClientDocument,
} from '../utils/clientDocuments'
import {
  deriveDocumentCategory,
  VAULT_CATEGORIES,
  categoryLabel,
} from '../utils/documentCategories'

const listOrEmpty = (value) => (Array.isArray(value) ? value : [])

const formatPlanLabel = (value) =>
  String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim()

const getPlanItemText = (item, fields = ['description', 'summary', 'title', 'need_key', 'reason']) => {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return ''
  for (const field of fields) {
    if (item[field]) return String(item[field])
  }
  return ''
}

const getAftercareEntries = (aftercarePlan) => {
  if (!aftercarePlan || typeof aftercarePlan !== 'object') return []
  return Object.entries(aftercarePlan).flatMap(([key, value]) => {
    if (!value) return []
    if (typeof value === 'boolean') return [formatPlanLabel(key.replace(/_needed$/i, ''))]
    if (typeof value === 'string') return [{ label: formatPlanLabel(key), value }]
    return []
  })
}

const getReferralDisplayType = (referral) =>
  referral?.service_type ||
  referral?.service_name ||
  referral?.provider_type ||
  referral?.provider_category ||
  'Referral'

const getReferralDisplayStatus = (referral) =>
  referral?.status ||
  referral?.referral_status ||
  'Pending'

const getRoiSummaryStats = (records) => {
  const roiRecords = Array.isArray(records) ? records : []
  return {
    active: roiRecords.filter((record) => record?.status === 'active').length,
    awaitingSignature: roiRecords.filter((record) => ['draft', 'needs_signature'].includes(record?.status)).length,
    revoked: roiRecords.filter((record) => record?.status === 'revoked').length,
    total: roiRecords.length,
  }
}

const isConsentForm = (form) =>
  String(form?.category || '').toLowerCase().includes('consent')

const isPacketRoiForm = (form) => {
  const key = String(form?.form_key || '').toLowerCase()
  return key.includes('roi') || key.includes('release')
}

const buildPlanTasks = (plan) => {
  if (!plan) return []

  const tasks = [
    ...listOrEmpty(plan.operational_needs).map((need) => ({
      source: 'Operational need',
      text: need.reason || formatPlanLabel(need.need_key || need.domain || 'Need'),
      meta: [need.priority, need.domain].filter(Boolean).map(formatPlanLabel).join(' · '),
    })),
    ...listOrEmpty(plan.objectives).map((objective) => ({
      source: 'Objective',
      text: getPlanItemText(objective, ['description', 'summary', 'title']),
      meta: objective?.measure ? `Measure: ${objective.measure}` : '',
    })),
    ...listOrEmpty(plan.interventions).map((intervention) => ({
      source: 'Intervention',
      text: getPlanItemText(intervention, ['description', 'summary', 'title']),
      meta: [intervention?.assigned_module && `Module: ${formatPlanLabel(intervention.assigned_module)}`, intervention?.frequency].filter(Boolean).join(' · '),
    })),
    ...getAftercareEntries(plan.aftercare_plan).map((entry) => ({
      source: 'Aftercare',
      text: typeof entry === 'string' ? entry : `${entry.label}: ${entry.value}`,
      meta: '',
    })),
  ]

  const seen = new Set()
  return tasks.filter((task) => {
    const text = String(task.text || '').trim()
    if (!text) return false
    const key = text.toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const normalizeTaskPriority = (value) => {
  const normalized = String(value || 'medium').trim().toLowerCase()
  return normalized || 'medium'
}

const normalizeTaskStatus = (value) => {
  const normalized = String(value || 'pending').trim().toLowerCase().replace(/-/g, '_')
  if (normalized === 'active') return 'pending'
  return normalized || 'pending'
}

const sortTasksByDueDate = (left, right) => {
  const leftTime = left?.due_date ? new Date(left.due_date).getTime() : Number.POSITIVE_INFINITY
  const rightTime = right?.due_date ? new Date(right.due_date).getTime() : Number.POSITIVE_INFINITY
  if (leftTime !== rightTime) return leftTime - rightTime
  return String(left?.title || '').localeCompare(String(right?.title || ''))
}

const ClientDashboard = () => {
  const { clientId } = useParams()
  const navigate = useNavigate()
  const [clientData, setClientData] = useState(null)
  const [treatmentPlan, setTreatmentPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [clientWorkItems, setClientWorkItems] = useState([])
  const [workItemsLoading, setWorkItemsLoading] = useState(false)
  const [searchRecommendations, setSearchRecommendations] = useState(null)
  
  // Notes functionality
  const { 
    notes, 
    loading: notesLoading, 
    syncing, 
    addNote, 
    updateNote, 
    deleteNote, 
    syncAllNotes, 
    getFilteredNotes, 
    getNotesStats 
  } = useNotes(clientId)
  
  const [showNoteForm, setShowNoteForm] = useState(false)
  const [editingNote, setEditingNote] = useState(null)
  const [selectedNoteType, setSelectedNoteType] = useState('All')
  
  // Tasks functionality
  const { 
    loading: tasksLoading, 
    syncing: tasksSyncing, 
    addTask, 
    updateTask, 
    deleteTask, 
    completeTask
  } = useTasks(clientId)
  
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [selectedTaskFilter, setSelectedTaskFilter] = useState('All')
  const [showTaskView, setShowTaskView] = useState(false)
  const [viewingTask, setViewingTask] = useState(null)

  // Appointments state
  const [appointments, setAppointments] = useState([])
  const [showAptModal, setShowAptModal] = useState(false)
  const [editingApt, setEditingApt] = useState(null)
  const [aptForm, setAptForm] = useState({
    title: '', appointment_date: '', appointment_time: '',
    location: '', doctor_name: '', service_type: '', notes: '', items_to_bring: ''
  })
  const [aptSaving, setAptSaving] = useState(false)

  // Documents state
  const [documents, setDocuments] = useState([])
  // Lightweight ROI record summary for the Documents-tab quick link.
  // The full ROI manager lives on its own "ROI / Releases" tab.
  const [roiRecords, setRoiRecords] = useState([])
  const [packetRoiPendingSignatureCount, setPacketRoiPendingSignatureCount] = useState(0)
  const [showDocViewer, setShowDocViewer] = useState(false)
  const [viewingDoc, setViewingDoc] = useState(null)
  // Authenticated blob preview for the doc viewer. Protected files are fetched
  // with the Firebase bearer token and surfaced as an object URL (raw src/href
  // cannot send the token).
  const [docBlobUrl, setDocBlobUrl] = useState(null)
  const [docBlobLoading, setDocBlobLoading] = useState(false)
  const [docBlobError, setDocBlobError] = useState(false)
  const [docBlobText, setDocBlobText] = useState(null)
  const [docUploading, setDocUploading] = useState(false)
  const [showDocUpload, setShowDocUpload] = useState(false)
  const [docForm, setDocForm] = useState({ title: '', doc_type: 'other', url: '' })
  const [docFile, setDocFile] = useState(null)
  const [docVaultFilter, setDocVaultFilter] = useState('all')

  // Edit client modal
  const [showEditModal, setShowEditModal] = useState(false)
  const [editForm, setEditForm] = useState({})
  const [editSaving, setEditSaving] = useState(false)

  // Saved housing leads / applications (persisted in the housing module)
  const [housingLeads, setHousingLeads] = useState([])
  const [housingLeadsLoading, setHousingLeadsLoading] = useState(false)

  useEffect(() => {
    if (clientId) {
      fetchClientData()
      fetchTreatmentPlan()
      fetchClientWorkItems()
      fetchSearchRecommendations()
      fetchAppointments()
      fetchDocuments()
      fetchRoiRecords()
      fetchPacketRoiStatus()
    }
  }, [clientId])

  useEffect(() => {
    if (clientId && activeTab === 'housing') {
      fetchHousingLeads()
    }
  }, [activeTab, clientId])

  const fetchHousingLeads = async () => {
    try {
      setHousingLeadsLoading(true)
      const res = await apiFetch(`/api/housing/applications/${clientId}`)
      if (res.ok) {
        const data = await res.json()
        setHousingLeads(data.success ? (data.applications || []) : [])
      } else {
        setHousingLeads([])
      }
    } catch (error) {
      console.error('Error fetching housing leads:', error)
      setHousingLeads([])
    } finally {
      setHousingLeadsLoading(false)
    }
  }

  useEffect(() => {
    if (clientId && (activeTab === 'docs' || activeTab === 'roi')) {
      fetchRoiRecords()
    }
  }, [activeTab, clientId])

  const fetchClientData = async () => {
    try {
      setLoading(true)
      setLoadError('')
      const response = await apiFetch(`/api/clients/${clientId}/unified-view`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setClientData(data.client_data)
        } else {
          throw new Error(data.message || 'Failed to fetch client data')
        }
      } else {
        throw new Error(`Failed to fetch client data (HTTP ${response.status})`)
      }
    } catch (error) {
      console.error('Error fetching client data:', error)
      setClientData(null)
      setLoadError(error?.message || 'Failed to load client data')
      toast.error('Failed to load client data')
    } finally {
      setLoading(false)
    }
  }

  const fetchClientWorkItems = async () => {
    try {
      setWorkItemsLoading(true)
      const response = await apiFetch(`/api/clients/${clientId}/work-items`)
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setClientWorkItems(Array.isArray(data.items) ? data.items : [])
        }
      }
    } catch (error) {
      console.log('Client work items not available:', error)
      setClientWorkItems([])
    } finally {
      setWorkItemsLoading(false)
    }
  }

  const fetchTreatmentPlan = async () => {
    try {
      const response = await apiFetch(`/api/clients/${clientId}/treatment-plan`)
      if (!response.ok) return
      const data = await response.json()
      if (data.success) {
        setTreatmentPlan(data.current_plan || null)
      }
    } catch (error) {
      console.log('Treatment plan not available on dashboard:', error)
    }
  }

  const fetchSearchRecommendations = async () => {
    try {
      const response = await apiFetch(`/api/clients/${clientId}/search-recommendations`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setSearchRecommendations(data.recommendations)
        }
      } else {
        console.log('Search recommendations not available')
      }
    } catch (error) {
      console.log('Search system not available:', error)
    }
  }

  const getRiskLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border border-red-500/30'
      case 'medium': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border border-yellow-500/30'
      case 'low': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
    }
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30'
      case 'inactive': return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
      case 'urgent': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border border-red-500/30'
      case 'pending': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border border-yellow-500/30'
      case 'completed': return 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 border border-blue-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'urgent': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border border-red-500/30'
      case 'high': return 'bg-gradient-to-r from-orange-500/20 to-amber-500/20 text-orange-300 border border-orange-500/30'
      case 'medium': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border border-yellow-500/30'
      case 'low': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const getActivityStyles = (type) => {
    switch (type) {
      case 'task':
        return {
          badge: 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 border border-blue-500/30',
          card: 'from-blue-500/15 to-cyan-500/15 border-blue-500/20',
        }
      case 'note':
        return {
          badge: 'bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-300 border border-emerald-500/30',
          card: 'from-emerald-500/15 to-green-500/15 border-emerald-500/20',
        }
      case 'reminder':
        return {
          badge: 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-300 border border-amber-500/30',
          card: 'from-amber-500/15 to-orange-500/15 border-amber-500/20',
        }
      case 'contact':
        return {
          badge: 'bg-gradient-to-r from-fuchsia-500/20 to-pink-500/20 text-fuchsia-300 border border-fuchsia-500/30',
          card: 'from-fuchsia-500/15 to-pink-500/15 border-fuchsia-500/20',
        }
      case 'milestone':
        return {
          badge: 'bg-gradient-to-r from-violet-500/20 to-purple-500/20 text-violet-300 border border-violet-500/30',
          card: 'from-violet-500/15 to-purple-500/15 border-violet-500/20',
        }
      default:
        return {
          badge: 'bg-gradient-to-r from-gray-500/20 to-slate-500/20 text-gray-300 border border-gray-500/30',
          card: 'from-white/10 to-white/5 border-white/10',
        }
    }
  }

  // Notes handler functions
  const handleAddNote = () => {
    setEditingNote(null)
    setShowNoteForm(true)
  }

  const handleEditNote = (note) => {
    setEditingNote(note)
    setShowNoteForm(true)
  }

  const handleNoteSubmit = async (noteData) => {
    try {
      if (editingNote) {
        await updateNote(editingNote.note_id, noteData)
      } else {
        await addNote(noteData)
      }
      setShowNoteForm(false)
      setEditingNote(null)
    } catch (error) {
      console.error('Error saving note:', error)
    }
  }

  const handleDeleteNote = async (noteId) => {
    try {
      await deleteNote(noteId)
    } catch (error) {
      console.error('Error deleting note:', error)
    }
  }

  const handleTemplateSelect = (template) => {
    const templateData = {
      note_type: getTemplateType(template),
      content: getTemplateContent(template)
    }
    setEditingNote(templateData)
    setShowNoteForm(true)
  }

  const getTemplateType = (template) => {
    const typeMap = {
      'Client Contact - Phone': 'Contact',
      'Client Contact - In Person': 'Contact',
      'Progress Update': 'Progress',
      'Barrier Identified': 'Assessment',
      'Goal Achievement': 'Progress',
      'Service Referral Made': 'Follow-up',
      'Court Date Reminder': 'Court',
      'Housing Update': 'Housing'
    }
    return typeMap[template] || 'General'
  }

  const getTemplateContent = (template) => {
    const templates = {
      'initial-contact': 'Initial contact made with client. Discussed case details and next steps.',
      'follow-up': 'Follow-up contact completed. Client provided additional information.',
      'documentation': 'Documentation review completed. All required forms submitted.',
      'referral': 'Client referred to appropriate service provider.',
      'case-closed': 'Case successfully closed. All objectives met.'
    };
    return templates[template] || 'Note added to case file.';
  };

  // Task Management Functions
  const handleAddTask = () => {
    setEditingTask(null)
    setShowTaskForm(true)
  }

  const handleEditTask = (task) => {
    if (task?.can_edit === false) return
    setEditingTask(task)
    setShowTaskForm(true)
  }

  const handleViewTask = (task) => {
    setViewingTask(task)
    setShowTaskView(true)
  }

  const handleTaskSubmit = async (taskData) => {
    try {
      if (editingTask?.source_kind === 'reminder') {
        const response = await apiFetch(`/api/reminders/${editingTask.task_id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            reminder_text: taskData.title,
            due_date: taskData.due_date,
            priority: taskData.priority,
            reminder_type: taskData.task_type,
          }),
        })
        if (!response.ok) {
          throw new Error('Failed to update reminder')
        }
        await Promise.all([fetchClientData(), fetchClientWorkItems()])
        toast.success('Reminder updated successfully!')
      } else if (editingTask) {
        await updateTask(editingTask.task_id, taskData)
        await fetchClientWorkItems()
        toast.success('Task updated successfully!')
      } else {
        await addTask(taskData)
        await fetchClientWorkItems()
        toast.success('Task created successfully!')
      }
      setShowTaskForm(false)
      setEditingTask(null)
    } catch (error) {
      console.error('Error saving task:', error)
      toast.error('Failed to save task. Please try again.')
    }
  }

  const handleCompleteTask = async (taskId) => {
    try {
      const task = mergedTasks.find((item) => item.task_id === taskId)
      if (task?.source_kind === 'reminder') {
        const response = await apiFetch(`/api/reminders/${taskId}/complete`, { method: 'POST' })
        if (!response.ok) {
          throw new Error('Failed to complete reminder')
        }
        await Promise.all([fetchClientData(), fetchClientWorkItems()])
        toast.success('Reminder marked as complete!')
        return
      }

      if (task?.source_kind === 'intelligent_task') {
        const response = await apiFetch(`/api/reminders/tasks/${taskId}/complete`, { method: 'POST' })
        if (!response.ok) {
          throw new Error('Failed to complete task')
        }
        await fetchClientWorkItems()
        toast.success('Task marked as complete!')
        return
      }

      await completeTask(taskId)
      await fetchClientWorkItems()
      toast.success('Task marked as complete!')
    } catch (error) {
      console.error('Error completing task:', error)
      toast.error('Failed to complete task. Please try again.')
    }
  }

  const handleDeleteTask = async (taskId) => {
    try {
      const task = mergedTasks.find((item) => item.task_id === taskId)
      if (task?.source_kind === 'reminder') {
        const response = await apiFetch(`/api/reminders/${taskId}`, { method: 'DELETE' })
        if (!response.ok) {
          throw new Error('Failed to delete reminder')
        }
        await Promise.all([fetchClientData(), fetchClientWorkItems()])
        toast.success('Reminder deleted successfully!')
        return
      }
      await deleteTask(taskId)
      await fetchClientWorkItems()
      toast.success('Task deleted successfully!')
    } catch (error) {
      console.error('Error deleting task:', error)
      toast.error('Failed to delete task. Please try again.')
    }
  }

  const handleOpenEdit = () => {
    if (!clientData?.client) return
    const c = clientData.client
    setEditForm({
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      phone: c.phone || '',
      email: c.email || '',
      date_of_birth: c.date_of_birth || '',
      address: c.address || '',
      city: c.city || '',
      state: c.state || '',
      zip_code: c.zip_code || '',
      emergency_contact_name: c.emergency_contact_name || '',
      emergency_contact_phone: c.emergency_contact_phone || '',
      emergency_contact_relationship: c.emergency_contact_relationship || '',
      risk_level: c.risk_level || 'medium',
      case_status: c.case_status || 'active',
      housing_status: c.housing_status || 'unknown',
      employment_status: c.employment_status || 'unknown',
      benefits_status: c.benefits_status || '',
      legal_status: c.legal_status || '',
      program_type: c.program_type || '',
    })
    setShowEditModal(true)
  }

  const handleSaveEdit = async () => {
    try {
      setEditSaving(true)
      const response = await apiFetch(`/api/clients/${clientId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      })
      if (response.ok) {
        toast.success('Client updated successfully!')
        setShowEditModal(false)
        fetchClientData()
      } else {
        const err = await response.json().catch(() => ({}))
        toast.error(err.message || 'Failed to update client')
      }
    } catch (error) {
      toast.error('Failed to update client')
    } finally {
      setEditSaving(false)
    }
  }

  // ── Appointments ──────────────────────────────────────────────────────────

  const fetchAppointments = async () => {
    try {
      const res = await apiFetch(`/api/clients/${clientId}/appointments`)
      if (res.ok) {
        const data = await res.json()
        if (data.success) setAppointments(data.appointments || [])
      }
    } catch (e) {
      console.log('Appointments not loaded:', e)
    }
  }

  const openAddApt = () => {
    setEditingApt(null)
    setAptForm({ title: '', appointment_date: '', appointment_time: '', location: '', doctor_name: '', service_type: '', notes: '', items_to_bring: '' })
    setShowAptModal(true)
  }

  const openEditApt = (apt) => {
    setEditingApt(apt)
    setAptForm({
      title: apt.title || '',
      appointment_date: apt.appointment_date || '',
      appointment_time: apt.appointment_time || '',
      location: apt.location || '',
      doctor_name: apt.doctor_name || '',
      service_type: apt.service_type || '',
      notes: apt.notes || '',
      items_to_bring: apt.items_to_bring || '',
    })
    setShowAptModal(true)
  }

  const saveApt = async () => {
    if (!aptForm.title || !aptForm.appointment_date) {
      toast.error('Title and date are required')
      return
    }
    setAptSaving(true)
    try {
      const method = editingApt ? 'PUT' : 'POST'
      const url = editingApt
        ? `/api/clients/${clientId}/appointments/${editingApt.apt_id}`
        : `/api/clients/${clientId}/appointments`
      const res = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(aptForm),
      })
      if (!res.ok) throw new Error('Failed to save')
      toast.success(editingApt ? 'Appointment updated!' : 'Appointment created!')
      setShowAptModal(false)
      fetchAppointments()
    } catch (e) {
      toast.error('Failed to save appointment')
    } finally {
      setAptSaving(false)
    }
  }

  const deleteApt = async (aptId) => {
    if (!window.confirm('Delete this appointment?')) return
    try {
      const res = await apiFetch(`/api/clients/${clientId}/appointments/${aptId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Appointment deleted')
      setAppointments(prev => prev.filter(a => a.apt_id !== aptId))
    } catch {
      toast.error('Failed to delete appointment')
    }
  }

  // ── Documents ─────────────────────────────────────────────────────────────

  const fetchDocuments = async () => {
    try {
      const res = await apiFetch(`/api/clients/${clientId}/documents`)
      if (res.ok) {
        const data = await res.json()
        if (data.success) setDocuments(data.documents || [])
      }
    } catch (e) {
      console.log('Documents not loaded:', e)
    }
  }

  const fetchRoiRecords = async () => {
    try {
      const res = await apiFetch(`/api/clients/${clientId}/roi-records`)
      if (res.ok) {
        const data = await res.json()
        setRoiRecords(data?.roi_records || [])
      }
    } catch (e) {
      // ROI summary is optional; the dedicated ROI / Releases tab is authoritative.
    }
  }

  const fetchPacketRoiStatus = async () => {
    try {
      const res = await apiFetch(`/api/admissions/packets/${clientId}`)
      if (!res.ok) {
        setPacketRoiPendingSignatureCount(0)
        return
      }
      const data = await res.json()
      const packetForms = Array.isArray(data?.packet?.forms) ? data.packet.forms : []
      const pendingCount = packetForms.filter(
        (form) =>
          isConsentForm(form) &&
          isPacketRoiForm(form) &&
          String(form?.status || '') === 'Needs Signature'
      ).length
      setPacketRoiPendingSignatureCount(pendingCount)
    } catch (e) {
      setPacketRoiPendingSignatureCount(0)
    }
  }

  const docViewEndpoint = (doc) => `/api/clients/${clientId}/documents/${doc.doc_id}/view`
  const isProtectedDoc = (doc) => isProtectedClientDocument(doc)
  const isHtmlDocument = (doc, blob) => {
    const mime = doc?.file_mime || blob?.type || ''
    if (/^text\/html\b/i.test(mime)) return true
    return /\.(html?)$/i.test(String(doc?.file_name || ''))
  }

  const isTextPreviewable = (doc, blob) => {
    const mime = doc?.file_mime || blob?.type || ''
    if (mime.startsWith('text/')) return true
    return /\.(txt|md|markdown|html?)$/i.test(String(doc?.file_name || ''))
  }

  const readBlobAsText = (blob) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = () => reject(reader.error)
      reader.readAsText(blob, 'utf-8')
    })

  const openDocViewer = async (doc) => {
    setViewingDoc(doc)
    setShowDocViewer(true)
    setDocBlobError(false)
    // External-URL documents need no authenticated fetch; preview uses doc.url.
    if (!isProtectedDoc(doc)) {
      setDocBlobUrl(null)
      setDocBlobLoading(false)
      return
    }
    setDocBlobLoading(true)
    setDocBlobUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null })
    try {
      const { objectUrl, blob } = await fetchClientDocumentObjectUrl(docViewEndpoint(doc))
      setDocBlobUrl(objectUrl)
      if (isTextPreviewable(doc, blob)) {
        const text = await readBlobAsText(blob)
        setDocBlobText(text)
      } else {
        setDocBlobText(null)
      }
    } catch {
      setDocBlobError(true)
    } finally {
      setDocBlobLoading(false)
    }
  }

  const closeDocViewer = () => {
    setShowDocViewer(false)
    setViewingDoc(null)
    setDocBlobLoading(false)
    setDocBlobError(false)
    setDocBlobText(null)
    setDocBlobUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null })
  }

  const handleOpenDocument = async (doc) => {
    if (!isProtectedDoc(doc)) {
      if (doc.url && typeof window !== 'undefined') window.open(doc.url, '_blank', 'noopener,noreferrer')
      return
    }
    try {
      const opened = await openClientDocument(docViewEndpoint(doc))
      if (!opened) toast.error('Could not open document. Please try again.')
    } catch {
      toast.error('Could not open document. Please try again.')
    }
  }

  const handleDownloadDocument = async (doc) => {
    if (!isProtectedDoc(doc)) {
      if (doc.url && typeof window !== 'undefined') window.open(doc.url, '_blank', 'noopener,noreferrer')
      return
    }
    try {
      await downloadClientDocument(docViewEndpoint(doc), doc.file_name || doc.title || 'document')
    } catch {
      toast.error('Could not download document. Please try again.')
    }
  }

  const uploadDocument = async () => {
    if (!docForm.title) { toast.error('Title is required'); return }
    if (!docFile && !docForm.url) { toast.error('Attach a file or enter a URL'); return }
    setDocUploading(true)
    try {
      const fd = new FormData()
      fd.append('title', docForm.title)
      fd.append('doc_type', docForm.doc_type)
      if (docForm.url) fd.append('url', docForm.url)
      if (docFile) fd.append('file', docFile)
      const res = await apiFetch(`/api/clients/${clientId}/documents`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error()
      toast.success('Document uploaded!')
      setShowDocUpload(false)
      setDocForm({ title: '', doc_type: 'other', url: '' })
      setDocFile(null)
      fetchDocuments()
    } catch {
      toast.error('Failed to upload document')
    } finally {
      setDocUploading(false)
    }
  }

  const roiSummary = getRoiSummaryStats(roiRecords)

  const filteredDocs = docVaultFilter === 'all'
    ? documents
    : documents.filter((d) => deriveDocumentCategory(d) === docVaultFilter)

  const deleteDocument = async (docId) => {
    if (!window.confirm('Delete this document?')) return
    try {
      const res = await apiFetch(`/api/clients/${clientId}/documents/${docId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Document deleted')
      setDocuments(prev => prev.filter(d => d.doc_id !== docId))
    } catch {
      toast.error('Failed to delete document')
    }
  }

  const getDocViewUrl = (doc) => {
    if (isProtectedDoc(doc)) return `/api/clients/${clientId}/documents/${doc.doc_id}/view`
    if (doc.url) return doc.url
    return null
  }

  if (loading) {
    return (
      <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative mx-auto mb-6 w-12 h-12">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-500/20 border-t-purple-500"></div>
            <div className="absolute inset-2 animate-spin rounded-full border-2 border-blue-500/20 border-t-blue-500" style={{animationDirection: 'reverse'}}></div>
          </div>
          <p className="text-gray-300 font-medium">Loading client data...</p>
        </div>
      </div>
    )
  }

  if (!clientData) {
    return (
      <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20">
          <div className="p-4 bg-gradient-to-r from-red-500/20 to-pink-500/20 rounded-2xl w-fit mx-auto mb-6">
            <AlertCircle className="h-12 w-12 text-red-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-3">Client Not Found</h2>
          <p className="text-gray-400 mb-3">The requested client could not be loaded.</p>
          {loadError && <p className="text-red-300 text-sm mb-6">{loadError}</p>}
          <button
            onClick={() => navigate('/case-management')}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25"
          >
            Back to Case Management
          </button>
        </div>
      </div>
    )
  }

  const { client } = clientData
  const activityTimeline = [
    ...(clientData.recent_activity || []).map((activity, index) => ({
      id: `activity-${index}-${activity.date || ''}`,
      type: activity.type || 'activity',
      title: activity.action || 'Activity recorded',
      detail: activity.category ? `Category: ${activity.category}` : '',
      date: activity.date,
      priority: activity.priority || null,
    })),
    ...(clientData.contact_history || []).map((contact, index) => ({
      id: `contact-${contact.contact_id || index}`,
      type: 'contact',
      title: `${contact.contact_type || 'Contact'} via ${contact.contact_method || 'recorded method'}`,
      detail: contact.notes || contact.outcome || '',
      date: contact.contact_date || contact.created_at,
      priority: null,
    })),
    ...(clientData.program_milestones || []).map((milestone, index) => ({
      id: `milestone-${milestone.milestone_id || index}`,
      type: 'milestone',
      title: milestone.milestone_name || 'Program milestone',
      detail: `${milestone.status || 'Pending'}${milestone.milestone_type ? ` • ${milestone.milestone_type}` : ''}`,
      date: milestone.completion_date || milestone.due_date || milestone.created_at,
      priority: milestone.priority || null,
    })),
  ]
    .filter((entry) => entry.date)
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  const recentTimeline = activityTimeline.slice(0, 8)
  const pendingMilestones = (clientData.program_milestones || [])
    .filter((milestone) => `${milestone.status || ''}`.toLowerCase() !== 'completed')
    .slice(0, 5)
  const dashboardGoals = listOrEmpty(treatmentPlan?.goals).length > 0 ? listOrEmpty(treatmentPlan.goals) : listOrEmpty(clientData.goals)
  const dashboardBarriers = listOrEmpty(treatmentPlan?.problems).length > 0 ? listOrEmpty(treatmentPlan.problems) : listOrEmpty(clientData.barriers)
  const planObjectives = listOrEmpty(treatmentPlan?.objectives)
  const planInterventions = listOrEmpty(treatmentPlan?.interventions)
  const planOperationalNeeds = listOrEmpty(treatmentPlan?.operational_needs)
  const planAftercareEntries = getAftercareEntries(treatmentPlan?.aftercare_plan)
  const planTasks = buildPlanTasks(treatmentPlan)
  const hasTreatmentPlan = Boolean(treatmentPlan)
  const clientFullName = `${client.first_name || ''} ${client.last_name || ''}`.trim() || 'Client record unavailable'

  const mergedTasks = clientWorkItems
    .map((task) => ({
      ...task,
      priority: normalizeTaskPriority(task.priority),
      status: normalizeTaskStatus(task.status),
      client_id: task.client_id || clientId,
      client_name: task.client_name || clientFullName,
    }))
    .filter((task, index, all) => task.task_id && all.findIndex((candidate) => `${candidate.source_kind}:${candidate.task_id}` === `${task.source_kind}:${task.task_id}`) === index)
    .sort(sortTasksByDueDate)

  const filteredTasks = mergedTasks.filter((task) => {
    if (selectedTaskFilter === 'All') return true
    if (selectedTaskFilter === 'high') return task.priority === 'high'
    if (selectedTaskFilter === 'urgent') return task.priority === 'urgent'
    return task.status === selectedTaskFilter
  })

  const taskStats = {
    total: mergedTasks.length,
    pending: mergedTasks.filter((task) => task.status === 'pending').length,
    inProgress: mergedTasks.filter((task) => task.status === 'in_progress').length,
    completed: mergedTasks.filter((task) => task.status === 'completed').length,
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User, gradient: 'from-blue-500 to-indigo-500' },
    { id: 'timeline', label: 'Timeline', icon: MessageSquare, gradient: 'from-teal-500 to-cyan-500' },
    { id: 'appointments', label: 'Appointments', icon: Calendar, gradient: 'from-blue-500 to-cyan-500' },
    { id: 'docs', label: 'Documents', icon: FolderOpen, gradient: 'from-violet-500 to-purple-500' },
    { id: 'roi', label: 'ROI / Releases', icon: ShieldCheck, gradient: 'from-emerald-500 to-teal-500' },
    { id: 'housing', label: 'Housing', icon: Home, gradient: 'from-orange-500 to-red-500' },
    { id: 'employment', label: 'Employment', icon: Briefcase, gradient: 'from-green-500 to-emerald-500' },
    { id: 'benefits', label: 'Benefits', icon: DollarSign, gradient: 'from-purple-500 to-violet-500' },
    { id: 'legal', label: 'Legal', icon: Scale, gradient: 'from-amber-500 to-orange-500' },
    { id: 'services', label: 'Services', icon: Building2, gradient: 'from-teal-500 to-cyan-500' },
    { id: 'tasks', label: 'Tasks', icon: CheckCircle, gradient: 'from-emerald-500 to-green-500' },
    { id: 'notes', label: 'Notes', icon: FileText, gradient: 'from-blue-500 to-cyan-500' }
  ]

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => navigate('/case-management')}
                  className="group p-3 hover:bg-white/10 rounded-xl transition-all duration-300 border border-white/20 hover:border-white/30"
                >
                  <ArrowLeft className="h-5 w-5 text-gray-400 group-hover:text-white transition-colors" />
                </button>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent">
                    {client.first_name} {client.last_name}
                  </h1>
                  <p className="text-gray-400">Client reference: {client.client_id}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className={`px-4 py-2 rounded-xl text-sm font-medium ${getRiskLevelColor(client.risk_level)}`}>
                  {client.risk_level} Risk
                </span>
                <span className={`px-4 py-2 rounded-xl text-sm font-medium ${getStatusColor(client.case_status)}`}>
                  {client.case_status}
                </span>
                <Link
                  to="/messages"
                  className="group flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm font-medium text-cyan-100 transition-all duration-300 hover:border-cyan-300/50 hover:bg-cyan-500/25"
                  title="Open client-linked message threads"
                >
                  <MessageSquare className="h-4 w-4" />
                  Messages
                </Link>
                <button
                  onClick={handleOpenEdit}
                  className="group p-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25"
                  title="Edit client"
                >
                  <Edit className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Client Info Bar */}
        <div className="bg-white/5 backdrop-blur-sm border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center space-x-3">
                <div className="p-1 bg-blue-500/20 rounded">
                  <Phone className="h-4 w-4 text-blue-400" />
                </div>
                <span className="text-gray-300">{client.phone || 'No phone'}</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="p-1 bg-green-500/20 rounded">
                  <Mail className="h-4 w-4 text-green-400" />
                </div>
                <span className="text-gray-300">{client.email || 'No email'}</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="p-1 bg-purple-500/20 rounded">
                  <MapPin className="h-4 w-4 text-purple-400" />
                </div>
                <span className="text-gray-300">
                  {[client.address, client.city, client.state, client.zip_code].filter(Boolean).join(', ') || 'No address'}
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="p-1 bg-orange-500/20 rounded">
                  <Calendar className="h-4 w-4 text-orange-400" />
                </div>
                <span className="text-gray-300">Intake: {formatDate(client.intake_date)}</span>
              </div>
            </div>
            {/* Second row — extended info */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm mt-3 pt-3 border-t border-white/10">
              {client.date_of_birth && (
                <div className="flex items-center space-x-3">
                  <div className="p-1 bg-cyan-500/20 rounded">
                    <User className="h-4 w-4 text-cyan-400" />
                  </div>
                  <span className="text-gray-300">DOB: {formatDate(client.date_of_birth)}</span>
                </div>
              )}
              {client.program_type && (
                <div className="flex items-center space-x-3">
                  <div className="p-1 bg-indigo-500/20 rounded">
                    <Building2 className="h-4 w-4 text-indigo-400" />
                  </div>
                  <span className="text-gray-300">{client.program_type}</span>
                </div>
              )}
              {client.emergency_contact_name && (
                <div className="flex items-center space-x-3">
                  <div className="p-1 bg-red-500/20 rounded">
                    <Phone className="h-4 w-4 text-red-400" />
                  </div>
                  <span className="text-gray-300">Emergency: {client.emergency_contact_name} {client.emergency_contact_phone ? `· ${client.emergency_contact_phone}` : ''}</span>
                </div>
              )}
              {client.referral_source && (
                <div className="flex items-center space-x-3">
                  <div className="p-1 bg-teal-500/20 rounded">
                    <ExternalLink className="h-4 w-4 text-teal-400" />
                  </div>
                  <span className="text-gray-300">Referred: {client.referral_source}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white/5 backdrop-blur-sm border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6">
            <div className="flex space-x-2 overflow-x-auto">
              {tabs.map((tab) => {
                const IconComponent = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`group flex items-center space-x-3 py-4 px-6 font-medium text-sm whitespace-nowrap transition-all duration-300 relative ${
                      activeTab === tab.id
                        ? 'text-white'
                        : 'text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <div className={`p-2 rounded-lg transition-all duration-300 ${
                      activeTab === tab.id 
                        ? `bg-gradient-to-r ${tab.gradient} shadow-lg` 
                        : 'bg-white/10 group-hover:bg-white/20'
                    }`}>
                      <IconComponent className="h-4 w-4 text-white" />
                    </div>
                    <span>{tab.label}</span>
                    {activeTab === tab.id && (
                      <div className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${tab.gradient}`}></div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-5 sm:py-8">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Quick Stats */}
              <div className="lg:col-span-2 space-y-8">
                {/* Status Overview */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg">
                      <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Status Overview</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="group p-6 bg-gradient-to-br from-blue-500/20 to-indigo-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg">
                          <Home className="h-6 w-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-blue-200">Housing</p>
                          <p className="text-sm text-white font-semibold">{clientData.housing?.status || 'Unknown'}</p>
                        </div>
                      </div>
                    </div>
                    <div className="group p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl border border-green-500/30 hover:border-green-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                          <Briefcase className="h-6 w-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-green-200">Employment</p>
                          <p className="text-sm text-white font-semibold">{clientData.employment?.status || client.employment_status || 'Unknown'}</p>
                        </div>
                      </div>
                    </div>
                    <div className="group p-6 bg-gradient-to-br from-purple-500/20 to-violet-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30 hover:border-purple-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gradient-to-r from-purple-500 to-violet-500 rounded-lg">
                          <DollarSign className="h-6 w-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-purple-200">Benefits</p>
                          <p className="text-sm text-white font-semibold">{clientData.benefits?.status || client.benefits_status || 'Unknown'}</p>
                        </div>
                      </div>
                    </div>
                    <div className="group p-6 bg-gradient-to-br from-orange-500/20 to-amber-500/20 backdrop-blur-sm rounded-xl border border-orange-500/30 hover:border-orange-400/50 transition-all duration-300 hover:scale-105">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                          <Scale className="h-6 w-6 text-white" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-orange-200">Legal</p>
                          <p className="text-sm text-white font-semibold">{clientData.legal?.status || client.legal_status || 'No active cases'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Unified Activity Feed */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                      <MessageSquare className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Unified Activity Feed</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                      <h4 className="font-medium text-white mb-4 flex items-center">
                        <div className="p-1 bg-cyan-500/20 rounded mr-2">
                          <RefreshCw className="h-4 w-4 text-cyan-400" />
                        </div>
                        Latest cross-module activity
                      </h4>
                      <div className="space-y-3">
                        {recentTimeline.length > 0 ? recentTimeline.slice(0, 4).map((entry) => {
                          const styles = getActivityStyles(entry.type)
                          return (
                          <div key={entry.id} className={`p-4 bg-gradient-to-br ${styles.card} backdrop-blur-sm rounded-xl border`}>
                            <div className="flex items-center justify-between mb-2">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${styles.badge}`}>
                                {entry.type}
                              </span>
                              <span className="text-xs text-gray-400">{formatDateTime(entry.date)}</span>
                            </div>
                            <p className="text-sm text-white font-medium">{entry.title}</p>
                            {entry.detail && <p className="text-sm text-gray-300 mt-1 line-clamp-2">{entry.detail}</p>}
                          </div>
                        )}) : <p className="text-gray-400 text-sm">No recent activity yet</p>}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium text-white mb-4 flex items-center">
                        <div className="p-1 bg-violet-500/20 rounded mr-2">
                          <Target className="h-4 w-4 text-violet-400" />
                        </div>
                        Upcoming milestones and follow-up
                      </h4>
                      <div className="space-y-3">
                        {pendingMilestones.length > 0 ? pendingMilestones.map((milestone, index) => (
                          <div key={milestone.milestone_id || index} className="p-4 bg-gradient-to-br from-violet-500/20 to-purple-500/20 backdrop-blur-sm rounded-xl border border-violet-500/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(milestone.status)}`}>
                                {milestone.status || 'Pending'}
                              </span>
                              <span className="text-xs text-gray-400">{formatDate(milestone.due_date)}</span>
                            </div>
                            <p className="text-sm text-white font-medium">{milestone.milestone_name}</p>
                            <p className="text-sm text-violet-200 mt-1">{milestone.milestone_type || 'Program milestone'}</p>
                          </div>
                        )) : <p className="text-gray-400 text-sm">No upcoming milestones</p>}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Goals & Barriers */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                        <Target className="h-6 w-6 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-white">Goals</h3>
                    </div>
                    <div className="space-y-4">
                      {dashboardGoals.length > 0 ? dashboardGoals.map((goal, index) => (
                        <div key={index} className="flex items-center justify-between p-4 bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl border border-green-500/30">
                          <div>
                            <p className="font-medium text-white">{getPlanItemText(goal, ['description', 'summary', 'title']) || 'Untitled goal'}</p>
                            <p className="text-sm text-green-200 capitalize">{goal.goal_type || goal.target_date || goal.status || 'Treatment plan goal'}</p>
                          </div>
                          {goal.status && (
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(goal.status)}`}>
                              {goal.status}
                            </span>
                          )}
                        </div>
                      )) : <p className="text-gray-400">No goals set</p>}
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                        <Shield className="h-6 w-6 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-white">Barriers</h3>
                    </div>
                    <div className="space-y-4">
                      {dashboardBarriers.length > 0 ? dashboardBarriers.map((barrier, index) => (
                        <div key={index} className="flex items-center justify-between p-4 bg-gradient-to-br from-red-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-red-500/30">
                          <div>
                            <p className="font-medium text-white">{getPlanItemText(barrier, ['description', 'summary', 'title']) || 'Untitled barrier'}</p>
                            <p className="text-sm text-red-200 capitalize">{barrier.barrier_type || barrier.domain || barrier.source || 'Treatment plan problem'}</p>
                          </div>
                          {(barrier.severity || barrier.priority) && (
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(barrier.severity || barrier.priority)}`}>
                              {barrier.severity || barrier.priority}
                            </span>
                          )}
                        </div>
                      )) : <p className="text-gray-400">No barriers identified</p>}
                    </div>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg">
                        <ClipboardList className="h-6 w-6 text-white" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-white">Treatment Plan Snapshot</h3>
                        <p className="text-sm text-cyan-200">Daily overview sourced from the client&apos;s current treatment plan.</p>
                      </div>
                    </div>
                    <Link
                      to={`/treatment-plan?client=${encodeURIComponent(clientId)}`}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/15 border border-white/15 rounded-lg text-sm font-medium text-white transition-colors"
                    >
                      Open Treatment Plan
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </div>

                  {!hasTreatmentPlan ? (
                    <div className="rounded-2xl border border-dashed border-white/15 bg-white/5 px-6 py-8 text-center">
                      <p className="text-white font-medium">No treatment plan yet. Generate or create one in Treatment Plan.</p>
                    </div>
                  ) : (
                    <div className="space-y-8">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm text-gray-300">Current plan status</span>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(treatmentPlan.status)}`}>
                          {treatmentPlan.status || 'draft'}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                        <div className="space-y-6">
                          <div>
                            <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-200 mb-3">Objectives</h4>
                            {planObjectives.length > 0 ? (
                              <div className="space-y-3">
                                {planObjectives.map((objective, index) => (
                                  <div key={index} className="p-4 rounded-xl border border-white/10 bg-white/5">
                                    <p className="text-sm text-white">{getPlanItemText(objective, ['description', 'summary', 'title'])}</p>
                                    {objective.measure && <p className="text-xs text-gray-400 mt-2">Measure: {objective.measure}</p>}
                                  </div>
                                ))}
                              </div>
                            ) : <p className="text-sm text-gray-400">No objectives in the current plan.</p>}
                          </div>

                          <div>
                            <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-200 mb-3">Interventions</h4>
                            {planInterventions.length > 0 ? (
                              <div className="space-y-3">
                                {planInterventions.map((intervention, index) => (
                                  <div key={index} className="p-4 rounded-xl border border-white/10 bg-white/5">
                                    <p className="text-sm text-white">{getPlanItemText(intervention, ['description', 'summary', 'title'])}</p>
                                    {(intervention.frequency || intervention.assigned_module) && (
                                      <p className="text-xs text-gray-400 mt-2">
                                        {[intervention.frequency, intervention.assigned_module && formatPlanLabel(intervention.assigned_module)].filter(Boolean).join(' · ')}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : <p className="text-sm text-gray-400">No interventions in the current plan.</p>}
                          </div>
                        </div>

                        <div className="space-y-6">
                          <div>
                            <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-200 mb-3">Aftercare Plan</h4>
                            {planAftercareEntries.length > 0 ? (
                              <div className="space-y-3">
                                {planAftercareEntries.map((entry, index) => (
                                  <div key={index} className="p-4 rounded-xl border border-white/10 bg-white/5">
                                    {typeof entry === 'string' ? (
                                      <p className="text-sm text-white">{entry}</p>
                                    ) : (
                                      <>
                                        <p className="text-sm font-medium text-white">{entry.label}</p>
                                        <p className="text-sm text-gray-300 mt-1">{entry.value}</p>
                                      </>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : <p className="text-sm text-gray-400">No aftercare plan documented yet.</p>}
                          </div>

                          <div>
                            <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-200 mb-3">Operational Needs</h4>
                            {planOperationalNeeds.length > 0 ? (
                              <div className="flex flex-wrap gap-3">
                                {planOperationalNeeds.map((need, index) => (
                                  <div key={index} className="px-4 py-3 rounded-xl border border-white/10 bg-white/5 min-w-[12rem]">
                                    <p className="text-sm font-medium text-white">{formatPlanLabel(need.need_key || need.domain || 'Need')}</p>
                                    <p className="text-xs text-gray-400 mt-1">
                                      {[need.priority && formatPlanLabel(need.priority), need.reason].filter(Boolean).join(' · ')}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            ) : <p className="text-sm text-gray-400">No operational needs attached to the current plan.</p>}
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-semibold uppercase tracking-wide text-cyan-200 mb-3">Plan Tasks</h4>
                        {planTasks.length > 0 ? (
                          <div className="space-y-3">
                            {planTasks.map((task, index) => (
                              <div key={`${task.source}-${index}`} className="p-4 rounded-xl border border-white/10 bg-gradient-to-br from-cyan-500/10 to-blue-500/10">
                                <div className="flex items-start justify-between gap-4">
                                  <div>
                                    <p className="text-sm font-medium text-white">{task.text}</p>
                                    {task.meta && <p className="text-xs text-gray-400 mt-1">{task.meta}</p>}
                                  </div>
                                  <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-white/10 text-cyan-100 border border-white/10">
                                    {task.source}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : <p className="text-sm text-gray-400">No treatment-plan-driven tasks available yet.</p>}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Sidebar */}
              <div className="space-y-8">
                {/* Urgent Tasks */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                      <Clock className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-white">Urgent Tasks</h3>
                  </div>
                  <div className="space-y-3">
                    {clientData.tasks?.filter(task => task.priority === 'urgent' || task.priority === 'high').map((task, index) => (
                      <div key={index} className="p-4 bg-gradient-to-br from-red-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-red-500/30">
                        <p className="font-medium text-white">{task.title}</p>
                        <p className="text-sm text-red-200">Due: {formatDate(task.due_date)}</p>
                        <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </span>
                      </div>
                    )) || <p className="text-gray-400">No urgent tasks</p>}
                  </div>
                </div>

                {/* Upcoming Appointments */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                        <Calendar className="h-5 w-5 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-white">Upcoming Appointments</h3>
                    </div>
                    <button
                      onClick={openAddApt}
                      className="group flex items-center gap-1 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs rounded-lg font-medium transition-all hover:scale-105"
                    >
                      <Plus className="h-3 w-3" /> Add
                    </button>
                  </div>
                  <div className="space-y-3">
                    {appointments.length > 0 ? appointments.slice(0, 3).map((apt) => (
                      <div key={apt.apt_id} className="p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-white">{apt.title}</p>
                            {apt.doctor_name && <p className="text-sm text-blue-200">With: {apt.doctor_name}</p>}
                            {apt.location && <p className="text-sm text-blue-200">At: {apt.location}</p>}
                            <p className="text-sm text-blue-300">{formatDate(apt.appointment_date)}{apt.appointment_time ? ` at ${apt.appointment_time}` : ''}</p>
                            {apt.items_to_bring && <p className="text-xs text-cyan-300 mt-1">Bring: {apt.items_to_bring}</p>}
                          </div>
                          <div className="flex gap-1 shrink-0">
                            <button onClick={() => openEditApt(apt)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors">
                              <Edit className="h-3.5 w-3.5" />
                            </button>
                            <button onClick={() => deleteApt(apt.apt_id)} className="p-1.5 hover:bg-red-500/20 rounded text-gray-400 hover:text-red-300 transition-colors">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-6">
                        <p className="text-gray-400 text-sm mb-3">No upcoming appointments</p>
                        <button onClick={openAddApt} className="text-blue-400 hover:text-blue-300 text-sm underline">
                          Schedule one now
                        </button>
                      </div>
                    )}
                    {appointments.length > 3 && (
                      <button onClick={() => setActiveTab('appointments')} className="w-full text-center text-blue-400 hover:text-blue-300 text-sm py-2 transition-colors">
                        View all {appointments.length} appointments →
                      </button>
                    )}
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <h3 className="text-xl font-bold text-white mb-6">Quick Actions</h3>
                  <div className="space-y-3">
                    {/* Add Note */}
                    <button
                      onClick={handleAddNote}
                      className="group w-full flex items-center justify-between p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-blue-500/30 rounded mr-3">
                          <FileText className="h-4 w-4 text-blue-400" />
                        </div>
                        <span className="text-white group-hover:text-blue-200 transition-colors font-medium">Add Note</span>
                      </span>
                      <Plus className="h-4 w-4 text-blue-400" />
                    </button>
                    {/* Add Task */}
                    <button
                      onClick={handleAddTask}
                      className="group w-full flex items-center justify-between p-4 bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-sm rounded-xl border border-emerald-500/30 hover:border-emerald-400/50 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-emerald-500/30 rounded mr-3">
                          <CheckCircle className="h-4 w-4 text-emerald-400" />
                        </div>
                        <span className="text-white group-hover:text-emerald-200 transition-colors font-medium">Add Task</span>
                      </span>
                      <Plus className="h-4 w-4 text-emerald-400" />
                    </button>
                    <Link
                      to={`/housing?client=${clientId}`}
                      className="group flex items-center justify-between p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20 hover:border-white/30 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-orange-500/20 rounded mr-3">
                          <Home className="h-4 w-4 text-orange-400" />
                        </div>
                        <span className="text-white group-hover:text-orange-200 transition-colors">Housing Search</span>
                      </span>
                      <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                    </Link>
                    <Link
                      to={`/jobs?client=${clientId}`}
                      className="group flex items-center justify-between p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20 hover:border-white/30 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-green-500/20 rounded mr-3">
                          <Briefcase className="h-4 w-4 text-green-400" />
                        </div>
                        <span className="text-white group-hover:text-green-200 transition-colors">Job Search</span>
                      </span>
                      <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                    </Link>
                    <Link
                      to={`/benefits?client=${clientId}`}
                      className="group flex items-center justify-between p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20 hover:border-white/30 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-purple-500/20 rounded mr-3">
                          <DollarSign className="h-4 w-4 text-purple-400" />
                        </div>
                        <span className="text-white group-hover:text-purple-200 transition-colors">Benefits</span>
                      </span>
                      <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                    </Link>
                    <Link
                      to={`/legal?client=${clientId}`}
                      className="group flex items-center justify-between p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20 hover:border-white/30 transition-all duration-300 hover:scale-105"
                    >
                      <span className="flex items-center">
                        <div className="p-1 bg-amber-500/20 rounded mr-3">
                          <Scale className="h-4 w-4 text-amber-400" />
                        </div>
                        <span className="text-white group-hover:text-amber-200 transition-colors">Legal Services</span>
                      </span>
                      <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-white transition-colors" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              <div className="xl:col-span-2 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                    <MessageSquare className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-white">Client Timeline</h3>
                    <p className="text-sm text-cyan-200">Notes, tasks, reminders, contacts, and milestones in one feed.</p>
                  </div>
                </div>
                <div className="space-y-4">
                  {activityTimeline.length > 0 ? activityTimeline.map((entry) => {
                    const styles = getActivityStyles(entry.type)
                    return (
                      <div key={entry.id} className={`p-5 bg-gradient-to-br ${styles.card} backdrop-blur-sm rounded-xl border`}>
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div>
                            <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium mb-3 ${styles.badge}`}>
                              {entry.type}
                            </span>
                            <p className="text-white font-semibold">{entry.title}</p>
                            {entry.detail && <p className="text-sm text-gray-300 mt-1">{entry.detail}</p>}
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-xs text-gray-400">{formatDateTime(entry.date)}</p>
                            {entry.priority && (
                              <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(entry.priority)}`}>
                                {entry.priority}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  }) : (
                    <p className="text-gray-400">No activity has been recorded for this client yet.</p>
                  )}
                </div>
              </div>

              <div className="space-y-8">
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-violet-500 to-purple-500 rounded-lg">
                      <Target className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-white">Program Milestones</h3>
                  </div>
                  <div className="space-y-3">
                    {(clientData.program_milestones || []).length > 0 ? (clientData.program_milestones || []).slice(0, 6).map((milestone, index) => (
                      <div key={milestone.milestone_id || index} className="p-4 bg-gradient-to-br from-violet-500/20 to-purple-500/20 backdrop-blur-sm rounded-xl border border-violet-500/30">
                        <p className="font-medium text-white">{milestone.milestone_name}</p>
                        <p className="text-sm text-violet-200">{milestone.milestone_type || 'Program milestone'}</p>
                        <div className="flex items-center justify-between mt-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(milestone.status)}`}>
                            {milestone.status || 'Pending'}
                          </span>
                          <span className="text-xs text-gray-300">{formatDate(milestone.due_date)}</span>
                        </div>
                      </div>
                    )) : <p className="text-gray-400">No milestones recorded.</p>}
                  </div>
                </div>

                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-fuchsia-500 to-pink-500 rounded-lg">
                      <Phone className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-white">Contact History</h3>
                  </div>
                  <div className="space-y-3">
                    {(clientData.contact_history || []).length > 0 ? (clientData.contact_history || []).slice(0, 6).map((contact, index) => (
                      <div key={contact.contact_id || index} className="p-4 bg-gradient-to-br from-fuchsia-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-fuchsia-500/30">
                        <p className="font-medium text-white">{contact.contact_type || 'Client contact'}</p>
                        <p className="text-sm text-fuchsia-200">{contact.contact_method || 'Contact method not recorded'}</p>
                        {contact.outcome && <p className="text-sm text-gray-300 mt-2 line-clamp-2">{contact.outcome}</p>}
                        <p className="text-xs text-gray-300 mt-3">{formatDateTime(contact.contact_date || contact.created_at)}</p>
                      </div>
                    )) : <p className="text-gray-400">No contact history recorded.</p>}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Other tab content would go here - same pattern for all tabs */}
          {activeTab === 'housing' && (
            <div className="space-y-8">
              {/* Housing Status */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                      <Home className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Housing Information</h3>
                  </div>
                  <Link
                    to={`/housing?client=${clientId}`}
                    className="group px-6 py-3 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                    <span>Search Housing</span>
                  </Link>
                </div>
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-br from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-xl border border-orange-500/30">
                    <h4 className="font-medium text-white mb-3">Current Status</h4>
                    <p className="text-xl font-medium text-orange-200">{clientData.housing?.status || 'Unknown'}</p>
                  </div>
                  <div>
                    <h4 className="font-medium text-white mb-4">Saved Housing Leads & Applications</h4>
                    {housingLeadsLoading ? (
                      <p className="text-sm text-gray-400">Loading saved housing leads...</p>
                    ) : housingLeads.length > 0 ? (
                      <div className="space-y-3">
                        {housingLeads.map((app) => {
                          const noteParts = String(app.notes || '').split(' | ').filter(Boolean)
                          const leadUrl = noteParts.find((p) => /^https?:\/\//i.test(p))
                          const otherNotes = noteParts.filter((p) => p !== leadUrl)
                          return (
                            <div key={app.application_id} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                              <div className="flex justify-between items-start">
                                <div>
                                  <p className="font-medium text-white">{app.facility_name || 'Housing Lead'}</p>
                                  <p className="text-sm text-gray-300">Saved: {formatDate(app.application_date)}</p>
                                  {otherNotes.length > 0 && (
                                    <p className="text-sm text-gray-400 mt-1">{otherNotes.join(' · ')}</p>
                                  )}
                                  {leadUrl && (
                                    <a
                                      href={leadUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-sm text-orange-300 hover:text-orange-200 underline mt-1 inline-block"
                                    >
                                      View listing
                                    </a>
                                  )}
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                                  {app.status}
                                </span>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-400">
                        No saved housing leads yet. Use "Search Housing" and save a listing for this client.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Housing Recommendations from Search System */}
              {searchRecommendations?.housing && searchRecommendations.housing.length > 0 && (
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                        <TrendingUp className="h-6 w-6 text-white" />
                      </div>
                      <h3 className="text-2xl font-bold text-white">Recommended Housing</h3>
                      <span className="px-3 py-1 bg-gradient-to-r from-orange-500/20 to-red-500/20 text-orange-300 text-sm rounded-full border border-orange-500/30">
                        AI Powered
                      </span>
                    </div>
                    <Link
                      to={`/housing?client=${clientId}`}
                      className="text-orange-400 hover:text-orange-300 text-sm transition-colors"
                    >
                      View All Housing →
                    </Link>
                  </div>
                  <div className="space-y-4">
                    {searchRecommendations.housing.slice(0, 3).map((housing, index) => (
                      <div key={index} className="p-6 bg-gradient-to-r from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-xl border border-orange-500/30">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h4 className="font-medium text-white">{housing.title}</h4>
                            <p className="text-orange-200">{housing.location}</p>
                            {housing.rent && (
                              <p className="text-sm text-green-400 font-medium">${housing.rent}/month</p>
                            )}
                            {housing.bedrooms && (
                              <p className="text-sm text-gray-300">{housing.bedrooms} bedrooms</p>
                            )}
                          </div>
                          <div className="flex space-x-3">
                            <button className="px-4 py-2 bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-500 hover:to-red-500 text-white rounded-lg text-sm font-medium transition-all duration-300 transform hover:scale-105">
                              Apply
                            </button>
                            <button className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-lg text-sm font-medium hover:bg-white/20 hover:text-white transition-all duration-300">
                              Save
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* EMPLOYMENT TAB */}
          {activeTab === 'employment' && (
            <div className="space-y-8">
              {/* Employment Status */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                      <Briefcase className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Employment Information</h3>
                  </div>
                  <Link
                    to={`/jobs?client=${clientId}`}
                    className="group px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-green-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                    <span>Search Jobs</span>
                  </Link>
                </div>
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl border border-green-500/30">
                    <h4 className="font-medium text-white mb-3">Current Status</h4>
                    <p className="text-xl font-medium text-green-200">{clientData.employment?.status || 'Unknown'}</p>
                  </div>
                  
                  {/* Job Applications */}
                  {clientData.employment?.applications && (
                    <div>
                      <h4 className="font-medium text-white mb-4">Recent Job Applications</h4>
                      <div className="space-y-3">
                        {clientData.employment.applications.map((app, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-white">{app.job_title}</p>
                                <p className="text-sm text-green-300">{app.company}</p>
                                <p className="text-sm text-gray-300">Applied: {formatDate(app.applied_date)}</p>
                              </div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                                {app.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resumes */}
                  {clientData.employment?.resumes && (
                    <div>
                      <h4 className="font-medium text-white mb-4">Resumes</h4>
                      <div className="space-y-3">
                        {clientData.employment.resumes.map((resume, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                            <div className="flex justify-between items-center">
                              <div>
                                <p className="font-medium text-white">{resume.resume_name}</p>
                                <p className="text-sm text-blue-300">Created: {formatDate(resume.created_at)}</p>
                              </div>
                              <div className="flex space-x-2">
                                <Link
                                  to={resume.download_url}
                                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-lg text-sm font-medium transition-all duration-300 transform hover:scale-105"
                                >
                                  Download
                                </Link>
                                <Link
                                  to="/resume"
                                  className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-lg text-sm font-medium hover:bg-white/20 hover:text-white transition-all duration-300"
                                >
                                  Edit
                                </Link>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* BENEFITS TAB */}
          {activeTab === 'benefits' && (
            <div className="space-y-8">
              {/* Benefits Status */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-purple-500 to-violet-500 rounded-lg">
                      <DollarSign className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Benefits Information</h3>
                  </div>
                  <Link
                    to={`/benefits?client=${clientId}`}
                    className="group px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-purple-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                    <span>Apply for Benefits</span>
                  </Link>
                </div>
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-br from-purple-500/20 to-violet-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30">
                    <h4 className="font-medium text-white mb-3">Current Status</h4>
                    <p className="text-xl font-medium text-purple-200">{clientData.benefits?.status || 'No benefits'}</p>
                  </div>
                  
                  {/* Benefits Applications */}
                  {clientData.benefits?.applications && (
                    <div>
                      <h4 className="font-medium text-white mb-4">Benefit Applications</h4>
                      <div className="space-y-3">
                        {clientData.benefits.applications.map((app, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-white">{app.benefit_type}</p>
                                {app.approval_amount && (
                                  <p className="text-sm text-green-400 font-medium">${app.approval_amount}/month</p>
                                )}
                                {app.submitted_date && (
                                  <p className="text-sm text-gray-300">Submitted: {formatDate(app.submitted_date)}</p>
                                )}
                              </div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                                {app.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* LEGAL TAB */}
          {activeTab === 'legal' && (
            <div className="space-y-8">
              {/* Legal Status */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg">
                      <Scale className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Legal Information</h3>
                  </div>
                  <Link
                    to={`/legal?client=${clientId}`}
                    className="group px-6 py-3 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-amber-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                    <span>Legal Services</span>
                  </Link>
                </div>
                <div className="space-y-6">
                  <div className="p-6 bg-gradient-to-br from-amber-500/20 to-orange-500/20 backdrop-blur-sm rounded-xl border border-amber-500/30">
                    <h4 className="font-medium text-white mb-3">Current Status</h4>
                    <p className="text-xl font-medium text-amber-200">{clientData.legal?.status || 'No active cases'}</p>
                  </div>
                  
                  {/* Legal Cases */}
                  {clientData.legal?.cases && (
                    <div>
                      <h4 className="font-medium text-white mb-4">Legal Cases</h4>
                      <div className="space-y-3">
                        {clientData.legal.cases.map((legalCase, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-white capitalize">{legalCase.case_type}</p>
                                <p className="text-sm text-amber-300">{legalCase.court_name}</p>
                                {legalCase.next_date && (
                                  <p className="text-sm text-gray-300">Next Date: {formatDate(legalCase.next_date)}</p>
                                )}
                              </div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(legalCase.status)}`}>
                                {legalCase.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* SERVICES TAB */}
          {activeTab === 'services' && (
            <div className="space-y-8">
              {/* Services Overview */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                      <Building2 className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Services & Referrals</h3>
                  </div>
                  <Link
                    to={`/services?client=${clientId}`}
                    className="group px-6 py-3 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-teal-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                    <span>Find Services</span>
                  </Link>
                </div>
                <div className="space-y-6">
                  {/* Service Referrals */}
                  {clientData.services?.referrals && clientData.services.referrals.length > 0 ? (
                    <div>
                      <h4 className="font-medium text-white mb-4">Active Referrals</h4>
                      <div className="space-y-3">
                        {clientData.services.referrals.map((referral, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-white">{getReferralDisplayType(referral)}</p>
                                <p className="text-sm text-teal-300">{referral.provider_name}</p>
                                <p className="text-sm text-gray-300">Referred: {formatDate(referral.referral_date)}</p>
                                {referral.notes ? (
                                  <p className="mt-2 text-sm text-gray-300">{referral.notes}</p>
                                ) : null}
                              </div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(getReferralDisplayStatus(referral))}`}>
                                {getReferralDisplayStatus(referral)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-teal-500/30">
                      <div className="p-4 bg-gradient-to-r from-teal-500/20 to-cyan-500/20 rounded-2xl w-fit mx-auto mb-4">
                        <Building2 className="h-8 w-8 text-teal-400" />
                      </div>
                      <h4 className="text-lg font-medium text-white mb-2">No Active Referrals</h4>
                      <p className="text-teal-200 mb-4">This client has no active service referrals.</p>
                      <Link
                        to={`/services?client=${clientId}`}
                        className="px-6 py-3 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105"
                      >
                        Browse Services Directory
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TASKS TAB */}
          {activeTab === 'tasks' && (
            <div className="space-y-8">
              {/* Tasks Header */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                      <CheckCircle className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-white">Task Management</h3>
                      <p className="text-sm text-emerald-100/80">
                        This view combines client tasks, Smart Daily tasks, and reminders for the selected client.
                      </p>
                    </div>
                    {tasksSyncing && (
                      <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 rounded-full">
                        <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />
                        <span className="text-blue-300 text-sm">Syncing...</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedTaskFilter}
                      onChange={(e) => setSelectedTaskFilter(e.target.value)}
                      className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    >
                      <option value="All" className="bg-gray-800">All Tasks</option>
                      <option value="pending" className="bg-gray-800">Pending</option>
                      <option value="in_progress" className="bg-gray-800">In Progress</option>
                      <option value="completed" className="bg-gray-800">Completed</option>
                      <option value="urgent" className="bg-gray-800">Urgent</option>
                      <option value="high" className="bg-gray-800">High Priority</option>
                    </select>
                    <button
                      onClick={handleAddTask}
                      className="group px-6 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-emerald-500/25 flex items-center space-x-2"
                    >
                      <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                      <span>Add Task</span>
                    </button>
                  </div>
                </div>

                {/* Task Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  {[
                    { key: 'total', label: 'Total', value: taskStats.total },
                    { key: 'pending', label: 'Pending', value: taskStats.pending },
                    { key: 'inProgress', label: 'In Progress', value: taskStats.inProgress },
                    { key: 'completed', label: 'Completed', value: taskStats.completed }
                  ].map(({ key, label, value }) => (
                    <div key={key} className="p-4 bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-sm rounded-xl border border-emerald-500/30">
                      <p className="text-sm text-emerald-300">{label}</p>
                      <p className="text-2xl font-bold text-white">{value}</p>
                    </div>
                  ))}
                </div>

                {/* Tasks List */}
                <TasksList
                  tasks={filteredTasks}
                  loading={tasksLoading || workItemsLoading}
                  onEdit={handleEditTask}
                  onView={handleViewTask}
                  onComplete={handleCompleteTask}
                  onDelete={handleDeleteTask}
                  className="space-y-4"
                />
              </div>
            </div>
          )}

          {/* NOTES TAB */}
          {activeTab === 'notes' && (
            <div className="space-y-8">
              {/* Notes Header */}
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                      <FileText className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Case Notes</h3>
                    {syncing && (
                      <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 rounded-full">
                        <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />
                        <span className="text-blue-300 text-sm">Syncing...</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedNoteType}
                      onChange={(e) => setSelectedNoteType(e.target.value)}
                      className="px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="All" className="bg-gray-800">All Notes</option>
                      <option value="Contact" className="bg-gray-800">Contact</option>
                      <option value="Progress" className="bg-gray-800">Progress</option>
                      <option value="Assessment" className="bg-gray-800">Assessment</option>
                      <option value="Follow-up" className="bg-gray-800">Follow-up</option>
                      <option value="Court" className="bg-gray-800">Court</option>
                      <option value="Housing" className="bg-gray-800">Housing</option>
                      <option value="General" className="bg-gray-800">General</option>
                    </select>
                    <button
                      onClick={handleAddNote}
                      className="group px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25 flex items-center space-x-2"
                    >
                      <Plus className="h-4 w-4 group-hover:scale-110 transition-transform duration-300" />
                      <span>Add Note</span>
                    </button>
                  </div>
                </div>

                {/* Note Stats */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  {(() => {
                    const stats = getNotesStats();
                    return [
                      { key: 'total', label: 'Total', value: stats.total },
                      { key: 'thisWeek', label: 'This Week', value: stats.thisWeek },
                      { key: 'thisMonth', label: 'This Month', value: stats.thisMonth },
                      { key: 'unsynced', label: 'Unsynced', value: stats.unsynced }
                    ].map(({ key, label, value }) => (
                      <div key={key} className="p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                        <p className="text-sm text-blue-300">{label}</p>
                        <p className="text-2xl font-bold text-white">{value || 0}</p>
                      </div>
                    ));
                  })()}
                </div>

                {/* Quick Note Templates */}
                <div className="mb-6">
                  <h4 className="font-medium text-white mb-4">Quick Templates</h4>
                  <div className="flex flex-wrap gap-2">
                    {[
                      'Client Contact - Phone',
                      'Client Contact - In Person', 
                      'Progress Update',
                      'Barrier Identified',
                      'Goal Achievement',
                      'Service Referral Made',
                      'Court Date Reminder',
                      'Housing Update'
                    ].map((template) => (
                      <button
                        key={template}
                        onClick={() => handleTemplateSelect(template)}
                        className="px-4 py-2 bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-sm border border-white/20 hover:border-white/30 text-gray-300 hover:text-white rounded-lg text-sm transition-all duration-300 hover:scale-105"
                      >
                        {template}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Notes List */}
                <NotesList
                  notes={getFilteredNotes(selectedNoteType)}
                  loading={notesLoading}
                  onEdit={handleEditNote}
                  onDelete={handleDeleteNote}
                  className="space-y-4"
                />
              </div>
            </div>
          )}

          {/* APPOINTMENTS TAB */}
          {activeTab === 'appointments' && (
            <div className="space-y-8">
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                      <Calendar className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Appointments</h3>
                    <span className="px-3 py-1 bg-blue-500/20 rounded-full text-blue-300 text-sm">{appointments.length} total</span>
                  </div>
                  <button
                    onClick={openAddApt}
                    className="group px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25 flex items-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Appointment</span>
                  </button>
                </div>

                {appointments.length === 0 ? (
                  <div className="text-center py-16 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                    <Calendar className="h-12 w-12 text-blue-400 mx-auto mb-4" />
                    <h4 className="text-lg font-medium text-white mb-2">No Appointments Yet</h4>
                    <p className="text-blue-200 mb-4">Schedule appointments and they will sync to the daily reminder system.</p>
                    <button onClick={openAddApt} className="px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl font-medium hover:scale-105 transition-all">
                      Schedule First Appointment
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {appointments.map((apt) => (
                      <div key={apt.apt_id} className="p-5 bg-gradient-to-br from-blue-500/15 to-cyan-500/15 backdrop-blur-sm rounded-xl border border-blue-500/25 hover:border-blue-500/40 transition-all">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h4 className="font-bold text-white text-lg">{apt.title}</h4>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(apt.status)}`}>{apt.status}</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                              <div className="flex items-center gap-2 text-blue-200">
                                <Calendar className="h-4 w-4" />
                                <span>{formatDate(apt.appointment_date)}{apt.appointment_time ? ` at ${apt.appointment_time}` : ''}</span>
                              </div>
                              {apt.doctor_name && (
                                <div className="flex items-center gap-2 text-blue-200">
                                  <User className="h-4 w-4" />
                                  <span>{apt.doctor_name}</span>
                                </div>
                              )}
                              {apt.location && (
                                <div className="flex items-center gap-2 text-blue-200">
                                  <MapPin className="h-4 w-4" />
                                  <span>{apt.location}</span>
                                </div>
                              )}
                              {apt.service_type && (
                                <div className="flex items-center gap-2 text-blue-200">
                                  <Building2 className="h-4 w-4" />
                                  <span>{apt.service_type}</span>
                                </div>
                              )}
                            </div>
                            {apt.items_to_bring && (
                              <div className="mt-2 px-3 py-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
                                <p className="text-xs font-medium text-cyan-300">Bring: {apt.items_to_bring}</p>
                              </div>
                            )}
                            {apt.notes && <p className="mt-2 text-sm text-gray-300">{apt.notes}</p>}
                          </div>
                          <div className="flex gap-2 ml-4 shrink-0">
                            <button onClick={() => openEditApt(apt)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
                              <Edit className="h-4 w-4" />
                            </button>
                            <button onClick={() => deleteApt(apt.apt_id)} className="p-2 hover:bg-red-500/20 rounded-lg text-gray-400 hover:text-red-300 transition-colors">
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* DOCUMENTS TAB — general client document vault. The full ROI manager
              lives on its own "ROI / Releases" tab; only a compact link sits here. */}
          {activeTab === 'docs' && (
            <div className="space-y-8">
              {/* Compact ROI / Releases summary + link (full manager is its own tab) */}
              <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 backdrop-blur-xl p-5 rounded-2xl border border-emerald-500/25 shadow-xl shadow-emerald-500/10">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg shrink-0">
                      <ShieldCheck className="h-6 w-6 text-white" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-lg font-bold text-white">ROI / Releases</h3>
                      <p className="text-xs text-gray-400">
                        Client ROI records are managed on their own page, separate from the
                        Admissions packet and the general document vault.
                      </p>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs">
                        <span className="text-emerald-300">
                          Client ROI records: {roiSummary.total}
                        </span>
                        <span className="text-emerald-200">
                          {roiSummary.active} active
                        </span>
                        <span className="text-amber-300">
                          {roiSummary.awaitingSignature} awaiting signature
                        </span>
                        <span className="text-red-300">
                          {roiSummary.revoked} revoked
                        </span>
                        <span className="text-sky-300">
                          Packet ROI pending signature: {packetRoiPendingSignatureCount}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setActiveTab('roi')}
                    className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-medium transition-all duration-300 hover:scale-105 text-sm"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Open ROI / Releases
                  </button>
                </div>
              </div>

              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 overflow-hidden">

                {/* Vault header */}
                <div className="flex items-center justify-between p-6 pb-4 border-b border-white/10">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-r from-violet-500 to-purple-500 rounded-lg">
                      <FolderOpen className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-white">Client Documents</h3>
                      <p className="text-xs text-gray-400">
                        {documents.length} {documents.length === 1 ? 'file' : 'files'} in vault
                        {docVaultFilter !== 'all' && ` · ${filteredDocs.length} shown`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowDocUpload(true)}
                    className="group px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-violet-500/25 flex items-center space-x-2"
                  >
                    <Upload className="h-4 w-4" />
                    <span>Upload Document</span>
                  </button>
                </div>

                {/* Category filter chips — only rendered when vault has documents */}
                {documents.length > 0 && (
                  <div className="px-6 py-3 border-b border-white/10 overflow-x-auto">
                    <div className="flex gap-2 min-w-max">
                      <button
                        onClick={() => setDocVaultFilter('all')}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                          docVaultFilter === 'all'
                            ? 'bg-violet-600 text-white'
                            : 'bg-white/10 text-gray-300 hover:bg-white/20 hover:text-white'
                        }`}
                      >
                        All ({documents.length})
                      </button>
                      {VAULT_CATEGORIES.filter((c) => c.key !== 'all').map((cat) => {
                        const count = documents.filter((d) => deriveDocumentCategory(d) === cat.key).length
                        if (count === 0) return null
                        return (
                          <button
                            key={cat.key}
                            onClick={() => setDocVaultFilter(cat.key)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                              docVaultFilter === cat.key
                                ? 'bg-violet-600 text-white'
                                : 'bg-white/10 text-gray-300 hover:bg-white/20 hover:text-white'
                            }`}
                          >
                            {cat.label} ({count})
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}

                <div className="p-6">
                  {showDocUpload && (
                    <div className="mb-6 p-5 bg-violet-500/10 border border-violet-500/30 rounded-xl">
                      <h4 className="font-medium text-white mb-4">Upload New Document</h4>
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">Title *</label>
                          <input
                            type="text"
                            placeholder="e.g. State ID, Insurance Card"
                            value={docForm.title}
                            onChange={e => setDocForm(f => ({ ...f, title: e.target.value }))}
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">Document Type</label>
                          <select
                            value={docForm.doc_type}
                            onChange={e => setDocForm(f => ({ ...f, doc_type: e.target.value }))}
                            className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                          >
                            <option value="id">Government ID</option>
                            <option value="insurance">Insurance Card</option>
                            <option value="medical">Medical Record</option>
                            <option value="legal">Legal Document</option>
                            <option value="housing">Housing Document</option>
                            <option value="employment">Employment Document</option>
                            <option value="benefits">Benefits Document</option>
                            <option value="admissions">Admissions / Intake</option>
                            <option value="discharge">Discharge / Transition</option>
                            <option value="generated">Generated Letter or Form</option>
                            <option value="other">Other</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">Upload File</label>
                          <input
                            type="file"
                            onChange={e => setDocFile(e.target.files[0])}
                            className="w-full text-sm text-gray-300 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-violet-600 file:text-white hover:file:bg-violet-500 cursor-pointer"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-1">Or Enter URL</label>
                          <input
                            type="url"
                            placeholder="https://..."
                            value={docForm.url}
                            onChange={e => setDocForm(f => ({ ...f, url: e.target.value }))}
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                          />
                        </div>
                      </div>
                      <div className="flex gap-3 mt-4">
                        <button
                          onClick={() => { setShowDocUpload(false); setDocForm({ title: '', doc_type: 'other', url: '' }); setDocFile(null) }}
                          className="flex-1 px-4 py-2 bg-white/10 border border-white/20 text-gray-300 rounded-xl hover:bg-white/20 transition-all"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={uploadDocument}
                          disabled={docUploading}
                          className="flex-1 px-4 py-2 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white rounded-xl font-medium transition-all disabled:opacity-50"
                        >
                          {docUploading ? 'Uploading...' : 'Upload'}
                        </button>
                      </div>
                    </div>
                  )}

                  {filteredDocs.length === 0 && !showDocUpload ? (
                    documents.length === 0 ? (
                      <div className="text-center py-16 bg-gradient-to-br from-violet-500/20 to-purple-500/20 backdrop-blur-sm rounded-xl border border-violet-500/30">
                        <FolderOpen className="h-12 w-12 text-violet-400 mx-auto mb-4" />
                        <h4 className="text-lg font-medium text-white mb-2">No Documents Yet</h4>
                        <p className="text-violet-200 mb-4">Upload IDs, insurance cards, and other client documents.</p>
                        <button onClick={() => setShowDocUpload(true)} className="px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl font-medium hover:scale-105 transition-all">
                          Upload First Document
                        </button>
                      </div>
                    ) : (
                      <div className="text-center py-12 bg-white/5 rounded-xl border border-white/10">
                        <FolderOpen className="h-10 w-10 text-violet-400/60 mx-auto mb-3" />
                        <p className="text-gray-400 text-sm">No documents in this category.</p>
                        <button
                          onClick={() => setDocVaultFilter('all')}
                          className="mt-3 text-violet-400 hover:text-violet-300 text-xs underline transition-colors"
                        >
                          Show all documents
                        </button>
                      </div>
                    )
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {filteredDocs.map((doc) => {
                        const viewUrl = getDocViewUrl(doc)
                        const docCat = deriveDocumentCategory(doc)
                        const docCatLabel = categoryLabel(docCat)
                        return (
                          <div key={doc.doc_id} className="p-5 bg-gradient-to-br from-violet-500/15 to-purple-500/15 backdrop-blur-sm rounded-xl border border-violet-500/25 hover:border-violet-500/40 transition-all">
                            <div className="flex justify-between items-start">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-bold text-white truncate">{doc.title}</h4>
                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                  <span className="px-2 py-0.5 bg-violet-500/20 text-violet-300 rounded text-xs font-medium">
                                    {docCatLabel}
                                  </span>
                                  {doc.doc_type && doc.doc_type !== 'other' && (
                                    <span className="text-xs text-gray-500 capitalize">
                                      {doc.doc_type.replace(/_/g, ' ')}
                                    </span>
                                  )}
                                </div>
                                {doc.file_name && <p className="text-xs text-gray-400 truncate mt-1">{doc.file_name}</p>}
                                {doc.file_size && <p className="text-xs text-gray-500">{(doc.file_size / 1024).toFixed(1)} KB</p>}
                                <p className="text-xs text-gray-500 mt-1">{formatDate(doc.created_at)}</p>
                              </div>
                              <div className="flex gap-2 ml-3 shrink-0">
                                {viewUrl && (
                                  <button
                                    onClick={() => isProtectedDoc(doc) ? openDocViewer(doc) : window.open(viewUrl, '_blank', 'noopener,noreferrer')}
                                    className="p-2 hover:bg-violet-500/20 rounded-lg text-gray-400 hover:text-violet-300 transition-colors"
                                    title="View"
                                  >
                                    <Eye className="h-4 w-4" />
                                  </button>
                                )}
                                {viewUrl && (
                                  <button
                                    onClick={() => handleOpenDocument(doc)}
                                    className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
                                    title="Open in new tab"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </button>
                                )}
                                {isProtectedDoc(doc) && (
                                  <button
                                    onClick={() => handleDownloadDocument(doc)}
                                    className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"
                                    title="Download"
                                  >
                                    <Download className="h-4 w-4" />
                                  </button>
                                )}
                                <button
                                  onClick={() => deleteDocument(doc.doc_id)}
                                  className="p-2 hover:bg-red-500/20 rounded-lg text-gray-400 hover:text-red-300 transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ROI / RELEASES TAB — dedicated home for ongoing client ROI records */}
          {activeTab === 'roi' && (
            <div className="space-y-8">
              <RoiConsentTracker clientId={clientId} onRoiRecordsChange={setRoiRecords} />
            </div>
          )}
        </div>

        {/* Task Form Modal */}
        <TaskForm
          isOpen={showTaskForm}
          onClose={() => {
            setShowTaskForm(false)
            setEditingTask(null)
          }}
          onSubmit={handleTaskSubmit}
          initialData={editingTask}
          isEditing={!!editingTask}
        />

        {/* Task View Modal */}
        <TaskViewModal
          isOpen={showTaskView}
          onClose={() => {
            setShowTaskView(false)
            setViewingTask(null)
          }}
          task={viewingTask}
          onEdit={handleEditTask}
          onComplete={handleCompleteTask}
        />

        {/* Note Form Modal */}
        <NoteForm
          isOpen={showNoteForm}
          onClose={() => {
            setShowNoteForm(false)
            setEditingNote(null)
          }}
          onSubmit={handleNoteSubmit}
          initialData={editingNote}
          isEditing={!!editingNote}
          clientId={clientId}
          clientName={client ? `${client.first_name} ${client.last_name}` : ''}
        />

        {/* Appointment Modal */}
        {showAptModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowAptModal(false)} />
            <div className="relative z-10 w-full max-w-lg bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border border-white/20 shadow-2xl shadow-blue-500/20 p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                    <Calendar className="h-5 w-5 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-white">{editingApt ? 'Edit Appointment' : 'Add Appointment'}</h2>
                </div>
                <button onClick={() => setShowAptModal(false)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Title *</label>
                  <input type="text" placeholder="e.g. Medical Check-up" value={aptForm.title} onChange={e => setAptForm(f => ({ ...f, title: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Date *</label>
                    <input type="date" value={aptForm.appointment_date} onChange={e => setAptForm(f => ({ ...f, appointment_date: e.target.value }))}
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Time</label>
                    <input type="time" value={aptForm.appointment_time} onChange={e => setAptForm(f => ({ ...f, appointment_time: e.target.value }))}
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Doctor / Provider</label>
                  <input type="text" placeholder="e.g. Dr. Smith" value={aptForm.doctor_name} onChange={e => setAptForm(f => ({ ...f, doctor_name: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Location / Address</label>
                  <input type="text" placeholder="e.g. 123 Main St" value={aptForm.location} onChange={e => setAptForm(f => ({ ...f, location: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Service Type</label>
                  <input type="text" placeholder="e.g. Dental, Medical, Mental Health" value={aptForm.service_type} onChange={e => setAptForm(f => ({ ...f, service_type: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">What to Bring</label>
                  <input type="text" placeholder="e.g. ID, insurance card" value={aptForm.items_to_bring} onChange={e => setAptForm(f => ({ ...f, items_to_bring: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1">Notes</label>
                  <textarea rows={3} value={aptForm.notes} onChange={e => setAptForm(f => ({ ...f, notes: e.target.value }))}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button onClick={() => setShowAptModal(false)} className="flex-1 px-4 py-2.5 bg-white/10 border border-white/20 text-gray-300 rounded-xl hover:bg-white/20 hover:text-white transition-all">Cancel</button>
                <button onClick={saveApt} disabled={aptSaving} className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all disabled:opacity-50">
                  {aptSaving ? 'Saving...' : (editingApt ? 'Save Changes' : 'Create Appointment')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Doc Viewer Modal */}
        {showDocViewer && viewingDoc && (() => {
          // For protected uploaded files the preview source is the authenticated
          // blob object URL; for external-URL documents it is the URL itself.
          const previewSrc = isProtectedDoc(viewingDoc) ? docBlobUrl : (viewingDoc.url || null)
          return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={closeDocViewer} />
            <div className="relative z-10 w-full max-w-4xl max-h-[90vh] bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border border-white/20 shadow-2xl flex flex-col">
              <div className="flex items-center justify-between p-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                  <FolderOpen className="h-5 w-5 text-violet-400" />
                  <span className="font-medium text-white">{viewingDoc.title}</span>
                  {viewingDoc.file_name && <span className="text-xs text-gray-400">{viewingDoc.file_name}</span>}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleOpenDocument(viewingDoc)}
                    className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Open in new tab">
                    <ExternalLink className="h-4 w-4" />
                  </button>
                  {isProtectedDoc(viewingDoc) && (
                    <button onClick={() => handleDownloadDocument(viewingDoc)}
                      className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Download">
                      <Download className="h-4 w-4" />
                    </button>
                  )}
                  <button onClick={closeDocViewer} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-auto p-2 min-h-0">
                {docBlobLoading ? (
                  <div className="text-center py-16">
                    <div className="animate-spin rounded-full h-8 w-8 border-4 border-violet-500/20 border-t-violet-500 mx-auto mb-4"></div>
                    <p className="text-gray-300">Loading document…</p>
                  </div>
                ) : docBlobError ? (
                  <div className="text-center py-16">
                    <AlertCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                    <p className="text-gray-300 mb-4">Could not open document. Please try again.</p>
                    <button onClick={() => openDocViewer(viewingDoc)}
                      className="px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl font-medium hover:scale-105 transition-all inline-block">
                      Retry
                    </button>
                  </div>
                ) : viewingDoc.file_mime?.startsWith('image/') && previewSrc ? (
                  <img src={previewSrc} alt={viewingDoc.title} className="max-w-full mx-auto rounded-lg" />
                ) : viewingDoc.file_mime === 'application/pdf' && previewSrc ? (
                  <iframe src={previewSrc} className="w-full h-[70vh] rounded-lg border-0" title={viewingDoc.title} />
                ) : docBlobText !== null ? (
                  <div className="h-full min-h-0 overflow-auto p-6">
                    {isHtmlDocument(viewingDoc) && (
                      <div className="mb-4 rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                        HTML preview is shown as plain text for safety. Download the file to inspect the original markup.
                      </div>
                    )}
                    <pre className="whitespace-pre-wrap text-sm text-gray-200 leading-relaxed font-mono">
                      {docBlobText}
                    </pre>
                  </div>
                ) : viewingDoc.url ? (
                  <div className="text-center py-16">
                    <FileText className="h-12 w-12 text-violet-400 mx-auto mb-4" />
                    <p className="text-gray-300 mb-4">This file type cannot be previewed inline.</p>
                    <button onClick={() => handleOpenDocument(viewingDoc)}
                      className="px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl font-medium hover:scale-105 transition-all inline-block">
                      Open Document
                    </button>
                  </div>
                ) : (
                  <div className="text-center py-16">
                    <FileText className="h-12 w-12 text-violet-400 mx-auto mb-4" />
                    <p className="text-gray-300 mb-4">Preview not available for this file type.</p>
                    <button onClick={() => handleDownloadDocument(viewingDoc)}
                      className="px-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-xl font-medium hover:scale-105 transition-all inline-block">
                      Download Document
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
          )
        })()}

        {/* Edit Client Modal */}
        {showEditModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowEditModal(false)} />
            <div className="relative z-10 w-full max-w-lg bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/20 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg">
                    <Edit className="h-5 w-5 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-white">Edit Client</h2>
                </div>
                <button onClick={() => setShowEditModal(false)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors">✕</button>
              </div>

              <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">First Name</label>
                    <input value={editForm.first_name} onChange={e => setEditForm(f => ({ ...f, first_name: e.target.value }))} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Last Name</label>
                    <input value={editForm.last_name} onChange={e => setEditForm(f => ({ ...f, last_name: e.target.value }))} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Phone</label>
                    <input value={editForm.phone} onChange={e => setEditForm(f => ({ ...f, phone: e.target.value }))} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Email</label>
                    <input type="email" value={editForm.email} onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Date of Birth</label>
                    <input type="date" value={editForm.date_of_birth} onChange={e => setEditForm(f => ({ ...f, date_of_birth: e.target.value }))} className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1">Program Type</label>
                    <input value={editForm.program_type} onChange={e => setEditForm(f => ({ ...f, program_type: e.target.value }))} placeholder="e.g. Reentry Program" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                  </div>
                </div>

                {/* Address */}
                <div className="border-t border-white/10 pt-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Address</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <input value={editForm.address} onChange={e => setEditForm(f => ({ ...f, address: e.target.value }))} placeholder="Street address" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div>
                      <input value={editForm.city} onChange={e => setEditForm(f => ({ ...f, city: e.target.value }))} placeholder="City" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input value={editForm.state} onChange={e => setEditForm(f => ({ ...f, state: e.target.value }))} placeholder="State" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                      <input value={editForm.zip_code} onChange={e => setEditForm(f => ({ ...f, zip_code: e.target.value }))} placeholder="ZIP" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                  </div>
                </div>

                {/* Status Fields */}
                <div className="border-t border-white/10 pt-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Status</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Risk Level</label>
                      <select value={editForm.risk_level} onChange={e => setEditForm(f => ({ ...f, risk_level: e.target.value }))} className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Case Status</label>
                      <select value={editForm.case_status} onChange={e => setEditForm(f => ({ ...f, case_status: e.target.value }))} className="w-full px-3 py-2 bg-slate-700 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50">
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="pending">Pending</option>
                        <option value="urgent">Urgent</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Housing Status</label>
                      <input value={editForm.housing_status} onChange={e => setEditForm(f => ({ ...f, housing_status: e.target.value }))} placeholder="e.g. homeless, housed" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Employment Status</label>
                      <input value={editForm.employment_status} onChange={e => setEditForm(f => ({ ...f, employment_status: e.target.value }))} placeholder="e.g. unemployed, part-time" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Benefits Status</label>
                      <input value={editForm.benefits_status} onChange={e => setEditForm(f => ({ ...f, benefits_status: e.target.value }))} placeholder="e.g. receiving, pending" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 mb-1">Legal Status</label>
                      <input value={editForm.legal_status} onChange={e => setEditForm(f => ({ ...f, legal_status: e.target.value }))} placeholder="e.g. probation, pending case" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                  </div>
                </div>

                {/* Emergency Contact */}
                <div className="border-t border-white/10 pt-3">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Emergency Contact</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <input value={editForm.emergency_contact_name} onChange={e => setEditForm(f => ({ ...f, emergency_contact_name: e.target.value }))} placeholder="Contact name" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div>
                      <input value={editForm.emergency_contact_phone} onChange={e => setEditForm(f => ({ ...f, emergency_contact_phone: e.target.value }))} placeholder="Contact phone" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                    <div className="col-span-2">
                      <input value={editForm.emergency_contact_relationship} onChange={e => setEditForm(f => ({ ...f, emergency_contact_relationship: e.target.value }))} placeholder="Relationship (e.g. sister, spouse)" className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-4 py-2.5 bg-white/10 border border-white/20 text-gray-300 rounded-xl hover:bg-white/20 hover:text-white transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={editSaving}
                  className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all disabled:opacity-50"
                >
                  {editSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ClientDashboard
