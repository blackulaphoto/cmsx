import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const useNotes = (clientId) => {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (clientId) {
      loadNotesFromBackend()
    } else {
      setNotes([])
    }
  }, [clientId])

  const loadNotesFromBackend = async () => {
    try {
      const response = await apiFetch(`/api/case-management/notes/list/${clientId}`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.notes) {
          const backendNotes = data.notes
            .map(note => ({ ...note, synced: true }))
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
          setNotes(backendNotes)
        }
      }
    } catch (error) {
      console.error('Backend not available for notes loading:', error.message)
      setNotes([])
    }
  }

  const addNote = async (noteData) => {
    try {
      setLoading(true)
      
      const newNote = {
        title: noteData.title || '',
        note_type: noteData.note_type || 'General',
        content: noteData.content || '',
        created_by: noteData.created_by || 'Case Manager'
      }
      const created = await syncNoteToBackend(newNote)
      await loadNotesFromBackend()
      toast.success('Note added successfully')
      return created
    } catch (error) {
      console.error('Error adding note:', error)
      toast.error('Failed to add note')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const updateNote = async (noteId, updateData) => {
    try {
      setLoading(true)
      
      const existingNote = notes.find(note => note.note_id === noteId)
      if (!existingNote) {
        throw new Error('Note not found')
      }
      const response = await apiFetch(`/api/case-management/notes/update/${noteId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: updateData.title ?? existingNote.title ?? '',
          note_type: updateData.note_type || existingNote.note_type,
          content: updateData.content || existingNote.content,
          created_by: updateData.created_by || existingNote.created_by || 'Case Manager'
        })
      })
      if (!response.ok) {
        throw new Error('Failed to update note')
      }
      const data = await response.json()
      setNotes(current => current.map(note => note.note_id === noteId ? { ...data.note, synced: true } : note))
      toast.success('Note updated successfully')
      return data.note
    } catch (error) {
      console.error('Error updating note:', error)
      toast.error('Failed to update note')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const deleteNote = async (noteId) => {
    try {
      setLoading(true)
      
      const response = await apiFetch(`/api/case-management/notes/${noteId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete note')
      }
      setNotes(current => current.filter(note => note.note_id !== noteId))
      toast.success('Note deleted successfully')
    } catch (error) {
      console.error('Error deleting note:', error)
      toast.error('Failed to delete note')
      throw error
    } finally {
      setLoading(false)
    }
  }

  const syncNoteToBackend = async (note) => {
    try {
      setSyncing(true)
      const response = await apiFetch(`/api/case-management/notes/add/${clientId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: note.title || '',
          note_type: note.note_type,
          content: note.content,
          created_by: note.created_by
        })
      })

      if (response.ok) {
        const data = await response.json()
        return { ...data.note, synced: true }
      }
      throw new Error('Backend sync failed')
    } catch (error) {
      console.error('Backend not available, note not saved:', error.message)
      throw error
    } finally {
      setSyncing(false)
    }
  }

  const syncAllNotes = async () => {
    try {
      setSyncing(true)
      await loadNotesFromBackend()
      toast.success('Notes refreshed from backend')
    } catch (error) {
      console.error('Error syncing notes:', error)
      toast.error('Failed to sync some notes')
    } finally {
      setSyncing(false)
    }
  }

  const getFilteredNotes = (filterType = 'All') => {
    if (filterType === 'All') return notes
    return notes.filter(note => note.note_type === filterType)
  }

  const getNotesStats = () => {
    const now = new Date()
    const startOfWeek = new Date(now)
    startOfWeek.setDate(now.getDate() - now.getDay())
    startOfWeek.setHours(0, 0, 0, 0)
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

    const createdOnOrAfter = (note, threshold) =>
      note.created_at && new Date(note.created_at) >= threshold

    return {
      total: notes.length,
      thisWeek: notes.filter(note => createdOnOrAfter(note, startOfWeek)).length,
      thisMonth: notes.filter(note => createdOnOrAfter(note, startOfMonth)).length,
      unsynced: notes.filter(note => !note.synced).length,
      byType: notes.reduce((acc, note) => {
        acc[note.note_type] = (acc[note.note_type] || 0) + 1
        return acc
      }, {})
    }
  }

  return {
    notes,
    loading,
    syncing,
    addNote,
    updateNote,
    deleteNote,
    syncAllNotes,
    getFilteredNotes,
    getNotesStats,
    loadNotesFromBackend
  }
}

export default useNotes
