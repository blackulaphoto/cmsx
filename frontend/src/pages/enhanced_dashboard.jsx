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
  Briefcase,
  ClipboardList,
  TrendingUp,
  AlertCircle,
  Sparkles,
  Zap,
  StickyNote,
  BookOpen,
  Bookmark,
  FolderOpen,
  Plus,
  Pin,
  Edit3,
  Trash2,
  ExternalLink,
  Download,
  Upload,
  X,
  Save,
  FileIcon,
  File,
  Image,
  Video,
  Music
} from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'
import { useAuth } from '../contexts/AuthContext'

const EnhancedDashboard = () => {
  const { profile } = useAuth()
  const caseManagerId = profile?.case_manager_id || ''
  const displayName = profile?.full_name || 'Case Manager'
  const isSupervisorModeAvailable = profile?.role === 'admin'
  const displayRole = isSupervisorModeAvailable ? 'Admin / Supervisor' : 'Case Manager'
  const [dashboardStats, setDashboardStats] = useState({
    total_clients: 0,
    active_clients: 0,
    high_risk_clients: 0,
    recent_intakes: 0
  })
  const [loading, setLoading] = useState(true)
  const [fmlaSummary, setFmlaSummary] = useState({
    total_active_cases: 0,
    deadlines_next_7_days: 0,
    missing_paperwork: 0,
    needing_follow_up: 0,
    approved_cases: 0,
    denied_cases: 0
  })
  const [reminderSummary, setReminderSummary] = useState({
    today: 0,
    overdue: 0,
    next_3_days: 0,
    total_active: 0
  })

  // ClickUp-style component states
  // Ensure notes is always defined as an array
  const [notes, setNotes] = useState([])
  const [docs, setDocs] = useState([])
  const [bookmarks, setBookmarks] = useState([])
  const [resources, setResources] = useState([])
  
  // UI states
  const [showNoteEditor, setShowNoteEditor] = useState(false)
  const [showDocEditor, setShowDocEditor] = useState(false)
  const [showBookmarkEditor, setShowBookmarkEditor] = useState(false)
  const [editingNote, setEditingNote] = useState(null)
  const [editingDoc, setEditingDoc] = useState(null)
  const [newNote, setNewNote] = useState('')
  const [newDoc, setNewDoc] = useState({ title: '', content: '', url: '' })
  const [docUploadMode, setDocUploadMode] = useState(false)
  const [newBookmark, setNewBookmark] = useState({ title: '', url: '', description: '' })

  const getBookmarkFavicon = (bookmark) => {
    if (!bookmark?.url) {
      return null
    }

    const cleanedUrl = bookmark.url.trim().replace(/\)+$/, '')
    try {
      const { hostname } = new URL(cleanedUrl)
      if (!hostname) {
        return null
      }
      return `https://www.google.com/s2/favicons?domain=${hostname}`
    } catch {
      return null
    }
  }

  useEffect(() => {
    if (!caseManagerId) return
    fetchDashboardStats()
    fetchFmlaSummary()
    fetchReminderSummary()
    loadClickUpData()
  }, [caseManagerId])

  const fetchDashboardStats = async () => {
    try {
      const response = await apiFetch(`/api/dashboard/stats?case_manager_id=${encodeURIComponent(caseManagerId)}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setDashboardStats(data.stats || { active_clients: 0, total_clients: 0, high_risk_clients: 0, recent_intakes: 0 })
        }
      }
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchFmlaSummary = async () => {
    try {
      const response = await apiFetch(`/api/fmla/summary?case_manager_id=${encodeURIComponent(caseManagerId)}`)
      if (!response.ok) {
        throw new Error('Failed to load FMLA summary')
      }
      const data = await response.json()
      if (data.success) {
        setFmlaSummary({
          total_active_cases: data.total_active_cases || 0,
          deadlines_next_7_days: data.deadlines_next_7_days || 0,
          missing_paperwork: data.missing_paperwork || 0,
          needing_follow_up: data.needing_follow_up || 0,
          approved_cases: data.approved_cases || 0,
          denied_cases: data.denied_cases || 0
        })
      }
    } catch (error) {
      console.error('Failed to load FMLA summary:', error)
    }
  }

  const fetchReminderSummary = async () => {
    try {
      // Use local date (not UTC) so overnight offset doesn't shift bucket boundaries
      const now = new Date()
      const clientDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
      const response = await apiFetch(`/api/reminders/prioritized/${encodeURIComponent(caseManagerId)}?date=${clientDate}`)
      if (!response.ok) {
        throw new Error('Failed to load reminder summary')
      }
      const data = await response.json()
      const counts = data.counts || {}
      setReminderSummary({
        today: counts.today || 0,
        overdue: counts.overdue || 0,
        next_3_days: counts.next_3_days || 0,
        total_active: data.total_active || 0
      })
    } catch (error) {
      console.error('Failed to load reminder summary:', error)
    }
  }

  const loadClickUpData = async () => {
    try {
      // Load data from API endpoints
      const [notesRes, docsRes, bookmarksRes, resourcesRes] = await Promise.all([
        apiFetch('/api/dashboard/notes'),
        apiFetch('/api/dashboard/docs'),
        apiFetch('/api/dashboard/bookmarks'),
        apiFetch('/api/dashboard/resources')
      ])

      if (notesRes.ok) {
        const notesData = await notesRes.json()
        if (notesData.success && Array.isArray(notesData.notes)) {
          setNotes(notesData.notes)
        } else {
          // Ensure notes is set to an empty array if the response is invalid
          setNotes([])
          console.warn('Notes API response was invalid, using empty array instead')
        }
      } else {
        // Handle non-OK response
        setNotes([])
        console.warn('Notes API request failed, using empty array instead')
      }

      if (docsRes.ok) {
        const docsData = await docsRes.json()
        if (docsData.success && Array.isArray(docsData.docs)) {
          setDocs(docsData.docs)
        } else {
          // Ensure docs is set to an empty array if the response is invalid
          setDocs([])
          console.warn('Docs API response was invalid, using empty array instead')
        }
      } else {
        // Handle non-OK response
        setDocs([])
        console.warn('Docs API request failed, using empty array instead')
      }

      if (bookmarksRes.ok) {
        const bookmarksData = await bookmarksRes.json()
        if (bookmarksData.success && Array.isArray(bookmarksData.bookmarks)) {
          setBookmarks(bookmarksData.bookmarks)
        } else {
          // Ensure bookmarks is set to an empty array if the response is invalid
          setBookmarks([])
          console.warn('Bookmarks API response was invalid, using empty array instead')
        }
      } else {
        // Handle non-OK response
        setBookmarks([])
        console.warn('Bookmarks API request failed, using empty array instead')
      }

      if (resourcesRes.ok) {
        const resourcesData = await resourcesRes.json()
        if (resourcesData.success && Array.isArray(resourcesData.resources)) {
          setResources(resourcesData.resources)
        } else {
          // Ensure resources is set to an empty array if the response is invalid
          setResources([])
          console.warn('Resources API response was invalid, using empty array instead')
        }
      } else {
        // Handle non-OK response
        setResources([])
        console.warn('Resources API request failed, using empty array instead')
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error)
      setNotes([])
      setDocs([])
      setBookmarks([])
      setResources([])
    }
  }

  // Notes functions
  const addNote = async () => {
    if (!newNote.trim()) return
    
    try {
      const response = await apiFetch('/api/dashboard/notes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: newNote,
          pinned: false
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setNotes([data.note, ...notes])
          setNewNote('')
          setShowNoteEditor(false)
          toast.success('Note added!')
        }
      } else {
        throw new Error('Failed to add note')
      }
    } catch (error) {
      console.error('Error adding note:', error)
      toast.error('Failed to add note')
    }
  }

  const togglePinNote = async (id) => {
    const note = notes.find(n => n.id === id)
    if (!note) return
    
    try {
      const response = await apiFetch(`/api/dashboard/notes/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: note.content,
          pinned: !note.pinned
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          const updatedNotes = notes.map(note => 
            note.id === id ? data.note : note
          ).sort((a, b) => b.pinned - a.pinned)
          setNotes(updatedNotes)
        }
      }
    } catch (error) {
      console.error('Error toggling pin:', error)
      toast.error('Failed to update note')
    }
  }

  const deleteNote = async (id) => {
    try {
      const response = await apiFetch(`/api/dashboard/notes/${id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        const updatedNotes = notes.filter(note => note.id !== id)
        setNotes(updatedNotes)
        toast.success('Note deleted!')
      } else {
        throw new Error('Failed to delete note')
      }
    } catch (error) {
      console.error('Error deleting note:', error)
      toast.error('Failed to delete note')
    }
  }

  const updateNote = async (id, content) => {
    const note = notes.find(n => n.id === id)
    if (!note) return
    
    try {
      const response = await apiFetch(`/api/dashboard/notes/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: content,
          pinned: note.pinned
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          const updatedNotes = notes.map(note => 
            note.id === id ? data.note : note
          )
          setNotes(updatedNotes)
          setEditingNote(null)
          toast.success('Note updated!')
        }
      } else {
        throw new Error('Failed to update note')
      }
    } catch (error) {
      console.error('Error updating note:', error)
      toast.error('Failed to update note')
    }
  }

  const uploadDocFile = async (file) => {
    if (!file) return
    const autoTitle = newDoc.title.trim() || file.name.replace(/\.[^.]+$/, '')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const uploadRes = await apiFetch('/api/dashboard/resources', {
        method: 'POST',
        body: formData
      })
      if (!uploadRes.ok) throw new Error('Upload failed')
      const uploadData = await uploadRes.json()
      const resourceId = uploadData.resource?.id
      if (!resourceId) throw new Error('No resource ID returned')
      const docRes = await apiFetch('/api/dashboard/docs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: autoTitle,
          content: newDoc.content || '',
          url: `/api/dashboard/resources/${resourceId}/download`
        })
      })
      if (!docRes.ok) throw new Error('Failed to save document record')
      const docData = await docRes.json()
      setDocs(current => [docData.doc, ...current])
      setResources(current => [uploadData.resource, ...current])
      setNewDoc({ title: '', content: '', url: '' })
      setDocUploadMode(false)
      setShowDocEditor(false)
      toast.success('Document uploaded!')
    } catch (error) {
      console.error('Error uploading document:', error)
      toast.error('Failed to upload document')
    }
  }

  // Docs functions
  const addDoc = async () => {
    if (!newDoc.title.trim()) return
    try {
      const response = await apiFetch('/api/dashboard/docs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newDoc)
      })
      if (!response.ok) {
        throw new Error('Failed to save document')
      }
      const data = await response.json()
      setDocs(current => [data.doc, ...current])
      setNewDoc({ title: '', content: '', url: '' })
      setShowDocEditor(false)
      toast.success('Document saved!')
    } catch (error) {
      console.error('Error saving document:', error)
      toast.error('Failed to save document')
    }
  }

  const deleteDoc = async (id) => {
    try {
      const response = await apiFetch(`/api/dashboard/docs/${id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete document')
      }
      setDocs(current => current.filter(doc => doc.id !== id))
      toast.success('Document deleted!')
    } catch (error) {
      console.error('Error deleting document:', error)
      toast.error('Failed to delete document')
    }
  }

  // Bookmarks functions
  const addBookmark = async () => {
    if (!newBookmark.title.trim() || !newBookmark.url.trim()) return
    try {
      const response = await apiFetch('/api/dashboard/bookmarks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newBookmark)
      })
      if (!response.ok) {
        throw new Error('Failed to save bookmark')
      }
      const data = await response.json()
      setBookmarks(current => [data.bookmark, ...current])
      setNewBookmark({ title: '', url: '', description: '' })
      setShowBookmarkEditor(false)
      toast.success('Bookmark saved!')
    } catch (error) {
      console.error('Error saving bookmark:', error)
      toast.error('Failed to save bookmark')
    }
  }

  const deleteBookmark = async (id) => {
    try {
      const response = await apiFetch(`/api/dashboard/bookmarks/${id}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete bookmark')
      }
      setBookmarks(current => current.filter(bookmark => bookmark.id !== id))
      toast.success('Bookmark deleted!')
    } catch (error) {
      console.error('Error deleting bookmark:', error)
      toast.error('Failed to delete bookmark')
    }
  }

  // File type icon helper
  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase()
    switch (ext) {
      case 'pdf': return <FileText className="h-8 w-8 text-red-400" />
      case 'doc':
      case 'docx': return <FileText className="h-8 w-8 text-blue-400" />
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif': return <Image className="h-8 w-8 text-green-400" />
      case 'mp4':
      case 'avi':
      case 'mov': return <Video className="h-8 w-8 text-purple-400" />
      case 'mp3':
      case 'wav': return <Music className="h-8 w-8 text-yellow-400" />
      default: return <File className="h-8 w-8 text-gray-400" />
    }
  }

  const uploadResources = async (files) => {
    try {
      const uploaded = []
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        const response = await apiFetch('/api/dashboard/resources', {
          method: 'POST',
          body: formData
        })
        if (!response.ok) {
          throw new Error(`Failed to upload ${file.name}`)
        }
        const data = await response.json()
        uploaded.push(data.resource)
      }
      setResources(current => [...uploaded, ...current])
      toast.success(`${uploaded.length} file(s) uploaded!`)
    } catch (error) {
      console.error('Error uploading resources:', error)
      toast.error('Failed to upload resource files')
    }
  }

  const downloadResource = (resourceId) => {
    window.open(`/api/dashboard/resources/${resourceId}/download`, '_blank', 'noopener,noreferrer')
  }

  const deleteResource = async (resourceId) => {
    try {
      const response = await apiFetch(`/api/dashboard/resources/${resourceId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete resource')
      }
      setResources(current => current.filter(resource => resource.id !== resourceId))
      toast.success('File deleted!')
    } catch (error) {
      console.error('Error deleting resource:', error)
      toast.error('Failed to delete resource')
    }
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
      description: 'Court dates, compliance tracking, and legal document assistance',
      path: '/legal',
      icon: Scale,
      gradient: 'from-orange-500 via-amber-600 to-yellow-600',
      stats: 'Legal Aid Available',
      accent: 'bg-orange-500/20 border-orange-500/30'
    },
    {
      title: 'FMLA Tracker',
      description: 'Track paperwork, employer/provider follow-up, deadlines, and reminders',
      path: '/fmla',
      icon: ClipboardList,
      gradient: 'from-cyan-500 via-sky-600 to-blue-600',
      stats: `${fmlaSummary.total_active_cases} Active Cases`,
      accent: 'bg-cyan-500/20 border-cyan-500/30'
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
      title: 'Job Search',
      description: 'Find employment opportunities and track applications',
      path: '/jobs',
      icon: Briefcase,
      gradient: 'from-emerald-500 via-green-600 to-lime-600',
      stats: 'Hiring Now',
      accent: 'bg-emerald-500/20 border-emerald-500/30'
    },
    {
      title: 'Smart Daily Dashboard',
      description: 'Prioritized daily tasks and intelligent recommendations',
      path: '/smart-dashboard',
      icon: Calendar,
      gradient: 'from-cyan-500 via-sky-600 to-blue-600',
      stats: 'AI Powered',
      accent: 'bg-cyan-500/20 border-cyan-500/30'
    },
    {
      title: 'Rolodex',
      description: 'Quick-access contact directory for providers, agencies, and community resources',
      path: '/rolodex',
      icon: BookOpen,
      gradient: 'from-violet-500 via-purple-600 to-fuchsia-600',
      stats: 'Contact Directory',
      accent: 'bg-violet-500/20 border-violet-500/30'
    },
    {
      title: 'Documents',
      description: 'Generate, manage, and store case documents, letters, and treatment plans',
      path: '/documentation',
      icon: FolderOpen,
      gradient: 'from-rose-500 via-pink-600 to-red-600',
      stats: 'Case Records',
      accent: 'bg-rose-500/20 border-rose-500/30'
    }
  ]

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-[96rem] mx-auto px-3 sm:px-6 lg:px-8 py-5 sm:py-8">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex-shrink-0">
                    <Sparkles className="h-6 w-6 text-white" />
                  </div>
                  <h1 className="truncate text-3xl sm:text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-pink-200 bg-clip-text text-transparent">
                    Dashboard
                  </h1>
                </div>
                <p className="max-w-2xl text-sm text-slate-300">
                  Review caseload activity, linked workspace notes, and service modules without squeezing primary actions off-screen.
                </p>
              </div>
              <div className="flex w-full xl:w-auto items-center">
                <div className="w-full xl:w-auto min-w-0 xl:max-w-xs bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10">
                  <p className="text-sm text-gray-400">{displayRole}</p>
                  <p className="truncate font-semibold text-white">{displayName}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="max-w-[96rem] mx-auto px-3 sm:px-6 lg:px-8 py-5 sm:py-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-12">
            {/* Total Clients */}
            <div className="group bg-gradient-to-br from-blue-500/10 to-purple-500/10 backdrop-blur-xl p-6 rounded-2xl border border-blue-500/20 hover:border-blue-400/40 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/20">
              <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <div className="p-4 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl shadow-lg">
                  <Users className="h-7 w-7 text-white" />
                </div>
                <div className="sm:ml-4">
                  <p className="text-sm font-medium text-gray-400">Total Clients</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <span className="inline-block animate-pulse bg-gray-700 h-8 w-12 rounded"></span>
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
              <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <div className="p-4 bg-gradient-to-r from-emerald-500 to-green-600 rounded-xl shadow-lg">
                  <TrendingUp className="h-7 w-7 text-white" />
                </div>
                <div className="sm:ml-4">
                  <p className="text-sm font-medium text-gray-400">Active Cases</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <span className="inline-block animate-pulse bg-gray-700 h-8 w-12 rounded"></span>
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
              <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <div className="p-4 bg-gradient-to-r from-red-500 to-pink-600 rounded-xl shadow-lg">
                  <AlertCircle className="h-7 w-7 text-white" />
                </div>
                <div className="sm:ml-4">
                  <p className="text-sm font-medium text-gray-400">High Risk</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <span className="inline-block animate-pulse bg-gray-700 h-8 w-12 rounded"></span>
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
              <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <div className="p-4 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-xl shadow-lg">
                  <Calendar className="h-7 w-7 text-white" />
                </div>
                <div className="sm:ml-4">
                  <p className="text-sm font-medium text-gray-400">Recent Intakes</p>
                  <p className="text-3xl font-bold text-white">
                    {loading ? (
                      <span className="inline-block animate-pulse bg-gray-700 h-8 w-12 rounded"></span>
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

          {/* Daily Reminders band — mirrors the FMLA Tracker band styling */}
          <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 via-slate-900/30 to-blue-500/10 backdrop-blur-xl p-6 mb-12">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
                  <Calendar className="h-4 w-4" />
                  Smart Daily
                </div>
                <h2 className="mt-4 text-2xl font-bold text-white">Daily Reminders</h2>
                <p className="mt-2 max-w-2xl text-sm text-slate-300">
                  Court dates, appointments, paperwork deadlines, and follow-up tasks.
                </p>
              </div>
              <Link
                to="/smart-dashboard"
                className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                Open Smart Daily
              </Link>
            </div>
            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Due Today', value: reminderSummary.today, to: '/smart-dashboard' },
                { label: 'Overdue', value: reminderSummary.overdue, to: '/smart-dashboard' },
                { label: 'Next 3 Days', value: reminderSummary.next_3_days, to: '/smart-dashboard' },
                { label: 'Total Active', value: reminderSummary.total_active, to: '/smart-dashboard' }
              ].map((item) => (
                <Link key={item.label} to={item.to} className="rounded-2xl border border-white/10 bg-black/20 p-4 transition hover:-translate-y-0.5 hover:bg-white/10">
                  <div className="text-3xl font-bold text-white">{item.value}</div>
                  <div className="mt-2 text-sm text-slate-300">{item.label}</div>
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 via-slate-900/30 to-blue-500/10 backdrop-blur-xl p-6 mb-12">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
                  <ClipboardList className="h-4 w-4" />
                  FMLA Tracker
                </div>
                <h2 className="mt-4 text-2xl font-bold text-white">Keep every FMLA deadline, fax, and follow-up visible</h2>
                <p className="mt-2 max-w-2xl text-sm text-slate-300">
                  Open the FMLA workspace to manage employer packets, provider certifications, document status, communication history, and linked reminders in one case file.
                </p>
              </div>
              <Link
                to="/fmla"
                className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                Open FMLA Tracker
              </Link>
            </div>
            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
              {[
                { label: 'Active', value: fmlaSummary.total_active_cases, to: '/fmla' },
                { label: 'Due In 7 Days', value: fmlaSummary.deadlines_next_7_days, to: '/fmla?deadline=next_7_days' },
                { label: 'Missing Paperwork', value: fmlaSummary.missing_paperwork, to: '/fmla' },
                { label: 'Needs Follow-Up', value: fmlaSummary.needing_follow_up, to: '/fmla?status=Confirmation+pending' },
                { label: 'Approved', value: fmlaSummary.approved_cases, to: '/fmla?status=Approved' },
                { label: 'Denied', value: fmlaSummary.denied_cases, to: '/fmla?status=Denied' }
              ].map((item) => (
                <Link key={item.label} to={item.to} className="rounded-2xl border border-white/10 bg-black/20 p-4 transition hover:-translate-y-0.5 hover:bg-white/10">
                  <div className="text-3xl font-bold text-white">{item.value}</div>
                  <div className="mt-2 text-sm text-slate-300">{item.label}</div>
                </Link>
              ))}
            </div>
          </div>

          {/* ClickUp-Style Components Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-6 mb-12">
            {/* Notes Section */}
            <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 backdrop-blur-xl p-6 rounded-2xl border border-indigo-500/20">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <StickyNote className="h-5 w-5 text-indigo-400" />
                  <h3 className="font-bold text-white">Notes</h3>
                  <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-1 rounded-full">
                    {Array.isArray(notes) ? notes.length : 0}
                  </span>
                </div>
                <button
                  onClick={() => setShowNoteEditor(true)}
                  className="p-1 hover:bg-indigo-500/20 rounded-lg transition-colors"
                >
                  <Plus className="h-4 w-4 text-indigo-400" />
                </button>
              </div>

              {/* Note Editor */}
              {showNoteEditor && (
                <div className="mb-4 p-3 bg-black/20 rounded-lg border border-indigo-500/30">
                  <textarea
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    placeholder="Add a quick note..."
                    className="w-full bg-transparent text-white placeholder-gray-400 resize-none border-none outline-none"
                    rows="3"
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button
                      onClick={() => {
                        setShowNoteEditor(false)
                        setNewNote('')
                      }}
                      className="px-3 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={addNote}
                      className="px-3 py-1 text-xs bg-indigo-500 text-white rounded hover:bg-indigo-400 transition-colors"
                    >
                      Save
                    </button>
                  </div>
                </div>
              )}

              {/* Notes List */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {notes.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No notes yet</p>
                ) : (
                  notes.map((note) => (
                    <div
                      key={note.id}
                      className={`group p-3 rounded-lg border transition-all ${
                        note.pinned 
                          ? 'bg-indigo-500/20 border-indigo-500/40' 
                          : 'bg-white/5 border-white/10 hover:border-indigo-500/30'
                      }`}
                    >
                      {editingNote === note.id ? (
                        <div>
                          <textarea
                            defaultValue={note.content}
                            className="w-full bg-transparent text-white resize-none border-none outline-none"
                            rows="2"
                            onBlur={(e) => updateNote(note.id, e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && e.ctrlKey) {
                                updateNote(note.id, e.target.value)
                              }
                            }}
                            autoFocus
                          />
                        </div>
                      ) : (
                        <div>
                          <p className="text-white text-sm whitespace-pre-wrap">{note.content}</p>
                          <div className="flex items-center justify-between mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <span className="text-xs text-gray-400">
                              {new Date(note.createdAt).toLocaleDateString()}
                            </span>
                            <div className="flex gap-1">
                              <button
                                onClick={() => togglePinNote(note.id)}
                                className={`p-1 rounded hover:bg-white/10 transition-colors ${
                                  note.pinned ? 'text-indigo-400' : 'text-gray-400'
                                }`}
                              >
                                <Pin className="h-3 w-3" />
                              </button>
                              <button
                                onClick={() => setEditingNote(note.id)}
                                className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400"
                              >
                                <Edit3 className="h-3 w-3" />
                              </button>
                              <button
                                onClick={() => deleteNote(note.id)}
                                className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400 hover:text-red-400"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Docs Section */}
            <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 backdrop-blur-xl p-6 rounded-2xl border border-blue-500/20">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-blue-400" />
                  <h3 className="font-bold text-white">Docs</h3>
                  <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded-full">
                    {Array.isArray(docs) ? docs.length : 0}
                  </span>
                </div>
                <button
                  onClick={() => { setShowDocEditor(true); setDocUploadMode(false) }}
                  className="p-1 hover:bg-blue-500/20 rounded-lg transition-colors"
                >
                  <Plus className="h-4 w-4 text-blue-400" />
                </button>
              </div>

              {/* Doc Editor */}
              {showDocEditor && (
                <div className="mb-4 p-3 bg-black/20 rounded-lg border border-blue-500/30">
                  {/* Mode toggle */}
                  <div className="flex gap-1 mb-3">
                    <button
                      onClick={() => setDocUploadMode(false)}
                      className={`px-2 py-1 text-xs rounded transition-colors ${!docUploadMode ? 'bg-blue-500 text-white' : 'text-gray-400 hover:text-white'}`}
                    >
                      Write
                    </button>
                    <button
                      onClick={() => setDocUploadMode(true)}
                      className={`px-2 py-1 text-xs rounded transition-colors flex items-center gap-1 ${docUploadMode ? 'bg-blue-500 text-white' : 'text-gray-400 hover:text-white'}`}
                    >
                      <Upload className="h-3 w-3" /> Upload
                    </button>
                  </div>
                  <input
                    type="text"
                    value={newDoc.title}
                    onChange={(e) => setNewDoc({...newDoc, title: e.target.value})}
                    placeholder="Document title..."
                    className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none mb-2"
                  />
                  {docUploadMode ? (
                    <div
                      className="border-2 border-dashed border-blue-500/40 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400/60 transition-colors"
                      onClick={() => {
                        const input = document.createElement('input')
                        input.type = 'file'
                        input.accept = '.pdf,.doc,.docx,.txt,.md,.jpg,.jpeg,.png,.xlsx,.csv'
                        input.onchange = (e) => {
                          const file = e.target.files?.[0]
                          if (file) uploadDocFile(file)
                        }
                        input.click()
                      }}
                    >
                      <Upload className="h-6 w-6 text-blue-400 mx-auto mb-1" />
                      <p className="text-xs text-gray-400">Click to upload a file</p>
                      <p className="text-xs text-gray-500 mt-1">PDF, Word, images, spreadsheets</p>
                    </div>
                  ) : (
                    <>
                      <textarea
                        value={newDoc.content}
                        onChange={(e) => setNewDoc({...newDoc, content: e.target.value})}
                        placeholder="Document content..."
                        className="w-full bg-transparent text-white placeholder-gray-400 resize-none border-none outline-none mb-2"
                        rows="3"
                      />
                      <input
                        type="url"
                        value={newDoc.url}
                        onChange={(e) => setNewDoc({...newDoc, url: e.target.value})}
                        placeholder="External URL (optional)..."
                        className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none mb-2"
                      />
                    </>
                  )}
                  <div className="flex justify-end gap-2 mt-2">
                    <button
                      onClick={() => {
                        setShowDocEditor(false)
                        setDocUploadMode(false)
                        setNewDoc({ title: '', content: '', url: '' })
                      }}
                      className="px-3 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    {!docUploadMode && (
                      <button
                        onClick={addDoc}
                        className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-400 transition-colors"
                      >
                        Save
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Docs List */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {!Array.isArray(docs) || docs.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No documents yet</p>
                ) : (
                  docs.map((doc) => (
                    <div
                      key={doc.id}
                      className="group p-3 rounded-lg bg-white/5 border border-white/10 hover:border-blue-500/30 transition-all"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-1">
                            <h4 className="text-white font-medium text-sm">{doc.title}</h4>
                            {doc.url?.includes('/api/dashboard/resources/') && (
                              <span className="text-xs bg-blue-500/20 text-blue-300 px-1 rounded">file</span>
                            )}
                          </div>
                          {doc.content && (
                            <p className="text-gray-300 text-xs mt-1 line-clamp-2">{doc.content}</p>
                          )}
                          <span className="text-xs text-gray-400 mt-1 block">
                            {new Date(doc.createdAt).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {doc.url && (
                            <button
                              onClick={() => window.open(doc.url, '_blank')}
                              className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400"
                              title={doc.url.includes('/api/dashboard/resources/') ? 'Download file' : 'Open URL'}
                            >
                              {doc.url.includes('/api/dashboard/resources/') ? (
                                <Download className="h-3 w-3" />
                              ) : (
                                <ExternalLink className="h-3 w-3" />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => deleteDoc(doc.id)}
                            className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400 hover:text-red-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Bookmarks Section */}
            <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 backdrop-blur-xl p-6 rounded-2xl border border-green-500/20">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Bookmark className="h-5 w-5 text-green-400" />
                  <h3 className="font-bold text-white">Bookmarks</h3>
                  <span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded-full">
                    {Array.isArray(bookmarks) ? bookmarks.length : 0}
                  </span>
                </div>
                <button
                  onClick={() => setShowBookmarkEditor(true)}
                  className="p-1 hover:bg-green-500/20 rounded-lg transition-colors"
                >
                  <Plus className="h-4 w-4 text-green-400" />
                </button>
              </div>

              {/* Bookmark Editor */}
              {showBookmarkEditor && (
                <div className="mb-4 p-3 bg-black/20 rounded-lg border border-green-500/30">
                  <input
                    type="text"
                    value={newBookmark.title}
                    onChange={(e) => setNewBookmark({...newBookmark, title: e.target.value})}
                    placeholder="Bookmark title..."
                    className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none mb-2"
                  />
                  <input
                    type="url"
                    value={newBookmark.url}
                    onChange={(e) => setNewBookmark({...newBookmark, url: e.target.value})}
                    placeholder="Website URL..."
                    className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none mb-2"
                  />
                  <input
                    type="text"
                    value={newBookmark.description}
                    onChange={(e) => setNewBookmark({...newBookmark, description: e.target.value})}
                    placeholder="Description (optional)..."
                    className="w-full bg-transparent text-white placeholder-gray-400 border-none outline-none mb-2"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setShowBookmarkEditor(false)
                        setNewBookmark({ title: '', url: '', description: '' })
                      }}
                      className="px-3 py-1 text-xs text-gray-400 hover:text-white transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={addBookmark}
                      className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-400 transition-colors"
                    >
                      Save
                    </button>
                  </div>
                </div>
              )}

              {/* Bookmarks List */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {!Array.isArray(bookmarks) || bookmarks.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No bookmarks yet</p>
                ) : (
                  bookmarks.map((bookmark) => (
                    <div
                      key={bookmark.id}
                      className="group p-3 rounded-lg bg-white/5 border border-white/10 hover:border-green-500/30 transition-all cursor-pointer"
                      onClick={() => window.open(bookmark.url, '_blank')}
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={getBookmarkFavicon(bookmark)}
                          alt=""
                          className="w-4 h-4 rounded"
                          onError={(e) => {
                            e.target.style.display = 'none'
                          }}
                        />
                        <div className="flex-1">
                          <h4 className="text-white font-medium text-sm">{bookmark.title}</h4>
                          {bookmark.description && (
                            <p className="text-gray-300 text-xs mt-1">{bookmark.description}</p>
                          )}
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteBookmark(bookmark.id)
                            }}
                            className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400 hover:text-red-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Resources Section */}
            <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 backdrop-blur-xl p-6 rounded-2xl border border-purple-500/20">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <FolderOpen className="h-5 w-5 text-purple-400" />
                  <h3 className="font-bold text-white">Resources</h3>
                  <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full">
                    {resources.length}
                  </span>
                </div>
                <button
                  onClick={() => {
                    const input = document.createElement('input')
                    input.type = 'file'
                    input.multiple = true
                    input.onchange = async (e) => {
                      const files = Array.from(e.target.files || [])
                      if (files.length > 0) {
                        await uploadResources(files)
                      }
                    }
                    input.click()
                  }}
                  className="p-1 hover:bg-purple-500/20 rounded-lg transition-colors"
                >
                  <Upload className="h-4 w-4 text-purple-400" />
                </button>
              </div>

              {/* Resources List */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {resources.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No files yet</p>
                ) : (
                  resources.map((resource) => (
                    <div
                      key={resource.id}
                      className="group p-3 rounded-lg bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex-shrink-0">
                          {getFileIcon(resource.name)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-white font-medium text-sm truncate">{resource.name}</h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-400">
                              {(resource.size / 1024).toFixed(1)} KB
                            </span>
                            <span className="text-xs text-gray-400">
                              {new Date(resource.uploaded_at || resource.uploadedAt).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => downloadResource(resource.id)}
                            className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400 mr-1"
                          >
                            <Download className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => deleteResource(resource.id)}
                            className="p-1 rounded hover:bg-white/10 transition-colors text-gray-400 hover:text-red-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {isSupervisorModeAvailable && (
            <div className="mb-12 rounded-3xl border border-cyan-400/20 bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-indigo-500/10 p-6 backdrop-blur-xl">
              <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
                <div className="min-w-0">
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200">
                    <TrendingUp className="h-4 w-4" />
                    Supervisor Mode
                  </div>
                  <h2 className="text-2xl font-bold text-white">Team oversight lives in the supervisor dashboard</h2>
                  <p className="mt-2 max-w-3xl text-sm text-slate-300">
                    Review caseload pressure, overdue work, high-risk trends, and team follow-through from the dedicated supervisor workspace instead of the standard case manager service grid.
                  </p>
                </div>
                <Link
                  to="/supervisor-dashboard"
                  className="inline-flex items-center justify-center rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition-all duration-300 hover:bg-cyan-400"
                >
                  Open Supervisor Dashboard
                </Link>
              </div>
            </div>
          )}

          {/* Modules Grid */}
          <div>
            <div className="flex items-center gap-3 mb-8">
              <h2 className="text-2xl font-bold text-white">Available Services</h2>
              <div className="px-3 py-1 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full">
                <span className="text-xs font-medium text-white">9 Modules</span>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
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
                  </Link>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EnhancedDashboard
