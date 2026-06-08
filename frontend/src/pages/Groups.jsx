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
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  topicsAPI,
  playlistsAPI,
  videosAPI,
  sessionsAPI,
  TOPIC_CATEGORIES,
  GROUP_TYPES,
  categoryColor,
  sourceLabel,
  sourceBadgeColor,
  youtubeEmbedUrl,
  youtubePlaylistEmbedUrl,
  fetchYoutubeThumbnail,
  formatDate,
} from '../utils/groups'

const TABS = ['Topics', 'Sessions', 'Video Library']

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
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showAI, setShowAI] = useState(false)
  const [editTopic, setEditTopic] = useState(null)

  const filtered = topics.filter((t) => {
    const matchCat = !categoryFilter || t.category === categoryFilter
    const matchSearch = !search || t.title.toLowerCase().includes(search.toLowerCase()) || (t.description || '').toLowerCase().includes(search.toLowerCase())
    return matchCat && matchSearch
  })

  const toggle = (id) => setExpanded((e) => (e === id ? null : id))

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="input-field w-full pl-9"
            placeholder="Search topics…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="input-field" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
          <option value="">All Categories</option>
          {TOPIC_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
        </select>
        <button onClick={() => setShowAI(true)} className="btn-secondary flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-400" />
          AI Generate
        </button>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Custom Topic
        </button>
      </div>

      {loading && <LoadingSpinner />}
      {error && <ErrorMsg message={error} />}
      {!loading && !error && filtered.length === 0 && (
        <p className="text-center text-gray-500 py-12">No topics found.</p>
      )}

      <div className="space-y-2">
        {filtered.map((topic) => (
          <Card key={topic.topic_id}>
            <div
              className="flex items-start justify-between gap-3 cursor-pointer"
              onClick={() => toggle(topic.topic_id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="font-medium text-white text-sm">{topic.title}</span>
                  <Badge className={categoryColor(topic.category)}>{topic.category}</Badge>
                  <Badge className={sourceBadgeColor(topic.source)}>{sourceLabel(topic.source)}</Badge>
                </div>
                {topic.description && (
                  <p className="text-xs text-gray-400 line-clamp-2">{topic.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={(e) => { e.stopPropagation(); setEditTopic(topic) }}
                  className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-white/10 transition-colors"
                >
                  Edit
                </button>
                {expanded === topic.topic_id ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
              </div>
            </div>

            {expanded === topic.topic_id && (
              <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
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

// ── Main Groups page ──────────────────────────────────────────────────────────

export default function Groups() {
  const [activeTab, setActiveTab] = useState('Topics')
  const [topics, setTopics] = useState([])
  const [topicsLoading, setTopicsLoading] = useState(true)
  const [topicsError, setTopicsError] = useState(null)

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

  useEffect(() => { loadTopics() }, [loadTopics])

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
      <div className="flex gap-1 bg-slate-800/50 rounded-xl p-1 mb-6 w-fit">
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
      </div>
    </div>
  )
}
