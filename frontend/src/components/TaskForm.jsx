import { useState, useEffect } from 'react'
import { X, Calendar, Clock, AlertTriangle, User, FileText, Tag } from 'lucide-react'

const TaskForm = ({ isOpen, onClose, onSubmit, initialData = null, isEditing = false }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'medium',
    task_type: 'general',
    due_date: '',
    assigned_to: 'Current User'
  })

  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Task types available
  const taskTypes = [
    { value: 'general', label: 'General Task', icon: '📋' },
    { value: 'assessment', label: 'Assessment', icon: '📊' },
    { value: 'follow_up', label: 'Follow-up', icon: '📞' },
    { value: 'court', label: 'Court Date', icon: '⚖️' },
    { value: 'appointment', label: 'Appointment', icon: '📅' },
    { value: 'documentation', label: 'Documentation', icon: '📄' },
    { value: 'housing', label: 'Housing', icon: '🏠' },
    { value: 'employment', label: 'Employment', icon: '💼' },
    { value: 'benefits', label: 'Benefits', icon: '💰' },
    { value: 'legal', label: 'Legal', icon: '⚖️' },
    { value: 'medical', label: 'Medical', icon: '🏥' },
    { value: 'education', label: 'Education', icon: '🎓' }
  ]

  const priorities = [
    { value: 'low', label: 'Low', color: 'bg-gray-100 text-gray-800' },
    { value: 'medium', label: 'Medium', color: 'bg-blue-100 text-blue-800' },
    { value: 'high', label: 'High', color: 'bg-orange-100 text-orange-800' },
    { value: 'urgent', label: 'Urgent', color: 'bg-red-100 text-red-800' }
  ]

  // Reset form when modal opens/closes or initialData changes
  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setFormData({
          title: initialData.title || '',
          description: initialData.description || '',
          priority: initialData.priority || 'medium',
          task_type: initialData.task_type || 'general',
          due_date: initialData.due_date ? initialData.due_date.split('T')[0] : '',
          assigned_to: initialData.assigned_to || 'Current User'
        })
      } else {
        setFormData({
          title: '',
          description: '',
          priority: 'medium',
          task_type: 'general',
          due_date: '',
          assigned_to: 'Current User'
        })
      }
      setErrors({})
    }
  }, [isOpen, initialData])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Task title is required'
    }

    if (!formData.due_date) {
      newErrors.due_date = 'Due date is required'
    } else {
      const dueDate = new Date(formData.due_date)
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      
      if (dueDate < today) {
        newErrors.due_date = 'Due date cannot be in the past'
      }
    }

    if (!formData.assigned_to.trim()) {
      newErrors.assigned_to = 'Assigned to field is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    
    try {
      // Format due date to include time
      const dueDateTime = new Date(formData.due_date + 'T23:59:59').toISOString()
      
      const taskData = {
        ...formData,
        due_date: dueDateTime
      }
      
      await onSubmit(taskData)
      onClose()
    } catch (error) {
      console.error('Error submitting task:', error)
      setErrors({ submit: 'Failed to save task. Please try again.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleTemplateSelect = (template) => {
    const templates = {
      'initial_assessment': {
        title: 'Complete Initial Assessment',
        description: 'Conduct comprehensive intake assessment with client to identify needs and goals.',
        task_type: 'assessment',
        priority: 'high'
      },
      'follow_up_call': {
        title: 'Follow-up Phone Call',
        description: 'Check in with client regarding progress and any new developments.',
        task_type: 'follow_up',
        priority: 'medium'
      },
      'court_reminder': {
        title: 'Court Date Reminder',
        description: 'Remind client of upcoming court appearance and required documentation.',
        task_type: 'court',
        priority: 'urgent'
      },
      'housing_search': {
        title: 'Housing Search Assistance',
        description: 'Help client search for suitable housing options and complete applications.',
        task_type: 'housing',
        priority: 'high'
      },
      'job_application': {
        title: 'Job Application Support',
        description: 'Assist client with job applications and interview preparation.',
        task_type: 'employment',
        priority: 'medium'
      },
      'benefits_application': {
        title: 'Benefits Application',
        description: 'Help client complete and submit benefits applications.',
        task_type: 'benefits',
        priority: 'high'
      }
    }

    const templateData = templates[template]
    if (templateData) {
      setFormData(prev => ({
        ...prev,
        ...templateData
      }))
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            {isEditing ? 'Edit Task' : 'Add New Task'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Quick Templates */}
        {!isEditing && (
          <div className="p-6 border-b bg-gray-50">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Quick Templates</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {[
                { key: 'initial_assessment', label: 'Initial Assessment' },
                { key: 'follow_up_call', label: 'Follow-up Call' },
                { key: 'court_reminder', label: 'Court Reminder' },
                { key: 'housing_search', label: 'Housing Search' },
                { key: 'job_application', label: 'Job Application' },
                { key: 'benefits_application', label: 'Benefits Application' }
              ].map((template) => (
                <button
                  key={template.key}
                  onClick={() => handleTemplateSelect(template.key)}
                  className="p-2 text-xs bg-white border rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors text-left"
                >
                  {template.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <FileText className="h-4 w-4 inline mr-1" />
              Task Title *
            </label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.title ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Enter task title..."
            />
            {errors.title && (
              <p className="mt-1 text-sm text-red-600">{errors.title}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter task description..."
            />
          </div>

          {/* Task Type and Priority Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Task Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Tag className="h-4 w-4 inline mr-1" />
                Task Type
              </label>
              <select
                name="task_type"
                value={formData.task_type}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {taskTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.icon} {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <AlertTriangle className="h-4 w-4 inline mr-1" />
                Priority
              </label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {priorities.map((priority) => (
                  <option key={priority.value} value={priority.value}>
                    {priority.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Due Date and Assigned To Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Due Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar className="h-4 w-4 inline mr-1" />
                Due Date *
              </label>
              <input
                type="date"
                name="due_date"
                value={formData.due_date}
                onChange={handleInputChange}
                min={new Date().toISOString().split('T')[0]}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.due_date ? 'border-red-300' : 'border-gray-300'
                }`}
              />
              {errors.due_date && (
                <p className="mt-1 text-sm text-red-600">{errors.due_date}</p>
              )}
            </div>

            {/* Assigned To */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <User className="h-4 w-4 inline mr-1" />
                Assigned To *
              </label>
              <input
                type="text"
                name="assigned_to"
                value={formData.assigned_to}
                onChange={handleInputChange}
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.assigned_to ? 'border-red-300' : 'border-gray-300'
                }`}
                placeholder="Enter assignee name..."
              />
              {errors.assigned_to && (
                <p className="mt-1 text-sm text-red-600">{errors.assigned_to}</p>
              )}
            </div>
          </div>

          {/* Submit Error */}
          {errors.submit && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{errors.submit}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              {isSubmitting && <Clock className="h-4 w-4 animate-spin" />}
              <span>{isSubmitting ? 'Saving...' : (isEditing ? 'Update Task' : 'Create Task')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default TaskForm