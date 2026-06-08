import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  Clock,
  MapPin,
  Play,
  ExternalLink,
  Edit3,
  Check,
  X,
  Loader2,
  AlertCircle,
  ListVideo,
  Video,
  Plus,
  Printer,
  Users,
  FileText,
  Sparkles,
  Trash2,
  ChevronDown,
  ChevronUp,
  Copy,
  CheckCheck,
  ClipboardList,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'
import {
  sessionsAPI,
  videosAPI,
  playlistsAPI,
  topicsAPI,
  attendanceAPI,
  groupNotesAPI,
  categoryColor,
  youtubeEmbedUrl,
  youtubePlaylistEmbedUrl,
  fetchYoutubeThumbnail,
  GROUP_TYPES,
  SESSION_STATUSES,
  ATTENDANCE_STATUSES,
  PARTICIPATION_LEVELS,
  formatDate,
} from '../utils/groups'

// ── Small shared UI ───────────────────────────────────────────────────────────

function Badge({ children, className = '' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${className}`}>
      {children}
    </span>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 backdrop-blur-sm">
      <h3 className="text-xs font-semibold text-purple-300 uppercase tracking-wider mb-3">{title}</h3>
      {children}
    </div>
  )
}

function BulletList({ items }) {
  if (!items?.length) return <p className="text-sm text-gray-500 italic">None added.</p>
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2 text-sm text-gray-300">
          <span className="text-purple-400 font-bold mt-0.5 flex-shrink-0">•</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

// ── YouTube thumbnail card ─────────────────────────────────────────────────────

function YoutubeThumbnailCard({ url, title, onPlay, playlistEmbed = false }) {
  const [thumb, setThumb] = useState(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
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
        <div className="w-full h-full bg-slate-700/50 flex items-center justify-center" />
      )}
      <div className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors flex items-center justify-center">
        <div className="w-11 h-11 rounded-full bg-red-600/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
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

// ── Video picker modal ────────────────────────────────────────────────────────

function MediaPickerModal({ sessionId, currentVideoIds, currentPlaylistIds, onClose, onSaved }) {
  const [allVideos, setAllVideos] = useState([])
  const [allPlaylists, setAllPlaylists] = useState([])
  const [selectedVideos, setSelectedVideos] = useState(new Set(currentVideoIds || []))
  const [selectedPlaylists, setSelectedPlaylists] = useState(new Set(currentPlaylistIds || []))
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([videosAPI.list(), playlistsAPI.list()]).then(([vd, pd]) => {
      setAllVideos(vd.videos || [])
      setAllPlaylists(pd.playlists || [])
      setLoading(false)
    })
  }, [])

  const toggleVideo = (id) => setSelectedVideos((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })
  const togglePlaylist = (id) => setSelectedPlaylists((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })

  const handleSave = async () => {
    setSaving(true)
    try {
      await sessionsAPI.update(sessionId, {
        video_ids: Array.from(selectedVideos),
        playlist_ids: Array.from(selectedPlaylists),
      })
      toast.success('Media updated')
      onSaved()
    } catch (err) {
      toast.error(err?.message || 'Failed to update media')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-white/15 rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h3 className="font-semibold text-white text-base">Attach Media</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="overflow-y-auto flex-1 p-5 space-y-6">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 text-purple-400 animate-spin" /></div>
          ) : (
            <>
              {allPlaylists.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase mb-2">Playlists</p>
                  <div className="space-y-2">
                    {allPlaylists.map((pl) => (
                      <label key={pl.playlist_id} className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/5">
                        <input type="checkbox" checked={selectedPlaylists.has(pl.playlist_id)} onChange={() => togglePlaylist(pl.playlist_id)} className="rounded border-gray-600" />
                        <span className="text-sm text-gray-300">{pl.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {allVideos.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase mb-2">Individual Videos</p>
                  <div className="space-y-2">
                    {allVideos.map((v) => (
                      <label key={v.video_id} className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/5">
                        <input type="checkbox" checked={selectedVideos.has(v.video_id)} onChange={() => toggleVideo(v.video_id)} className="rounded border-gray-600" />
                        <span className="text-sm text-gray-300">{v.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              {allPlaylists.length === 0 && allVideos.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">No videos in library yet.</p>
              )}
            </>
          )}
        </div>
        <div className="flex justify-end gap-2 p-5 border-t border-white/10">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving || loading} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Topic picker modal ────────────────────────────────────────────────────────

function TopicPickerModal({ sessionId, currentTopicId, onClose, onSaved }) {
  const [topics, setTopics] = useState([])
  const [selected, setSelected] = useState(currentTopicId || '')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    topicsAPI.list().then((d) => { setTopics(d.topics || []); setLoading(false) })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await sessionsAPI.update(sessionId, { topic_id: selected || null })
      toast.success('Topic updated')
      onSaved()
    } catch (err) {
      toast.error(err?.message || 'Failed to update topic')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-white/15 rounded-2xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h3 className="font-semibold text-white text-base">Select Topic</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="overflow-y-auto flex-1 p-5">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 text-purple-400 animate-spin" /></div>
          ) : (
            <div className="space-y-2">
              <label className="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/5">
                <input type="radio" value="" checked={selected === ''} onChange={() => setSelected('')} />
                <span className="text-sm text-gray-400 italic">No topic</span>
              </label>
              {topics.map((t) => (
                <label key={t.topic_id} className="flex items-start gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/5">
                  <input type="radio" value={t.topic_id} checked={selected === t.topic_id} onChange={() => setSelected(t.topic_id)} className="mt-0.5" />
                  <div>
                    <p className="text-sm text-gray-300">{t.title}</p>
                    <p className="text-xs text-gray-500">{t.category}</p>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 p-5 border-t border-white/10">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Select Topic
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Inline editable field ─────────────────────────────────────────────────────

function InlineEdit({ label, value, onSave, textarea = false, selectOptions = null }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(draft)
      setEditing(false)
    } catch {
      toast.error('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <div className="flex items-start gap-2 group">
        <div className="flex-1">
          {label && <p className="text-xs text-gray-500 mb-0.5">{label}</p>}
          <p className="text-sm text-gray-200">{value || <span className="text-gray-600 italic">Not set</span>}</p>
        </div>
        <button onClick={() => { setDraft(value || ''); setEditing(true) }} className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-white transition-all p-1">
          <Edit3 className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div>
      {label && <p className="text-xs text-gray-500 mb-1">{label}</p>}
      {selectOptions ? (
        <select className="input-field w-full text-sm" value={draft} onChange={(e) => setDraft(e.target.value)}>
          {selectOptions.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : textarea ? (
        <textarea className="input-field w-full h-24 resize-none text-sm" value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
      ) : (
        <input className="input-field w-full text-sm" value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
      )}
      <div className="flex gap-2 mt-2">
        <button onClick={handleSave} disabled={saving} className="btn-primary text-xs py-1 px-3 flex items-center gap-1">
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
          Save
        </button>
        <button onClick={() => setEditing(false)} className="btn-secondary text-xs py-1 px-3">Cancel</button>
      </div>
    </div>
  )
}

// ── Add client modal ──────────────────────────────────────────────────────────

function AddClientModal({ sessionId, existingClientIds, onClose, onAdded }) {
  const [clients, setClients] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(new Set())
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    apiFetch('/api/clients?limit=200')
      .then((r) => r.json())
      .then((d) => {
        const list = d.clients || d.data || []
        setClients(list.filter((c) => !existingClientIds.has(c.client_id || c.id)))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [existingClientIds])

  const filtered = clients.filter((c) => {
    const name = `${c.first_name || ''} ${c.last_name || ''}`.toLowerCase()
    return !search || name.includes(search.toLowerCase())
  })

  const filteredIds = filtered.map((c) => c.client_id || c.id)
  const allFilteredSelected = filteredIds.length > 0 && filteredIds.every((id) => selected.has(id))

  const toggleOne = (id) => setSelected((s) => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })

  const toggleAllFiltered = () => {
    if (allFilteredSelected) {
      setSelected((s) => { const n = new Set(s); filteredIds.forEach((id) => n.delete(id)); return n })
    } else {
      setSelected((s) => { const n = new Set(s); filteredIds.forEach((id) => n.add(id)); return n })
    }
  }

  const handleAddSelected = async () => {
    if (selected.size === 0) return
    setAdding(true)
    const toAdd = clients.filter((c) => selected.has(c.client_id || c.id))
    let succeeded = 0
    let failed = 0
    await Promise.all(
      toAdd.map(async (c) => {
        try {
          await attendanceAPI.upsert(sessionId, {
            client_id: c.client_id || c.id,
            status: 'present',
            participation_level: 'active',
          })
          succeeded++
        } catch {
          failed++
        }
      })
    )
    setAdding(false)
    if (succeeded > 0) toast.success(`Added ${succeeded} client${succeeded !== 1 ? 's' : ''}`)
    if (failed > 0) toast.error(`${failed} failed to add`)
    onAdded()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border border-white/15 rounded-2xl shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <h3 className="font-semibold text-white text-base">Add Clients to Session</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X className="h-5 w-5" /></button>
        </div>

        <div className="p-3 border-b border-white/10 space-y-2">
          <input
            className="input-field w-full"
            placeholder="Search clients…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
          {!loading && filtered.length > 0 && (
            <div className="flex items-center justify-between px-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={allFilteredSelected}
                  onChange={toggleAllFiltered}
                  className="rounded border-gray-600 accent-purple-500"
                />
                <span className="text-xs text-gray-400">
                  {allFilteredSelected ? 'Deselect all' : `Select all${search ? ' matching' : ''} (${filtered.length})`}
                </span>
              </label>
              {selected.size > 0 && (
                <span className="text-xs text-purple-300">{selected.size} selected</span>
              )}
            </div>
          )}
        </div>

        <div className="overflow-y-auto flex-1 p-3">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 text-purple-400 animate-spin" /></div>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-6">No clients found.</p>
          ) : (
            <div className="space-y-0.5">
              {filtered.map((c) => {
                const cid = c.client_id || c.id
                const isSelected = selected.has(cid)
                return (
                  <label
                    key={cid}
                    className={`flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-colors ${
                      isSelected ? 'bg-purple-500/10 border border-purple-500/20' : 'hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleOne(cid)}
                      className="rounded border-gray-600 accent-purple-500 flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-200">{c.first_name} {c.last_name}</p>
                      {c.program && <p className="text-xs text-gray-500 truncate">{c.program}</p>}
                    </div>
                  </label>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-2 p-4 border-t border-white/10">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={handleAddSelected}
            disabled={selected.size === 0 || adding}
            className="btn-primary flex items-center gap-2"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add {selected.size > 0 ? `${selected.size} Client${selected.size !== 1 ? 's' : ''}` : 'Selected'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Attendance row ────────────────────────────────────────────────────────────

function AttendanceRow({ record, sessionId, onChanged, clientName }) {
  const [status, setStatus] = useState(record.status)
  const [participation, setParticipation] = useState(record.participation_level)
  const [removing, setRemoving] = useState(false)

  const handleStatusChange = async (val) => {
    setStatus(val)
    try {
      await attendanceAPI.upsert(sessionId, { client_id: record.client_id, status: val, participation_level: participation })
    } catch {
      toast.error('Failed to update status')
      setStatus(record.status)
    }
  }

  const handleParticipationChange = async (val) => {
    setParticipation(val)
    try {
      await attendanceAPI.upsert(sessionId, { client_id: record.client_id, status: status, participation_level: val })
    } catch {
      toast.error('Failed to update participation')
      setParticipation(record.participation_level)
    }
  }

  const handleRemove = async () => {
    setRemoving(true)
    try {
      await attendanceAPI.remove(sessionId, record.client_id)
      onChanged()
    } catch {
      toast.error('Failed to remove client')
      setRemoving(false)
    }
  }

  const statusColors = {
    present: 'bg-green-500/20 text-green-300 border-green-500/30',
    absent: 'bg-red-500/20 text-red-300 border-red-500/30',
    late: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    excused: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  }

  return (
    <div className="flex flex-wrap items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200">{clientName || <span className="text-xs text-gray-500 font-mono">{record.client_id}</span>}</p>
      </div>
      <select
        value={status}
        onChange={(e) => handleStatusChange(e.target.value)}
        className={`text-xs px-2 py-1 rounded-full border font-medium cursor-pointer bg-transparent ${statusColors[status] || 'text-gray-300 border-gray-600'}`}
      >
        {ATTENDANCE_STATUSES.map((s) => <option key={s} value={s} className="bg-slate-800 text-gray-200">{s}</option>)}
      </select>
      <select
        value={participation}
        onChange={(e) => handleParticipationChange(e.target.value)}
        className="text-xs px-2 py-1 rounded border border-white/15 bg-slate-700/50 text-gray-300 cursor-pointer"
      >
        {PARTICIPATION_LEVELS.map((p) => <option key={p} value={p}>{p}</option>)}
      </select>
      <button onClick={handleRemove} disabled={removing} className="text-gray-500 hover:text-red-400 transition-colors p-1" title="Remove">
        {removing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
      </button>
    </div>
  )
}

// ── Attendance tab ────────────────────────────────────────────────────────────

function AttendanceSection({ sessionId }) {
  const [attendance, setAttendance] = useState([])
  const [clientNames, setClientNames] = useState({})
  const [loading, setLoading] = useState(true)
  const [showAddClient, setShowAddClient] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ad, cd] = await Promise.all([
        attendanceAPI.list(sessionId),
        apiFetch('/api/clients?limit=500').then((r) => r.json()).catch(() => ({})),
      ])
      setAttendance(ad.attendance || [])
      const list = cd.clients || cd.data || []
      const map = {}
      list.forEach((c) => {
        const id = c.client_id || c.id
        if (id) map[id] = `${c.first_name || ''} ${c.last_name || ''}`.trim()
      })
      setClientNames(map)
    } catch { /* silently fail */ }
    finally { setLoading(false) }
  }, [sessionId])

  useEffect(() => { load() }, [load])

  const existingClientIds = new Set(attendance.map((a) => a.client_id))
  const presentCount = attendance.filter((a) => a.status === 'present' || a.status === 'late').length

  return (
    <div className="space-y-4">
      <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-semibold text-purple-300 uppercase tracking-wider">Attendance</h3>
            {attendance.length > 0 && (
              <span className="text-xs text-gray-500">{presentCount} / {attendance.length} present</span>
            )}
          </div>
          <button onClick={() => setShowAddClient(true)} className="text-xs text-gray-400 hover:text-white flex items-center gap-1">
            <Plus className="h-3 w-3" />
            Add Client
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 text-purple-400 animate-spin" /></div>
        ) : attendance.length === 0 ? (
          <p className="text-sm text-gray-500 italic">
            No clients added.{' '}
            <button onClick={() => setShowAddClient(true)} className="text-purple-400 hover:text-purple-300 underline">Add clients</button>
          </p>
        ) : (
          <div>
            <div className="flex gap-3 text-xs text-gray-500 mb-1 px-0.5">
              <span className="flex-1">Client</span>
              <span>Status</span>
              <span>Participation</span>
              <span className="w-5" />
            </div>
            {attendance.map((record) => (
              <AttendanceRow key={record.attendance_id} record={record} sessionId={sessionId} onChanged={load} clientName={clientNames[record.client_id] || null} />
            ))}
          </div>
        )}
      </div>

      {showAddClient && (
        <AddClientModal
          sessionId={sessionId}
          existingClientIds={existingClientIds}
          onClose={() => setShowAddClient(false)}
          onAdded={() => { setShowAddClient(false); load() }}
        />
      )}
    </div>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Copy failed')
    }
  }
  return (
    <button onClick={handleCopy} className="text-gray-500 hover:text-gray-300 transition-colors p-1" title="Copy note">
      {copied ? <CheckCheck className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  )
}

