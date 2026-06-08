import { useEffect, useMemo, useState } from 'react'
import {
  FileText,
  FolderOpen,
  Sparkles,
  ClipboardList,
  PenSquare,
  Save,
  RefreshCw,
  Trash2,
  Plus,
  Search,
  User,
  CheckCircle2,
  Upload,
  Download,
  ScrollText,
  Filter,
  Clock,
  Wand2,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'

import ClientSelector from '../components/ClientSelector'
import DocumentationAssistPanel from '../components/DocumentationAssistPanel'
import VoiceNoteRecorder from '../components/VoiceNoteRecorder'
import { apiFetch } from '../api/config'

const TEMPLATE_CATEGORIES = ['all', 'clinical', 'planning', 'letters', 'fmla']
const BRAND_RESOURCE_CATEGORIES = ['general', 'templates', 'style guide', 'policy', 'sample note', 'letterhead', 'workflow']

const FALLBACK_DOCUMENTATION_TEMPLATES = [
  {
    id: 'initial-cm-note',
    label: 'Initial CM Note',
    mode: 'note',
    category: 'clinical',
    noteType: 'Progress',
    noteKind: 'initial_note',
    bestFor: 'Week 1 intake - introduce treatment team, establish client goals and treatment plan.',
    body: `GOAL:
Introduce client to the current treatment team and establish client's treatment plan. Answer any questions the client has about the program and establish any needs the client has. Establish client goals to stabilize condition medically, behaviorally, emotionally, and cognitively, and return to functioning within normal parameters.

INTERVENTION:
CM and client began the discussion of aftercare.
CM addressed immediate needs.
CM assessed for financial stability.
CM inquired about legal issues and FMLA.
CM inquired about discharge planning.
CM asked about 12-step / sponsor involvement.
CM encouraged client to get the most out of treatment by engaging in groups and 1:1 sessions with TH and CM.
CM used open-ended questions, positive affirmations, motivational interviewing, reflection, and enduring questions.

RESPONSE:
Client is a [AGE]-year-old [RACE], [GENDER] with a history of [SUBSTANCES / PRESENTING CONCERNS]. Client [DID / DID NOT] report current medical issues and reported [LEGAL STATUS]. Client [HAS / DOES NOT HAVE] children; if applicable, [CUSTODY / CAREGIVER ARRANGEMENT].

Client reported [EMPLOYMENT / ID / VOCATIONAL STATUS]. Client's long-term goals after completing the program include [GOALS]. Client identified strengths as [STRENGTHS] and identified [WEAKNESS / BARRIER]. Client presents [MOTIVATION / AFFECT / ENGAGEMENT].

Client stated, "[VERBATIM DISCHARGE / MOTIVATION QUOTE]"

MEDICAL:
Client will stabilize on all medications as prescribed and comply with physician's orders. No intervention needed at this time.

PLAN:
CM will continue to meet with the client on a weekly basis to solidify a discharge treatment plan. Client's tentative step-down / discharge date: [DATE].

[CM NAME], Case Manager [CM CREDENTIALS] [CM LICENSE #]
Date: [TODAY]`,
  },
  {
    id: 'progress-note',
    label: 'Weekly CM Note',
    mode: 'note',
    category: 'clinical',
    noteType: 'Progress',
    noteKind: 'progress_note',
    bestFor: 'Ongoing weekly notes after week 1 - discharge planning and progress tracking.',
    body: `GOAL:
To discuss and plan a comprehensive discharge from treatment. Identify any needs for transition including sober living, aftercare, and financial stability.

INTERVENTION:
CM validated client's feelings and addressed concerns.
CM addressed immediate needs.
CM assessed for financial stability.
CM inquired about legal issues and FMLA.
CM inquired about discharge planning.
CM asked about 12-step / sponsor involvement.
CM continued to encourage client to engage in groups and 1:1 sessions with TH and CM.
CM used open-ended questions, positive affirmations, motivational interviewing, reflection, and enduring questions.

RESPONSE:
CM and client discussed aftercare plans, which is an ongoing conversation.
Client stated, "[VERBATIM CLIENT QUOTE THIS WEEK]"
CM and client will continue making progress toward discharge plans and treatment plan goals.

MEDICAL:
Client will stabilize on all medications as prescribed and comply with physician's orders. No intervention needed at this time.

PLAN:
CM will continue to meet with the client on a weekly basis to solidify a discharge treatment plan. Client's tentative step-down / discharge date: [DATE].

[CM NAME], Case Manager [CM CREDENTIALS] [CM LICENSE #]
Date: [TODAY]`,
  },
  {
    id: 'treatment-plan-review',
    label: 'Treatment Plan Review',
    mode: 'document',
    category: 'planning',
    noteType: 'Treatment Plan',
    noteKind: 'treatment_plan',
    bestFor: 'Goal reviews, objective updates, and intervention planning.',
    body: `TREATMENT PLAN REVIEW

Level of Care: [ ] RTC  [ ] PHP  [ ] IOP  [ ] OP
Date of Review: [TODAY]
Case Manager: [CM NAME], Case Manager [CM CREDENTIALS] [CM LICENSE #]
Date Assigned: [ADMIT DATE]
Projected Length of Stay: 30-45 days

Client Strengths:
CT stated, "[CLIENT QUOTE — strengths]"

Client Weaknesses:
CT stated, "[CLIENT QUOTE — weaknesses]"

I am here because:
CT stated, "[CLIENT QUOTE — motivation for treatment]"

My discharge plans are:
CT stated, "[CLIENT QUOTE — discharge goals]"

Problem 1: Discharge Planning

Problem 1: Goal
[LIST CLIENT'S THREE SPECIFIC IDENTIFIED NEEDS — e.g., "Maintain sobriety while developing coping skills to manage environmental triggers. Secure stable employment in the recovery field after obtaining ID and completing certification. Strengthen family stability by maintaining custody and consistent visitation."] CT stated, "[REPEAT 'I AM HERE BECAUSE' QUOTE]"

Problem 1: Objective
CM will meet with client weekly to discuss options for aftercare planning and explore high-risk situations and motivation for maintaining sobriety. CM will educate client on various sober support groups and the importance of building sober support networks.

Problem 1: Plan
Client to work on developing safe aftercare plans AEB reviewing sober support systems, exploring various sober support groups, reviewing potential outpatient programs, and procuring therapy and psychiatry referrals as appropriate.
- [BULLET 1 — specific to client situation, e.g., "Case Manager will assist client with ID application follow-up and provide transportation resources."]
- [BULLET 2 — e.g., "Case Manager will connect client with employment resources and training programs in recovery services."]
- [BULLET 3 — e.g., "Client will engage with therapy to address environmental triggers and build relapse prevention skills."]
- [BULLET 4 — e.g., "Client will explore 12-step or recovery support groups weekly to build community support."]

Problem 1: Frequency/Duration:
  RTC:  1x1x3 weeks RTC
  PHP/IOP:  1x1x4 weeks PHP/IOP

Problem 1: Target Date: [3-4 WEEKS FROM TODAY]
Problem 1: Status: open
Problem 1: Outcome: in progress
Problem 1: Comment: Initial Goal Developed

I acknowledge that I have participated in the development of my treatment plan, I have reviewed and received a copy of this Treatment Plan, and I agree to participate in this part of my treatment to the best of my ability.

I have read this report and: agree with its contents.`,
  },
  {
    id: 'group-note',
    label: 'Group Note',
    mode: 'note',
    category: 'clinical',
    noteType: 'Group',
    noteKind: 'group_note',
    bestFor: 'Attendance, participation, interventions, and client response in groups.',
    body: `Location of Client: [Sober Living / Home / Treatment Facility]. The client attended the group virtually via [Google Meet / Zoom / In-Person]. The client displayed active listening and self-awareness, AEB maintaining eye contact, nodding in agreement, and responding respectfully to others. The client participated in each group activity and offered insight into their emotional progress. The client stated, "[VERBATIM TOPIC-RELATED QUOTE]"`,
  },
  {
    id: 'discharge-summary',
    label: 'Discharge Summary',
    mode: 'document',
    category: 'planning',
    noteType: 'Discharge',
    noteKind: 'discharge_summary',
    bestFor: 'Transition planning, aftercare coordination, and discharge readiness.',
    body: `DISCHARGE SUMMARY

Date of Admission: [ADMIT DATE]
Date of Discharge: [DC DATE]
Reason for Discharge: Completed treatment
Initiated By: [☑] Mutual  [ ] Patient  [ ] Family  [ ] Clinical

NARRATIVE:
Client has successfully completed [#] days in Residential treatment and is transitioning to the outpatient facility of [NAME OF OP FACILITY]: [ADDRESS].

While in our care, client met weekly with their Case Manager and Therapist for individual sessions. Client was also seen by psychiatry and nursing to coordinate medical needs and monitor adjustment to medications. Client attended evidence-based group programming.

Client was able to gain insight into triggers for substance use and incorporate coping strategies such as physical and emotional self-care, building a sober support network, use of distraction and avoidance strategies, establishing and adhering to routine, and practicing vulnerability by avoiding isolation and communicating with others in order to decrease the chances of relapse. Client attained all treatment plan goals.

During the length of treatment, client made positive progress toward increasing self-care as evidenced by making and maintaining medical appointments, establishing a relapse prevention plan, coordinating a safe place of living, obtaining referrals for financial resources, and compiling a list of local ongoing 12-step meetings. Client continuously participated in self-assessment of triggers and cravings.

Case Manager and Therapist recommendations are for client to participate in an outpatient program, attend individual therapy, and continue in a 12-step recovery process to aid in sober social support and ongoing abstinence.

Aftercare Appointments & Recommendations: [SEE TABLE BELOW]
AA/NA/GA: Attend 90 meetings in 90 days, obtain sponsor, aftercare, obtain home group, get phone numbers, attend 12-step functions, develop a sober support system.
Return to Independent Residence: [FULL ADDRESS — do not leave blank or write only "home"]
Patient Diagnosis: [COPY FROM DX BOX]

Client took all personal belongings and all approved medications upon leaving the facility.`,
  },
  {
    id: 'referral-summary',
    label: 'Referral Summary',
    mode: 'document',
    category: 'planning',
    noteType: 'Referral',
    noteKind: 'referral_summary',
    bestFor: 'Warm handoffs, provider referrals, and service coordination.',
    body: `REFERRAL NEED:\nDescribe the presenting issue and why referral is needed.\n\nACTION TAKEN:\nList providers contacted, information given, and appointments arranged.\n\nCLIENT RESPONSE:\nDocument the client's agreement, concerns, and barriers.\n\nNEXT STEP:\nList follow-up tasks, deadlines, and verification steps.`,
  },
  {
    id: 'court-letter',
    label: 'Court / Probation Letter',
    mode: 'document',
    category: 'letters',
    noteType: 'Court',
    noteKind: 'referral_summary',
    bestFor: 'Attendance letters, treatment participation summaries, and status updates.',
    body: `DATE:\n\nTO WHOM IT MAY CONCERN:\n\nThis letter is to confirm that [Client Name] is engaged in services and receiving case management support.\n\nCURRENT STATUS:\nSummarize attendance, participation, treatment status, and relevant compliance information.\n\nCLINICALLY RELEVANT CONTEXT:\nDocument only what is appropriate to disclose.\n\nPlease contact our office with any questions.\n`,
  },
  {
    id: 'fmla-correspondence',
    label: 'FMLA Correspondence',
    mode: 'document',
    category: 'fmla',
    noteType: 'FMLA',
    noteKind: 'fmla_correspondence',
    bestFor: 'Employer, provider, and HR communication tracking.',
    body: `CONTACT METHOD:\n\nCONTACTED PARTY:\n\nSUMMARY:\nDescribe what was requested, provided, or clarified.\n\nOUTCOME:\nDocument what was confirmed or what remains pending.\n\nFOLLOW-UP:\nList due dates, missing items, and next outreach step.`,
  },
  {
    id: 'loc-transition',
    label: 'LOC Transition Note',
    mode: 'note',
    category: 'planning',
    noteType: 'Progress',
    noteKind: 'progress_note',
    bestFor: 'Level-of-care changes, handoffs, and step-down planning.',
    body: `CURRENT LOC:\n\nNEW LOC / TRANSITION PLAN:\n\nRATIONALE:\nDocument the reason for the transition and key clinical or case management considerations.\n\nCOORDINATION COMPLETED:\nList providers, transportation, housing, and follow-up supports arranged.\n\nNEXT STEP:\nDocument immediate follow-up and monitoring plan.`,
  },
]

const EMPTY_COMPOSER = {
  title: '',
  noteType: 'Progress',
  body: '',
  url: '',
  createdBy: 'Case Manager',
}

function DocumentationCenter() {
  const [mode, setMode] = useState('note')
  const [inputMode, setInputMode] = useState('type')
  const [selectedClient, setSelectedClient] = useState(null)
  const [templateFilter, setTemplateFilter] = useState('all')
  const [selectedTemplateId, setSelectedTemplateId] = useState(null)
  const [fileTemplates, setFileTemplates] = useState([])
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [composer, setComposer] = useState(EMPTY_COMPOSER)
  const [notes, setNotes] = useState([])
  const [docs, setDocs] = useState([])
  const [loadingNotes, setLoadingNotes] = useState(false)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [roughNotes, setRoughNotes] = useState('')
  const [generatingDraft, setGeneratingDraft] = useState(false)
  const [draftQuality, setDraftQuality] = useState(null)
  const [brandResources, setBrandResources] = useState([])
  const [loadingBrandResources, setLoadingBrandResources] = useState(false)
  const [uploadingBrandResource, setUploadingBrandResource] = useState(false)
  const [brandUpload, setBrandUpload] = useState({
    category: 'general',
    description: '',
    file: null,
  })

  const availableTemplates = useMemo(() => {
    const seen = new Set()
    return [...fileTemplates, ...FALLBACK_DOCUMENTATION_TEMPLATES].filter((template) => {
      if (!template?.id || seen.has(template.id)) return false
      seen.add(template.id)
      return true
    })
  }, [fileTemplates])

  const filteredTemplates = useMemo(
    () =>
      availableTemplates.filter((template) => {
        const categoryMatch = templateFilter === 'all' || template.category === templateFilter
        const searchMatch =
          !searchTerm ||
          template.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
          template.bestFor.toLowerCase().includes(searchTerm.toLowerCase())
        return categoryMatch && searchMatch
      }),
    [availableTemplates, searchTerm, templateFilter]
  )

  const selectedTemplate =
    availableTemplates.find((template) => template.id === selectedTemplateId) || null

  const recentItems = mode === 'note' ? notes : docs

  useEffect(() => {
    loadTemplates()
    loadDocs()
    loadBrandResources()
  }, [])

  useEffect(() => {
    if (selectedClient?.client_id) {
      loadNotes(selectedClient.client_id)
    } else {
      setNotes([])
    }
  }, [selectedClient?.client_id])

  useEffect(() => {
    if (selectedTemplate) {
      setMode(selectedTemplate.mode)
    }
  }, [selectedTemplate])

  const loadNotes = async (clientId) => {
    try {
      setLoadingNotes(true)
      const response = await apiFetch(`/api/case-management/notes/list/${clientId}`)
      if (!response.ok) throw new Error('Failed to load notes')
      const data = await response.json()
      setNotes(Array.isArray(data.notes) ? data.notes : [])
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load notes')
    } finally {
      setLoadingNotes(false)
    }
  }

  const loadDocs = async () => {
    try {
      setLoadingDocs(true)
      const response = await apiFetch('/api/dashboard/docs')
      if (!response.ok) throw new Error('Failed to load documents')
      const data = await response.json()
      setDocs(Array.isArray(data.docs) ? data.docs : [])
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load documents')
    } finally {
      setLoadingDocs(false)
    }
  }

  const loadTemplates = async () => {
    try {
      setLoadingTemplates(true)
      const response = await apiFetch('/api/ai-documentation/templates')
      if (!response.ok) throw new Error('Failed to load templates')
      const data = await response.json()
      setFileTemplates(Array.isArray(data.templates) ? data.templates : [])
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load templates')
      setFileTemplates([])
    } finally {
      setLoadingTemplates(false)
    }
  }

  const loadBrandResources = async () => {
    try {
      setLoadingBrandResources(true)
      const response = await apiFetch('/api/ai-documentation/brand-resources')
      if (!response.ok) throw new Error('Failed to load company guidance library')
      const data = await response.json()
      setBrandResources(Array.isArray(data.resources) ? data.resources : [])
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to load company guidance library')
    } finally {
      setLoadingBrandResources(false)
    }
  }

  const resetComposer = () => {
    setEditingItem(null)
    setRoughNotes('')
    setInputMode('type')
    setDraftQuality(null)
    setComposer({
      ...EMPTY_COMPOSER,
      noteType: selectedTemplate?.noteType || 'Progress',
      title: '',
      body: '',
    })
  }

  const buildClientLabel = () =>
    selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : ''

  const insertTranscriptIntoBrief = (transcript) => {
    setRoughNotes(transcript)
    setInputMode('type')
  }

  const applyGeneratedTranscriptNote = (draft, transcript) => {
    const clientLabel = buildClientLabel()
    setMode('note')
    setComposer((prev) => ({
      ...prev,
      title: prev.title && prev.title.trim() ? prev.title : `Dictated CM Note${clientLabel ? ` - ${clientLabel}` : ''}`,
      noteType: 'Progress',
      body: draft,
    }))
    setDraftQuality(null)
    if (!roughNotes.trim()) {
      setRoughNotes(transcript)
    }
  }

  const generateDraftFromTranscriptForTemplate = async (transcript) => {
    if (!selectedTemplate) {
      throw new Error('Select a template first')
    }

    if (mode === 'note' && !selectedClient?.client_id) {
      throw new Error('Select a client before generating a client note')
    }

    const clientLabel = buildClientLabel()
    const applyDraftToComposer = (draft) => {
      setComposer((prev) => ({
        ...prev,
        title:
          prev.title && prev.title.trim()
            ? prev.title
            : `${selectedTemplate.label}${clientLabel ? ` - ${clientLabel}` : ''}`,
        noteType: selectedTemplate.noteType,
        body: draft || transcript,
      }))
      setRoughNotes(transcript)
    }

    try {
      const response = await apiFetch('/api/ai-documentation/note-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module: 'documentation_center_voice',
          note_kind: selectedTemplate.noteKind,
          client_id: selectedClient?.client_id || undefined,
          client_name: selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : undefined,
          user_prompt: transcript,
          current_text: selectedTemplate.body,
          context: {
            template_label: selectedTemplate.label,
            template_category: selectedTemplate.category,
            observations: `Template: ${selectedTemplate.label}. Mode: ${mode}. Source: dictated transcript.`,
            next_steps: '',
            direct_quotes: [],
          },
        }),
      })

      const data = await response.json().catch(() => ({}))
      if (response.ok && data.draft) {
        setDraftQuality(data.quality_review || data.compliance_preview?.quality_review || null)
        applyDraftToComposer(data.draft)
        return
      }

      if (!selectedClient?.client_id) {
        setDraftQuality(null)
        applyDraftToComposer(transcript)
        toast.error(data.detail || 'Template draft failed. Loaded transcript for manual review.')
        return
      }
    } catch (error) {
      if (!selectedClient?.client_id) {
        setDraftQuality(null)
        applyDraftToComposer(transcript)
        toast.error('Template draft failed. Loaded transcript for manual review.')
        return
      }
    }

    const fallbackResponse = await apiFetch('/api/notes/generate-from-transcript', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        clientId: selectedClient.client_id,
        noteType: 'cm_note',
        transcript,
      }),
    })

    const fallbackData = await fallbackResponse.json().catch(() => ({}))
    if (!fallbackResponse.ok) {
      applyDraftToComposer(transcript)
      throw new Error(fallbackData.detail || 'Failed to generate draft from transcript')
    }

    applyDraftToComposer(fallbackData.draft || transcript)
    setDraftQuality(null)
  }

  const applyTemplate = (template) => {
    const clientLabel = selectedClient ? ` - ${selectedClient.first_name} ${selectedClient.last_name}` : ''
    setSelectedTemplateId(template.id)
    setMode(template.mode)
    setInputMode('type')
    setEditingItem(null)
    setRoughNotes('')
    setDraftQuality(null)
    setComposer((prev) => ({
      ...prev,
      title: prev.title && prev.title.trim() ? prev.title : `${template.label}${clientLabel}`,
      noteType: template.noteType,
      body: '',
      url: prev.url || '',
    }))
  }

  const clearSelectedTemplate = () => {
    setSelectedTemplateId(null)
    setMode('note')
    setInputMode('type')
    setEditingItem(null)
    setRoughNotes('')
    setDraftQuality(null)
    setComposer({
      ...EMPTY_COMPOSER,
      title: '',
      body: '',
    })
  }

  const generateDraftFromBrief = async () => {
    if (!selectedTemplate) {
      toast.error('Select a template first')
      return
    }

    if (!roughNotes.trim()) {
      toast.error('Type rough notes in the case manager brief first')
      return
    }

    if (mode === 'note' && !selectedClient?.client_id) {
      toast.error('Select a client before generating a client note')
      return
    }

    try {
      setGeneratingDraft(true)
      const response = await apiFetch('/api/ai-documentation/note-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module: 'documentation_center',
          note_kind: selectedTemplate.noteKind,
          client_id: selectedClient?.client_id || undefined,
          client_name: selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : undefined,
          user_prompt: roughNotes,
          current_text: selectedTemplate.body,
          context: {
            template_label: selectedTemplate.label,
            template_category: selectedTemplate.category,
            observations: `Template: ${selectedTemplate.label}. Mode: ${mode}.`,
            next_steps: '',
            direct_quotes: [],
          },
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate draft')
      }

      const data = await response.json()
      setDraftQuality(data.quality_review || data.compliance_preview?.quality_review || null)
      setComposer((prev) => ({
        ...prev,
        title:
          prev.title && prev.title.trim()
            ? prev.title
            : `${selectedTemplate.label}${selectedClient ? ` - ${selectedClient.first_name} ${selectedClient.last_name}` : ''}`,
        noteType: selectedTemplate.noteType,
        body: data.draft || '',
      }))
      toast.success('Draft generated from your rough notes')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to generate draft')
    } finally {
      setGeneratingDraft(false)
    }
  }

  const saveCurrentItem = async () => {
    if (!composer.title.trim() || !composer.body.trim()) {
      toast.error('Title and body are required')
      return
    }

    if (mode === 'note' && !selectedClient?.client_id) {
      toast.error('Select a client before saving a note')
      return
    }

    try {
      setSaving(true)
      if (mode === 'note') {
        const endpoint = editingItem?.source === 'note'
          ? `/api/case-management/notes/update/${editingItem.note_id}`
          : `/api/case-management/notes/add/${selectedClient.client_id}`

        const response = await apiFetch(endpoint, {
          method: editingItem?.source === 'note' ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: composer.title,
            note_type: composer.noteType,
            content: composer.body,
            created_by: composer.createdBy,
          }),
        })

        if (!response.ok) {
          throw new Error('Failed to save note')
        }
        await loadNotes(selectedClient.client_id)
        toast.success(editingItem?.source === 'note' ? 'Note updated' : 'Note saved')
      } else {
        const endpoint = editingItem?.source === 'doc'
          ? `/api/dashboard/docs/${editingItem.id}`
          : '/api/dashboard/docs'
        const response = await apiFetch(endpoint, {
          method: editingItem?.source === 'doc' ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: composer.title,
            content: composer.body,
            url: composer.url || null,
          }),
        })
        if (!response.ok) {
          throw new Error('Failed to save document')
        }
        await loadDocs()
        toast.success(editingItem?.source === 'doc' ? 'Document updated' : 'Document saved')
      }

      resetComposer()
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const loadItemIntoEditor = (item, source) => {
    setEditingItem({ ...item, source })
    setDraftQuality(null)
    if (source === 'note') {
      setMode('note')
      setRoughNotes('')
      setComposer({
        title: item.title || '',
        noteType: item.note_type || 'Progress',
        body: item.content || '',
        url: '',
        createdBy: item.created_by || 'Case Manager',
      })
    } else {
      setMode('document')
      setRoughNotes('')
      setComposer({
        title: item.title || '',
        noteType: 'Document',
        body: item.content || '',
        url: item.url || '',
        createdBy: 'Case Manager',
      })
    }
  }

  const deleteItem = async (item, source) => {
    try {
      const endpoint =
        source === 'note'
          ? `/api/case-management/notes/${item.note_id}`
          : `/api/dashboard/docs/${item.id}`
      const response = await apiFetch(endpoint, { method: 'DELETE' })
      if (!response.ok) throw new Error(`Failed to delete ${source}`)

      if (source === 'note' && selectedClient?.client_id) {
        await loadNotes(selectedClient.client_id)
      } else if (source === 'doc') {
        await loadDocs()
      }

      if (
        editingItem &&
        ((source === 'note' && editingItem.note_id === item.note_id) ||
          (source === 'doc' && editingItem.id === item.id))
      ) {
        resetComposer()
      }

      toast.success(source === 'note' ? 'Note deleted' : 'Document deleted')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to delete item')
    }
  }

  const downloadDocument = async (item) => {
    try {
      const response = await apiFetch(`/api/dashboard/docs/${item.id}/download?format=pdf`)
      if (!response.ok) throw new Error('Failed to download document')

      const blob = await response.blob()
      const disposition = response.headers.get('content-disposition') || ''
      const filenameMatch = disposition.match(/filename="([^"]+)"/i)
      const fallbackName = `${(item.title || 'document').replace(/[^a-z0-9._-]+/gi, '_')}.pdf`
      const filename = filenameMatch?.[1] || fallbackName
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success('Document download started')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to download document')
    }
  }

  const uploadBrandResource = async () => {
    if (!brandUpload.file) {
      toast.error('Choose a file to upload')
      return
    }

    try {
      setUploadingBrandResource(true)
      const formData = new FormData()
      formData.append('file', brandUpload.file)
      formData.append('category', brandUpload.category)
      formData.append('description', brandUpload.description)

      const response = await apiFetch('/api/ai-documentation/brand-resources/upload', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        throw new Error('Failed to upload company guidance file')
      }
      await loadBrandResources()
      setBrandUpload({
        category: 'general',
        description: '',
        file: null,
      })
      toast.success('Company guidance uploaded')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to upload company guidance file')
    } finally {
      setUploadingBrandResource(false)
    }
  }

  const deleteBrandResource = async (resourceId) => {
    try {
      const response = await apiFetch(`/api/ai-documentation/brand-resources/${resourceId}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error('Failed to delete company guidance file')
      }
      await loadBrandResources()
      toast.success('Company guidance deleted')
    } catch (error) {
      console.error(error)
      toast.error(error.message || 'Failed to delete company guidance file')
    }
  }

  const documentationContext = {
    observations: `Template: ${selectedTemplate?.label || 'No template selected'}. Mode: ${mode}.`,
    next_steps: '',
    direct_quotes: [],
  }

  const hasDraft = composer.body.trim().length > 0
  const shouldShowDraftSummary = Boolean(selectedTemplate || selectedClient)

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 right-12 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute top-1/3 -left-24 h-64 w-64 rounded-full bg-fuchsia-500/10 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl space-y-6 px-3 py-6 sm:space-y-8 sm:px-6 sm:py-8">
        <section className="rounded-[20px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-4 shadow-2xl shadow-purple-500/10 backdrop-blur-xl sm:rounded-[28px] sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-200">
                <Sparkles className="h-4 w-4" />
                Documentation Center
              </div>
              <h1 className="text-2xl font-bold text-white sm:text-4xl">Notes and Documents Command Center</h1>
              <p className="mt-3 max-w-2xl text-lg text-slate-300">
                One professional workspace for progress notes, treatment plans, discharge summaries, referral packets, court letters, FMLA documentation, and file-backed templates.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard icon={ClipboardList} label="Templates" value={String(availableTemplates.length)} accent="from-cyan-500 to-blue-500" />
              <StatCard icon={FileText} label="Client Notes" value={String(notes.length)} accent="from-blue-500 to-indigo-500" />
              <StatCard icon={FolderOpen} label="Documents" value={String(docs.length)} accent="from-fuchsia-500 to-purple-500" />
              <StatCard icon={User} label="Client Linked" value={selectedClient ? 'Yes' : 'No'} accent="from-emerald-500 to-teal-500" />
            </div>
          </div>
        </section>

        {!selectedTemplate ? (
          <section className="rounded-[20px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-4 shadow-2xl shadow-purple-500/10 backdrop-blur-xl sm:rounded-[28px] sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-xl font-bold text-white sm:text-2xl">Template Gallery</h2>
                <p className="mt-1 text-sm text-slate-300">Choose a structured starting point, then edit and save it as a real client note or formal document.</p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search templates"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/40 py-3 pl-10 pr-4 text-sm text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none sm:w-60"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {TEMPLATE_CATEGORIES.map((category) => (
                    <button
                      key={category}
                      onClick={() => setTemplateFilter(category)}
                      className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                        templateFilter === category
                          ? 'bg-white text-slate-900'
                          : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                      }`}
                    >
                      {category === 'all' ? 'All' : category.charAt(0).toUpperCase() + category.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              {loadingTemplates && (
                <div className="md:col-span-2 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-100">
                  Loading file-based templates from the templates folder...
                </div>
              )}
              {filteredTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => applyTemplate(template)}
                  className="group rounded-2xl border border-white/10 bg-slate-950/30 p-5 text-left transition-all duration-300 hover:-translate-y-1 hover:border-white/20 hover:shadow-xl"
                >
                  <div className="flex items-start justify-between gap-2 sm:gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          template.mode === 'note' ? 'bg-blue-500/20 text-blue-200' : 'bg-fuchsia-500/20 text-fuchsia-200'
                        }`}>
                          {template.mode === 'note' ? 'Client Note' : 'Document'}
                        </span>
                        <span className="text-xs uppercase tracking-widest text-slate-400">{template.category}</span>
                        {template.source === 'file' && (
                          <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-cyan-200">
                            File template
                          </span>
                        )}
                      </div>
                      <h3 className="mt-2 text-base font-semibold leading-snug text-white sm:text-xl">{template.label}</h3>
                      <p className="mt-1.5 text-sm leading-5 text-slate-300">{template.bestFor}</p>
                      {template.relativePath && <p className="mt-1.5 truncate text-xs text-slate-500">{template.relativePath}</p>}
                    </div>
                    <div className="flex-shrink-0 rounded-xl bg-white/10 p-2.5 text-slate-200 sm:p-3">
                      {template.mode === 'note' ? <PenSquare className="h-4 w-4 sm:h-5 sm:w-5" /> : <ScrollText className="h-4 w-4 sm:h-5 sm:w-5" />}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        ) : (
          <SelectedTemplateBadge template={selectedTemplate} onClear={clearSelectedTemplate} />
        )}

        <section className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Writer</h2>
              <p className="mt-1 text-sm text-slate-300">Draft, refine, and save without leaving the suite.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setMode('note')}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  mode === 'note' ? 'bg-blue-500 text-white' : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                }`}
              >
                Client Notes
              </button>
              <button
                onClick={() => setMode('document')}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  mode === 'document' ? 'bg-fuchsia-500 text-white' : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                }`}
              >
                Documents
              </button>
              <button
                onClick={resetComposer}
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
              >
                <Plus className="h-4 w-4" />
                New Draft
              </button>
            </div>
          </div>

          <div className="mt-6 space-y-6">
            <div className="rounded-[24px] border border-cyan-400/20 bg-cyan-500/10 p-5">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-cyan-500/20 p-3 text-cyan-200">
                  <Wand2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Start here</h3>
                  <p className="mt-1 text-sm text-slate-300">
                    Pick a template, choose how you want to work, then generate and edit the final draft in one place.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setInputMode('type')}
                className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                  inputMode === 'type' ? 'bg-white text-slate-900' : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                }`}
              >
                Type
              </button>
              <button
                onClick={() => setInputMode('dictate')}
                className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                  inputMode === 'dictate' ? 'bg-white text-slate-900' : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                }`}
              >
                Dictate
              </button>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">Linked Client</label>
              <ClientSelector
                selectedClientId={selectedClient?.client_id || null}
                onClientSelect={setSelectedClient}
                placeholder={mode === 'note' ? 'Select a client for this note' : 'Optional client context'}
                className="max-w-xl"
              />
            </div>

            {inputMode === 'type' ? (
              <div className="rounded-[24px] border border-cyan-400/20 bg-slate-950/35 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Case manager brief</h3>
                    <p className="mt-1 text-sm text-slate-400">
                      This is the main input. If you want AI to turn freehand notes into a treatment plan or note, type them here.
                    </p>
                  </div>
                  <button
                    onClick={generateDraftFromBrief}
                    disabled={generatingDraft || !selectedTemplate}
                    className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:from-cyan-400 hover:to-blue-400 disabled:opacity-60"
                  >
                    {generatingDraft ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    Generate Draft
                  </button>
                </div>

                <textarea
                  value={roughNotes}
                  onChange={(e) => setRoughNotes(e.target.value)}
                  rows={8}
                  placeholder={selectedTemplate ? `Example: Write a ${selectedTemplate.label.toLowerCase()} for CT Johnson. 34, needs dental work, on probation, needs to stay in contact with PO, wants to relocate to LA, work in treatment, strengths are hardworking, barrier is relationship triggers, quote: "I need to take control of my life."` : 'Select a template, then type your rough notes here.'}
                  className="mt-4 w-full rounded-[24px] border border-white/10 bg-slate-950/50 px-5 py-4 text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                />

                <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Use bullets or fragments</span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Include direct quotes if you have them</span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">The popup AI chat is not required for this workflow</span>
                </div>
              </div>
            ) : (
              <VoiceNoteRecorder
                clientId={selectedClient?.client_id || ''}
                noteType="cm_note"
                insertLabel="Use Transcript in Brief"
                onInsertTranscript={insertTranscriptIntoBrief}
                onGenerateNote={applyGeneratedTranscriptNote}
                onGenerateRequested={generateDraftFromTranscriptForTemplate}
              />
            )}

            <div className="border-t border-white/10 pt-6" />

            <div className="grid gap-4 md:grid-cols-[1.4fr_0.9fr]">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">Title</label>
                <input
                  value={composer.title}
                  onChange={(e) => setComposer((prev) => ({ ...prev, title: e.target.value }))}
                  placeholder="Enter a strong document title"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">Type</label>
                <select
                  value={composer.noteType}
                  onChange={(e) => setComposer((prev) => ({ ...prev, noteType: e.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white focus:border-cyan-400 focus:outline-none"
                >
                  {['Progress', 'Assessment', 'General', 'Group', 'Treatment Plan', 'Court', 'Housing', 'Employment', 'Benefits', 'Legal', 'Discharge', 'Referral', 'FMLA'].map((item) => (
                    <option key={item} value={item} className="bg-slate-900">
                      {item}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {mode === 'document' && (
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">Reference URL</label>
                <input
                  value={composer.url}
                  onChange={(e) => setComposer((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder="Optional supporting link or source"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
            )}

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label className="block text-sm font-medium text-slate-300">Final draft</label>
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-400">
                  <ArrowRight className="h-3.5 w-3.5" />
                  Generate from the active input mode, then edit here
                </div>
              </div>
              <textarea
                value={composer.body}
                onChange={(e) => setComposer((prev) => ({ ...prev, body: e.target.value }))}
                rows={18}
                placeholder="Your generated or hand-written final draft appears here."
                className="w-full rounded-[24px] border border-white/10 bg-slate-950/50 px-5 py-4 text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={saveCurrentItem}
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:from-cyan-400 hover:to-blue-400 disabled:opacity-60"
              >
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {editingItem ? 'Update' : 'Save'} {mode === 'note' ? 'Note' : 'Document'}
              </button>
              {editingItem && (
                <button
                  onClick={resetComposer}
                  className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-slate-200 transition hover:bg-white/10"
                >
                  <Plus className="h-4 w-4" />
                  New Draft
                </button>
              )}
            </div>

            {shouldShowDraftSummary && (
              <p className="text-xs text-slate-400">
                {selectedTemplate ? `Template: ${selectedTemplate.label}` : ''}
                {selectedTemplate ? ` ? Saving to: ${mode === 'note' ? 'Client note record' : 'Document library'}` : ''}
                {selectedClient ? ` ? Client: ${selectedClient.first_name} ${selectedClient.last_name}` : ''}
              </p>
            )}

            {draftQuality && <DraftQualityCard quality={draftQuality} />}

            {hasDraft && (
              <div className="space-y-5 border-t border-white/10 pt-6">
                <p className="text-sm font-medium text-slate-400">Draft review tools</p>
                <DocumentationAssistPanel
                  module="documentation_center"
                  noteKind={selectedTemplate?.noteKind || 'progress_note'}
                  clientId={selectedClient?.client_id || ''}
                  clientName={selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : ''}
                  currentText={composer.body}
                  context={documentationContext}
                  onApplyDraft={(draft) => setComposer((prev) => ({ ...prev, body: draft }))}
                />
              </div>
            )}
          </div>
        </section>

        <div className="px-2">
          <a href="/settings/guidance" className="text-sm text-slate-400 transition hover:text-slate-200">
            ? Manage AI style guides and company guidance ?
          </a>
        </div>

        <section className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-white">{mode === 'note' ? 'Saved Notes' : 'Saved Documents'}</h2>
              <p className="mt-1 text-sm text-slate-300">
                {mode === 'note'
                  ? selectedClient
                    ? `Showing client-linked notes for ${selectedClient.first_name} ${selectedClient.last_name}.`
                    : 'Select a client to review and edit saved notes.'
                  : 'Recent documents from the suite library.'}
              </p>
            </div>
            <button
              onClick={() => (mode === 'note' && selectedClient?.client_id ? loadNotes(selectedClient.client_id) : loadDocs())}
              className="rounded-xl border border-white/10 bg-white/5 p-3 text-slate-200 transition hover:bg-white/10"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-6 space-y-3">
            {mode === 'note' && !selectedClient ? (
              <EmptyState
                icon={User}
                title="Select a client first"
                body="Client notes stay tied to one case record. Choose a client to open the note library."
              />
            ) : loadingNotes || loadingDocs ? (
              <div className="py-10 text-center text-slate-400">Loading saved items...</div>
            ) : recentItems.length === 0 ? (
              <EmptyState
                icon={mode === 'note' ? FileText : FolderOpen}
                title={mode === 'note' ? 'No notes saved yet' : 'No documents saved yet'}
                body="Use the template gallery and writer to create the first item."
              />
            ) : (
              recentItems.map((item) => (
                <div key={item.note_id || item.id} className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">{item.title || item.note_type || 'Untitled'}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">{mode === 'note' ? item.note_type || 'note' : 'document'}</p>
                    </div>
                    <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-slate-300">{mode === 'note' ? 'Note' : 'Doc'}</span>
                  </div>
                  <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-300">{item.content || 'No content'}</p>
                  <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-400">
                    <span>{formatSavedDate(item.updated_at || item.created_at)}</span>
                    <div className="flex items-center gap-2">
                      {mode === 'document' && (
                        <button
                          onClick={() => downloadDocument(item)}
                          className="inline-flex items-center gap-1 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-emerald-100 transition hover:bg-emerald-500/20"
                        >
                          <Download className="h-3.5 w-3.5" />
                          Download PDF
                        </button>
                      )}
                      <button
                        onClick={() => loadItemIntoEditor(item, mode === 'note' ? 'note' : 'doc')}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-slate-200 transition hover:bg-white/10"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => deleteItem(item, mode === 'note' ? 'note' : 'doc')}
                        className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-red-200 transition hover:bg-red-500/20"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

const StatCard = ({ icon: Icon, label, value, accent }) => (
  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
        <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      </div>
      <div className={`rounded-xl bg-gradient-to-r ${accent} p-3 text-white shadow-lg`}>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  </div>
)

const SelectedTemplateBadge = ({ template, onClear }) => (
  <section className="rounded-[20px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-4 shadow-2xl shadow-purple-500/10 backdrop-blur-xl sm:rounded-[28px] sm:p-5">
    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 text-sm text-slate-200">
        <span className="rounded-full bg-white/10 px-3 py-1 font-semibold text-white">{template.label}</span>
        <span className="rounded-full bg-white/10 px-3 py-1">{template.mode === 'note' ? 'Client Note' : 'Document'}</span>
        <span className="rounded-full bg-white/10 px-3 py-1">{template.noteType}</span>
        <span className="rounded-full bg-white/10 px-3 py-1 capitalize">{template.category}</span>
      </div>
      <button
        onClick={onClear}
        className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
      >
        Change template ×
      </button>
    </div>
  </section>
)

const DraftQualityCard = ({ quality }) => {
  const warnings = [
    ...(quality.warnings || []),
    ...(quality.data_warnings || []),
  ].filter(Boolean)
  const uniqueWarnings = [...new Set(warnings)]
  const unresolvedPlaceholders = quality.unresolved_placeholders || []
  const isPass = quality.status === 'pass'

  return (
    <section className={`rounded-[24px] border p-5 ${
      isPass
        ? 'border-emerald-400/25 bg-emerald-500/10'
        : 'border-amber-400/30 bg-amber-500/10'
    }`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className={`rounded-2xl p-3 ${isPass ? 'bg-emerald-400/15 text-emerald-100' : 'bg-amber-400/15 text-amber-100'}`}>
            {isPass ? <CheckCircle2 className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Draft Quality Guardrails</h3>
            <p className="mt-1 text-sm text-slate-300">
              {isPass
                ? 'Template structure passed the automated review.'
                : 'Review these items before saving or sending this document.'}
            </p>
          </div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/35 px-4 py-3 text-right">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Quality Score</p>
          <p className="mt-1 text-2xl font-bold text-white">{quality.score ?? 'N/A'}</p>
        </div>
      </div>

      {uniqueWarnings.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm text-amber-100">
          {uniqueWarnings.map((warning) => (
            <li key={warning}>- {warning}</li>
          ))}
        </ul>
      )}

      {unresolvedPlaceholders.length > 0 && (
        <p className="mt-4 text-xs text-slate-300">
          Unresolved placeholders: {unresolvedPlaceholders.join(', ')}
        </p>
      )}
    </section>
  )
}

const EmptyState = ({ icon: Icon, title, body }) => (
  <div className="rounded-2xl border border-dashed border-white/10 bg-slate-950/20 p-8 text-center">
    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-slate-300">
      <Icon className="h-5 w-5" />
    </div>
    <h3 className="text-lg font-semibold text-white">{title}</h3>
    <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
  </div>
)

const formatSavedDate = (value) => {
  if (!value) return 'No timestamp'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export default DocumentationCenter
