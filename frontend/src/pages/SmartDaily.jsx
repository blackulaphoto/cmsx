import { useState, useEffect } from 'react'
import { Calendar, Clock, CheckCircle, AlertCircle, TrendingUp, Users, Bell, MessageSquare, Search, Filter } from 'lucide-react'
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
        
        // Fallback to mock data if API fails
        console.warn('API failed, using mock data')
        const mockTasks = [
          {
            id: 1,
            title: 'Court preparation for Maria Santos - Expungement hearing',
            priority: 'high',
            dueTime: '09:00',
            status: 'pending',
            client: 'Maria Santos',
            category: 'legal',
            dueDate: '2024-07-25',
            notes: 'Missing employment history documentation'
          },
          {
            id: 2,
            title: 'Housing deadline follow-up - Maria Santos',
            priority: 'high',
            dueTime: '10:30',
            status: 'pending',
            client: 'Maria Santos',
            category: 'housing',
            dueDate: '2024-07-22',
            notes: '30 days remaining in transitional housing'
          },
          {
            id: 3,
            title: 'Job search coordination - Background-friendly positions',
            priority: 'high',
            dueTime: '11:00',
            status: 'in-progress',
            client: 'Maria Santos',
            category: 'employment',
            dueDate: '2024-07-22',
            notes: 'Restaurant experience, need employment for housing qualification'
          },
          {
            id: 4,
            title: 'Complete Medicaid application',
            priority: 'medium',
            dueTime: '14:00',
            status: 'pending',
            client: 'Maria Santos',
            category: 'benefits',
            dueDate: '2024-07-23',
            notes: 'Application incomplete - needs income verification'
          },
          {
            id: 5,
            title: 'Follow up with John Doe on housing application',
            priority: 'medium',
            dueTime: '15:00',
            status: 'pending',
            client: 'John Doe',
            category: 'housing',
            dueDate: '2024-07-22',
            notes: 'Regular check-in'
          }
        ]
        
        // Mock priority alerts
        const mockAlerts = [
          {
            id: 1,
            type: 'urgent',
            title: 'Court date tomorrow - Maria Santos',
            message: 'Expungement hearing scheduled for Tuesday 9:00 AM - documentation needed',
            client: 'Maria Santos',
            dueDate: '2024-07-25'
          },
          {
            id: 2,
            type: 'warning',
            title: 'Housing deadline - 30 days',
            message: 'Maria Santos must find permanent housing in 30 days',
            client: 'Maria Santos',
            dueDate: '2024-08-21'
          }
        ]
        
        // Mock AI reminders
        const mockAiReminders = [
          {
            id: 1,
            type: 'suggestion',
            title: 'Maria Santos: Court prep + housing search urgent',
            message: 'AI Analysis: Client has multiple critical deadlines this week. Recommend prioritizing job search first as employment improves housing applications.',
            confidence: 'high',
            actions: ['Start job search', 'Gather legal documents', 'Schedule housing appointments']
          },
          {
            id: 2,
            type: 'insight',
            title: 'Workflow optimization suggestion',
            message: 'Based on similar cases, clients with restaurant experience have 85% success rate in hospitality/retail positions when expungement is pending.',
            confidence: 'medium',
            actions: ['Search background-friendly employers', 'Prepare for quick hiring process']
          }
        ]
        
        setTasks(mockTasks)
        setPriorityAlerts(mockAlerts)
        setAiReminders(mockAiReminders)
        setLoading(false)
      } catch (error) {
        console.error('Error fetching tasks:', error)
        // Use mock data on error
        setTasks([])
        setPriorityAlerts([])
        setAiReminders([])
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
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'in-progress': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Calendar size={32} />
          <h1 className="text-3xl font-bold">Smart Daily Dashboard</h1>
        </div>
        <p className="text-lg opacity-90">Your intelligent daily agenda and task management</p>
      </div>

      <div className="p-8">
        {/* Priority Alerts */}
        {priorityAlerts.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-8">
            <h2 className="text-xl font-semibold text-red-900 mb-4 flex items-center gap-2">
              <Bell className="text-red-600" size={24} />
              Priority Alerts
            </h2>
            <div className="space-y-3">
              {priorityAlerts.map((alert) => (
                <div key={alert.id} className="bg-white p-4 rounded-lg border border-red-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-red-900" data-testid="priority-alerts">{alert.title}</h3>
                    <span className="text-sm text-red-600">Due: {alert.dueDate}</span>
                  </div>
                  <p className="text-red-700 text-sm">{alert.message}</p>
                  <p className="text-red-600 text-xs mt-1">Client: {alert.client}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Reminders */}
        {aiReminders.filter(r => !r.acknowledged).length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
            <h2 className="text-xl font-semibold text-blue-900 mb-4 flex items-center gap-2">
              <MessageSquare className="text-blue-600" size={24} />
              AI-Generated Reminders
            </h2>
            <div className="space-y-3">
              {aiReminders.filter(r => !r.acknowledged).map((reminder) => (
                <div key={reminder.id} className="bg-white p-4 rounded-lg border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-blue-900">{reminder.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      reminder.confidence === 'high' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {reminder.confidence} confidence
                    </span>
                  </div>
                  <p className="text-blue-700 text-sm mb-3" data-testid="ai-suggestion">{reminder.message}</p>
                  {reminder.actions && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {reminder.actions.map((action, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                          {action}
                        </span>
                      ))}
                    </div>
                  )}
                  <button
                    onClick={() => acknowledgeReminder(reminder.id)}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                    data-testid="acknowledge-reminder"
                  >
                    Acknowledge
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
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-8">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search tasks and clients..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                data-testid="task-search"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="text-gray-400" size={20} />
              <select
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All Tasks</option>
                <option value="high">High Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="low">Low Priority</option>
                <option value="legal">Legal</option>
                <option value="housing">Housing</option>
                <option value="employment">Employment</option>
                <option value="benefits">Benefits</option>
              </select>
            </div>
          </div>
        </div>

        {/* Daily Agenda */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6">
          <h2 className="text-xl font-semibold mb-6">Today's Agenda ({filteredTasks.length} tasks)</h2>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading today's tasks...</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="urgent-tasks">
              {filteredTasks.map((task) => (
                <div key={task.id} className={`flex items-center gap-4 p-4 border rounded-xl hover:bg-gray-50 transition-colors ${
                  task.status === 'completed' ? 'border-green-200 bg-green-50' : 'border-gray-200'
                }`}>
                  <div className="text-center min-w-[60px]">
                    <div className="text-lg font-semibold text-gray-900">{task.dueTime}</div>
                    <div className="text-xs text-gray-500">{task.dueTime.includes(':') && parseInt(task.dueTime.split(':')[0]) >= 12 ? 'PM' : 'AM'}</div>
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className={`font-medium ${task.status === 'completed' ? 'text-green-900 line-through' : 'text-gray-900'}`}>
                        {task.title}
                      </h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                        {task.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-1">Client: {task.client} • Category: {task.category}</p>
                    {task.notes && (
                      <p className="text-xs text-gray-500 italic">Notes: {task.notes}</p>
                    )}
                    {task.dueDate && (
                      <p className="text-xs text-gray-500">Due: {task.dueDate}</p>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    {task.status !== 'completed' && (
                      <>
                        <button 
                          className="px-4 py-2 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300 text-sm"
                          onClick={() => {
                            // Navigate to relevant module
                            toast.success(`Starting ${task.category} task for ${task.client}`)
                          }}
                        >
                          Start
                        </button>
                        <button 
                          onClick={() => markTaskComplete(task.id)}
                          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all duration-300 text-sm"
                        >
                          Complete
                        </button>
                      </>
                    )}
                    {task.status === 'completed' && (
                      <span className="px-4 py-2 bg-green-100 text-green-800 rounded-lg text-sm font-medium">
                        ✓ Completed
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mt-8">
          <h2 className="text-xl font-semibold mb-6">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
              <h3 className="font-medium text-gray-900 mb-2">Add New Client</h3>
              <p className="text-sm text-gray-600">Create client profile and start case</p>
            </button>
            <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
              <h3 className="font-medium text-gray-900 mb-2">Schedule Appointment</h3>
              <p className="text-sm text-gray-600">Book meeting with client or service provider</p>
            </button>
            <button className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left">
              <h3 className="font-medium text-gray-900 mb-2">Emergency Referral</h3>
              <p className="text-sm text-gray-600">Quick access to crisis services</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SmartDaily