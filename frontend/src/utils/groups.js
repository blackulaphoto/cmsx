import { apiFetch, apiCall } from '../api/config'

// ── Topics ────────────────────────────────────────────────────────────────────

export const topicsAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.category) qs.set('category', params.category)
    if (params.search) qs.set('search', params.search)
    if (params.source) qs.set('source', params.source)
    const query = qs.toString()
    return apiCall(`/api/groups/topics${query ? `?${query}` : ''}`)
  },

  categories: () => apiCall('/api/groups/topics/categories'),

  get: (topicId) => apiCall(`/api/groups/topics/${topicId}`),

  create: (data) =>
    apiCall('/api/groups/topics', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (topicId, data) =>
    apiCall(`/api/groups/topics/${topicId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  aiGenerate: (data) =>
    apiCall('/api/groups/topics/ai-generate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// ── Playlists ─────────────────────────────────────────────────────────────────

export const playlistsAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.category) qs.set('category', params.category)
    return apiCall(`/api/groups/playlists${qs.toString() ? `?${qs}` : ''}`)
  },

  create: (data) =>
    apiCall('/api/groups/playlists', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (playlistId, data) =>
    apiCall(`/api/groups/playlists/${playlistId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}

// ── Videos ────────────────────────────────────────────────────────────────────

export const videosAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.playlist_id) qs.set('playlist_id', params.playlist_id)
    if (params.category) qs.set('category', params.category)
    return apiCall(`/api/groups/videos${qs.toString() ? `?${qs}` : ''}`)
  },

  create: (data) =>
    apiCall('/api/groups/videos', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (videoId, data) =>
    apiCall(`/api/groups/videos/${videoId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export const sessionsAPI = {
  list: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.topic_id) qs.set('topic_id', params.topic_id)
    return apiCall(`/api/groups/sessions${qs.toString() ? `?${qs}` : ''}`)
  },

  get: (sessionId) => apiCall(`/api/groups/sessions/${sessionId}`),

  create: (data) =>
    apiCall('/api/groups/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (sessionId, data) =>
    apiCall(`/api/groups/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export const TOPIC_CATEGORIES = [
  'Addiction Education',
  'Relapse Prevention',
  'Coping Skills',
  'Mental Health',
  'Relationships',
  'Emotional Skills',
  'Identity & Recovery',
  'Practical Life Skills',
]

export const GROUP_TYPES = [
  'psychoeducation',
  'process',
  'skills',
  'support',
  'other',
]

export const SESSION_STATUSES = ['planned', 'completed', 'cancelled']

/** Returns a YouTube embed URL for a video, or null if ID cannot be extracted. */
export function youtubeEmbedUrl(ytVideoId) {
  if (!ytVideoId) return null
  return `https://www.youtube.com/embed/${ytVideoId}`
}

/** Returns a YouTube playlist embed URL. */
export function youtubePlaylistEmbedUrl(ytPlaylistId) {
  if (!ytPlaylistId) return null
  return `https://www.youtube.com/embed/videoseries?list=${ytPlaylistId}`
}

/** Returns a full YouTube watch URL for a video ID. */
export function youtubeWatchUrl(ytVideoId) {
  if (!ytVideoId) return null
  return `https://www.youtube.com/watch?v=${ytVideoId}`
}

export function categoryColor(category) {
  const map = {
    'Addiction Education': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    'Relapse Prevention': 'bg-red-500/20 text-red-300 border-red-500/30',
    'Coping Skills': 'bg-green-500/20 text-green-300 border-green-500/30',
    'Mental Health': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    'Relationships': 'bg-pink-500/20 text-pink-300 border-pink-500/30',
    'Emotional Skills': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    'Identity & Recovery': 'bg-teal-500/20 text-teal-300 border-teal-500/30',
    'Practical Life Skills': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  }
  return map[category] || 'bg-slate-500/20 text-slate-300 border-slate-500/30'
}

export function sourceLabel(source) {
  if (source === 'seeded') return 'Starter'
  if (source === 'ai_generated') return 'AI Generated'
  return 'Custom'
}

export function sourceBadgeColor(source) {
  if (source === 'seeded') return 'bg-cyan-500/20 text-cyan-300'
  if (source === 'ai_generated') return 'bg-purple-500/20 text-purple-300'
  return 'bg-emerald-500/20 text-emerald-300'
}

// ── Attendance / Notes APIs ───────────────────────────────────────────────────

export const attendanceAPI = {
  list: (sessionId) => apiCall(`/api/groups/sessions/${sessionId}/attendance`),

  upsert: (sessionId, data) =>
    apiCall(`/api/groups/sessions/${sessionId}/attendance`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  remove: (sessionId, clientId) =>
    apiCall(`/api/groups/sessions/${sessionId}/attendance/${clientId}`, {
      method: 'DELETE',
    }),
}

export const groupNotesAPI = {
  list: (sessionId) => apiCall(`/api/groups/sessions/${sessionId}/notes`),

  create: (sessionId, data) =>
    apiCall(`/api/groups/sessions/${sessionId}/notes`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (sessionId, noteId, data) =>
    apiCall(`/api/groups/sessions/${sessionId}/notes/${noteId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  aiGenerate: (sessionId, data) =>
    apiCall(`/api/groups/sessions/${sessionId}/notes/ai-generate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

export const ATTENDANCE_STATUSES = ['present', 'absent', 'late', 'excused']
export const PARTICIPATION_LEVELS = ['none', 'minimal', 'moderate', 'active']

// ── YouTube oEmbed thumbnail ──────────────────────────────────────────────────

const _thumbnailCache = {}

/**
 * Fetches the real YouTube thumbnail via oEmbed (no API key required).
 * Returns a thumbnail URL string, or null on failure.
 * Results are cached in memory for the session lifetime.
 */
export async function fetchYoutubeThumbnail(youtubeUrl) {
  if (!youtubeUrl) return null
  if (_thumbnailCache[youtubeUrl] !== undefined) return _thumbnailCache[youtubeUrl]
  try {
    const oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(youtubeUrl)}&format=json`
    const res = await fetch(oembedUrl)
    if (!res.ok) { _thumbnailCache[youtubeUrl] = null; return null }
    const json = await res.json()
    const thumb = json.thumbnail_url || null
    _thumbnailCache[youtubeUrl] = thumb
    return thumb
  } catch {
    _thumbnailCache[youtubeUrl] = null
    return null
  }
}

export function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

// ── Schedules ─────────────────────────────────────────────────────────────────

export const schedulesAPI = {
  list: () => apiCall('/api/groups/schedules'),

  create: (data) =>
    apiCall('/api/groups/schedules', { method: 'POST', body: JSON.stringify(data) }),

  update: (scheduleId, data) =>
    apiCall(`/api/groups/schedules/${scheduleId}`, { method: 'PUT', body: JSON.stringify(data) }),

  instances: (scheduleId) => apiCall(`/api/groups/schedules/${scheduleId}/instances`),

  generateSessions: (scheduleId, data) =>
    apiCall(`/api/groups/schedules/${scheduleId}/generate-sessions`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// ── Curriculum Packs ──────────────────────────────────────────────────────────

export const curriculumPacksAPI = {
  list: () => apiCall('/api/groups/curriculum-packs'),

  create: (data) =>
    apiCall('/api/groups/curriculum-packs', { method: 'POST', body: JSON.stringify(data) }),

  get: (packId) => apiCall(`/api/groups/curriculum-packs/${packId}`),

  update: (packId, data) =>
    apiCall(`/api/groups/curriculum-packs/${packId}`, { method: 'PUT', body: JSON.stringify(data) }),
}

// ── Reports ───────────────────────────────────────────────────────────────────

export const reportsAPI = {
  attendance: (params) => {
    const qs = new URLSearchParams(params).toString()
    return apiCall(`/api/groups/reports/attendance?${qs}`)
  },
  topics: (params) => {
    const qs = new URLSearchParams(params).toString()
    return apiCall(`/api/groups/reports/topics?${qs}`)
  },
  notes: (params) => {
    const qs = new URLSearchParams(params).toString()
    return apiCall(`/api/groups/reports/notes?${qs}`)
  },
}

export const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
export const RECURRENCE_OPTIONS = ['weekly', 'biweekly', 'monthly']