// ── Note card ─────────────────────────────────────────────────────────────────

const ENGAGEMENT_PRESETS = [
  'active', 'moderate', 'minimal', 'quiet/non-speaking',
  'resistant', 'distracted', 'camera off', 'late',
]

function NoteCard({ note, sessionId, onUpdated, clientName }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(note.content || '')
  const [saving, setSaving] = useState(false)

  const isAI = note.ai_generated === 1 || note.ai_generated === true
  const isQuote = note.quote_generated === 1 || note.quote_generated === true
  const isReviewed = note.reviewed === 1 || note.reviewed === true
  const isFinalized = note.finalized === 1 || note.finalized === true
  const label = note.note_type === 'group'
    ? 'Group Summary Note'
    : `Individual — ${clientName || note.client_id || 'Client'}`

  const handleSave = async () => {
    setSaving(true)
    try {
      await groupNotesAPI.update(sessionId, note.note_id, { content: draft })
      toast.success('Note saved')
      setEditing(false)
      onUpdated()
    } catch { toast.error('Failed to save note') }
    finally { setSaving(false) }
  }

  const handleMarkReviewed = async () => {
    try {
      await groupNotesAPI.update(sessionId, note.note_id, { reviewed: true })
      toast.success('Marked as reviewed')
      onUpdated()
    } catch { toast.error('Failed to update') }
  }

  const handleFinalize = async () => {
    try {
      await groupNotesAPI.update(sessionId, note.note_id, { finalized: true, reviewed: true })
      toast.success('Note finalized')
      onUpdated()
    } catch { toast.error('Failed to finalize') }
  }

  const handleUnfinalize = async () => {
    try {
      await groupNotesAPI.update(sessionId, note.note_id, { finalized: false })
      onUpdated()
    } catch { toast.error('Failed to update') }
  }

  return (
    <div className={`border rounded-xl overflow-hidden transition-colors ${
      isFinalized
        ? 'border-green-500/30 bg-green-500/5'
        : isReviewed
        ? 'border-purple-500/30 bg-purple-500/5'
        : 'border-white/10 bg-slate-800/40'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-white/8">
        <div className="flex items-center gap-2 flex-wrap">
          <FileText className="h-3.5 w-3.5 text-purple-400 flex-shrink-0" />
          <span className="text-sm text-gray-200 font-medium">{label}</span>
          {note.engagement_preset && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700/60 text-gray-400 border border-white/10">
              {note.engagement_preset}
            </span>
          )}
          {isAI && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              AI draft
            </span>
          )}
          {isQuote && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
              AI quote
            </span>
          )}
          {isReviewed && !isFinalized && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Reviewed
            </span>
          )}
          {isFinalized && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-300 border border-green-500/30">
              Finalized
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <CopyButton text={note.content || ''} />
          {!isFinalized && !editing && (
            <button onClick={() => { setDraft(note.content || ''); setEditing(true) }} className="text-gray-500 hover:text-gray-300 p-1" title="Edit">
              <Edit3 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3">
        {editing ? (
          <div>
            <textarea
              className="input-field w-full h-44 resize-y text-sm leading-relaxed font-sans"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2 mt-2">
              <button onClick={handleSave} disabled={saving} className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1">
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                Save
              </button>
              <button onClick={() => setEditing(false)} className="btn-secondary text-xs py-1.5 px-3">Cancel</button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
            {note.content || <span className="text-gray-500 italic">Empty note</span>}
          </p>
        )}
      </div>

      {/* Footer actions */}
      {!editing && (
        <div className="flex items-center gap-2 px-4 py-2 border-t border-white/5">
          {!isReviewed && !isFinalized && (
            <button onClick={handleMarkReviewed} className="text-xs text-gray-500 hover:text-blue-400 flex items-center gap-1 transition-colors">
              <Check className="h-3 w-3" />
              Mark reviewed
            </button>
          )}
          {!isFinalized && (
            <button onClick={handleFinalize} className="text-xs text-gray-500 hover:text-green-400 flex items-center gap-1 transition-colors">
              <CheckCheck className="h-3 w-3" />
              Finalize
            </button>
          )}
          {isFinalized && (
            <button onClick={handleUnfinalize} className="text-xs text-gray-500 hover:text-yellow-400 flex items-center gap-1 transition-colors">
              <Edit3 className="h-3 w-3" />
              Unfinalize to edit
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Notes tab ─────────────────────────────────────────────────────────────────

function NotesSection({ sessionId, session }) {
  const [notes, setNotes] = useState([])
  const [attendance, setAttendance] = useState([])
  const [clientNames, setClientNames] = useState({}) // clientId → "First Last"
  const [loading, setLoading] = useState(true)
  const [noteSetting, setNoteSetting] = useState('in-person')
  const [allowAiQuotes, setAllowAiQuotes] = useState(false)
  const [generatingGroup, setGeneratingGroup] = useState(false)
  const [bulkProgress, setBulkProgress] = useState(null)

  const loadNotes = useCallback(async () => {
    setLoading(true)
    try {
      const [nd, ad, cd] = await Promise.all([
        groupNotesAPI.list(sessionId),
        attendanceAPI.list(sessionId),
        apiFetch('/api/clients?limit=500').then((r) => r.json()).catch(() => ({})),
      ])
      setNotes(nd.notes || [])
      setAttendance(ad.attendance || [])
      const list = cd.clients || cd.data || []
      const map = {}
      list.forEach((c) => {
        const id = c.client_id || c.id
        if (id) map[id] = `${c.first_name || ''} ${c.last_name || ''}`.trim()
      })
      setClientNames(map)
    } catch { /* silently fail */ }
    finally { setLoading(false) }
  }, [sessionId])

  useEffect(() => { loadNotes() }, [loadNotes])

  const hasGroupNote = notes.some((n) => n.note_type === 'group')
  const presentAttendees = attendance.filter((a) => a.status !== 'absent')
  const notesByClient = new Map(notes.filter((n) => n.note_type === 'individual').map((n) => [n.client_id, n]))

  const handleGenerateGroupNote = async () => {
    setGeneratingGroup(true)
    try {
      await groupNotesAPI.aiGenerate(sessionId, {
        note_type: 'group',
        note_setting: noteSetting,
        allow_ai_quotes: false,
      })
      toast.success('Group summary note generated')
      loadNotes()
    } catch (err) {
      toast.error(err?.message || 'AI generation failed')
    } finally {
      setGeneratingGroup(false)
    }
  }

  const handleBulkGenerate = async () => {
    if (presentAttendees.length === 0) {
      toast.error('No attendees to generate notes for. Mark attendance first.')
      return
    }
    if (presentAttendees.length > 50) {
      toast.error('Maximum 50 attendees per bulk generation.')
      return
    }

    setBulkProgress({ running: true, succeeded: 0, failed: 0, total: presentAttendees.length })

    try {
      const attendees = presentAttendees.map((a) => ({
        client_id: a.client_id,
        attendance_status: a.status,
        participation_level: a.participation_level || 'moderate',
        engagement_preset: a.participation_level || 'moderate',
        staff_quote: '',
      }))

      const res = await apiFetch(`/api/groups/sessions/${sessionId}/notes/bulk-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_setting: noteSetting, allow_ai_quotes: allowAiQuotes, attendees }),
      }).then((r) => r.json())

      setBulkProgress({ running: false, succeeded: res.succeeded, failed: res.failed, total: res.total })
      toast.success(`Generated ${res.succeeded} / ${res.total} notes`)
      loadNotes()
    } catch (err) {
      toast.error(err?.message || 'Bulk generation failed')
      setBulkProgress(null)
    }
  }

  return (
    <div className="space-y-5">
      {/* Settings bar */}
      <div className="bg-slate-800/60 border border-white/10 rounded-xl p-4 backdrop-blur-sm">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-1">Note style</p>
            <div className="flex gap-1.5">
              {['in-person', 'telehealth', 'mixed'].map((s) => (
                <button
                  key={s}
                  onClick={() => setNoteSetting(s)}
                  className={`text-xs px-2.5 py-1 rounded border capitalize transition-colors ${
                    noteSetting === s
                      ? 'bg-purple-600/30 border-purple-500/50 text-purple-200'
                      : 'border-white/15 text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {s === 'in-person' ? 'In-Person' : s === 'telehealth' ? 'Telehealth' : 'Mixed'}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <div
                onClick={() => setAllowAiQuotes((v) => !v)}
                className={`relative w-9 h-5 rounded-full transition-colors ${allowAiQuotes ? 'bg-purple-600' : 'bg-slate-600'}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${allowAiQuotes ? 'translate-x-4 left-0.5' : 'left-0.5'}`} />
              </div>
              <span className="text-xs text-gray-400">Allow AI to draft client quotes</span>
            </label>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            {!hasGroupNote && (
              <button
                onClick={handleGenerateGroupNote}
                disabled={generatingGroup}
                className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-500/40 text-purple-300 hover:bg-purple-500/10 transition-colors"
              >
                {generatingGroup ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                Group Summary Note
              </button>
            )}
            <button
              onClick={handleBulkGenerate}
              disabled={bulkProgress?.running || presentAttendees.length === 0}
              className="btn-primary text-xs flex items-center gap-1.5 py-1.5"
            >
              {bulkProgress?.running ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
              Bulk Generate ({presentAttendees.length})
            </button>
          </div>
        </div>

        {/* Bulk progress */}
        {bulkProgress && !bulkProgress.running && (
          <div className="mt-3 pt-3 border-t border-white/8 flex items-center gap-3 text-xs">
            <span className="text-green-400">{bulkProgress.succeeded} succeeded</span>
            {bulkProgress.failed > 0 && <span className="text-red-400">{bulkProgress.failed} failed</span>}
            <span className="text-gray-500">of {bulkProgress.total} total</span>
            <button onClick={() => setBulkProgress(null)} className="ml-auto text-gray-600 hover:text-gray-400">
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        {bulkProgress?.running && (
          <div className="mt-3 pt-3 border-t border-white/8 flex items-center gap-2 text-xs text-gray-400">
            <Loader2 className="h-3 w-3 animate-spin text-purple-400" />
            Generating notes for {bulkProgress.total} clients…
          </div>
        )}
      </div>

      {/* Notes list */}
      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 text-purple-400 animate-spin" /></div>
      ) : notes.length === 0 ? (
        <div className="bg-slate-800/40 border border-white/8 rounded-xl p-8 text-center">
          <FileText className="h-8 w-8 text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No notes yet.</p>
          <p className="text-xs text-gray-600 mt-1">
            {attendance.length === 0
              ? 'Add clients in the Attendance tab first, then generate notes here.'
              : 'Click "Group Summary Note" or "Bulk Generate" above to get started.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Group note first */}
          {notes.filter((n) => n.note_type === 'group').map((note) => (
            <NoteCard key={note.note_id} note={note} sessionId={sessionId} onUpdated={loadNotes} />
          ))}
          {/* Individual notes */}
          {notes.filter((n) => n.note_type === 'individual').map((note) => (
            <NoteCard
              key={note.note_id}
              note={note}
              sessionId={sessionId}
              onUpdated={loadNotes}
              clientName={clientNames[note.client_id] || null}
            />
          ))}
        </div>
      )}

      {/* Attendees without notes */}
      {!loading && presentAttendees.length > 0 && (() => {
        const missing = presentAttendees.filter((a) => !notesByClient.has(a.client_id))
        if (!missing.length) return null
        return (
          <div className="bg-slate-800/30 border border-white/8 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-2">{missing.length} attendee{missing.length !== 1 ? 's' : ''} without notes</p>
            <div className="flex flex-wrap gap-1.5">
              {missing.map((a) => (
                <span key={a.client_id} className="text-xs px-2 py-0.5 rounded-full bg-slate-700/60 text-gray-400 border border-white/10">
                  {clientNames[a.client_id] || a.client_id}
                </span>
              ))}
            </div>
          </div>
        )
      })()}
    </div>
  )
}

// ── Plan tab ──────────────────────────────────────────────────────────────────

function PlanTab({ session, sessionId, onUpdate, activeEmbed, setActiveEmbed, onShowMediaPicker, onShowTopicPicker }) {
  const topic = session.topic
  const playlists = session.playlists?.filter(Boolean) || []
  const videos = session.videos?.filter(Boolean) || []

  return (
    <div className="grid lg:grid-cols-3 gap-5">
      {/* Left — Plan */}
      <div className="lg:col-span-2 space-y-5">
        {/* Topic */}
        <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-purple-300 uppercase tracking-wider">Group Topic</h3>
            <button onClick={onShowTopicPicker} className="text-xs text-gray-400 hover:text-white flex items-center gap-1">
              <Edit3 className="h-3 w-3" />
              {topic ? 'Change' : 'Select Topic'}
            </button>
          </div>
          {topic ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-semibold text-white">{topic.title}</h2>
                <Badge className={categoryColor(topic.category)}>{topic.category}</Badge>
              </div>
              {topic.description && <p className="text-sm text-gray-300 leading-relaxed">{topic.description}</p>}
            </div>
          ) : (
            <p className="text-sm text-gray-500 italic">
              No topic selected.{' '}
              <button onClick={onShowTopicPicker} className="text-purple-400 hover:text-purple-300 underline">Select one</button>
            </p>
          )}
        </div>

        {topic?.key_points_json?.length > 0 && (
          <Section title="Key Points"><BulletList items={topic.key_points_json} /></Section>
        )}
        {topic?.discussion_questions_json?.length > 0 && (
          <Section title="Discussion Questions"><BulletList items={topic.discussion_questions_json} /></Section>
        )}
        {topic?.activity && (
          <Section title="Group Activity"><p className="text-sm text-gray-300 leading-relaxed">{topic.activity}</p></Section>
        )}
        {topic?.writing_prompt && (
          <Section title="Writing Prompt"><p className="text-sm text-gray-200 italic leading-relaxed">"{topic.writing_prompt}"</p></Section>
        )}
        {topic?.facilitator_tips && (
          <Section title="Facilitator Tips"><p className="text-sm text-gray-300 leading-relaxed">{topic.facilitator_tips}</p></Section>
        )}
      </div>

      {/* Right — Facilitator Notes + Media */}
      <div className="space-y-5">
        <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 backdrop-blur-sm">
          <h3 className="text-xs font-semibold text-purple-300 uppercase tracking-wider mb-3">Facilitator Notes</h3>
          <InlineEdit label="" value={session.facilitator_notes || ''} textarea onSave={(v) => onUpdate({ facilitator_notes: v })} />
        </div>

        <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-purple-300 uppercase tracking-wider">Playlists & Videos</h3>
            <button onClick={onShowMediaPicker} className="text-xs text-gray-400 hover:text-white flex items-center gap-1">
              <Plus className="h-3 w-3" />Attach
            </button>
          </div>
          {playlists.length === 0 && videos.length === 0 ? (
            <p className="text-sm text-gray-500 italic">
              No media attached.{' '}
              <button onClick={onShowMediaPicker} className="text-purple-400 hover:text-purple-300 underline">Attach videos</button>
            </p>
          ) : (
            <div className="space-y-4">
              {playlists.map((pl) => (
                <div key={pl.playlist_id}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-200">{pl.title}</p>
                    <a href={pl.youtube_playlist_url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                  {activeEmbed === pl.playlist_id && pl.playlist_yt_id ? (
                    <div className="aspect-video rounded-lg overflow-hidden">
                      <iframe width="100%" height="100%" src={youtubePlaylistEmbedUrl(pl.playlist_yt_id)} title={pl.title}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
                    </div>
                  ) : (
                    <YoutubeThumbnailCard url={pl.youtube_playlist_url} title={pl.title} onPlay={() => setActiveEmbed(pl.playlist_id)} playlistEmbed />
                  )}
                </div>
              ))}
              {videos.map((v) => (
                <div key={v.video_id}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-200">{v.title}</p>
                    <a href={v.youtube_url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white">
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                  {activeEmbed === v.video_id && v.video_yt_id ? (
                    <div className="aspect-video rounded-lg overflow-hidden">
                      <iframe width="100%" height="100%" src={youtubeEmbedUrl(v.video_yt_id)} title={v.title}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
                    </div>
                  ) : (
                    <YoutubeThumbnailCard url={v.youtube_url} title={v.title} onPlay={() => setActiveEmbed(v.video_id)} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

const TABS = [
  { id: 'plan', label: 'Plan', icon: BookOpen },
  { id: 'attendance', label: 'Attendance', icon: Users },
  { id: 'notes', label: 'Notes', icon: FileText },
]

export default function GroupSessionDetail() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('plan')
  const [showMediaPicker, setShowMediaPicker] = useState(false)
  const [showTopicPicker, setShowTopicPicker] = useState(false)
  const [activeEmbed, setActiveEmbed] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await sessionsAPI.get(sessionId)
      setSession(data)
    } catch (err) {
      setError(err?.message || 'Failed to load session')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { load() }, [load])

  const update = async (fields) => {
    await sessionsAPI.update(sessionId, fields)
    await load()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-purple-400 animate-spin" />
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
          <p className="text-gray-400">{error || 'Session not found'}</p>
          <button onClick={() => navigate('/groups')} className="btn-secondary mt-4">Back to Groups</button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 p-4 sm:p-6">
      {/* Back nav */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/groups" className="text-gray-400 hover:text-white flex items-center gap-1.5 text-sm transition-colors">
          <ArrowLeft className="h-4 w-4" />
          Groups
        </Link>
        <span className="text-gray-600">/</span>
        <span className="text-gray-300 text-sm truncate">{session.title}</span>
      </div>

      {/* Session header */}
      <div className="bg-slate-800/60 border border-white/10 rounded-xl p-5 mb-5 backdrop-blur-sm">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <div className="p-1.5 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                <BookOpen className="h-4 w-4 text-white" />
              </div>
              <h1 className="text-xl font-bold text-white">{session.title}</h1>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium capitalize ${
                session.status === 'completed' ? 'bg-green-500/20 text-green-300'
                  : session.status === 'cancelled' ? 'bg-red-500/20 text-red-300'
                  : 'bg-blue-500/20 text-blue-300'
              }`}>{session.status}</span>
            </div>
          </div>
          <button onClick={() => window.print()} className="btn-secondary flex items-center gap-2 text-sm print:hidden">
            <Printer className="h-4 w-4" />
            Print Plan
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <InlineEdit label="Date" value={formatDate(session.scheduled_date)} onSave={(v) => update({ scheduled_date: v })} />
          <InlineEdit label="Time" value={session.scheduled_time || ''} onSave={(v) => update({ scheduled_time: v })} />
          <InlineEdit label="Location" value={session.location || ''} onSave={(v) => update({ location: v })} />
          <InlineEdit label="Status" value={session.status} selectOptions={SESSION_STATUSES} onSave={(v) => update({ status: v })} />
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-5 bg-slate-800/40 border border-white/8 rounded-xl p-1 w-fit">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-purple-600/30 text-purple-200 border border-purple-500/30'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'plan' && (
        <PlanTab
          session={session}
          sessionId={sessionId}
          onUpdate={update}
          activeEmbed={activeEmbed}
          setActiveEmbed={setActiveEmbed}
          onShowMediaPicker={() => setShowMediaPicker(true)}
          onShowTopicPicker={() => setShowTopicPicker(true)}
        />
      )}
      {activeTab === 'attendance' && <AttendanceSection sessionId={sessionId} />}
      {activeTab === 'notes' && <NotesSection sessionId={sessionId} session={session} />}

      {/* Modals */}
      {showMediaPicker && (
        <MediaPickerModal
          sessionId={sessionId}
          currentVideoIds={session.video_ids_json || []}
          currentPlaylistIds={session.playlist_ids_json || []}
          onClose={() => setShowMediaPicker(false)}
          onSaved={() => { setShowMediaPicker(false); load() }}
        />
      )}
      {showTopicPicker && (
        <TopicPickerModal
          sessionId={sessionId}
          currentTopicId={session.topic_id}
          onClose={() => setShowTopicPicker(false)}
          onSaved={() => { setShowTopicPicker(false); load() }}
        />
      )}

      <style>{`
        @media print {
          .print\\:hidden { display: none !important; }
          .print\\:block { display: block !important; }
          body { background: white !important; color: black !important; }
        }
      `}</style>
    </div>
  )
}
