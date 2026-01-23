import { useState } from 'react'
import { 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  Calendar, 
  User, 
  Edit, 
  Trash2, 
  Eye,
  RefreshCw,
  AlertCircle
} from 'lucide-react'

const TasksList = ({ tasks, onEdit, onDelete, onComplete, onView, loading }) => {
  const [deletingTaskId, setDeletingTaskId] = useState(null)

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'low':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'pending':
        return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'overdue':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4" />
      case 'in_progress':
        return <RefreshCw className="h-4 w-4" />
      case 'pending':
        return <Clock className="h-4 w-4" />
      case 'overdue':
        return <AlertCircle className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case 'urgent':
        return <AlertTriangle className="h-4 w-4 text-red-600" />
      case 'high':
        return <AlertTriangle className="h-4 w-4 text-orange-600" />
      default:
        return null
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'No due date'
    
    const date = new Date(dateString)
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    
    // Reset time for comparison
    today.setHours(0, 0, 0, 0)
    tomorrow.setHours(0, 0, 0, 0)
    date.setHours(0, 0, 0, 0)
    
    if (date.getTime() === today.getTime()) {
      return 'Today'
    } else if (date.getTime() === tomorrow.getTime()) {
      return 'Tomorrow'
    } else if (date < today) {
      return `Overdue (${date.toLocaleDateString()})`
    } else {
      return date.toLocaleDateString()
    }
  }

  const isOverdue = (dueDate, status) => {
    if (status === 'completed') return false
    if (!dueDate) return false
    
    const due = new Date(dueDate)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    due.setHours(0, 0, 0, 0)
    
    return due < today
  }

  const handleDelete = async (taskId) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      setDeletingTaskId(taskId)
      try {
        await onDelete(taskId)
      } catch (error) {
        console.error('Error deleting task:', error)
      } finally {
        setDeletingTaskId(null)
      }
    }
  }

  const getTaskTypeIcon = (taskType) => {
    const icons = {
      'general': '📋',
      'assessment': '📊',
      'follow_up': '📞',
      'court': '⚖️',
      'appointment': '📅',
      'documentation': '📄',
      'housing': '🏠',
      'employment': '💼',
      'benefits': '💰',
      'legal': '⚖️',
      'medical': '🏥',
      'education': '🎓'
    }
    return icons[taskType] || '📋'
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 bg-gray-50 rounded-lg animate-pulse">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-300 rounded w-1/2 mb-2"></div>
                <div className="flex space-x-2">
                  <div className="h-6 bg-gray-300 rounded w-16"></div>
                  <div className="h-6 bg-gray-300 rounded w-20"></div>
                </div>
              </div>
              <div className="flex space-x-2">
                <div className="h-8 bg-gray-300 rounded w-16"></div>
                <div className="h-8 bg-gray-300 rounded w-16"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-12">
        <CheckCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No tasks found</h3>
        <p className="text-gray-500 mb-4">
          No tasks match your current filter criteria.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => {
        const taskIsOverdue = isOverdue(task.due_date, task.status)
        const actualStatus = taskIsOverdue ? 'overdue' : task.status
        
        return (
          <div 
            key={task.task_id} 
            className={`p-4 rounded-lg border transition-all hover:shadow-md ${
              taskIsOverdue ? 'bg-red-50 border-red-200' : 
              task.status === 'completed' ? 'bg-green-50 border-green-200' : 
              'bg-white border-gray-200'
            }`}
          >
            <div className="flex justify-between items-start">
              <div className="flex-1 min-w-0">
                {/* Task Header */}
                <div className="flex items-start space-x-2 mb-2">
                  <span className="text-lg flex-shrink-0 mt-0.5">
                    {getTaskTypeIcon(task.task_type)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h4 className={`font-medium text-gray-900 ${
                      task.status === 'completed' ? 'line-through text-gray-500' : ''
                    }`}>
                      {task.title}
                    </h4>
                    {task.description && (
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {task.description}
                      </p>
                    )}
                  </div>
                  {!task.synced && (
                    <div className="flex-shrink-0">
                      <div className="w-2 h-2 bg-orange-400 rounded-full" title="Not synced"></div>
                    </div>
                  )}
                </div>

                {/* Task Details */}
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  {/* Due Date */}
                  <div className={`flex items-center space-x-1 ${
                    taskIsOverdue ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    <Calendar className="h-4 w-4" />
                    <span>{formatDate(task.due_date)}</span>
                  </div>

                  {/* Assigned To */}
                  <div className="flex items-center space-x-1 text-gray-600">
                    <User className="h-4 w-4" />
                    <span>{task.assigned_to}</span>
                  </div>
                </div>

                {/* Status and Priority Tags */}
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {/* Priority */}
                  <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(task.priority)}`}>
                    {getPriorityIcon(task.priority)}
                    <span className="capitalize">{task.priority}</span>
                  </span>

                  {/* Status */}
                  <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(actualStatus)}`}>
                    {getStatusIcon(actualStatus)}
                    <span className="capitalize">
                      {taskIsOverdue ? 'Overdue' : task.status.replace('_', ' ')}
                    </span>
                  </span>

                  {/* Task Type */}
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium">
                    {task.task_type.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => onView(task)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="View task details"
                >
                  <Eye className="h-4 w-4" />
                </button>

                {task.status !== 'completed' && (
                  <button
                    onClick={() => onComplete(task.task_id)}
                    className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                    title="Mark as complete"
                  >
                    <CheckCircle className="h-4 w-4" />
                  </button>
                )}

                <button
                  onClick={() => onEdit(task)}
                  className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                  title="Edit task"
                >
                  <Edit className="h-4 w-4" />
                </button>

                <button
                  onClick={() => handleDelete(task.task_id)}
                  disabled={deletingTaskId === task.task_id}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                  title="Delete task"
                >
                  {deletingTaskId === task.task_id ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default TasksList