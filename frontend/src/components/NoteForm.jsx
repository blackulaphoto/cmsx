import { useEffect, useState } from 'react'
import { X, Save, FileText, Loader2, Users } from 'lucide-react'
import toast from 'react-hot-toast'

import { apiFetch } from '../api/config'
import DocumentationAssistPanel from './DocumentationAssistPanel'
import VoiceNoteRecorder from './VoiceNoteRecorder'

const EMPTY_GROUP_FIELDS = {
  group_topic: '',
  attendance: '',
  participation_level: '',
  observations: '',
  direct_quotes: ''
}

const getDirectQuoteLines = (directQuotes) =>
  directQuotes
    .split('\n')
    .map((quote) => quote.trim())
    .filter(Boolean)

const NoteForm = ({
  isOpen,
  onClose,
  onSubmit,
  initialData = null,
  isEditing = false,
  clientId = '',
  clientName = ''
}) => {
  const [formData, setFormData] = useState({
    note_type: 'Contact',
    content: '',
    created_by: 'Case Manager'
  })
  const [groupFields, setGroupFields] = useState(EMPTY_GROUP_FIELDS)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [generatingGroupNote, setGeneratingGroupNote] = useState(false)

  const noteTypes = [
    'Contact',
    'Assessment',
    'Progress',
    'Incident',
    'Follow-up',
    'General',
    'Group',
    'Housing',
    'Employment',
    'Benefits',
    'Legal',
    'Medical',
    'Court'
  ]

  const templates = {
    Contact: 'Client contact made via phone. Discussed current status and upcoming appointments.',
    Assessment: 'Conducted assessment of client needs and current situation.',
    Progress: 'Client showing progress in the following areas:',
    Incident: 'Incident reported:',
    'Follow-up': 'Follow-up on previous action items:',
    General: 'General case management note:',
    Group: 'Group session note:',
    Housing: 'Housing update:',
    Employment: 'Employment status update:',
    Benefits: 'Benefits application/status update:',
    Legal: 'Legal matter update:',
    Medical: 'Medical appointment/update:',
    Court: 'Court date/legal proceeding:'
  }

  useEffect(() => {
    if (initialData) {
      setFormData({
        note_type: initialData.note_type || 'Contact',
        content: initialData.content || '',
        created_by: initialData.created_by || 'Case Manager'
      })
    } else {
      setFormData({
        note_type: 'Contact',
        content: '',
        created_by: 'Case Manager'
      })
    }

    setGroupFields(EMPTY_GROUP_FIELDS)
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
    setFormData((prev) => ({
      ...prev,
      content: template
    }))
  }

  const handleTypeChange = (type) => {
    setFormData((prev) => ({
      ...prev,
      note_type: type,
      content: templates[type] || prev.content
    }))

    if (type !== 'Group') {
      setGroupFields(EMPTY_GROUP_FIELDS)
    }
  }

  const handleGenerateGroupNote = async () => {
    try {
      setGeneratingGroupNote(true)
      const response = await apiFetch('/api/ai-documentation/group-note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId || undefined,
          client_name: clientName || undefined,
          current_text: formData.content,
          context: {
            group_topic: groupFields.group_topic,
            attendance: groupFields.attendance,
            participation_level: groupFields.participation_level,
            observations: groupFields.observations,
            direct_quotes: getDirectQuoteLines(groupFields.direct_quotes)
          }
        })
      })

      if (!response.ok) {
        throw new Error('Failed to generate group note')
      }

      const data = await response.json()
      setFormData((prev) => ({
        ...prev,
        content: data.draft || prev.content
      }))
      toast.success('Group note draft generated')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to generate group note')
    } finally {
      setGeneratingGroupNote(false)
    }
  }

  const assistContext =
    formData.note_type === 'Group'
      ? {
          observations: groupFields.observations,
          direct_quotes: getDirectQuoteLines(groupFields.direct_quotes),
          group_topic: groupFields.group_topic,
          attendance: groupFields.attendance,
          participation_level: groupFields.participation_level,
          next_steps: ''
        }
      : {
          observations: `Note type: ${formData.note_type}`,
          next_steps: '',
          direct_quotes: []
        }

  const assistNoteKind =
    formData.note_type === 'Group'
      ? 'group_note'
      : isEditing
        ? 'progress_note'
        : 'initial_note'

  const applyTranscriptToNote = (transcript) => {
    setFormData((prev) => ({
      ...prev,
      content: transcript,
    }))
  }

  const applyGeneratedTranscriptNote = (draft, transcript) => {
    setFormData((prev) => ({
      ...prev,
      note_type: prev.note_type === 'Group' ? 'Progress' : prev.note_type,
      content: draft || transcript,
    }))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b p-6">
          <div className="flex items-center space-x-3">
            <FileText className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">
              {isEditing ? 'Edit Note' : 'Add New Note'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 transition-colors hover:bg-gray-100"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 p-6">
          <div>
            <label className="mb-3 block text-sm font-medium text-gray-700">
              Note Type
            </label>
            <div className="grid grid-cols-3 gap-2 md:grid-cols-4">
              {noteTypes.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeChange(type)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
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

          {templates[formData.note_type] && (
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Quick Template
              </label>
              <button
                type="button"
                onClick={() => handleTemplateSelect(templates[formData.note_type])}
                className="w-full rounded-lg border border-blue-200 bg-blue-50 p-3 text-left transition-colors hover:bg-blue-100"
              >
                <p className="text-sm text-blue-800">{templates[formData.note_type]}</p>
                <p className="mt-1 text-xs text-blue-600">Click to use this template</p>
              </button>
            </div>
          )}

          {formData.note_type === 'Group' && (
            <div className="space-y-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-indigo-700" />
                <p className="text-sm font-semibold text-indigo-900">Group Note Inputs</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Group Topic
                  </label>
                  <input
                    type="text"
                    value={groupFields.group_topic}
                    onChange={(e) =>
                      setGroupFields((prev) => ({ ...prev, group_topic: e.target.value }))
                    }
                    placeholder="Relapse prevention, anger management, discharge planning..."
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Attendance
                  </label>
                  <input
                    type="text"
                    value={groupFields.attendance}
                    onChange={(e) =>
                      setGroupFields((prev) => ({ ...prev, attendance: e.target.value }))
                    }
                    placeholder="Present, 8 of 10 attended, left early..."
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Participation Level
                </label>
                <input
                  type="text"
                  value={groupFields.participation_level}
                  onChange={(e) =>
                    setGroupFields((prev) => ({ ...prev, participation_level: e.target.value }))
                  }
                  placeholder="Active, moderate, minimal, resistant..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Staff Observations
                </label>
                <textarea
                  value={groupFields.observations}
                  onChange={(e) =>
                    setGroupFields((prev) => ({ ...prev, observations: e.target.value }))
                  }
                  rows={3}
                  placeholder="Observed affect, engagement, barriers, recovery themes, behavioral concerns..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Direct Quotes
                </label>
                <textarea
                  value={groupFields.direct_quotes}
                  onChange={(e) =>
                    setGroupFields((prev) => ({ ...prev, direct_quotes: e.target.value }))
                  }
                  rows={3}
                  placeholder="One quote per line"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="button"
                onClick={handleGenerateGroupNote}
                disabled={generatingGroupNote}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {generatingGroupNote ? <Loader2 className="h-4 w-4 animate-spin" /> : <Users className="h-4 w-4" />}
                Generate Group Note
              </button>
            </div>
          )}

          <div>
            <label htmlFor="content" className="mb-2 block text-sm font-medium text-gray-700">
              Note Content *
            </label>
            <textarea
              id="content"
              value={formData.content}
              onChange={(e) => setFormData((prev) => ({ ...prev, content: e.target.value }))}
              placeholder="Enter your note here..."
              rows={8}
              className="w-full resize-y rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">{formData.content.length} characters</p>
          </div>

          <VoiceNoteRecorder
            clientId={clientId}
            noteType="cm_note"
            insertLabel="Use Transcript in Note"
            onInsertTranscript={applyTranscriptToNote}
            onGenerateNote={applyGeneratedTranscriptNote}
            theme="light"
          />

          <DocumentationAssistPanel
            module="case_management"
            noteKind={assistNoteKind}
            clientId={clientId}
            clientName={clientName}
            currentText={formData.content}
            context={assistContext}
            onApplyDraft={(draft) => setFormData((prev) => ({ ...prev, content: draft }))}
          />

          <div>
            <label htmlFor="created_by" className="mb-2 block text-sm font-medium text-gray-700">
              Created By
            </label>
            <input
              id="created_by"
              type="text"
              value={formData.created_by}
              onChange={(e) => setFormData((prev) => ({ ...prev, created_by: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
              placeholder="Your name"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg bg-gray-100 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-200"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!formData.content.trim() || isSubmitting}
              className="flex items-center space-x-2 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{isSubmitting ? 'Saving...' : isEditing ? 'Update Note' : 'Save Note'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default NoteForm
