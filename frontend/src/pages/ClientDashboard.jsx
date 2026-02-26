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
  RefreshCw,
  Filter,
  Sparkles,
  Zap
} from 'lucide-react'
import toast from 'react-hot-toast'
import useNotes from '../hooks/useNotes'
import NoteForm from '../components/NoteForm'
import NotesList from '../components/NotesList'
import useTasks from '../hooks/useTasks'
import TaskForm from '../components/TaskForm'
import TasksList from '../components/TasksList'
import TaskViewModal from '../components/TaskViewModal'

const ClientDashboard = () => {
  const { clientId } = useParams()
  const navigate = useNavigate()
  const [clientData, setClientData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')
  const [intelligentTasks, setIntelligentTasks] = useState(null)
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
    tasks, 
    loading: tasksLoading, 
    syncing: tasksSyncing, 
    addTask, 
    updateTask, 
    deleteTask, 
    completeTask, 
    syncAllTasks, 
    getFilteredTasks, 
    getTasksStats,
    getTaskById
  } = useTasks(clientId)
  
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [selectedTaskFilter, setSelectedTaskFilter] = useState('All')
  const [showTaskView, setShowTaskView] = useState(false)
  const [viewingTask, setViewingTask] = useState(null)

  useEffect(() => {
    if (clientId) {
      fetchClientData()
      fetchIntelligentTasks()
      fetchSearchRecommendations()
    }
  }, [clientId])

  const fetchClientData = async () => {
    try {
      setLoading(true)
      setLoadError('')
      const response = await fetch(`/api/clients/${clientId}/unified-view`)
      
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

  const fetchIntelligentTasks = async () => {
    try {
      const response = await fetch(`/api/clients/${clientId}/intelligent-tasks`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setIntelligentTasks(data)
        }
      } else {
        console.log('Intelligent tasks not available, using basic tasks')
      }
    } catch (error) {
      console.log('Intelligent tasks system not available:', error)
    }
  }

  const fetchSearchRecommendations = async () => {
    try {
      const response = await fetch(`/api/clients/${clientId}/search-recommendations`)
      
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
    setEditingTask(task)
    setShowTaskForm(true)
  }

  const handleViewTask = (task) => {
    setViewingTask(task)
    setShowTaskView(true)
  }

  const handleTaskSubmit = async (taskData) => {
    try {
      if (editingTask) {
        await updateTask(editingTask.task_id, taskData)
        toast.success('Task updated successfully!')
      } else {
        await addTask(taskData)
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
      await completeTask(taskId)
      toast.success('Task marked as complete!')
    } catch (error) {
      console.error('Error completing task:', error)
      toast.error('Failed to complete task. Please try again.')
    }
  }

  const handleDeleteTask = async (taskId) => {
    try {
      await deleteTask(taskId)
      toast.success('Task deleted successfully!')
    } catch (error) {
      console.error('Error deleting task:', error)
      toast.error('Failed to delete task. Please try again.')
    }
  }

  // Helper functions for task display (using existing functions above)

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
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
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
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

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User, gradient: 'from-blue-500 to-indigo-500' },
    { id: 'housing', label: 'Housing', icon: Home, gradient: 'from-orange-500 to-red-500' },
    { id: 'employment', label: 'Employment', icon: Briefcase, gradient: 'from-green-500 to-emerald-500' },
    { id: 'benefits', label: 'Benefits', icon: DollarSign, gradient: 'from-purple-500 to-violet-500' },
    { id: 'legal', label: 'Legal', icon: Scale, gradient: 'from-amber-500 to-orange-500' },
    { id: 'services', label: 'Services', icon: Building2, gradient: 'from-teal-500 to-cyan-500' },
    { id: 'tasks', label: 'Tasks', icon: CheckCircle, gradient: 'from-emerald-500 to-green-500' },
    { id: 'notes', label: 'Notes', icon: FileText, gradient: 'from-blue-500 to-cyan-500' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
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
                  <p className="text-gray-400">Client ID: {client.client_id}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className={`px-4 py-2 rounded-xl text-sm font-medium ${getRiskLevelColor(client.risk_level)}`}>
                  {client.risk_level} Risk
                </span>
                <span className={`px-4 py-2 rounded-xl text-sm font-medium ${getStatusColor(client.case_status)}`}>
                  {client.case_status}
                </span>
                <button className="group p-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25">
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
                <span className="text-gray-300">{client.address || 'No address'}</span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="p-1 bg-orange-500/20 rounded">
                  <Calendar className="h-4 w-4 text-orange-400" />
                </div>
                <span className="text-gray-300">Intake: {formatDate(client.intake_date)}</span>
              </div>
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
        <div className="max-w-7xl mx-auto px-6 py-8">
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
                          <p className="text-sm text-white font-semibold">{clientData.employment?.status || 'Unknown'}</p>
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
                          <p className="text-sm text-white font-semibold">{clientData.benefits?.status || 'Unknown'}</p>
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
                          <p className="text-sm text-white font-semibold">{clientData.legal?.status || 'No active cases'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent Activity */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                      <MessageSquare className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white">Recent Activity</h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Recent Notes */}
                    <div>
                      <h4 className="font-medium text-white mb-4 flex items-center">
                        <div className="p-1 bg-green-500/20 rounded mr-2">
                          <FileText className="h-4 w-4 text-green-400" />
                        </div>
                        Recent Notes
                      </h4>
                      <div className="space-y-3">
                        {notes?.slice(0, 3).map((note) => (
                          <div key={note.note_id} className="p-4 bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl border border-green-500/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(note.note_type)}`}>
                                {note.note_type}
                              </span>
                              <span className="text-xs text-gray-400">{formatDate(note.created_at)}</span>
                            </div>
                            <p className="text-sm text-gray-300 line-clamp-2">{note.content}</p>
                          </div>
                        )) || <p className="text-gray-400 text-sm">No recent notes</p>}
                      </div>
                    </div>

                    {/* Recent Tasks */}
                    <div>
                      <h4 className="font-medium text-white mb-4 flex items-center">
                        <div className="p-1 bg-blue-500/20 rounded mr-2">
                          <CheckCircle className="h-4 w-4 text-blue-400" />
                        </div>
                        Recent Tasks
                      </h4>
                      <div className="space-y-3">
                        {tasks?.slice(0, 3).map((task) => (
                          <div key={task.task_id} className="p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                                {task.priority}
                              </span>
                              <span className="text-xs text-gray-400">{formatDate(task.due_date)}</span>
                            </div>
                            <p className="text-sm text-white font-medium">{task.title}</p>
                            <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                              {task.status}
                            </span>
                          </div>
                        )) || <p className="text-gray-400 text-sm">No recent tasks</p>}
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
                      {clientData.goals?.map((goal, index) => (
                        <div key={index} className="flex items-center justify-between p-4 bg-gradient-to-br from-green-500/20 to-emerald-500/20 backdrop-blur-sm rounded-xl border border-green-500/30">
                          <div>
                            <p className="font-medium text-white">{goal.description}</p>
                            <p className="text-sm text-green-200 capitalize">{goal.goal_type}</p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(goal.status)}`}>
                            {goal.status}
                          </span>
                        </div>
                      )) || <p className="text-gray-400">No goals set</p>}
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
                      {clientData.barriers?.map((barrier, index) => (
                        <div key={index} className="flex items-center justify-between p-4 bg-gradient-to-br from-red-500/20 to-pink-500/20 backdrop-blur-sm rounded-xl border border-red-500/30">
                          <div>
                            <p className="font-medium text-white">{barrier.description}</p>
                            <p className="text-sm text-red-200 capitalize">{barrier.barrier_type}</p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(barrier.severity)}`}>
                            {barrier.severity}
                          </span>
                        </div>
                      )) || <p className="text-gray-400">No barriers identified</p>}
                    </div>
                  </div>
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
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                      <Calendar className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-xl font-bold text-white">Upcoming Appointments</h3>
                  </div>
                  <div className="space-y-3">
                    {clientData.appointments?.map((appointment, index) => (
                      <div key={index} className="p-4 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                        <p className="font-medium text-white">{appointment.appointment_type}</p>
                        <p className="text-sm text-blue-200">{appointment.provider_name}</p>
                        <p className="text-sm text-blue-200">{formatDateTime(appointment.appointment_date)}</p>
                      </div>
                    )) || <p className="text-gray-400">No upcoming appointments</p>}
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                  <h3 className="text-xl font-bold text-white mb-6">Quick Actions</h3>
                  <div className="space-y-3">
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
                  {clientData.housing?.applications && (
                    <div>
                      <h4 className="font-medium text-white mb-4">Applications</h4>
                      <div className="space-y-3">
                        {clientData.housing.applications.map((app, index) => (
                          <div key={index} className="p-4 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div className="flex justify-between items-start">
                              <div>
                                <p className="font-medium text-white">{app.property_name}</p>
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
                                <p className="font-medium text-white">{referral.service_type}</p>
                                <p className="text-sm text-teal-300">{referral.provider_name}</p>
                                <p className="text-sm text-gray-300">Referred: {formatDate(referral.referral_date)}</p>
                              </div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(referral.status)}`}>
                                {referral.status}
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
                    <h3 className="text-2xl font-bold text-white">Task Management</h3>
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
                  {(() => {
                    const stats = getTasksStats();
                    return [
                      { key: 'total', label: 'Total', value: stats.total },
                      { key: 'pending', label: 'Pending', value: stats.pending },
                      { key: 'inProgress', label: 'In Progress', value: stats.inProgress },
                      { key: 'completed', label: 'Completed', value: stats.completed }
                    ].map(({ key, label, value }) => (
                      <div key={key} className="p-4 bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-sm rounded-xl border border-emerald-500/30">
                        <p className="text-sm text-emerald-300">{label}</p>
                        <p className="text-2xl font-bold text-white">{value}</p>
                      </div>
                    ));
                  })()}
                </div>

                {/* Tasks List */}
                <TasksList
                  tasks={getFilteredTasks(selectedTaskFilter)}
                  loading={tasksLoading}
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
        />
      </div>
    </div>
  )
}

export default ClientDashboard
