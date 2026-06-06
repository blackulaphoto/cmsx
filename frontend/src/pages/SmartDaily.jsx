import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Calendar, Clock, CheckCircle, AlertCircle, TrendingUp, Bell,
  Search, Filter, Sparkles, Zap, Brain, Star, PlusCircle, ArrowRight,
  AlertTriangle, ChevronDown, ChevronRight, ListChecks
} from 'lucide-react'
import StatsCard from '../components/StatsCard'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const CASE_MANAGER_ID = 'default_cm'

const BUCKET_META = {
  overdue: {
    label: 'Overdue',
    icon: AlertTriangle,
    color: 'from-red-600/30 to-red-500/20',
    border: 'border-red-500/40',
    badge: 'bg-red-500/30 text-red-200 border border-red-500/40',
    dot: 'bg-red-500',
  },
  today: {
    label: 'Due Today',
    icon: Clock,
    color: 'from-orange-600/30 to-orange-500/20',
    border: 'border-orange-500/40',
    badge: 'bg-orange-500/30 text-orange-200 border border-orange-500/40',
    dot: 'bg-orange-400',
  },
  next_3_days: {
    label: 'Next 3 Days',
    icon: Calendar,
    color: 'from-yellow-600/20 to-yellow-500/10',
    border: 'border-yellow-500/30',
    badge: 'bg-yellow-500/20 text-yellow-200 border border-yellow-500/30',
    dot: 'bg-yellow-400',
  },
  this_week: {
    label: 'This Week',
    icon: TrendingUp,
    color: 'from-blue-600/20 to-blue-500/10',
    border: 'border-blue-500/30',
    badge: 'bg-blue-500/20 text-blue-200 border border-blue-500/30',
    dot: 'bg-blue-400',
  },
  high_priority_no_date: {
    label: 'High Priority — No Due Date',
    icon: Star,
    color: 'from-purple-600/20 to-purple-500/10',
    border: 'border-purple-500/30',
    badge: 'bg-purple-500/20 text-purple-200 border border-purple-500/30',
    dot: 'bg-purple-400',
  },
}

