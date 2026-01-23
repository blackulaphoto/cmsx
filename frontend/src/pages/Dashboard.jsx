import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Users, 
  Home, 
  DollarSign, 
  Scale, 
  FileText, 
  MessageSquare,
  Building2,
  Calendar,
  TrendingUp,
  AlertCircle,
  Sparkles,
  Zap
} from 'lucide-react'
import NotesList from '../components/NotesList'
import NoteForm from '../components/NoteForm'
import useNotes from '../hooks/useNotes'

const Dashboard = () => {
  const [dashboardStats, setDashboardStats] = useState({
    total_clients: 0,
    active_clients: 0,
    high_risk_clients: 0,
    recent_intakes: 0
  })
  const [loading, setLoading] = useState(true)
  
  // Notes management
  const {
    notes,
    addNote,
    editNote,
    deleteNote,
    loading: notesLoading
  } = useNotes()
  
  const [showNoteForm, setShowNoteForm] = useState(false)
  const [editingNote, setEditingNote] = useState(null)

  useEffect(() => {
    fetchDashboardStats()
  }, [])

  const fetchDashboardStats = async () => {
    try {
      const caseManagerId = 'cm_001' // This would come from auth context
      const response = await fetch(`/api/dashboard/${caseManagerId}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setDashboardStats(data.statistics)
        }
      }
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddNote = async (noteData) => {
    try {
      await addNote(noteData)
      setShowNoteForm(false)
    } catch (error) {
      console.error('Failed to add note:', error)
    }
  }

  const handleEditNote = async (noteData) => {
    try {
      if (editingNote) {
        await editNote(editingNote.note_id, noteData)
        setEditingNote(null)
      }
      setShowNoteForm(false)
    } catch (error) {
      console.error('Failed to edit note:', error)
    }
  }

  const handleDeleteNote = async (noteId) => {
    try {
      await deleteNote(noteId)
    } catch (error) {
      console.error('Failed to delete note:', error)
    }
  }

  const handleEditClick = (note) => {
    setEditingNote(note)
    setShowNoteForm(true)
  }

  const moduleCards = [
    {
      title: 'Case Management',
      description: 'Manage client cases, track progress, and maintain case notes',
      path: '/case-management',
      icon: Users,
      gradient: 'from-blue-500 via-blue-600 to-purple-600',
      stats: `${dashboardStats.active_clients} Active Cases`,
      accent: 'bg-blue-500/20 border-blue-500/30'
    },
    {
      title: 'Housing Search',
      description: 'Find affordable housing options and transitional programs',
      path: '/housing',
      icon: Home,
      gradient: 'from-emerald-500 via-green-600 to-teal-600',
      stats: 'Search Available',
      accent: 'bg-emerald-500/20 border-emerald-500/30'
    },
    {
      title: 'Benefits Assistant',
      description: 'Apply for SNAP, SSDI, Medicaid, and other assistance programs',
      path: '/benefits',
      icon: DollarSign,
      gradient: 'from-purple-500 via-violet-600 to-indigo-600',
      stats: 'Multiple Programs',
      accent: 'bg-purple-500/20 border-purple-500/30'
    },
    {
      title: 'Legal Services',
      description: 'Expungement, court dates, and legal document assistance',
      path: '/legal',
      icon: Scale,
      gradient: 'from-orange-500 via-amber-600 to-yellow-600',
      stats: 'Legal Aid Available',
      accent: 'bg-orange-500/20 border-orange-500/30'
    },
    {
      title: 'Resume Builder',
      description: 'AI-powered resume creation tailored for second chance employment',
      path: '/resume',
      icon: FileText,
      gradient: 'from-indigo-500 via-blue-600 to-cyan-600',
      stats: 'ATS Optimized',
      accent: 'bg-indigo-500/20 border-indigo-500/30'
    },
    {
      title: 'AI Assistant',
      description: 'Get help with applications, advice, and case planning',
      path: '/ai-chat',
      icon: MessageSquare,
      gradient: 'from-pink-500 via-rose-600 to-red-600',
      stats: '24/7 Available',
      accent: 'bg-pink-500/20 border-pink-500/30'
    },
    {
      title: 'Services Directory',
      description: 'Comprehensive directory of local support services',
      path: '/services',
      icon: Building2,
      gradient: 'from-teal-500 via-cyan-600 to-blue-600',
      stats: 'Local Resources',
      accent: 'bg-teal-500/20 border-teal-500/30'
    },
    {
      title: 'Smart Daily Dashboard',
      description: 'Prioritized daily tasks and intelligent recommendations',
      path: '/smart-dashboard',
      icon: Calendar,
      gradient: 'from-cyan-500 via-sky-600 to-blue-600',
      stats: 'AI Powered',
      accent: 'bg-cyan-500/20 border-cyan-500/30'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                    <Sparkles className="h-6 w-6 text-white" />
                  </div>
                  <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-pink-200 bg-clip-text text-transparent">
                    Case Management Suite
                  </h1>
                </div>
                <p className="text-gray-300 text-lg">Comprehensive reentry services platform</p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-right bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                  <p className="text-sm text-gray-400">Case Manager</p>
                  <p className="font-semibold text-white">John Doe</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {/* Total Clients */}
            <div className="group bg-gradient-to-br from-blue-500/10 to-purple-500/10 backdrop-blur-xl p-6 rounded-2xl border border-blue-500/20 hover:border-blue-400/40 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/20">
              <div className="flex items-center">
                <div className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl shadow-lg">
                  <Users className="h-7 w-7 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Total Clients</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <div className="animate-pulse bg-gray-700 h-8 w-12 rounded"></div>
                    ) : (
                      dashboardStats.total_clients
                    )}
                  </p>
                  <div className="flex items-center mt-1">
                    <TrendingUp className="h-4 w-4 text-green-400 mr-1" />
                    <span className="text-xs text-green-400">+12% this month</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Active Cases */}
            <div className="group bg-gradient-to-br from-emerald-500/10 to-green-500/10 backdrop-blur-xl p-6 rounded-2xl border border-emerald-500/20 hover:border-emerald-400/40 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-emerald-500/20">
              <div className="flex items-center">
                <div className="p-4 bg-gradient-to-r from-emerald-500 to-green-600 rounded-xl shadow-lg">
                  <TrendingUp className="h-7 w-7 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Active Cases</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <div className="animate-pulse bg-gray-700 h-8 w-12 rounded"></div>
                    ) : (
                      dashboardStats.active_clients
                    )}
                  </p>
                  <div className="flex items-center mt-1">
                    <Zap className="h-4 w-4 text-yellow-400 mr-1" />
                    <span className="text-xs text-yellow-400">High activity</span>
                  </div>
                </div>
              </div>
            </div>

            {/* High Risk */}
            <div className="group bg-gradient-to-br from-red-500/10 to-pink-500/10 backdrop-blur-xl p-6 rounded-2xl border border-red-500/20 hover:border-red-400/40 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-red-500/20">
              <div className="flex items-center">
                <div className="p-4 bg-gradient-to-r from-red-500 to-pink-600 rounded-xl shadow-lg">
                  <AlertCircle className="h-7 w-7 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">High Risk</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <div className="animate-pulse bg-gray-700 h-8 w-12 rounded"></div>
                    ) : (
                      dashboardStats.high_risk_clients
                    )}
                  </p>
                  <div className="flex items-center mt-1">
                    <AlertCircle className="h-4 w-4 text-orange-400 mr-1" />
                    <span className="text-xs text-orange-400">Needs attention</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Intakes */}
            <div className="group bg-gradient-to-br from-purple-500/10 to-indigo-500/10 backdrop-blur-xl p-6 rounded-2xl border border-purple-500/20 hover:border-purple-400/40 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/20">
              <div className="flex items-center">
                <div className="p-4 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-xl shadow-lg">
                  <Calendar className="h-7 w-7 text-white" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Recent Intakes</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <div className="animate-pulse bg-gray-700 h-8 w-12 rounded"></div>
                    ) : (
                      dashboardStats.recent_intakes
                    )}
                  </p>
                  <div className="flex items-center mt-1">
                    <Calendar className="h-4 w-4 text-blue-400 mr-1" />
                    <span className="text-xs text-blue-400">This week</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Modules Grid */}
          <div>
            <div className="flex items-center gap-3 mb-8">
              <h2 className="text-2xl font-bold text-white">Available Services</h2>
              <div className="px-3 py-1 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full">
                <span className="text-xs font-medium text-white">8 Modules</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {moduleCards.map((module, index) => {
                const IconComponent = module.icon
                return (
                  <Link
                    key={index}
                    to={module.path}
                    className="group relative overflow-hidden bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/20"
                  >
                    {/* Gradient Background */}
                    <div className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500 bg-gradient-to-br ${module.gradient}`}></div>
                    
                    {/* Content */}
                    <div className="relative z-10 flex flex-col h-full">
                      <div className="flex items-center mb-4">
                        <div className={`p-3 bg-gradient-to-r ${module.gradient} rounded-xl shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                          <IconComponent className="h-6 w-6 text-white" />
                        </div>
                        <div className="ml-3 flex-1">
                          <h3 className="font-bold text-white group-hover:text-purple-200 transition-colors">
                            {module.title}
                          </h3>
                          <div className={`text-xs px-2 py-1 rounded-full mt-1 ${module.accent} border`}>
                            <span className="text-white/80">{module.stats}</span>
                          </div>
                        </div>
                      </div>
                      <p className="text-sm text-gray-300 group-hover:text-gray-200 flex-grow transition-colors leading-relaxed">
                        {module.description}
                      </p>
                      <div className="mt-6 pt-4 border-t border-white/10">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-purple-400 group-hover:text-purple-300 transition-colors">
                            Access Module
                          </span>
                          <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                            <span className="text-white text-xs">→</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Hover Glow Effect */}
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-purple-500/0 via-pink-500/0 to-purple-500/0 group-hover:from-purple-500/10 group-hover:via-pink-500/5 group-hover:to-purple-500/10 transition-all duration-500"></div>
                  </Link>
                )
              })}
            </div>
          </div>

          {/* Notes Section */}
          <div className="mt-16 bg-gradient-to-r from-black/20 to-indigo-900/20 backdrop-blur-xl p-8 rounded-2xl border border-white/10">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-400" />
                Recent Notes
              </h3>
              <button
                onClick={() => {
                  setEditingNote(null)
                  setShowNoteForm(!showNoteForm)
                }}
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-500 hover:to-indigo-500 transition-all duration-200 text-sm font-medium"
              >
                {showNoteForm ? 'Cancel' : '+ Add Note'}
              </button>
            </div>

            {showNoteForm && (
              <div className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
                <NoteForm
                  onSave={editingNote ? handleEditNote : handleAddNote}
                  initialData={editingNote}
                  onCancel={() => {
                    setShowNoteForm(false)
                    setEditingNote(null)
                  }}
                />
              </div>
            )}

            {notesLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-4 bg-white/5 rounded-lg animate-pulse">
                    <div className="h-4 bg-white/10 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-white/10 rounded w-full"></div>
                  </div>
                ))}
              </div>
            ) : notes.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="h-8 w-8 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-400">No notes yet. Create one to get started.</p>
              </div>
            ) : (
              <NotesList
                notes={notes}
                onEdit={handleEditClick}
                onDelete={handleDeleteNote}
                loading={notesLoading}
              />
            )}
          </div>

          {/* Quick Actions */}
          <div className="mt-16 bg-gradient-to-r from-black/20 to-purple-900/20 backdrop-blur-xl p-8 rounded-2xl border border-white/10">
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-400" />
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-4">
              <Link
                to="/case-management"
                className="group px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-500 hover:to-blue-600 transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-blue-500/25 flex items-center gap-2"
              >
                <Users className="h-4 w-4" />
                Add New Client
              </Link>
              <Link
                to="/smart-dashboard"
                className="group px-6 py-3 bg-gradient-to-r from-emerald-600 to-green-700 text-white rounded-xl hover:from-emerald-500 hover:to-green-600 transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-emerald-500/25 flex items-center gap-2"
              >
                <Calendar className="h-4 w-4" />
                View Today's Tasks
              </Link>
              <Link
                to="/housing"
                className="group px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-700 text-white rounded-xl hover:from-purple-500 hover:to-indigo-600 transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25 flex items-center gap-2"
              >
                <Home className="h-4 w-4" />
                Search Housing
              </Link>
              <Link
                to="/resume"
                className="group px-6 py-3 bg-gradient-to-r from-orange-600 to-amber-700 text-white rounded-xl hover:from-orange-500 hover:to-amber-600 transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-orange-500/25 flex items-center gap-2"
              >
                <FileText className="h-4 w-4" />
                Build Resume
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard