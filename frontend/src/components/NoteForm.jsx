import { useState, useEffect } from 'react'
import { X, Save, FileText } from 'lucide-react'

const NoteForm = ({ 
  isOpen, 
  onClose, 
  onSubmit, 
  initialData = null,
  isEditing = false 
}) => {
  const [formData, setFormData] = useState({
    note_type: 'Contact',
    content: '',
    created_by: 'Current User' // TODO: Get from auth context
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const noteTypes = [
    'Contact',
    'Assessment', 
    'Progress',
    'Incident',
    'Follow-up',
    'General',
    'Housing',
    'Employment',
    'Benefits',
    'Legal',
    'Medical',
    'Court'
  ]

  const templates = {
    'Contact': 'Client contact made via phone. Discussed current status and upcoming appointments.',
    'Assessment': 'Conducted assessment of client needs and current situation.',
    'Progress': 'Client showing progress in the following areas:',
    'Incident': 'Incident reported:',
    'Follow-up': 'Follow-up on previous action items:',
    'Housing': 'Housing update:',
    'Employment': 'Employment status update:',
    'Benefits': 'Benefits application/status update:',
    'Legal': 'Legal matter update:',
    'Medical': 'Medical appointment/update:',
    'Court': 'Court date/legal proceeding:'
  }

  useEffect(() => {
    if (initialData) {
      setFormData({
        note_type: initialData.note_type || 'Contact',
        content: initialData.content || '',
        created_by: initialData.created_by || 'Current User'
      })
    } else {
      setFormData({
        note_type: 'Contact',
        content: '',
        created_by: 'Current User'
      })
    }
  }, [initialData, isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.content.trim()) {
      return
    }

    try {
      setIsSubmitting(true)
      await onSubmit(formData)
      onClose()
    } catch (error) {
      console.error('Error submitting note:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleTemplateSelect = (template) => {
    setFormData(prev => ({
      ...prev,
      content: template
    }))
  }

  const handleTypeChange = (type) => {
    setFormData(prev => ({
      ...prev,
      note_type: type,
      content: templates[type] || prev.content
    }))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <FileText className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">
              {isEditing ? 'Edit Note' : 'Add New Note'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Note Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Note Type
            </label>
            <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
              {noteTypes.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeChange(type)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    formData.note_type === type
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Quick Templates */}
          {templates[formData.note_type] && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quick Template
              </label>
              <button
                type="button"
                onClick={() => handleTemplateSelect(templates[formData.note_type])}
                className="w-full p-3 text-left bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
              >
                <p className="text-sm text-blue-800">{templates[formData.note_type]}</p>
                <p className="text-xs text-blue-600 mt-1">Click to use this template</p>
              </button>
            </div>
          )}

          {/* Note Content */}
          <div>
            <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
              Note Content *
            </label>
            <textarea
              id="content"
              value={formData.content}
              onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
              placeholder="Enter your note here..."
              rows={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              {formData.content.length} characters
            </p>
          </div>

          {/* Created By (for now, static) */}
          <div>
            <label htmlFor="created_by" className="block text-sm font-medium text-gray-700 mb-2">
              Created By
            </label>
            <input
              id="created_by"
              type="text"
              value={formData.created_by}
              onChange={(e) => setFormData(prev => ({ ...prev, created_by: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Your name"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.content.trim() || isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
            >
              <Save className="h-4 w-4" />
              <span>{isSubmitting ? 'Saving...' : (isEditing ? 'Update Note' : 'Save Note')}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default NoteForm