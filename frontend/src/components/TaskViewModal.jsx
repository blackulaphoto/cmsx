import { X, Calendar, User, AlertTriangle, Tag, Clock, CheckCircle } from 'lucide-react'

const TaskViewModal = ({ isOpen, onClose, task, onEdit, onComplete }) => {
  if (!isOpen || !task) return null

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
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
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

  const formatDateTime = (dateString) => {
    if (!dateString) return 'Not set'
    return new Date(dateString).toLocaleString()
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Not set'
    return new Date(dateString).toLocaleDateString()
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

  const taskIsOverdue = isOverdue(task.due_date, task.status)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{getTaskTypeIcon(task.task_type)}</span>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Task Details</h2>
              <p className="text-sm text-gray-500">
                Created {formatDateTime(task.created_at)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title */}
          <div>
            <h3 className={`text-2xl font-bold text-gray-900 ${
              task.status === 'completed' ? 'line-through text-gray-500' : ''
            }`}>
              {task.title}
            </h3>
          </div>

          {/* Status and Priority Tags */}
          <div className="flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium border ${getPriorityColor(task.priority)}`}>
              <AlertTriangle className="h-4 w-4" />
              <span className="capitalize">{task.priority} Priority</span>
            </span>

            <span className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(task.status)}`}>
              {task.status === 'completed' ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <Clock className="h-4 w-4" />
              )}
              <span className="capitalize">{task.status.replace('_', ' ')}</span>
            </span>

            {taskIsOverdue && (
              <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 border border-red-200">
                <AlertTriangle className="h-4 w-4" />
                <span>Overdue</span>
              </span>
            )}

            {!task.synced && (
              <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800 border border-orange-200">
                <Clock className="h-4 w-4" />
                <span>Not Synced</span>
              </span>
            )}
          </div>

          {/* Description */}
          {task.description && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Description</h4>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-900 whitespace-pre-wrap">{task.description}</p>
              </div>
            </div>
          )}

          {/* Task Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Due Date */}
            <div className="flex items-start space-x-3">
              <Calendar className={`h-5 w-5 mt-0.5 ${taskIsOverdue ? 'text-red-600' : 'text-gray-400'}`} />
              <div>
                <h4 className="text-sm font-medium text-gray-700">Due Date</h4>
                <p className={`text-gray-900 ${taskIsOverdue ? 'text-red-600 font-medium' : ''}`}>
                  {formatDate(task.due_date)}
                  {taskIsOverdue && ' (Overdue)'}
                </p>
              </div>
            </div>

            {/* Assigned To */}
            <div className="flex items-start space-x-3">
              <User className="h-5 w-5 mt-0.5 text-gray-400" />
              <div>
                <h4 className="text-sm font-medium text-gray-700">Assigned To</h4>
                <p className="text-gray-900">{task.assigned_to}</p>
              </div>
            </div>

            {/* Task Type */}
            <div className="flex items-start space-x-3">
              <Tag className="h-5 w-5 mt-0.5 text-gray-400" />
              <div>
                <h4 className="text-sm font-medium text-gray-700">Task Type</h4>
                <p className="text-gray-900 capitalize">{task.task_type.replace('_', ' ')}</p>
              </div>
            </div>

            {/* Client ID */}
            <div className="flex items-start space-x-3">
              <User className="h-5 w-5 mt-0.5 text-gray-400" />
              <div>
                <h4 className="text-sm font-medium text-gray-700">Client ID</h4>
                <p className="text-gray-900 font-mono text-sm">{task.client_id}</p>
              </div>
            </div>
          </div>

          {/* Timestamps */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">Timeline</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Created:</span>
                <span className="text-gray-900">{formatDateTime(task.created_at)}</span>
              </div>
              {task.updated_at && task.updated_at !== task.created_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Updated:</span>
                  <span className="text-gray-900">{formatDateTime(task.updated_at)}</span>
                </div>
              )}
              {task.completed_at && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Completed:</span>
                  <span className="text-green-600 font-medium">{formatDateTime(task.completed_at)}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          
          {task.status !== 'completed' && (
            <button
              onClick={() => {
                onComplete(task.task_id)
                onClose()
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
            >
              <CheckCircle className="h-4 w-4" />
              <span>Mark Complete</span>
            </button>
          )}
          
          <button
            onClick={() => {
              onEdit(task)
              onClose()
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Edit Task
          </button>
        </div>
      </div>
    </div>
  )
}

export default TaskViewModal