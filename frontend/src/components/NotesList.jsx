import { useState } from 'react'
import { Edit, Trash2, Clock, User, Wifi, WifiOff } from 'lucide-react'

const NotesList = ({ 
  notes, 
  onEdit, 
  onDelete, 
  loading = false 
}) => {
  const [deletingNoteId, setDeletingNoteId] = useState(null)

  const handleDelete = async (noteId) => {
    if (window.confirm('Are you sure you want to delete this note?')) {
      try {
        setDeletingNoteId(noteId)
        await onDelete(noteId)
      } catch (error) {
        console.error('Error deleting note:', error)
      } finally {
        setDeletingNoteId(null)
      }
    }
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getNoteTypeColor = (type) => {
    const colors = {
      'Contact': 'bg-blue-100 text-blue-800',
      'Assessment': 'bg-purple-100 text-purple-800',
      'Progress': 'bg-green-100 text-green-800',
      'Incident': 'bg-red-100 text-red-800',
      'Follow-up': 'bg-yellow-100 text-yellow-800',
      'General': 'bg-gray-100 text-gray-800',
      'Housing': 'bg-orange-100 text-orange-800',
      'Employment': 'bg-indigo-100 text-indigo-800',
      'Benefits': 'bg-pink-100 text-pink-800',
      'Legal': 'bg-red-100 text-red-800',
      'Medical': 'bg-teal-100 text-teal-800',
      'Court': 'bg-red-100 text-red-800'
    }
    return colors[type] || 'bg-gray-100 text-gray-800'
  }

  const truncateContent = (content, maxLength = 200) => {
    if (content.length <= maxLength) return content
    return content.substring(0, maxLength) + '...'
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 bg-gray-50 rounded-lg animate-pulse">
            <div className="flex justify-between items-start mb-2">
              <div className="space-y-2">
                <div className="h-4 bg-gray-300 rounded w-20"></div>
                <div className="h-3 bg-gray-300 rounded w-32"></div>
              </div>
              <div className="h-4 bg-gray-300 rounded w-4"></div>
            </div>
            <div className="space-y-2">
              <div className="h-3 bg-gray-300 rounded w-full"></div>
              <div className="h-3 bg-gray-300 rounded w-3/4"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (notes.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <Edit className="h-8 w-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No notes yet</h3>
        <p className="text-gray-500 mb-4">Start documenting client interactions and progress.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {notes.map((note) => (
        <div 
          key={note.note_id} 
          className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
        >
          {/* Note Header */}
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center space-x-3">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getNoteTypeColor(note.note_type)}`}>
                {note.note_type}
              </span>
              
              {/* Sync Status Indicator */}
              <div className="flex items-center space-x-1">
                {note.synced ? (
                  <Wifi className="h-3 w-3 text-green-500" title="Synced to server" />
                ) : (
                  <WifiOff className="h-3 w-3 text-orange-500" title="Saved locally only" />
                )}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onEdit(note)}
                className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="Edit note"
              >
                <Edit className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleDelete(note.note_id)}
                disabled={deletingNoteId === note.note_id}
                className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                title="Delete note"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Note Content */}
          <div className="mb-3">
            <p className="text-gray-900 whitespace-pre-wrap">
              {truncateContent(note.content)}
            </p>
            {note.content.length > 200 && (
              <button 
                onClick={() => onEdit(note)}
                className="text-blue-600 hover:text-blue-700 text-sm mt-1"
              >
                Read more...
              </button>
            )}
          </div>

          {/* Note Footer */}
          <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1">
                <Clock className="h-3 w-3" />
                <span>{formatDateTime(note.created_at)}</span>
              </div>
              <div className="flex items-center space-x-1">
                <User className="h-3 w-3" />
                <span>{note.created_by}</span>
              </div>
            </div>
            
            {note.updated_at !== note.created_at && (
              <div className="text-xs text-gray-400">
                Updated: {formatDateTime(note.updated_at)}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default NotesList