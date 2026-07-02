import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Video,
  Calendar,
  Plus,
  Search,
  Sparkles,
  ExternalLink,
  Play,
  Filter,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  ListVideo,
  X,
  Check,
  Clock,
  MapPin,
  User,
  BarChart2,
  Package,
  RefreshCw,
  Edit3,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  topicsAPI,
  playlistsAPI,
  videosAPI,
  sessionsAPI,
  schedulesAPI,
  curriculumPacksAPI,
  reportsAPI,
  TOPIC_CATEGORIES,
  GROUP_TYPES,
  DAYS_OF_WEEK,
  RECURRENCE_OPTIONS,
  categoryColor,
  sourceLabel,
  sourceBadgeColor,
  youtubeEmbedUrl,
  youtubePlaylistEmbedUrl,
  fetchYoutubeThumbnail,
  formatDate,
} from '../utils/groups'

const TABS = ['Topics', 'Sessions', 'Video Library', 'Schedule', 'Curriculum Packs', 'Reports']

// ── YouTube thumbnail card ────────────────────────────────────────────────────

function YoutubeThumbnailCard({ url, title, onPlay, playlistEmbed = false }) {
  const [thumb, setThumb] = React.useState(null)
  const [loaded, setLoaded] = React.useState(false)

  React.useEffect(() => {
    if (!url) return
    fetchYoutubeThumbnail(url).then((t) => { setThumb(t); setLoaded(true) })
  }, [url])

  return (
    <button
      onClick={onPlay}
      className="w-full aspect-video rounded-lg overflow-hidden relative group hover:ring-2 hover:ring-purple-400/50 transition-all"
    >
      {loaded && thumb ? (
        <img src={thumb} alt={title} className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full bg-slate-700/50" />
      )}
      <div className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors flex items-center justify-center">
        <div className="w-12 h-12 rounded-full bg-red-600/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
          <Play className="h-5 w-5 text-white ml-0.5" />
        </div>
      </div>
      {playlistEmbed && (
        <div className="absolute bottom-2 right-2 text-xs bg-black/60 text-gray-300 px-1.5 py-0.5 rounded">
          Playlist
        </div>
      )}
    </button>
  )
}

// ── Small reusable pieces ─────────────────────────────────────────────────────

