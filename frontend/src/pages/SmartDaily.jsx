import { useState, useEffect } from 'react'
import { Calendar, Clock, CheckCircle, AlertCircle, TrendingUp, Users, Bell, MessageSquare, Search, Filter, Sparkles, Zap, Brain, Star } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import toast from 'react-hot-toast'

function SmartDaily() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [priorityAlerts, setPriorityAlerts] = useState([])
  const [aiReminders, setAiReminders] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')

  useEffect(() => {
    const fetchDailyTasks = async () => {
      try {
        // Fetch real data from sophisticated reminders API
        const [dashboardResponse, tasksResponse] = await Promise.all([
          fetch('/api/reminders/smart-dashboard/default_cm'),
          fetch('/api/reminders/tasks?case_manager_id=default_cm')
        ])
        
        if (dashboardResponse.ok && tasksResponse.ok) {
          const dashboardData = await dashboardResponse.json()
          const tasksData = await tasksResponse.json()
          
          // Transform API data to component format
          const transformedTasks = tasksData.tasks?.map(task => ({
            id: task.task_id,
            title: task.title,
            priority: task.priority.toLowerCase(),
            dueTime: new Date(task.due_date).toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            }),
            status: task.status,
            client: task.client_name,
            category: task.task_type,
            dueDate: new Date(task.due_date).toLocaleDateString(),
            notes: task.description
          })) || []
          
          // Generate priority alerts from dashboard data
          const alerts = dashboardData.dashboard?.urgent_items?.map((item, index) => ({
            id: index + 1,
            type: 'urgent',
            title: item.message,
            message: `Action required: ${item.action}`,
            client: item.client_name,
            dueDate: new Date().toLocaleDateString()
          })) || []
          
          // Generate AI reminders from recommendations
          const aiReminders = dashboardData.dashboard?.recommendations?.map((rec, index) => ({
            id: index + 1,
            type: 'suggestion',
            title: 'AI Recommendation',
            message: rec,
            confidence: 'high',
            actions: ['Review', 'Implement']
          })) || []
          
          setTasks(transformedTasks)
          setPriorityAlerts(alerts)
          setAiReminders(aiReminders)
          setLoading(false)
          return
        }
        
        setTasks([])
        setPriorityAlerts([])
        setAiReminders([])
        toast.error('Failed to load smart daily dashboard')
        setLoading(false)
      } catch (error) {
        console.error('Error fetching tasks:', error)
        setTasks([])
        setPriorityAlerts([])
        setAiReminders([])
        toast.error('Failed to load smart daily dashboard')
        setLoading(false)
      }
    }

    fetchDailyTasks()
  }, [])

  // Filter tasks based on search and filter
  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         task.client.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = selectedFilter === 'all' || 
                         task.priority === selectedFilter || 
                         task.category === selectedFilter
    return matchesSearch && matchesFilter
  })

  const markTaskComplete = (taskId) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId ? { ...task, status: 'completed' } : task
    ))
    toast.success('Task marked as complete!')
  }

  const acknowledgeReminder = (reminderId) => {
    setAiReminders(prev => prev.map(reminder => 
      reminder.id === reminderId ? { ...reminder, acknowledged: true } : reminder
    ))
    toast.success('Reminder acknowledged')
  }

  const stats = [
    { icon: Clock, label: 'Today\'s Tasks', value: tasks.length.toString(), variant: 'primary' },
    { icon: CheckCircle, label: 'Completed', value: tasks.filter(t => t.status === 'completed').length.toString(), variant: 'success' },
    { icon: AlertCircle, label: 'Urgent', value: tasks.filter(t => t.priority === 'high').length.toString(), variant: 'warning' },
    { icon: TrendingUp, label: 'Progress', value: `${Math.round((tasks.filter(t => t.status === 'completed').length / tasks.length) * 100)}%`, variant: 'secondary' },
  ]

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border border-red-500/30'
      case 'medium': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border border-yellow-500/30'
      case 'low': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30'
      case 'in-progress': return 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 border border-blue-500/30'
      case 'pending': return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-gray-600/20 text-gray-300 border border-gray-500/30'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
        <div className="absolute top-1/4 left-1/4 w-40 h-40 bg-purple-500/5 rounded-full blur-2xl animate-pulse delay-3000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="relative p-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl shadow-lg">
                <Calendar className="h-8 w-8 text-white" />
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white animate-pulse"></div>
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent">
                  Smart Daily Dashboard
                </h1>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                    <Brain size={16} className="text-cyan-400" />
                    <span className="text-gray-300 text-lg">Your intelligent daily agenda and task management</span>
                  </div>
                  <span className="px-3 py-1 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 text-sm rounded-full border border-cyan-500/30">
                    AI Powered
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Priority Alerts */}
          {priorityAlerts.length > 0 && (
            <div className="bg-gradient-to-r from-red-500/20 to-pink-500/20 backdrop-blur-xl border border-red-500/30 rounded-2xl p-8 mb-8 shadow-2xl shadow-red-500/10">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg">
                  <Bell className="text-white" size={24} />
                </div>
                <h2 className="text-2xl font-bold text-white">Priority Alerts</h2>
                <div className="px-3 py-1 bg-red-500/30 text-red-200 text-sm rounded-full border border-red-500/40">
                  {priorityAlerts.length} urgent
                </div>
              </div>
              <div className="space-y-4">
                {priorityAlerts.map((alert) => (
                  <div key={alert.id} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm p-6 rounded-xl border border-red-500/30 hover:border-red-400/50 transition-all duration-300 hover:scale-[1.02]">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-white text-lg" data-testid="priority-alerts">{alert.title}</h3>
                      <span className="text-sm text-red-300 px-3 py-1 bg-red-500/20 rounded-full border border-red-500/30">
                        Due: {alert.dueDate}
                      </span>
                    </div>
                    <p className="text-red-200 mb-2">{alert.message}</p>
                    <p className="text-red-300 text-sm">Client: <span className="font-semibold text-white">{alert.client}</span></p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Reminders */}
          {aiReminders.filter(r => !r.acknowledged).length > 0 && (
            <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-xl border border-blue-500/30 rounded-2xl p-8 mb-8 shadow-2xl shadow-blue-500/10">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                  <MessageSquare className="text-white" size={24} />
                </div>
                <h2 className="text-2xl font-bold text-white">AI-Generated Reminders</h2>
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-cyan-400" />
                  <span className="px-3 py-1 bg-blue-500/30 text-blue-200 text-sm rounded-full border border-blue-500/40">
                    Intelligent Insights
                  </span>
                </div>
              </div>
              <div className="space-y-4">
                {aiReminders.filter(r => !r.acknowledged).map((reminder) => (
                  <div key={reminder.id} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm p-6 rounded-xl border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:scale-[1.02]">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-bold text-white text-lg">{reminder.title}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        reminder.confidence === 'high' 
                          ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border border-green-500/30' 
                          : 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border border-yellow-500/30'
                      }`}>
                        {reminder.confidence} confidence
                      </span>
                    </div>
                    <p className="text-blue-200 mb-4 leading-relaxed" data-testid="ai-suggestion">{reminder.message}</p>
                    {reminder.actions && (
                      <div className="flex flex-wrap gap-2 mb-4">
                        {reminder.actions.map((action, index) => (
                          <span key={index} className="px-3 py-1 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 rounded-lg text-sm border border-cyan-500/30">
                            {action}
                          </span>
                        ))}
                      </div>
                    )}
                    <button
                      onClick={() => acknowledgeReminder(reminder.id)}
                      className="group px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25"
                      data-testid="acknowledge-reminder"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle size={16} className="group-hover:scale-110 transition-transform duration-300" />
                        Acknowledge
                      </div>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, index) => (
              <StatsCard key={index} {...stat} />
            ))}
          </div>

          {/* Search and Filter */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search tasks and clients..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                  data-testid="task-search"
                />
              </div>
              <div className="flex items-center gap-3">
                <div className="p-1 bg-purple-500/20 rounded">
                  <Filter className="text-purple-400" size={20} />
                </div>
                <select
                  value={selectedFilter}
                  onChange={(e) => setSelectedFilter(e.target.value)}
                  className="px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-white transition-all duration-300"
                >
                  <option value="all" className="bg-gray-800 text-white">All Tasks</option>
                  <option value="high" className="bg-gray-800 text-white">High Priority</option>
                  <option value="medium" className="bg-gray-800 text-white">Medium Priority</option>
                  <option value="low" className="bg-gray-800 text-white">Low Priority</option>
                  <option value="legal" className="bg-gray-800 text-white">Legal</option>
                  <option value="housing" className="bg-gray-800 text-white">Housing</option>
                  <option value="employment" className="bg-gray-800 text-white">Employment</option>
                  <option value="benefits" className="bg-gray-800 text-white">Benefits</option>
                </select>
              </div>
            </div>
          </div>

          {/* Daily Agenda */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 p-8">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg">
                <Calendar className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">Today's Agenda</h2>
              <span className="px-4 py-2 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 rounded-xl border border-indigo-500/30">
                {filteredTasks.length} tasks
              </span>
            </div>
            
            {loading ? (
              <div className="text-center py-16">
                <div className="relative mx-auto mb-6 w-12 h-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-cyan-500/20 border-t-cyan-500"></div>
                  <div className="absolute inset-2 animate-spin rounded-full border-2 border-blue-500/20 border-t-blue-500" style={{animationDirection: 'reverse'}}></div>
                </div>
                <p className="text-gray-300 font-medium">Loading today's tasks...</p>
              </div>
            ) : (
              <div className="space-y-4" data-testid="urgent-tasks">
                {filteredTasks.map((task, index) => (
                  <div key={task.id ?? `task_${index}`} className={`group flex items-center gap-6 p-6 border rounded-2xl transition-all duration-300 hover:scale-[1.02] ${
                    task.status === 'completed' 
                      ? 'border-green-500/50 bg-gradient-to-r from-green-500/20 to-emerald-500/20 hover:shadow-xl hover:shadow-green-500/20' 
                      : 'border-white/20 bg-gradient-to-br from-white/10 to-white/5 hover:border-white/30 hover:shadow-xl hover:shadow-purple-500/20'
                  }`}>
                    <div className="text-center min-w-[80px]">
                      <div className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                        {task.dueTime}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {task.dueTime.includes(':') && parseInt(task.dueTime.split(':')[0]) >= 12 ? 'PM' : 'AM'}
                      </div>
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className={`font-bold text-lg ${task.status === 'completed' ? 'text-green-300 line-through' : 'text-white group-hover:text-cyan-200'} transition-colors`}>
                          {task.title}
                        </h3>
                        <span className={`px-3 py-1 rounded-xl text-xs font-medium ${getPriorityColor(task.priority)}`}>
                          {task.priority}
                        </span>
                        <span className={`px-3 py-1 rounded-xl text-xs font-medium ${getStatusColor(task.status)}`}>
                          {task.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-2">
                        Client: <span className="font-semibold text-cyan-300">{task.client}</span> • 
                        Category: <span className="font-semibold text-purple-300">{task.category}</span>
                      </p>
                      {task.notes && (
                        <p className="text-xs text-gray-400 italic mb-2 bg-white/5 p-2 rounded-lg">
                          Notes: {task.notes}
                        </p>
                      )}
                      {task.dueDate && (
                        <p className="text-xs text-gray-500">Due: {task.dueDate}</p>
                      )}
                    </div>
                    
                    <div className="flex gap-3">
                      {task.status !== 'completed' && (
                        <>
                          <button 
                            className="group/btn px-6 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-cyan-500/25"
                            onClick={() => {
                              // Navigate to relevant module
                              toast.success(`Starting ${task.category} task for ${task.client}`)
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <Zap size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                              Start
                            </div>
                          </button>
                          <button 
                            onClick={() => markTaskComplete(task.id)}
                            className="group/btn px-6 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-xl font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300 transform hover:scale-105"
                          >
                            <div className="flex items-center gap-2">
                              <CheckCircle size={16} className="group-hover/btn:scale-110 transition-transform duration-300" />
                              Complete
                            </div>
                          </button>
                        </>
                      )}
                      {task.status === 'completed' && (
                        <span className="px-6 py-3 bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 rounded-xl font-medium border border-green-500/30 flex items-center gap-2">
                          <CheckCircle size={16} />
                          Completed
                        </span>
                      )}
                    </div>
                  </div>
                ))}
                
                {filteredTasks.length === 0 && (
                  <div className="text-center py-16">
                    <div className="p-4 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 rounded-2xl w-fit mx-auto mb-6">
                      <Calendar size={48} className="text-cyan-400" />
                    </div>
                    <h3 className="text-xl font-medium text-white mb-3">No tasks found</h3>
                    <p className="text-gray-400">Try adjusting your search or filter criteria</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10 p-8 mt-8">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                <Star className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <button className="group p-6 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl hover:border-white/30 transition-all duration-300 text-left hover:scale-105 hover:shadow-xl hover:shadow-blue-500/20">
                <h3 className="font-bold text-white mb-3 group-hover:text-blue-200 transition-colors text-lg">Add New Client</h3>
                <p className="text-gray-300 group-hover:text-gray-200 transition-colors">Create client profile and start case</p>
              </button>
              <button className="group p-6 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl hover:border-white/30 transition-all duration-300 text-left hover:scale-105 hover:shadow-xl hover:shadow-green-500/20">
                <h3 className="font-bold text-white mb-3 group-hover:text-green-200 transition-colors text-lg">Schedule Appointment</h3>
                <p className="text-gray-300 group-hover:text-gray-200 transition-colors">Book meeting with client or service provider</p>
              </button>
              <button className="group p-6 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl hover:border-white/30 transition-all duration-300 text-left hover:scale-105 hover:shadow-xl hover:shadow-red-500/20">
                <h3 className="font-bold text-white mb-3 group-hover:text-red-200 transition-colors text-lg">Emergency Referral</h3>
                <p className="text-gray-300 group-hover:text-gray-200 transition-colors">Quick access to crisis services</p>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SmartDaily
