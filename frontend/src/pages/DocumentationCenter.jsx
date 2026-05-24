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
  ScrollText,
  Filter,
  Clock,
  Wand2,
  ArrowRight,
} from 'lucide-react'
import toast from 'react-hot-toast'

import ClientSelector from '../components/ClientSelector'
import DocumentationAssistPanel from '../components/DocumentationAssistPanel'
import { apiFetch } from '../api/config'

const TEMPLATE_CATEGORIES = ['all', 'clinical', 'planning', 'letters', 'fmla']

const DOCUMENTATION_TEMPLATES = [
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
  const [selectedClient, setSelectedClient] = useState(null)
  const [templateFilter, setTemplateFilter] = useState('all')
  const [selectedTemplateId, setSelectedTemplateId] = useState('progress-note')
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

  const filteredTemplates = useMemo(
    () =>
      DOCUMENTATION_TEMPLATES.filter((template) => {
        const categoryMatch = templateFilter === 'all' || template.category === templateFilter
        const searchMatch =
          !searchTerm ||
          template.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
          template.bestFor.toLowerCase().includes(searchTerm.toLowerCase())
        return categoryMatch && searchMatch
      }),
    [searchTerm, templateFilter]
  )

  const selectedTemplate =
    DOCUMENTATION_TEMPLATES.find((template) => template.id === selectedTemplateId) ||
    DOCUMENTATION_TEMPLATES[0]

  const recentItems = mode === 'note' ? notes : docs

  useEffect(() => {
    loadDocs()
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

  const resetComposer = () => {
    setEditingItem(null)
    setRoughNotes('')
    setComposer({
      ...EMPTY_COMPOSER,
      noteType: selectedTemplate?.noteType || 'Progress',
      title: '',
      body: '',
    })
  }

  const applyTemplate = (template) => {
    const clientLabel = selectedClient ? ` - ${selectedClient.first_name} ${selectedClient.last_name}` : ''
    setSelectedTemplateId(template.id)
    setMode(template.mode)
    setEditingItem(null)
    setRoughNotes('')
    setComposer((prev) => ({
      ...prev,
      title: prev.title && prev.title.trim() ? prev.title : `${template.label}${clientLabel}`,
      noteType: template.noteType,
      body: '',
      url: prev.url || '',
    }))
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

  const documentationContext = {
    observations: `Template: ${selectedTemplate.label}. Mode: ${mode}.`,
    next_steps: '',
    direct_quotes: [],
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 right-12 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute top-1/3 -left-24 h-64 w-64 rounded-full bg-fuchsia-500/10 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8 space-y-8">
        <section className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-8 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-200">
                <Sparkles className="h-4 w-4" />
                Documentation Center
              </div>
              <h1 className="text-4xl font-bold text-white">Notes and Documents Command Center</h1>
              <p className="mt-3 max-w-2xl text-lg text-slate-300">
                One professional workspace for progress notes, treatment plans, discharge summaries, referral packets, court letters, and FMLA documentation.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard icon={ClipboardList} label="Templates" value={String(DOCUMENTATION_TEMPLATES.length)} accent="from-cyan-500 to-blue-500" />
              <StatCard icon={FileText} label="Client Notes" value={String(notes.length)} accent="from-blue-500 to-indigo-500" />
              <StatCard icon={FolderOpen} label="Documents" value={String(docs.length)} accent="from-fuchsia-500 to-purple-500" />
              <StatCard icon={User} label="Client Linked" value={selectedClient ? 'Yes' : 'No'} accent="from-emerald-500 to-teal-500" />
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-8 xl:grid-cols-[1.45fr_0.95fr]">
          <div className="space-y-8">
            <div className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-white">Template Gallery</h2>
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
                {filteredTemplates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => applyTemplate(template)}
                    className={`group rounded-2xl border p-5 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${
                      selectedTemplateId === template.id
                        ? 'border-cyan-400/60 bg-gradient-to-br from-cyan-500/20 to-blue-500/10 shadow-cyan-500/20'
                        : 'border-white/10 bg-slate-950/30 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            template.mode === 'note'
                              ? 'bg-blue-500/20 text-blue-200'
                              : 'bg-fuchsia-500/20 text-fuchsia-200'
                          }`}>
                            {template.mode === 'note' ? 'Client Note' : 'Document'}
                          </span>
                          <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{template.category}</span>
                        </div>
                        <h3 className="mt-3 text-xl font-semibold text-white">{template.label}</h3>
                        <p className="mt-2 text-sm leading-6 text-slate-300">{template.bestFor}</p>
                      </div>
                      <div className="rounded-xl bg-white/10 p-3 text-slate-200">
                        {template.mode === 'note' ? <PenSquare className="h-5 w-5" /> : <ScrollText className="h-5 w-5" />}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-white">Writer</h2>
                  <p className="mt-1 text-sm text-slate-300">Draft, refine, and save without leaving the suite.</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => setMode('note')}
                    className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                      mode === 'note'
                        ? 'bg-blue-500 text-white'
                        : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                    }`}
                  >
                    Client Notes
                  </button>
                  <button
                    onClick={() => setMode('document')}
                    className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                      mode === 'document'
                        ? 'bg-fuchsia-500 text-white'
                        : 'border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
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

              <div className="mt-6">
                <div className="space-y-5">
                  <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                    <div className="rounded-[24px] border border-cyan-400/20 bg-cyan-500/10 p-5">
                      <div className="flex items-start gap-3">
                        <div className="rounded-2xl bg-cyan-500/20 p-3 text-cyan-200">
                          <Wand2 className="h-5 w-5" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-white">Start here</h3>
                          <p className="mt-1 text-sm text-slate-300">
                            This page should work like a writing assistant, not a separate chat app. Type your rough notes once in the case manager brief, then generate the draft below.
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 text-sm text-slate-200 md:grid-cols-3">
                        <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                          <p className="font-semibold text-white">1. Pick template</p>
                          <p className="mt-1 text-slate-400">Choose treatment plan, weekly note, discharge, FMLA, or another template above.</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                          <p className="font-semibold text-white">2. Type rough notes</p>
                          <p className="mt-1 text-slate-400">Use bullets, fragments, quotes, or a quick request in plain language.</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
                          <p className="font-semibold text-white">3. Edit final draft</p>
                          <p className="mt-1 text-slate-400">The generated note appears in the final draft editor and stays fully editable before saving.</p>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-[24px] border border-white/10 bg-slate-950/35 p-5">
                      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Selected template</p>
                      <h3 className="mt-3 text-xl font-semibold text-white">{selectedTemplate.label}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{selectedTemplate.bestFor}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white">
                          {selectedTemplate.mode === 'note' ? 'Client note' : 'Document'}
                        </span>
                        <span className="rounded-full bg-cyan-500/15 px-3 py-1 text-xs font-semibold text-cyan-200">
                          {selectedTemplate.noteType}
                        </span>
                        <span className="rounded-full bg-fuchsia-500/15 px-3 py-1 text-xs font-semibold text-fuchsia-200">
                          {selectedTemplate.category}
                        </span>
                      </div>
                    </div>
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
                        disabled={generatingDraft}
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
                      placeholder={`Example: Write a ${selectedTemplate.label.toLowerCase()} for CT Johnson. 34, needs dental work, on probation, needs to stay in contact with PO, wants to relocate to LA, work in treatment, strengths are hardworking, barrier is relationship triggers, quote: "I need to take control of my life."`}
                      className="mt-4 w-full rounded-[24px] border border-white/10 bg-slate-950/50 px-5 py-4 text-white placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
                    />

                    <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Use bullets or fragments</span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Include direct quotes if you have them</span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">The popup AI chat is not required for this workflow</span>
                    </div>
                  </div>

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
                        Generate from the case manager brief, then edit here
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
                    <div className="text-sm text-slate-400">
                      {mode === 'note'
                        ? 'Client-linked notes save into the case note record.'
                        : 'Documents save into the suite document library.'}
                    </div>
                  </div>
                </div>

                <div className="space-y-5">
                  <div className="rounded-[24px] border border-white/10 bg-slate-950/35 p-5">
                    <h3 className="text-lg font-semibold text-white">Review and follow-up tools</h3>
                    <p className="mt-1 text-sm text-slate-400">
                      Use these after you already have a draft. They are for refinement, compliance checks, and follow-up task creation.
                    </p>
                  </div>

                  <DocumentationAssistPanel
                    module="documentation_center"
                    noteKind={selectedTemplate.noteKind}
                    clientId={selectedClient?.client_id || ''}
                    clientName={selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : ''}
                    currentText={composer.body}
                    context={documentationContext}
                    onApplyDraft={(draft) => setComposer((prev) => ({ ...prev, body: draft }))}
                  />

                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-white">Current Draft Context</h3>
                        <p className="text-sm text-slate-400">The active template and save target for this draft.</p>
                      </div>
                      <div className="rounded-xl bg-white/10 p-3">
                        <Clock className="h-5 w-5 text-slate-200" />
                      </div>
                    </div>
                    <dl className="mt-4 space-y-3 text-sm">
                      <InfoRow label="Template" value={selectedTemplate.label} />
                      <InfoRow label="Save target" value={mode === 'note' ? 'Client note record' : 'Document library'} />
                      <InfoRow label="Client" value={selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : 'Not linked'} />
                      <InfoRow label="Editor mode" value={editingItem ? 'Editing existing item' : 'New draft'} />
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <aside className="space-y-8">
            <div className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-2xl shadow-purple-500/10 backdrop-blur-xl">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {mode === 'note' ? 'Saved Notes' : 'Saved Documents'}
                  </h2>
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
                ) : (loadingNotes || loadingDocs) ? (
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
                          <p className="truncate text-sm font-semibold text-white">
                            {item.title || item.note_type || 'Untitled'}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-400">
                            {mode === 'note' ? item.note_type || 'note' : 'document'}
                          </p>
                        </div>
                        <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] text-slate-300">
                          {mode === 'note' ? 'Note' : 'Doc'}
                        </span>
                      </div>
                      <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-300">{item.content || 'No content'}</p>
                      <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-400">
                        <span>{formatSavedDate(item.updated_at || item.created_at)}</span>
                        <div className="flex items-center gap-2">
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
            </div>
          </aside>
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

const InfoRow = ({ label, value }) => (
  <div className="flex items-start justify-between gap-4 border-b border-white/5 pb-3 last:border-0 last:pb-0">
    <dt className="text-slate-400">{label}</dt>
    <dd className="max-w-[65%] text-right text-slate-200">{value}</dd>
  </div>
)

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