function Badge({ children, className = '' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${className}`}>
      {children}
    </span>
  )
}

function Card({ children, className = '', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-slate-800/60 border border-white/10 rounded-xl p-4 backdrop-blur-sm transition-all duration-200 ${onClick ? 'cursor-pointer hover:border-purple-400/40 hover:bg-slate-800/80 hover:shadow-lg hover:shadow-purple-500/10' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

function SectionHeader({ title, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {action}
    </div>
  )
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
    </div>
  )
}

function ErrorMsg({ message }) {
  return (
    <div className="flex items-center gap-2 text-red-400 py-8 justify-center">
      <AlertCircle className="h-5 w-5" />
      <span className="text-sm">{message}</span>
    </div>
  )
}

// ── Topic form modal ──────────────────────────────────────────────────────────

function TopicFormModal({ onClose, onSaved, initial = null }) {
  const [form, setForm] = useState({
    title: initial?.title || '',
    category: initial?.category || 'Addiction Education',
    description: initial?.description || '',
    key_points: initial?.key_points_json
      ? (Array.isArray(initial.key_points_json) ? initial.key_points_json.join('\n') : '')
      : '',
    discussion_questions: initial?.discussion_questions_json
      ? (Array.isArray(initial.discussion_questions_json) ? initial.discussion_questions_json.join('\n') : '')
      : '',
    activity: initial?.activity || '',
    writing_prompt: initial?.writing_prompt || '',
    facilitator_tips: initial?.facilitator_tips || '',
  })
  const [saving, setSaving] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return }
    setSaving(true)
    try {
      const payload = {
        title: form.title.trim(),
        category: form.category,
        description: form.description,
        key_points: form.key_points.split('\n').map((s) => s.trim()).filter(Boolean),
        discussion_questions: form.discussion_questions.split('\n').map((s) => s.trim()).filter(Boolean),
        activity: form.activity,
        writing_prompt: form.writing_prompt,
        facilitator_tips: form.facilitator_tips,
      }
      let saved
      if (initial?.topic_id) {
        saved = await topicsAPI.update(initial.topic_id, payload)
      } else {
        saved = await topicsAPI.create(payload)
      }
      toast.success(initial ? 'Topic updated' : 'Topic created')
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || 'Failed to save topic')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title={initial ? 'Edit Topic' : 'Create Custom Topic'}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-gray-400 block mb-1">Title *</label>
            <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="Group topic title" />
          </div>
          <div className="col-span-2 sm:col-span-1">
            <label className="text-xs text-gray-400 block mb-1">Category</label>
            <select className="input-field w-full" value={form.category} onChange={set('category')}>
              {TOPIC_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea className="input-field w-full h-20 resize-none" value={form.description} onChange={set('description')} placeholder="Brief overview of the topic and its clinical purpose" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Key Points (one per line)</label>
          <textarea className="input-field w-full h-20 resize-none" value={form.key_points} onChange={set('key_points')} placeholder="Key point 1&#10;Key point 2&#10;Key point 3" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Discussion Questions (one per line)</label>
          <textarea className="input-field w-full h-20 resize-none" value={form.discussion_questions} onChange={set('discussion_questions')} placeholder="Question 1&#10;Question 2&#10;Question 3" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Activity</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.activity} onChange={set('activity')} placeholder="Describe a specific in-group activity" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Writing Prompt</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.writing_prompt} onChange={set('writing_prompt')} placeholder="Journal or writing prompt for members" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Facilitator Tips</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.facilitator_tips} onChange={set('facilitator_tips')} placeholder="Practical facilitation tips" />
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {initial ? 'Save Changes' : 'Create Topic'}
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

// ── AI Generate modal ─────────────────────────────────────────────────────────

function AIGenerateModal({ onClose, onSaved, prefillTitle = '' }) {
  const [form, setForm] = useState({
    title: prefillTitle,
    group_length_minutes: 60,
    population: 'Adults in SUD/MH treatment',
    tone: 'psychoeducational',
    additional_context: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleGenerate = async () => {
    if (!form.title.trim()) { toast.error('Topic title is required'); return }
    setLoading(true)
    setResult(null)
    try {
      const data = await topicsAPI.aiGenerate({
        ...form,
        group_length_minutes: Number(form.group_length_minutes),
      })
      setResult(data)
    } catch (err) {
      toast.error(err?.message || 'AI generation failed')
    } finally {
      setLoading(false)
    }
  }

  const handleUse = () => {
    toast.success('Topic saved to library')
    onSaved(result)
  }

  return (
    <ModalWrapper onClose={onClose} title="AI Generate Group Topic" wide>
      <div className="space-y-4">
        {!result && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="text-xs text-gray-400 block mb-1">Topic Title *</label>
                <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="e.g. Managing Cravings" />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Group Length (minutes)</label>
                <select className="input-field w-full" value={form.group_length_minutes} onChange={set('group_length_minutes')}>
                  {[30, 45, 60, 75, 90].map((m) => <option key={m} value={m}>{m} min</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Tone / Style</label>
                <select className="input-field w-full" value={form.tone} onChange={set('tone')}>
                  {['psychoeducational', 'CBT-based', 'DBT-based', 'motivational', 'trauma-informed', 'strengths-based'].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-400 block mb-1">Population</label>
                <input className="input-field w-full" value={form.population} onChange={set('population')} placeholder="e.g. Adults in SUD/MH treatment" />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-400 block mb-1">Additional Context (optional)</label>
                <textarea className="input-field w-full h-16 resize-none" value={form.additional_context} onChange={set('additional_context')} placeholder="Any specific focus, group needs, or constraints" />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="btn-secondary">Cancel</button>
              <button onClick={handleGenerate} disabled={loading} className="btn-primary flex items-center gap-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {loading ? 'Generating…' : 'Generate Topic Plan'}
              </button>
            </div>
          </>
        )}
        {result && (
          <div className="space-y-4">
            <div className="rounded-lg bg-purple-500/10 border border-purple-500/30 p-4 space-y-3">
              <h3 className="font-semibold text-white text-lg">{result.title}</h3>
              <Badge className={categoryColor(result.category)}>{result.category}</Badge>
              {result.description && <p className="text-sm text-gray-300">{result.description}</p>}
              {result.clinical_purpose && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Clinical Purpose</p>
                  <p className="text-sm text-gray-300">{result.clinical_purpose}</p>
                </div>
              )}
              {result.key_points_json?.length > 0 && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Key Points</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {result.key_points_json.map((p, i) => <li key={i} className="text-sm text-gray-300">{p}</li>)}
                  </ul>
                </div>
              )}
              {result.discussion_questions_json?.length > 0 && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Discussion Questions</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {result.discussion_questions_json.map((q, i) => <li key={i} className="text-sm text-gray-300">{q}</li>)}
                  </ul>
                </div>
              )}
              {result.activity && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Activity</p>
                  <p className="text-sm text-gray-300">{result.activity}</p>
                </div>
              )}
              {result.writing_prompt && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Writing Prompt</p>
                  <p className="text-sm text-gray-300 italic">"{result.writing_prompt}"</p>
                </div>
              )}
              {result.facilitator_tips && (
                <div>
                  <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Facilitator Tips</p>
                  <p className="text-sm text-gray-300">{result.facilitator_tips}</p>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setResult(null)} className="btn-secondary">Generate Another</button>
              <button onClick={handleUse} className="btn-primary flex items-center gap-2">
                <Check className="h-4 w-4" />
                Use This Topic
              </button>
            </div>
          </div>
        )}
      </div>
    </ModalWrapper>
  )
}

// ── Add playlist modal ────────────────────────────────────────────────────────

function AddPlaylistModal({ onClose, onSaved }) {
  const [form, setForm] = useState({ title: '', youtube_playlist_url: '', description: '', category: 'General' })
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return }
    if (!form.youtube_playlist_url.trim()) { toast.error('Playlist URL is required'); return }
    setSaving(true)
    try {
      const saved = await playlistsAPI.create({
        title: form.title.trim(),
        youtube_playlist_url: form.youtube_playlist_url.trim(),
        description: form.description,
        category: form.category,
        tags: [],
      })
      toast.success('Playlist added')
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || 'Failed to add playlist')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title="Add YouTube Playlist">
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Playlist Title *</label>
          <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="e.g. Recovery Education Videos" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">YouTube Playlist URL *</label>
          <input className="input-field w-full font-mono text-sm" value={form.youtube_playlist_url} onChange={set('youtube_playlist_url')} placeholder="https://www.youtube.com/playlist?list=..." />
          <p className="text-xs text-gray-500 mt-1">Paste the full YouTube playlist URL. Videos will be embeddable in groups.</p>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Category</label>
          <select className="input-field w-full" value={form.category} onChange={set('category')}>
            {['General', ...TOPIC_CATEGORIES].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.description} onChange={set('description')} placeholder="What is this playlist about?" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Add Playlist
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

// ── Add video modal ───────────────────────────────────────────────────────────

function AddVideoModal({ onClose, onSaved }) {
  const [form, setForm] = useState({ title: '', youtube_url: '', description: '', category: 'General' })
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return }
    if (!form.youtube_url.trim()) { toast.error('Video URL is required'); return }
    setSaving(true)
    try {
      const saved = await videosAPI.create({
        title: form.title.trim(),
        youtube_url: form.youtube_url.trim(),
        description: form.description,
        category: form.category,
        tags: [],
      })
      toast.success('Video added')
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || 'Failed to add video')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title="Add YouTube Video">
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Video Title *</label>
          <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="e.g. Understanding the Brain in Addiction" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">YouTube Video URL *</label>
          <input className="input-field w-full font-mono text-sm" value={form.youtube_url} onChange={set('youtube_url')} placeholder="https://www.youtube.com/watch?v=..." />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Category</label>
          <select className="input-field w-full" value={form.category} onChange={set('category')}>
            {['General', ...TOPIC_CATEGORIES].map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.description} onChange={set('description')} placeholder="Notes about this video" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Add Video
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

// ── Session create modal ──────────────────────────────────────────────────────

function CreateSessionModal({ onClose, onSaved, topics = [] }) {
  const [form, setForm] = useState({
    title: '',
    topic_id: '',
    scheduled_date: '',
    scheduled_time: '',
    location: '',
    group_type: 'psychoeducation',
    facilitator_notes: '',
  })
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Session title is required'); return }
    setSaving(true)
    try {
      const saved = await sessionsAPI.create({
        ...form,
        topic_id: form.topic_id || null,
        playlist_ids: [],
        video_ids: [],
      })
      toast.success('Session created')
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || 'Failed to create session')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title="Create Group Session">
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Session Title *</label>
          <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="e.g. Wednesday Morning Group — Cravings" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Select Topic (optional)</label>
          <select className="input-field w-full" value={form.topic_id} onChange={set('topic_id')}>
            <option value="">— No topic selected —</option>
            {topics.map((t) => (
              <option key={t.topic_id} value={t.topic_id}>{t.title}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Date</label>
            <input type="date" className="input-field w-full" value={form.scheduled_date} onChange={set('scheduled_date')} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Time</label>
            <input type="time" className="input-field w-full" value={form.scheduled_time} onChange={set('scheduled_time')} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Location</label>
            <input className="input-field w-full" value={form.location} onChange={set('location')} placeholder="e.g. Conference Room B" />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Group Type</label>
            <select className="input-field w-full" value={form.group_type} onChange={set('group_type')}>
              {GROUP_TYPES.map((g) => <option key={g}>{g}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Facilitator Notes</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.facilitator_notes} onChange={set('facilitator_notes')} placeholder="Any notes before the session" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Session
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

// ── Modal wrapper ─────────────────────────────────────────────────────────────

function ModalWrapper({ children, onClose, title, wide = false }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className={`bg-slate-900 border border-white/15 rounded-2xl shadow-2xl w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} max-h-[90vh] overflow-y-auto`}>
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h3 className="font-semibold text-white text-base">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ── Topics Tab ────────────────────────────────────────────────────────────────

function TopicsTab({ topics, loading, error, onRefresh }) {
  const ALL_CATEGORIES = 'All Categories'
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState(ALL_CATEGORIES)
  const [expandedCategories, setExpandedCategories] = useState([])
  const [expanded, setExpanded] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showAI, setShowAI] = useState(false)
  const [editTopic, setEditTopic] = useState(null)

  const normalizedSearch = search.trim().toLowerCase()
  const filtered = topics.filter((t) => {
    const matchCat = categoryFilter === ALL_CATEGORIES || t.category === categoryFilter
    const matchSearch = !normalizedSearch || t.title.toLowerCase().includes(normalizedSearch) || (t.description || '').toLowerCase().includes(normalizedSearch)
    return matchCat && matchSearch
  })
  const visibleCategories = TOPIC_CATEGORIES.filter((category) =>
    filtered.some((topic) => topic.category === category)
  )
  const uncategorizedTopics = filtered.filter((topic) => !TOPIC_CATEGORIES.includes(topic.category))
  const groupedTopics = [
    ...visibleCategories.map((category) => ({
      category,
      topics: filtered.filter((topic) => topic.category === category),
    })),
    ...(uncategorizedTopics.length > 0
      ? [{ category: 'Other Topics', topics: uncategorizedTopics }]
      : []),
  ]
  const groupedTopicKeys = groupedTopics.map((group) => group.category)
  const groupedTopicKeySignature = groupedTopicKeys.join('|')
  const totalStarterTopics = topics.filter((topic) => topic.source === 'seeded').length
  const totalCustomTopics = topics.length - totalStarterTopics

  useEffect(() => {
    setExpandedCategories((current) => {
      let nextExpanded = []

      if (groupedTopicKeys.length === 0) {
        nextExpanded = []
      } else if (normalizedSearch) {
        nextExpanded = groupedTopicKeys
      } else if (categoryFilter !== ALL_CATEGORIES) {
        nextExpanded = [categoryFilter]
      } else {
        nextExpanded = current.filter((category) => groupedTopicKeys.includes(category))
        if (nextExpanded.length === 0) nextExpanded = [groupedTopicKeys[0]]
      }

      return nextExpanded.length === current.length && nextExpanded.every((category, index) => category === current[index])
        ? current
        : nextExpanded
    })
  }, [categoryFilter, groupedTopicKeySignature, normalizedSearch])

  const toggle = (id) => setExpanded((e) => (e === id ? null : id))
  const toggleCategory = (category) => {
    setExpandedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    )
  }

  return (
    <div>
      {/* Controls */}
      <div className="mb-5 space-y-4">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="input-field w-full pl-9"
            placeholder="Search topics…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-900/40 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300/80">Topic Templates</p>
                <p className="mt-1 text-sm text-gray-400">
                  Browse the starter library by category and expand only the sections you need.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-gray-300">
                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1">
                  {topics.length} total topics
                </span>
                <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1">
                  {totalStarterTopics} starter
                </span>
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1">
                  {totalCustomTopics} custom or AI
                </span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setShowAI(true)} className="btn-secondary flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-400" />
                AI Generate
              </button>
              <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Custom Topic
              </button>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto pb-1">
            <div className="flex min-w-max gap-2">
              {[ALL_CATEGORIES, ...TOPIC_CATEGORIES].map((category) => {
                const count = category === ALL_CATEGORIES
                  ? topics.length
                  : topics.filter((topic) => topic.category === category).length
                const isActive = categoryFilter === category
                return (
                  <button
                    key={category}
                    type="button"
                    aria-label={`Filter ${category}`}
                    onClick={() => setCategoryFilter(category)}
                    className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                      isActive
                        ? 'border-purple-400/60 bg-purple-500/20 text-white'
                        : 'border-white/10 bg-slate-800/60 text-gray-300 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    {category} <span className="text-xs text-gray-400">({count})</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}
      {!loading && !error && filtered.length === 0 && (
        <p className="text-center text-gray-500 py-12">No topics found.</p>
      )}

      <div className="space-y-3">
        {groupedTopics.map((group) => {
          const isExpanded = expandedCategories.includes(group.category)
          const starterCount = group.topics.filter((topic) => topic.source === 'seeded').length
          return (
            <Card key={group.category} className="p-0 overflow-hidden">
              <button
                type="button"
                aria-expanded={isExpanded}
                aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${group.category} topics`}
                onClick={() => toggleCategory(group.category)}
                className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left hover:bg-white/5"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-white">{group.category}</span>
                    <Badge className={categoryColor(group.category)}>{group.topics.length} topics</Badge>
                    <span className="text-xs text-gray-500">
                      {starterCount} starter, {group.topics.length - starterCount} custom or AI
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">
                    {isExpanded ? 'Collapse this section to keep the page lighter.' : 'Expand to browse templates in this category.'}
                  </p>
                </div>
                <div className="flex-shrink-0 pt-0.5">
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                </div>
              </button>

              {isExpanded && (
                <div className="border-t border-white/10 px-4 py-4">
                  <div className="grid gap-3 lg:grid-cols-2">
                    {group.topics.map((topic) => (
                      <Card key={topic.topic_id} className="h-full">
                        <div className="flex items-start gap-3">
                          <button
                            type="button"
                            aria-expanded={expanded === topic.topic_id}
                            aria-controls={`topic-panel-${topic.topic_id}`}
                            onClick={() => toggle(topic.topic_id)}
                            className="flex-1 min-w-0 text-left"
                          >
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <span className="font-medium text-white text-sm">{topic.title}</span>
                              <Badge className={sourceBadgeColor(topic.source)}>{sourceLabel(topic.source)}</Badge>
                            </div>
                            {topic.description && (
                              <p className="text-xs text-gray-400 line-clamp-2">{topic.description}</p>
                            )}
                          </button>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <button
                              onClick={() => setEditTopic(topic)}
                              className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors"
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              aria-label={`${expanded === topic.topic_id ? 'Collapse' : 'Expand'} ${topic.title}`}
                              onClick={() => toggle(topic.topic_id)}
                              className="rounded p-1 text-gray-400 hover:bg-white/10 hover:text-white"
                            >
                              {expanded === topic.topic_id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </button>
                          </div>
                        </div>

                        {expanded === topic.topic_id && (
                          <div id={`topic-panel-${topic.topic_id}`} className="mt-4 pt-4 border-t border-white/10 space-y-3">
                            {topic.key_points_json?.length > 0 && (
                              <div>
                                <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Key Points</p>
                                <ul className="list-disc list-inside space-y-0.5">
                                  {topic.key_points_json.map((p, i) => <li key={i} className="text-xs text-gray-300">{p}</li>)}
                                </ul>
                              </div>
                            )}
                            {topic.discussion_questions_json?.length > 0 && (
                              <div>
                                <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Discussion Questions</p>
                                <ul className="list-disc list-inside space-y-0.5">
                                  {topic.discussion_questions_json.map((q, i) => <li key={i} className="text-xs text-gray-300">{q}</li>)}
                                </ul>
                              </div>
                            )}
                            {topic.activity && (
                              <div>
                                <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Activity</p>
                                <p className="text-xs text-gray-300">{topic.activity}</p>
                              </div>
                            )}
                            {topic.writing_prompt && (
                              <div>
                                <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Writing Prompt</p>
                                <p className="text-xs text-gray-300 italic">"{topic.writing_prompt}"</p>
                              </div>
                            )}
                            {topic.facilitator_tips && (
                              <div>
                                <p className="text-xs text-purple-300 font-medium uppercase tracking-wide mb-1">Facilitator Tips</p>
                                <p className="text-xs text-gray-300">{topic.facilitator_tips}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {showCreate && (
        <TopicFormModal
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); onRefresh() }}
        />
      )}
      {showAI && (
        <AIGenerateModal
          onClose={() => setShowAI(false)}
          onSaved={() => { setShowAI(false); onRefresh() }}
        />
      )}
      {editTopic && (
        <TopicFormModal
          initial={editTopic}
          onClose={() => setEditTopic(null)}
          onSaved={() => { setEditTopic(null); onRefresh() }}
        />
      )}
    </div>
  )
}

// ── Sessions Tab ──────────────────────────────────────────────────────────────

function SessionsTab({ topics, onRefresh }) {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await sessionsAPI.list()
      setSessions(data.sessions || [])
    } catch (err) {
      setError(err?.message || 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex justify-end mb-5">
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Session
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}
      {!loading && !error && sessions.length === 0 && (
        <div className="text-center py-16">
          <Calendar className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No sessions yet. Create your first group session.</p>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.map((s) => (
          <Card key={s.session_id} onClick={() => navigate(`/groups/sessions/${s.session_id}`)}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="font-medium text-white text-sm leading-snug flex-1">{s.title}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${
                s.status === 'completed' ? 'bg-green-500/20 text-green-300'
                  : s.status === 'cancelled' ? 'bg-red-500/20 text-red-300'
                  : 'bg-blue-500/20 text-blue-300'
              }`}>{s.status}</span>
            </div>
            {s.scheduled_date && (
              <p className="text-xs text-gray-400 mb-1">{formatDate(s.scheduled_date)} {s.scheduled_time || ''}</p>
            )}
            {s.location && <p className="text-xs text-gray-500">{s.location}</p>}
            <div className="flex items-center gap-2 mt-3">
              <Badge className="bg-slate-700/50 text-gray-300 border-slate-600/50 capitalize">{s.group_type}</Badge>
            </div>
          </Card>
        ))}
      </div>

      {showCreate && (
        <CreateSessionModal
          topics={topics}
          onClose={() => setShowCreate(false)}
          onSaved={(s) => {
            setShowCreate(false)
            load()
            navigate(`/groups/sessions/${s.session_id}`)
          }}
        />
      )}
    </div>
  )
}

// ── Video Library Tab ─────────────────────────────────────────────────────────

function VideoLibraryTab() {
  const [playlists, setPlaylists] = useState([])
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAddPlaylist, setShowAddPlaylist] = useState(false)
  const [showAddVideo, setShowAddVideo] = useState(false)
  const [activeEmbed, setActiveEmbed] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [plData, vData] = await Promise.all([
        playlistsAPI.list(),
        videosAPI.list(),
      ])
      setPlaylists(plData.playlists || [])
      setVideos(vData.videos || [])
    } catch (err) {
      setError(err?.message || 'Failed to load video library')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-5 justify-end">
        <button onClick={() => setShowAddPlaylist(true)} className="btn-secondary flex items-center gap-2">
          <ListVideo className="h-4 w-4" />
          Add Playlist
        </button>
        <button onClick={() => setShowAddVideo(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Add Video
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}

      {!loading && !error && (
        <>
          {/* Playlists */}
          {playlists.length > 0 && (
            <div className="mb-8">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Playlists</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                {playlists.map((pl) => (
                  <Card key={pl.playlist_id}>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div>
                        <h4 className="font-medium text-white text-sm">{pl.title}</h4>
                        {pl.description && <p className="text-xs text-gray-400 mt-0.5">{pl.description}</p>}
                      </div>
                      <a
                        href={pl.youtube_playlist_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-gray-400 hover:text-white flex-shrink-0"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                    {activeEmbed === pl.playlist_id && pl.playlist_yt_id ? (
                      <div className="aspect-video rounded-lg overflow-hidden">
                        <iframe
                          width="100%"
                          height="100%"
                          src={youtubePlaylistEmbedUrl(pl.playlist_yt_id)}
                          title={pl.title}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowFullScreen
                        />
                      </div>
                    ) : (
                      <YoutubeThumbnailCard
                        url={pl.youtube_playlist_url}
                        title={pl.title}
                        onPlay={() => setActiveEmbed(pl.playlist_id)}
                        playlistEmbed
                      />
                    )}
                    <Badge className={`mt-2 ${categoryColor(pl.category)}`}>{pl.category}</Badge>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Individual Videos */}
          {videos.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Individual Videos</h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {videos.map((v) => (
                  <Card key={v.video_id}>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h4 className="font-medium text-white text-sm leading-snug">{v.title}</h4>
                      <a
                        href={v.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-white flex-shrink-0"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                    {v.description && <p className="text-xs text-gray-400 mb-2">{v.description}</p>}
                    {activeEmbed === v.video_id && v.video_yt_id ? (
                      <div className="aspect-video rounded-lg overflow-hidden">
                        <iframe
                          width="100%"
                          height="100%"
                          src={youtubeEmbedUrl(v.video_yt_id)}
                          title={v.title}
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowFullScreen
                        />
                      </div>
                    ) : (
                      <YoutubeThumbnailCard
                        url={v.youtube_url}
                        title={v.title}
                        onPlay={() => setActiveEmbed(v.video_id)}
                      />
                    )}
                    <Badge className={`mt-2 ${categoryColor(v.category)}`}>{v.category}</Badge>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {playlists.length === 0 && videos.length === 0 && (
            <div className="text-center py-16">
              <Video className="h-10 w-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No videos yet. Add a YouTube playlist or individual video.</p>
            </div>
          )}
        </>
      )}

      {showAddPlaylist && (
        <AddPlaylistModal onClose={() => setShowAddPlaylist(false)} onSaved={() => { setShowAddPlaylist(false); load() }} />
      )}
      {showAddVideo && (
        <AddVideoModal onClose={() => setShowAddVideo(false)} onSaved={() => { setShowAddVideo(false); load() }} />
      )}
    </div>
  )
}

// ── Schedule Tab ──────────────────────────────────────────────────────────────

function ScheduleFormModal({ onClose, onSaved, topics = [], packs = [], initialSchedule = null }) {
  const isEdit = !!initialSchedule

  // Build initial schedule_days: prefer new field, fall back to legacy day_of_week/start_time
  const initDays = (() => {
    if (initialSchedule?.schedule_days?.length) return initialSchedule.schedule_days
    if (initialSchedule?.day_of_week != null)
      return [{ day: initialSchedule.day_of_week, time: initialSchedule.start_time || '10:00' }]
    return []
  })()
  // Map of dayIndex -> time string ('' means not selected)
  const initDayMap = {}
  initDays.forEach(({ day, time }) => { initDayMap[day] = time || '10:00' })

  const [form, setForm] = useState({
    title: initialSchedule?.title || '',
    group_type: initialSchedule?.group_type || 'psychoeducation',
    duration_minutes: initialSchedule?.duration_minutes ?? 60,
    location: initialSchedule?.location || '',
    facilitator: initialSchedule?.facilitator || '',
    recurrence: initialSchedule?.recurrence || 'weekly',
    topic_id: initialSchedule?.topic_id || '',
    curriculum_pack_id: initialSchedule?.curriculum_pack_id || '',
    is_active: initialSchedule ? Boolean(initialSchedule.is_active) : true,
  })
  // dayTimes: { [dayIndex]: timeString } — presence in map means day is checked
  const [dayTimes, setDayTimes] = useState(initDayMap)
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const setNum = (k) => (e) => setForm((f) => ({ ...f, [k]: Number(e.target.value) }))

  const toggleDay = (i) => {
    setDayTimes((prev) => {
      const next = { ...prev }
      if (i in next) { delete next[i] } else { next[i] = '10:00' }
      return next
    })
  }
  const setDayTime = (i, val) => setDayTimes((prev) => ({ ...prev, [i]: val }))

  const handleSave = async () => {
    if (!form.title.trim()) { toast.error('Title is required'); return }
    const schedule_days = Object.entries(dayTimes)
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([day, time]) => ({ day: Number(day), time }))
    if (!schedule_days.length) { toast.error('Select at least one day'); return }
    setSaving(true)
    try {
      const payload = {
        ...form,
        schedule_days,
        duration_minutes: Number(form.duration_minutes),
        topic_id: form.topic_id || null,
        curriculum_pack_id: form.curriculum_pack_id || null,
      }
      let saved
      if (isEdit) {
        saved = await schedulesAPI.update(initialSchedule.schedule_id, payload)
        toast.success('Schedule updated')
      } else {
        saved = await schedulesAPI.create(payload)
        toast.success('Schedule created')
      }
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || (isEdit ? 'Failed to update schedule' : 'Failed to create schedule'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title={isEdit ? `Edit: ${initialSchedule.title}` : 'Create Group Schedule'} wide>
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Schedule Title *</label>
          <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="e.g. Morning Psychoeducation Group" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Group Type</label>
            <select className="input-field w-full" value={form.group_type} onChange={set('group_type')}>
              {GROUP_TYPES.map((g) => <option key={g}>{g}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Recurrence</label>
            <select className="input-field w-full" value={form.recurrence} onChange={set('recurrence')}>
              {RECURRENCE_OPTIONS.map((r) => <option key={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Duration (minutes)</label>
            <input type="number" className="input-field w-full" value={form.duration_minutes} onChange={setNum('duration_minutes')} min={15} max={240} step={15} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Location</label>
            <input className="input-field w-full" value={form.location} onChange={set('location')} placeholder="Room A" />
          </div>
        </div>

        {/* Multi-day selector */}
        <div>
          <label className="text-xs text-gray-400 block mb-2">Days &amp; Times *</label>
          <div className="space-y-2">
            {DAYS_OF_WEEK.map((dayName, i) => {
              const checked = i in dayTimes
              return (
                <div key={i} className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => toggleDay(i)}
                    className={`flex items-center gap-2 min-w-[110px] px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                      checked
                        ? 'bg-purple-600/30 border-purple-500/60 text-purple-200'
                        : 'bg-slate-800/60 border-white/10 text-gray-400 hover:border-white/20'
                    }`}
                  >
                    <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 ${checked ? 'bg-purple-500 border-purple-400' : 'border-gray-500'}`}>
                      {checked && <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 12 12"><path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                    </div>
                    {dayName}
                  </button>
                  {checked && (
                    <input
                      type="time"
                      className="input-field"
                      style={{ width: '120px' }}
                      value={dayTimes[i]}
                      onChange={(e) => setDayTime(i, e.target.value)}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Facilitator</label>
          <input className="input-field w-full" value={form.facilitator} onChange={set('facilitator')} placeholder="Staff name" />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Fixed Topic (optional)</label>
          <select className="input-field w-full" value={form.topic_id} onChange={set('topic_id')}>
            <option value="">— Use curriculum pack or no topic —</option>
            {topics.map((t) => <option key={t.topic_id} value={t.topic_id}>{t.title}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Curriculum Pack (optional — rotates topics)</label>
          <select className="input-field w-full" value={form.curriculum_pack_id} onChange={set('curriculum_pack_id')}>
            <option value="">— No curriculum pack —</option>
            {packs.map((p) => <option key={p.pack_id} value={p.pack_id}>{p.name} ({p.total_sessions} sessions)</option>)}
          </select>
        </div>
        {isEdit && (
          <div className="flex items-center gap-3 pt-1">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
                className={`relative w-9 h-5 rounded-full transition-colors ${form.is_active ? 'bg-purple-600' : 'bg-slate-600'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.is_active ? 'translate-x-4 left-0.5' : 'left-0.5'}`} />
              </div>
              <span className="text-xs text-gray-400">{form.is_active ? 'Active' : 'Inactive (paused)'}</span>
            </label>
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {isEdit ? 'Save Changes' : 'Create Schedule'}
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

function GenerateSessionsModal({ schedule, onClose, onGenerated }) {
  const today = new Date().toISOString().split('T')[0]
  const [form, setForm] = useState({ start_date: today, num_sessions: 8 })
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const result = await schedulesAPI.generateSessions(schedule.schedule_id, {
        start_date: form.start_date,
        num_sessions: Number(form.num_sessions),
      })
      toast.success(`Created ${result.created} sessions`)
      onGenerated(result)
    } catch (err) {
      toast.error(err?.message || 'Failed to generate sessions')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ModalWrapper onClose={onClose} title={`Generate Sessions: ${schedule.title}`}>
      <div className="space-y-4">
        <p className="text-sm text-gray-400">
          Sessions will be created starting from the selected date ({schedule.recurrence}).
          {' '}Days: {(schedule.schedule_days?.length
            ? schedule.schedule_days.map((s) => DAYS_OF_WEEK[s.day]).join(', ')
            : DAYS_OF_WEEK[schedule.day_of_week] || '—'
          )}.
        </p>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Start Date</label>
          <input type="date" className="input-field w-full" value={form.start_date} onChange={set('start_date')} />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Number of Sessions (1-52)</label>
          <input type="number" className="input-field w-full" value={form.num_sessions} onChange={set('num_sessions')} min={1} max={52} />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleGenerate} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {loading ? 'Generating...' : 'Generate Sessions'}
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

function ScheduleTab({ topics, packs, onPacksRefresh }) {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editFor, setEditFor] = useState(null)
  const [generateFor, setGenerateFor] = useState(null)
  const [expandedInstances, setExpandedInstances] = useState({})
  const [instancesData, setInstancesData] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await schedulesAPI.list()
      setSchedules(data.schedules || [])
    } catch (err) {
      setError(err?.message || 'Failed to load schedules')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const toggleInstances = async (scheduleId) => {
    if (expandedInstances[scheduleId]) {
      setExpandedInstances((e) => ({ ...e, [scheduleId]: false }))
      return
    }
    try {
      const data = await schedulesAPI.instances(scheduleId)
      setInstancesData((d) => ({ ...d, [scheduleId]: data.instances || [] }))
      setExpandedInstances((e) => ({ ...e, [scheduleId]: true }))
    } catch (err) {
      toast.error('Failed to load instances')
    }
  }

  return (
    <div>
      <div className="flex justify-end mb-5">
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Schedule
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}
      {!loading && !error && schedules.length === 0 && (
        <div className="text-center py-16">
          <Calendar className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No schedules yet. Create a recurring group schedule.</p>
        </div>
      )}

      <div className="space-y-3">
        {schedules.map((s) => {
          const topicName = s.topic_id ? (topics.find((t) => t.topic_id === s.topic_id)?.title || s.topic_id) : null
          const packName = s.curriculum_pack_id ? (packs.find((p) => p.pack_id === s.curriculum_pack_id)?.name || s.curriculum_pack_id) : null
          return (
            <Card key={s.schedule_id}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <h3 className="font-medium text-white text-sm">{s.title}</h3>
                    <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30 capitalize">{s.recurrence}</Badge>
                    <Badge className="bg-slate-700/50 text-gray-300 border-slate-600/50 capitalize">{s.group_type}</Badge>
                    {!s.is_active && <Badge className="bg-red-500/20 text-red-300 border-red-500/30">Inactive</Badge>}
                  </div>
                  <div className="flex flex-wrap gap-3 text-xs text-gray-400 mt-1">
                    {(s.schedule_days?.length
                      ? s.schedule_days.map((slot, idx) => (
                          <span key={idx} className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />{DAYS_OF_WEEK[slot.day]} {slot.time}
                          </span>
                        ))
                      : [<span key="legacy" className="flex items-center gap-1"><Calendar className="h-3 w-3" />{DAYS_OF_WEEK[s.day_of_week] || '—'} {s.start_time}</span>]
                    )}
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{s.duration_minutes} min</span>
                    {s.location && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{s.location}</span>}
                    {s.facilitator && <span className="flex items-center gap-1"><User className="h-3 w-3" />{s.facilitator}</span>}
                  </div>
                  {topicName && <p className="text-xs text-cyan-400 mt-1">Topic: {topicName}</p>}
                  {packName && <p className="text-xs text-teal-400 mt-1">Pack: {packName}</p>}
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => toggleInstances(s.schedule_id)}
                    className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors"
                  >
                    {expandedInstances[s.schedule_id] ? 'Hide' : 'Instances'}
                  </button>
                  <button
                    onClick={() => setEditFor(s)}
                    className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors flex items-center gap-1"
                  >
                    <Edit3 className="h-3 w-3" />
                    Edit
                  </button>
                  <button
                    onClick={() => setGenerateFor(s)}
                    className="btn-secondary text-xs py-1 px-3 flex items-center gap-1"
                  >
                    <RefreshCw className="h-3 w-3" />
                    Generate
                  </button>
                </div>
              </div>
              {expandedInstances[s.schedule_id] && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  {(instancesData[s.schedule_id] || []).length === 0 ? (
                    <p className="text-xs text-gray-500">No instances yet. Use Generate Sessions to create them.</p>
                  ) : (
                    <div className="space-y-1 max-h-48 overflow-y-auto">
                      {(instancesData[s.schedule_id] || []).map((inst) => (
                        <div key={inst.instance_id} className="flex items-center justify-between text-xs py-1 border-b border-white/5">
                          <span className="text-gray-300">{formatDate(inst.scheduled_date)}</span>
                          <Badge className={
                            inst.status === 'completed' ? 'bg-green-500/20 text-green-300 border-green-500/30'
                              : inst.status === 'cancelled' ? 'bg-red-500/20 text-red-300 border-red-500/30'
                              : 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                          }>{inst.status}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {showCreate && (
        <ScheduleFormModal
          topics={topics}
          packs={packs}
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); load() }}
        />
      )}
      {editFor && (
        <ScheduleFormModal
          topics={topics}
          packs={packs}
          initialSchedule={editFor}
          onClose={() => setEditFor(null)}
          onSaved={() => { setEditFor(null); load() }}
        />
      )}
      {generateFor && (
        <GenerateSessionsModal
          schedule={generateFor}
          onClose={() => setGenerateFor(null)}
          onGenerated={() => { setGenerateFor(null) }}
        />
      )}
    </div>
  )
}

// ── Curriculum Packs Tab ──────────────────────────────────────────────────────

function CurriculumPackFormModal({ onClose, onSaved, topics: initialTopics = [], initialPackId = null }) {
  const [allTopics, setAllTopics] = useState(initialTopics)
  const [form, setForm] = useState({
    name: '',
    description: '',
    target_population: '',
    level_of_care: '',
    topic_ids: [],
  })
  const [saving, setSaving] = useState(false)
  const [topicTab, setTopicTab] = useState('browse') // 'browse' | 'ai' | 'custom'

  // AI Generate state
  const [aiForm, setAiForm] = useState({ title: '', population: '', tone: 'psychoeducational', group_length_minutes: 60, additional_context: '' })
  const [aiLoading, setAiLoading] = useState(false)
  const [aiPreview, setAiPreview] = useState(null)

  // Custom topic state
  const [customForm, setCustomForm] = useState({ title: '', category: 'General', description: '' })
  const [customSaving, setCustomSaving] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const setAi = (k) => (e) => setAiForm((f) => ({ ...f, [k]: e.target.value }))
  const setCustom = (k) => (e) => setCustomForm((f) => ({ ...f, [k]: e.target.value }))

  const toggleTopic = (topicId) => {
    setForm((f) => ({
      ...f,
      topic_ids: f.topic_ids.includes(topicId)
        ? f.topic_ids.filter((id) => id !== topicId)
        : [...f.topic_ids, topicId],
    }))
  }

  const addTopicToList = (topic) => {
    setAllTopics((prev) => prev.find((t) => t.topic_id === topic.topic_id) ? prev : [...prev, topic])
    setForm((f) => f.topic_ids.includes(topic.topic_id) ? f : { ...f, topic_ids: [...f.topic_ids, topic.topic_id] })
  }

  const moveTopic = (index, dir) => {
    setForm((f) => {
      const ids = [...f.topic_ids]
      const newIdx = index + dir
      if (newIdx < 0 || newIdx >= ids.length) return f
      ;[ids[index], ids[newIdx]] = [ids[newIdx], ids[index]]
      return { ...f, topic_ids: ids }
    })
  }

  const removeTopic = (topicId) => {
    setForm((f) => ({ ...f, topic_ids: f.topic_ids.filter((id) => id !== topicId) }))
  }

  // AI generate a topic then save it
  const handleAiGenerate = async () => {
    if (!aiForm.title.trim()) { toast.error('Enter a topic title'); return }
    setAiLoading(true)
    setAiPreview(null)
    try {
      const generated = await topicsAPI.aiGenerate({
        title: aiForm.title,
        population: aiForm.population || 'Adults in SUD/MH treatment',
        tone: aiForm.tone,
        group_length_minutes: Number(aiForm.group_length_minutes),
        additional_context: aiForm.additional_context,
      })
      setAiPreview(generated)
    } catch (err) {
      toast.error(err?.message || 'AI generation failed')
    } finally {
      setAiLoading(false)
    }
  }

  const handleAddAiTopic = async () => {
    if (!aiPreview) return
    setAiLoading(true)
    try {
      const saved = await topicsAPI.create({ ...aiPreview, source: 'ai_generated' })
      addTopicToList(saved)
      toast.success(`"${saved.title}" added to pack`)
      setAiPreview(null)
      setAiForm({ title: '', population: '', tone: 'psychoeducational', group_length_minutes: 60, additional_context: '' })
    } catch (err) {
      toast.error(err?.message || 'Failed to save topic')
    } finally {
      setAiLoading(false)
    }
  }

  const handleCustomSave = async () => {
    if (!customForm.title.trim()) { toast.error('Title is required'); return }
    setCustomSaving(true)
    try {
      const saved = await topicsAPI.create({ ...customForm, source: 'custom' })
      addTopicToList(saved)
      toast.success(`"${saved.title}" added to pack`)
      setCustomForm({ title: '', category: 'General', description: '' })
    } catch (err) {
      toast.error(err?.message || 'Failed to create topic')
    } finally {
      setCustomSaving(false)
    }
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return }
    setSaving(true)
    try {
      const saved = await curriculumPacksAPI.create(form)
      toast.success('Curriculum pack created')
      onSaved(saved)
    } catch (err) {
      toast.error(err?.message || 'Failed to create pack')
    } finally {
      setSaving(false)
    }
  }

  const orderedTopics = form.topic_ids.map((id) => allTopics.find((t) => t.topic_id === id)).filter(Boolean)

  return (
    <ModalWrapper onClose={onClose} title="Create Curriculum Pack" wide>
      <div className="space-y-4">
        {/* Pack meta */}
        <div>
          <label className="text-xs text-gray-400 block mb-1">Pack Name *</label>
          <input className="input-field w-full" value={form.name} onChange={set('name')} placeholder="e.g. 8-Week SUD Recovery Curriculum" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Target Population</label>
            <input className="input-field w-full" value={form.target_population} onChange={set('target_population')} placeholder="e.g. Adults in SUD treatment" />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Level of Care</label>
            <input className="input-field w-full" value={form.level_of_care} onChange={set('level_of_care')} placeholder="e.g. IOP, Residential" />
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Description</label>
          <textarea className="input-field w-full h-16 resize-none" value={form.description} onChange={set('description')} placeholder="Brief description of this curriculum" />
        </div>

        {/* Topic tabs */}
        <div>
          <label className="text-xs text-gray-400 block mb-2">Add Topics</label>
          <div className="flex gap-1 mb-3">
            {[['browse', 'Browse Library'], ['ai', 'AI Generate'], ['custom', 'Create Custom']].map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setTopicTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  topicTab === tab ? 'bg-purple-600 text-white' : 'bg-slate-700/60 text-gray-400 hover:text-white'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Browse tab */}
          {topicTab === 'browse' && (
            <div className="max-h-48 overflow-y-auto space-y-1 border border-white/10 rounded-lg p-2">
              {allTopics.length === 0 && <p className="text-xs text-gray-500 p-2">No topics available. Use AI Generate or Create Custom to add one.</p>}
              {allTopics.map((t) => (
                <label key={t.topic_id} className="flex items-center gap-2 cursor-pointer hover:bg-white/5 rounded px-2 py-1">
                  <input
                    type="checkbox"
                    checked={form.topic_ids.includes(t.topic_id)}
                    onChange={() => toggleTopic(t.topic_id)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-300 flex-1">{t.title}</span>
                  <Badge className={categoryColor(t.category)}>{t.category}</Badge>
                </label>
              ))}
            </div>
          )}

          {/* AI Generate tab */}
          {topicTab === 'ai' && (
            <div className="border border-white/10 rounded-lg p-3 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="text-xs text-gray-400 block mb-1">Topic Title *</label>
                  <input className="input-field w-full" value={aiForm.title} onChange={setAi('title')} placeholder="e.g. Coping with Cravings" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Population</label>
                  <input className="input-field w-full" value={aiForm.population} onChange={setAi('population')} placeholder="Adults in SUD treatment" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Tone</label>
                  <select className="input-field w-full" value={aiForm.tone} onChange={setAi('tone')}>
                    <option value="psychoeducational">Psychoeducational</option>
                    <option value="motivational">Motivational</option>
                    <option value="skills-based">Skills-Based</option>
                    <option value="process">Process</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Duration (min)</label>
                  <input type="number" className="input-field w-full" value={aiForm.group_length_minutes} onChange={setAi('group_length_minutes')} min={15} max={120} step={15} />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Extra Context</label>
                  <input className="input-field w-full" value={aiForm.additional_context} onChange={setAi('additional_context')} placeholder="Optional notes for AI" />
                </div>
              </div>
              <button
                type="button"
                onClick={handleAiGenerate}
                disabled={aiLoading}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                {aiLoading && !aiPreview ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                Generate Topic
              </button>

              {aiPreview && (
                <div className="bg-slate-800/60 border border-purple-500/30 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-white">{aiPreview.title}</p>
                    <Badge className={categoryColor(aiPreview.category)}>{aiPreview.category}</Badge>
                  </div>
                  {aiPreview.description && <p className="text-xs text-gray-400">{aiPreview.description}</p>}
                  {aiPreview.key_points?.length > 0 && (
                    <ul className="text-xs text-gray-400 list-disc list-inside space-y-0.5">
                      {aiPreview.key_points.slice(0, 3).map((kp, i) => <li key={i}>{kp}</li>)}
                    </ul>
                  )}
                  <button
                    type="button"
                    onClick={handleAddAiTopic}
                    disabled={aiLoading}
                    className="btn-primary text-xs flex items-center gap-1.5"
                  >
                    {aiLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                    Add to Pack
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Create Custom tab */}
          {topicTab === 'custom' && (
            <div className="border border-white/10 rounded-lg p-3 space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Topic Title *</label>
                <input className="input-field w-full" value={customForm.title} onChange={setCustom('title')} placeholder="e.g. Healthy Boundaries in Recovery" />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Category</label>
                <select className="input-field w-full" value={customForm.category} onChange={setCustom('category')}>
                  {TOPIC_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Description</label>
                <textarea className="input-field w-full h-16 resize-none" value={customForm.description} onChange={setCustom('description')} placeholder="Brief description of the topic" />
              </div>
              <button
                type="button"
                onClick={handleCustomSave}
                disabled={customSaving}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                {customSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                Create &amp; Add to Pack
              </button>
            </div>
          )}
        </div>

        {/* Ordered list of selected topics */}
        {orderedTopics.length > 0 && (
          <div>
            <label className="text-xs text-gray-400 block mb-2">Session Order ({orderedTopics.length} topics)</label>
            <div className="space-y-1">
              {orderedTopics.map((t, i) => (
                <div key={t.topic_id} className="flex items-center gap-2 bg-slate-700/40 rounded px-3 py-1.5">
                  <span className="text-xs text-gray-500 w-5">{i + 1}.</span>
                  <span className="text-sm text-gray-300 flex-1">{t.title}</span>
                  <button onClick={() => moveTopic(i, -1)} disabled={i === 0} className="text-gray-500 hover:text-white disabled:opacity-30 px-1">
                    <ChevronUp className="h-3 w-3" />
                  </button>
                  <button onClick={() => moveTopic(i, 1)} disabled={i === orderedTopics.length - 1} className="text-gray-500 hover:text-white disabled:opacity-30 px-1">
                    <ChevronDown className="h-3 w-3" />
                  </button>
                  <button onClick={() => removeTopic(t.topic_id)} className="text-gray-500 hover:text-red-400 px-1">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Create Pack
          </button>
        </div>
      </div>
    </ModalWrapper>
  )
}

function CurriculumPacksTab({ topics, packs, loading, error, onRefresh }) {
  const [showCreate, setShowCreate] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [packDetails, setPackDetails] = useState({})

  const toggleExpand = async (packId) => {
    if (expanded === packId) { setExpanded(null); return }
    setExpanded(packId)
    if (!packDetails[packId]) {
      try {
        const data = await curriculumPacksAPI.get(packId)
        setPackDetails((d) => ({ ...d, [packId]: data }))
      } catch (err) {
        toast.error('Failed to load pack details')
      }
    }
  }

  return (
    <div>
      <div className="flex justify-end mb-5">
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Pack
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}
      {!loading && !error && packs.length === 0 && (
        <div className="text-center py-16">
          <Package className="h-10 w-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No curriculum packs yet. Create a pack to organize topics into a structured curriculum.</p>
        </div>
      )}

      <div className="space-y-3">
        {packs.map((pack) => (
          <Card key={pack.pack_id}>
            <div className="flex items-start justify-between gap-3 cursor-pointer" onClick={() => toggleExpand(pack.pack_id)}>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <h3 className="font-medium text-white text-sm">{pack.name}</h3>
                  <Badge className="bg-teal-500/20 text-teal-300 border-teal-500/30">{pack.total_sessions} sessions</Badge>
                </div>
                {pack.description && <p className="text-xs text-gray-400 mb-1">{pack.description}</p>}
                <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                  {pack.target_population && <span>Population: {pack.target_population}</span>}
                  {pack.level_of_care && <span>Level: {pack.level_of_care}</span>}
                </div>
              </div>
              <div className="flex-shrink-0">
                {expanded === pack.pack_id ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
              </div>
            </div>
            {expanded === pack.pack_id && packDetails[pack.pack_id] && (
              <div className="mt-3 pt-3 border-t border-white/10">
                <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wide">Topics in Order</p>
                {packDetails[pack.pack_id].topics?.length === 0 ? (
                  <p className="text-xs text-gray-500">No topics in this pack.</p>
                ) : (
                  <div className="space-y-1">
                    {packDetails[pack.pack_id].topics?.map((t, i) => (
                      <div key={t.topic_id} className="flex items-center gap-2 text-xs py-1 border-b border-white/5">
                        <span className="text-gray-500 w-5">{i + 1}.</span>
                        <span className="text-gray-300 flex-1">{t.title}</span>
                        <Badge className={categoryColor(t.category)}>{t.category}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>

      {showCreate && (
        <CurriculumPackFormModal
          topics={topics}
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); onRefresh() }}
        />
      )}
    </div>
  )
}

// ── Reports Tab ───────────────────────────────────────────────────────────────

function ReportsTab({ topics }) {
  const today = new Date().toISOString().split('T')[0]
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]

  const [filters, setFilters] = useState({
    start_date: thirtyDaysAgo,
    end_date: today,
    facilitator: '',
    topic_id: '',
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)

  const setF = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }))

  const runReport = async () => {
    setLoading(true)
    try {
      const params = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        ...(filters.facilitator ? { facilitator: filters.facilitator } : {}),
        ...(filters.topic_id ? { topic_id: filters.topic_id } : {}),
      }
      const [attendance, topicsData, notesData] = await Promise.all([
        reportsAPI.attendance(params),
        reportsAPI.topics({ start_date: filters.start_date, end_date: filters.end_date }),
        reportsAPI.notes({ start_date: filters.start_date, end_date: filters.end_date }),
      ])
      setResults({ attendance, topics: topicsData, notes: notesData })
    } catch (err) {
      toast.error(err?.message || 'Failed to run report')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Filter bar */}
      <Card>
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-purple-400" />
          Report Filters
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Start Date</label>
            <input type="date" className="input-field w-full" value={filters.start_date} onChange={setF('start_date')} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">End Date</label>
            <input type="date" className="input-field w-full" value={filters.end_date} onChange={setF('end_date')} />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Facilitator (optional)</label>
            <input className="input-field w-full" value={filters.facilitator} onChange={setF('facilitator')} placeholder="Filter by facilitator" />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Topic (optional)</label>
            <select className="input-field w-full" value={filters.topic_id} onChange={setF('topic_id')}>
              <option value="">All topics</option>
              {topics.map((t) => <option key={t.topic_id} value={t.topic_id}>{t.title}</option>)}
            </select>
          </div>
        </div>
        <div className="flex justify-end mt-3">
          <button onClick={runReport} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <BarChart2 className="h-4 w-4" />}
            {loading ? 'Running...' : 'Run Report'}
          </button>
        </div>
      </Card>

      {results && (
        <>
          {/* Attendance table */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
              Attendance — {results.attendance.summary?.total_sessions} sessions
            </h3>
            {results.attendance.sessions?.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-6">No sessions in this date range.</p>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 bg-slate-800/80">
                      <th className="text-left px-4 py-2 text-xs text-gray-400 font-medium">Date</th>
                      <th className="text-left px-4 py-2 text-xs text-gray-400 font-medium">Session</th>
                      <th className="text-center px-3 py-2 text-xs text-gray-400 font-medium">Present</th>
                      <th className="text-center px-3 py-2 text-xs text-gray-400 font-medium">Absent</th>
                      <th className="text-center px-3 py-2 text-xs text-gray-400 font-medium">Late</th>
                      <th className="text-center px-3 py-2 text-xs text-gray-400 font-medium">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.attendance.sessions?.map((s) => (
                      <tr key={s.session_id} className="border-b border-white/5 hover:bg-white/5">
                        <td className="px-4 py-2 text-gray-400 text-xs">{formatDate(s.scheduled_date)}</td>
                        <td className="px-4 py-2 text-gray-200">{s.title}</td>
                        <td className="px-3 py-2 text-center text-green-400">{s.present_count || 0}</td>
                        <td className="px-3 py-2 text-center text-red-400">{s.absent_count || 0}</td>
                        <td className="px-3 py-2 text-center text-yellow-400">{s.late_count || 0}</td>
                        <td className="px-3 py-2 text-center text-gray-300">{s.total_attendees || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-slate-800/60 border-t border-white/10">
                      <td colSpan={2} className="px-4 py-2 text-xs text-gray-400 font-medium">Totals</td>
                      <td className="px-3 py-2 text-center text-green-400 font-medium">{results.attendance.summary?.total_present}</td>
                      <td className="px-3 py-2 text-center text-red-400 font-medium">{results.attendance.summary?.total_absent}</td>
                      <td className="px-3 py-2 text-center text-yellow-400 font-medium">{results.attendance.summary?.total_late}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>

          {/* Topics covered */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Topics Covered</h3>
            {results.topics.topics?.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-6">No topics covered in this date range.</p>
            ) : (
              <div className="space-y-2">
                {results.topics.topics?.map((t) => (
                  <div key={t.topic_id} className="flex items-center gap-3 bg-slate-800/60 border border-white/10 rounded-lg px-4 py-2">
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-white">{t.title}</span>
                    </div>
                    <Badge className={categoryColor(t.category)}>{t.category}</Badge>
                    <span className="text-xs text-gray-400">{t.session_count} {t.session_count === 1 ? 'session' : 'sessions'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Notes summary */}
          <div>
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">Notes Summary</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Drafted', value: results.notes.drafted, color: 'text-blue-400' },
                { label: 'Reviewed', value: results.notes.reviewed, color: 'text-yellow-400' },
                { label: 'Finalized', value: results.notes.finalized, color: 'text-green-400' },
                { label: 'AI Drafted', value: results.notes.ai_drafted, color: 'text-purple-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-slate-800/60 border border-white/10 rounded-xl p-4 text-center">
                  <div className={`text-2xl font-bold ${color}`}>{value ?? 0}</div>
                  <div className="text-xs text-gray-400 mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ── Main Groups page ──────────────────────────────────────────────────────────

export default function Groups() {
  const [activeTab, setActiveTab] = useState('Topics')
  const [topics, setTopics] = useState([])
  const [topicsLoading, setTopicsLoading] = useState(true)
  const [topicsError, setTopicsError] = useState(null)
  const [packs, setPacks] = useState([])
  const [packsLoading, setPacksLoading] = useState(true)
  const [packsError, setPacksError] = useState(null)

  const loadTopics = useCallback(async () => {
    setTopicsLoading(true)
    setTopicsError(null)
    try {
      const data = await topicsAPI.list()
      setTopics(data.topics || [])
    } catch (err) {
      setTopicsError(err?.message || 'Failed to load topics')
    } finally {
      setTopicsLoading(false)
    }
  }, [])

  const loadPacks = useCallback(async () => {
    setPacksLoading(true)
    setPacksError(null)
    try {
      const data = await curriculumPacksAPI.list()
      setPacks(data.packs || [])
    } catch (err) {
      setPacksError(err?.message || 'Failed to load packs')
    } finally {
      setPacksLoading(false)
    }
  }, [])

  useEffect(() => { loadTopics() }, [loadTopics])
  useEffect(() => { loadPacks() }, [loadPacks])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 p-4 sm:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-xl">
            <BookOpen className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Group Facilitation</h1>
        </div>
        <p className="text-gray-400 text-sm ml-12">
          Prepare SUD/MH groups with topic plans, AI-generated content, and a video library.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-1 bg-slate-800/50 rounded-xl p-1 mb-6 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === tab
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/25'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'Topics' && (
          <TopicsTab
            topics={topics}
            loading={topicsLoading}
            error={topicsError}
            onRefresh={loadTopics}
          />
        )}
        {activeTab === 'Sessions' && (
          <SessionsTab topics={topics} onRefresh={loadTopics} />
        )}
        {activeTab === 'Video Library' && <VideoLibraryTab />}
        {activeTab === 'Schedule' && (
          <ScheduleTab topics={topics} packs={packs} onPacksRefresh={loadPacks} />
        )}
        {activeTab === 'Curriculum Packs' && (
          <CurriculumPacksTab
            topics={topics}
            packs={packs}
            loading={packsLoading}
            error={packsError}
            onRefresh={loadPacks}
          />
        )}
        {activeTab === 'Reports' && <ReportsTab topics={topics} />}
      </div>
    </div>
  )
}
