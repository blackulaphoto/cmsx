import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const useNotes = (clientId) => {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // Load notes from localStorage and backend on mount
  useEffect(() => {
    if (clientId) {
      loadNotesFromStorage()
      loadNotesFromBackend()
    }
  }, [clientId])

  const loadNotesFromStorage = () => {
    try {
      const storedNotes = localStorage.getItem(`notes_${clientId}`)
      if (storedNotes) {
        const parsedNotes = JSON.parse(storedNotes)
        setNotes(parsedNotes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)))
      }
    } catch (error) {
      console.error('Error loading notes from storage:', error)
    }
  }

  const saveNotesToStorage = (updatedNotes) => {
    try {
      localStorage.setItem(`notes_${clientId}`, JSON.stringify(updatedNotes))
    } catch (error) {
      console.error('Error saving notes to storage:', error)
    }
  }

  const loadNotesFromBackend = async () => {
    try {
      const response = await apiFetch(`/api/case-management/notes/list/${clientId}`)
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.notes) {
          // Merge backend notes with local notes, avoiding duplicates
          const backendNotes = data.notes.map(note => ({ ...note, synced: true }))
          const localNotes = JSON.parse(localStorage.getItem(`notes_${clientId}`) || '[]')
          
          // Create a map of existing note IDs to avoid duplicates
          const existingIds = new Set(backendNotes.map(note => note.note_id))
          const uniqueLocalNotes = localNotes.filter(note => !existingIds.has(note.note_id))
          
          // Combine and sort notes
          const allNotes = [...backendNotes, ...uniqueLocalNotes]
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
          
          setNotes(allNotes)
          saveNotesToStorage(allNotes)
          console.log(`Loaded ${backendNotes.length} notes from backend`)
        }
      }
    } catch (error) {
      console.log('Backend not available for notes loading:', error.message)
    }
  }

  const addNote = async (noteData) => {
    try {
      setLoading(true)
      
      const newNote = {
        note_id: `note_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        client_id: clientId,
        note_type: noteData.note_type || 'General',
        content: noteData.content || '',
        created_by: noteData.created_by || 'Current User', // TODO: Get from auth context
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        synced: false // Track sync status
      }

      const updatedNotes = [newNote, ...notes]
      setNotes(updatedNotes)
      saveNotesToStorage(updatedNotes)
      
      toast.success('Note added successfully')
      
      // Attempt to sync to backend
      syncNoteToBackend(newNote)
      
      return newNote
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
      
      const updatedNotes = notes.map(note => 
        note.note_id === noteId 
          ? { 
              ...note, 
              ...updateData, 
              updated_at: new Date().toISOString(),
              synced: false 
            }
          : note
      )
      
      setNotes(updatedNotes)
      saveNotesToStorage(updatedNotes)
      
      toast.success('Note updated successfully')
      
      // Attempt to sync to backend
      const updatedNote = updatedNotes.find(note => note.note_id === noteId)
      if (updatedNote) {
        syncNoteToBackend(updatedNote)
      }
      
      return updatedNote
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
      
      const updatedNotes = notes.filter(note => note.note_id !== noteId)
      setNotes(updatedNotes)
      saveNotesToStorage(updatedNotes)
      
      toast.success('Note deleted successfully')
      
      // Attempt to sync deletion to backend
      syncNoteDeletionToBackend(noteId)
      
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
      
      // Try to sync to backend API
      const response = await apiFetch(`/api/case-management/notes/add/${clientId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          note_type: note.note_type,
          content: note.content,
          created_by: note.created_by
        })
      })

      if (response.ok) {
        // Mark as synced
        const updatedNotes = notes.map(n => 
          n.note_id === note.note_id ? { ...n, synced: true } : n
        )
        setNotes(updatedNotes)
        saveNotesToStorage(updatedNotes)
        console.log('Note synced to backend successfully')
      } else {
        console.log('Backend sync failed, note saved locally')
      }
    } catch (error) {
      console.log('Backend not available, note saved locally:', error.message)
    } finally {
      setSyncing(false)
    }
  }

  const syncNoteDeletionToBackend = async (noteId) => {
    try {
      await apiFetch(`/api/case-management/notes/${noteId}`, {
        method: 'DELETE'
      })
      console.log('Note deletion synced to backend')
    } catch (error) {
      console.log('Backend deletion sync failed:', error.message)
    }
  }

  const syncAllNotes = async () => {
    try {
      setSyncing(true)
      const unsyncedNotes = notes.filter(note => !note.synced)
      
      for (const note of unsyncedNotes) {
        await syncNoteToBackend(note)
      }
      
      toast.success(`Synced ${unsyncedNotes.length} notes to backend`)
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
    return {
      total: notes.length,
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
    loadNotesFromStorage,
    loadNotesFromBackend
  }
}

export default useNotes