function TaskCard({ task, onComplete, onStart }) {
  const priorityStyles = {
    high: 'bg-red-500/20 text-red-300 border border-red-500/30',
    medium: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
    low: 'bg-green-500/20 text-green-300 border border-green-500/30',
    critical: 'bg-red-600/30 text-red-200 border border-red-600/40',
  }

  const isCompleted = String(task.status).toLowerCase() === 'completed'

  return (
    <div className={`group flex items-center gap-4 p-5 border rounded-xl transition-all duration-200 hover:scale-[1.01] ${
      isCompleted
        ? 'border-green-500/40 bg-gradient-to-r from-green-500/15 to-emerald-500/10'
        : 'border-white/15 bg-gradient-to-br from-white/8 to-white/3 hover:border-white/25'
    }`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <h3 className={`font-semibold text-base ${isCompleted ? 'text-green-300 line-through' : 'text-white group-hover:text-cyan-200'} transition-colors truncate`}>
            {task.title}
          </h3>
          <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${priorityStyles[String(task.priority).toLowerCase()] || priorityStyles.low}`}>
            {task.priority}
          </span>
        </div>
        <p className="text-sm text-gray-400">
          <span className="text-cyan-300 font-medium">{task.client_name}</span>
          {task.task_type && task.task_type !== 'task' && (
            <> · <span className="text-purple-300">{task.task_type}</span></>
          )}
          {task.due_date && (
            <> · <span className="text-gray-500">Due {task.due_date}</span></>
          )}
        </p>
        {task.description && task.description !== task.title && (
          <p className="text-xs text-gray-500 mt-1 italic truncate">{task.description}</p>
        )}
      </div>

      <div className="flex gap-2 flex-shrink-0">
        {!isCompleted && (
          <>
            <button
              onClick={() => onStart(task)}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-sm font-medium transition-all hover:scale-105"
            >
              <span className="flex items-center gap-1.5">
                <Zap size={13} />
                Start
              </span>
            </button>
            <button
              onClick={() => onComplete(task)}
              className="px-4 py-2 bg-white/8 border border-white/15 text-gray-300 rounded-lg text-sm font-medium hover:bg-white/15 hover:text-white transition-all"
            >
              <span className="flex items-center gap-1.5">
                <CheckCircle size={13} />
                Done
              </span>
            </button>
          </>
        )}
        {isCompleted && (
          <span className="px-4 py-2 bg-green-500/15 text-green-300 rounded-lg text-sm font-medium border border-green-500/25 flex items-center gap-1.5">
            <CheckCircle size={13} />
            Completed
          </span>
        )}
      </div>
    </div>
  )
}

function BucketSection({ bucketKey, tasks, onComplete, onStart, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  const meta = BUCKET_META[bucketKey]
  if (!meta || tasks.length === 0) return null
  const Icon = meta.icon

  return (
    <div className={`bg-gradient-to-br ${meta.color} backdrop-blur-xl border ${meta.border} rounded-2xl overflow-hidden`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 p-5 hover:bg-white/5 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full ${meta.dot}`} />
        <Icon size={18} className="text-white/70" />
        <span className="font-bold text-white text-base">{meta.label}</span>
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${meta.badge}`}>
          {tasks.length}
        </span>
        <span className="ml-auto text-white/40">
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-3">
          {tasks.map(task => (
            <TaskCard
              key={task.task_id}
              task={task}
              onComplete={onComplete}
              onStart={onStart}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="bg-gradient-to-br from-white/8 to-white/3 backdrop-blur-xl border border-white/15 rounded-2xl p-16 text-center">
      <div className="p-5 bg-gradient-to-br from-cyan-500/15 to-blue-500/10 rounded-2xl w-fit mx-auto mb-6 border border-cyan-500/20">
        <ListChecks size={52} className="text-cyan-400" />
      </div>
      <h3 className="text-2xl font-bold text-white mb-3">No reminders yet</h3>
      <p className="text-gray-400 mb-2 max-w-md mx-auto">
        Add a task with a deadline and the system will help you prioritize what matters next.
      </p>
      <p className="text-gray-500 text-sm mb-8">
        Tasks due today, overdue items, and upcoming deadlines will appear here automatically.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white rounded-xl font-semibold transition-all hover:scale-105 hover:shadow-xl hover:shadow-cyan-500/20"
      >
        <PlusCircle size={18} />
        Create Task in Dashboard
        <ArrowRight size={16} />
      </Link>
    </div>
  )
}

function SmartDaily() {
  const navigate = useNavigate()
  const [buckets, setBuckets] = useState({})
  const [aiSummary, setAiSummary] = useState(null)
  const [counts, setCounts] = useState({})
  const [totalActive, setTotalActive] = useState(0)
  const [completedCount, setCompletedCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [prioritizedRes, dashboardRes] = await Promise.all([
          apiFetch(`/api/reminders/prioritized/${CASE_MANAGER_ID}`),
          apiFetch(`/api/reminders/smart-dashboard/${CASE_MANAGER_ID}`),
        ])

        if (prioritizedRes.ok) {
          const data = await prioritizedRes.json()
          setBuckets(data.buckets || {})
          setAiSummary(data.ai_summary || null)
          setCounts(data.counts || {})
          setTotalActive(data.total_active || 0)
        } else {
          setBuckets({})
          setAiSummary(null)
        }

        // Count completed tasks from smart dashboard if available
        if (dashboardRes.ok) {
          const dashData = await dashboardRes.json()
          const todayTasks = dashData.dashboard?.today_tasks || []
          setCompletedCount(todayTasks.filter(t => String(t.status).toLowerCase() === 'completed').length)
        }
      } catch (error) {
        console.error('Error fetching reminders:', error)
        toast.error('Failed to load reminders')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const getTaskDestination = (task) => {
    const cat = String(task.task_type || '').toLowerCase()
    const title = String(task.title || '').toLowerCase()
    const clientQuery = task.client_id ? `?client=${encodeURIComponent(task.client_id)}` : ''

    if (cat.includes('legal') || title.includes('court') || title.includes('probation')) return `/legal${clientQuery}`
    if (cat.includes('housing') || title.includes('housing') || title.includes('sober living')) return `/housing${clientQuery}`
    if (cat.includes('benefit') || title.includes('snap') || title.includes('calfresh') || title.includes('medi-cal')) return `/benefits${clientQuery}`
    if (cat.includes('employment') || cat.includes('job') || title.includes('resume')) return `/jobs${clientQuery}`
    if (cat.includes('fmla') || title.includes('fmla')) return `/fmla${clientQuery}`
    return clientQuery ? `/case-management${clientQuery}` : '/case-management'
  }

  const handleStart = (task) => {
    navigate(getTaskDestination(task))
    toast.success(`Opened ${task.task_type || 'task'} for ${task.client_name}`)
  }

  const handleComplete = async (task) => {
    const source = task.source || ''
    const taskId = task.task_id

    // Optimistically update UI
    setBuckets(prev => {
      const next = { ...prev }
      for (const key of Object.keys(next)) {
        next[key] = next[key].map(t =>
          t.task_id === taskId ? { ...t, status: 'completed' } : t
        )
      }
      return next
    })
    setCompletedCount(c => c + 1)
    setTotalActive(a => Math.max(0, a - 1))

    if (source === 'intelligent_task' && taskId) {
      try {
        const res = await apiFetch(`/api/reminders/tasks/${encodeURIComponent(taskId)}/complete`, { method: 'POST' })
        if (!res.ok) throw new Error('Server error')
        toast.success('Task marked complete')
      } catch {
        toast.error('Could not save completion — refresh to sync')
      }
    } else {
      toast.success('Task marked complete')
    }
  }

  // Flatten all tasks for search/filter
  const allTasks = Object.values(buckets).flat()

  const filteredBuckets = () => {
    if (!searchTerm && selectedFilter === 'all') return buckets

    const filtered = {}
    for (const [key, tasks] of Object.entries(buckets)) {
      filtered[key] = tasks.filter(task => {
        const matchSearch = !searchTerm ||
          String(task.title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          String(task.client_name || '').toLowerCase().includes(searchTerm.toLowerCase())
        const matchFilter = selectedFilter === 'all' ||
          String(task.priority || '').toLowerCase() === selectedFilter ||
          String(task.task_type || '').toLowerCase().includes(selectedFilter)
        return matchSearch && matchFilter
      })
    }
    return filtered
  }

  const activeBuckets = filteredBuckets()
  const hasAnyTask = Object.values(activeBuckets).some(arr => arr.length > 0)

  const stats = [
    { icon: Clock, label: "Today's Tasks", value: String(counts.today || 0), variant: 'primary' },
    { icon: CheckCircle, label: 'Completed', value: String(completedCount), variant: 'success' },
    { icon: AlertCircle, label: 'Overdue', value: String(counts.overdue || 0), variant: 'warning' },
    { icon: TrendingUp, label: 'Total Active', value: String(totalActive), variant: 'secondary' },
  ]

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Background glows */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-2000" />
      </div>

      <div className="relative z-10">
        {/* Header */}
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
            <div className="flex items-center gap-4 mb-1">
              <div className="relative p-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl shadow-lg">
                <Calendar className="h-8 w-8 text-white" />
                <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-green-400 rounded-full border-2 border-white animate-pulse" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-4xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent">
                  Daily Reminders
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  <Brain size={15} className="text-cyan-400" />
                  <span className="text-gray-300 text-base">Smart priority view — what matters most, right now</span>
                  <span className="px-2.5 py-0.5 bg-cyan-500/15 text-cyan-300 text-xs rounded-full border border-cyan-500/25">AI Powered</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">

          {/* AI Summary Banner */}
          {!loading && aiSummary && (
            <div className="bg-gradient-to-r from-blue-600/20 to-cyan-600/15 backdrop-blur-xl border border-blue-500/30 rounded-2xl p-5 flex items-start gap-4">
              <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex-shrink-0 mt-0.5">
                <Sparkles className="text-white" size={18} />
              </div>
              <div>
                <p className="text-sm text-blue-200 font-medium mb-0.5">Smart Summary</p>
                <p className="text-white font-semibold text-base leading-snug" data-testid="ai-suggestion">{aiSummary}</p>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((stat, i) => <StatsCard key={i} {...stat} />)}
          </div>

          {/* Search + Filter */}
          <div className="bg-gradient-to-br from-white/8 to-white/3 backdrop-blur-xl p-5 rounded-2xl border border-white/15 shadow-xl shadow-purple-500/5">
            <div className="flex flex-col gap-4 mb-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">Task Intake</h2>
                <p className="text-sm text-slate-400 mt-0.5">
                  New tasks are created in Dashboard and appear here once saved.
                </p>
              </div>
              <Link
                to="/"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 px-5 py-2.5 text-sm font-semibold text-white hover:from-cyan-400 hover:to-blue-400 hover:shadow-lg hover:shadow-cyan-500/20 transition-all"
              >
                <PlusCircle size={16} />
                Create Task
                <ArrowRight size={14} />
              </Link>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Search tasks and clients..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white/8 backdrop-blur-sm border border-white/15 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 text-white placeholder-gray-500 transition-all hover:bg-white/12"
                  data-testid="task-search"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter className="text-purple-400 flex-shrink-0" size={16} />
                <select
                  value={selectedFilter}
                  onChange={e => setSelectedFilter(e.target.value)}
                  className="px-4 py-3 bg-white/8 backdrop-blur-sm border border-white/15 rounded-xl focus:ring-2 focus:ring-purple-500 text-white transition-all"
                >
                  <option value="all" className="bg-gray-800">All Tasks</option>
                  <option value="high" className="bg-gray-800">High Priority</option>
                  <option value="medium" className="bg-gray-800">Medium Priority</option>
                  <option value="low" className="bg-gray-800">Low Priority</option>
                  <option value="housing" className="bg-gray-800">Housing</option>
                  <option value="disability" className="bg-gray-800">Disability</option>
                  <option value="employment" className="bg-gray-800">Employment</option>
                  <option value="benefits" className="bg-gray-800">Benefits</option>
                </select>
              </div>
            </div>
          </div>

          {/* Priority Buckets */}
          {loading ? (
            <div className="text-center py-20">
              <div className="relative mx-auto mb-5 w-12 h-12">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-cyan-500/20 border-t-cyan-500" />
                <div className="absolute inset-2 animate-spin rounded-full border-2 border-blue-500/20 border-t-blue-500" style={{ animationDirection: 'reverse' }} />
              </div>
              <p className="text-gray-300 font-medium">Loading your priorities...</p>
            </div>
          ) : !hasAnyTask ? (
            <EmptyState />
          ) : (
            <div className="space-y-4" data-testid="urgent-tasks">
              {/* Overdue — always expanded */}
              <BucketSection
                bucketKey="overdue"
                tasks={activeBuckets.overdue || []}
                onComplete={handleComplete}
                onStart={handleStart}
                defaultOpen
              />
              {/* Today — always expanded */}
              <BucketSection
                bucketKey="today"
                tasks={activeBuckets.today || []}
                onComplete={handleComplete}
                onStart={handleStart}
                defaultOpen
              />
              {/* Next 3 days — expanded */}
              <BucketSection
                bucketKey="next_3_days"
                tasks={activeBuckets.next_3_days || []}
                onComplete={handleComplete}
                onStart={handleStart}
                defaultOpen
              />
              {/* This week — collapsed by default */}
              <BucketSection
                bucketKey="this_week"
                tasks={activeBuckets.this_week || []}
                onComplete={handleComplete}
                onStart={handleStart}
                defaultOpen={false}
              />
              {/* High priority no date — collapsed */}
              <BucketSection
                bucketKey="high_priority_no_date"
                tasks={activeBuckets.high_priority_no_date || []}
                onComplete={handleComplete}
                onStart={handleStart}
                defaultOpen={false}
              />
              {/* "Later" tasks not shown by default — they're not priorities */}
            </div>
          )}

          {/* Quick Actions */}
          <div className="bg-gradient-to-br from-white/8 to-white/3 backdrop-blur-xl rounded-2xl border border-white/15 shadow-xl shadow-purple-500/5 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                <Star className="h-5 w-5 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Link to="/case-management" className="group p-5 bg-gradient-to-br from-white/8 to-white/3 border border-white/15 rounded-xl hover:border-white/25 transition-all hover:scale-105 hover:shadow-lg hover:shadow-blue-500/15 text-left">
                <h3 className="font-bold text-white mb-1.5 group-hover:text-blue-200 transition-colors">Add New Client</h3>
                <p className="text-gray-400 text-sm group-hover:text-gray-300 transition-colors">Create client profile and start case</p>
              </Link>
              <Link to="/legal" className="group p-5 bg-gradient-to-br from-white/8 to-white/3 border border-white/15 rounded-xl hover:border-white/25 transition-all hover:scale-105 hover:shadow-lg hover:shadow-green-500/15 text-left">
                <h3 className="font-bold text-white mb-1.5 group-hover:text-green-200 transition-colors">Schedule Appointment</h3>
                <p className="text-gray-400 text-sm group-hover:text-gray-300 transition-colors">Book meeting with client or provider</p>
              </Link>
              <Link to="/services" className="group p-5 bg-gradient-to-br from-white/8 to-white/3 border border-white/15 rounded-xl hover:border-white/25 transition-all hover:scale-105 hover:shadow-lg hover:shadow-red-500/15 text-left">
                <h3 className="font-bold text-white mb-1.5 group-hover:text-red-200 transition-colors">Emergency Referral</h3>
                <p className="text-gray-400 text-sm group-hover:text-gray-300 transition-colors">Quick access to crisis services</p>
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default SmartDaily
