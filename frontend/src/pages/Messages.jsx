import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bell,
  Check,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  Loader2,
  Megaphone,
  MessageSquare,
  Plus,
  Search,
  Send,
  ShieldAlert,
  Users,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clientsAPI, messagesAPI } from '../api/config'
import { useAuth } from '../contexts/AuthContext'

const THREAD_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'direct_message', label: 'Direct' },
  { id: 'client_thread', label: 'Client Threads' },
  { id: 'team_channel', label: 'Team Channels' },
  { id: 'announcement', label: 'Announcements' },
]

const THREAD_TYPES = [
  { id: 'direct_message', label: 'Direct message' },
  { id: 'team_channel', label: 'Team channel' },
  { id: 'client_thread', label: 'Client thread' },
  { id: 'announcement', label: 'Announcement' },
]

const typeLabel = {
  direct_message: 'Direct',
  team_channel: 'Team',
  client_thread: 'Client',
  announcement: 'Announcement',
}

function formatTime(value) {
  if (!value) return ''
  try {
    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(value))
  } catch {
    return value
  }
}

function ThreadIcon({ type }) {
  if (type === 'announcement') return <Megaphone className="h-4 w-4" />
  if (type === 'team_channel') return <Users className="h-4 w-4" />
  if (type === 'client_thread') return <ShieldAlert className="h-4 w-4" />
  return <MessageSquare className="h-4 w-4" />
}

function EmptyState({ onCreate }) {
  return (
    <div className="flex h-full min-h-[28rem] items-center justify-center px-6">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-200">
          <MessageSquare className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-semibold text-white">No thread selected</h2>
        <p className="mt-2 text-sm text-slate-300">
          Start a staff message, team channel, client-linked thread, or supervisor announcement.
        </p>
        <button type="button" onClick={onCreate} className="btn-primary mt-5 gap-2">
          <Plus className="h-4 w-4" />
          New Thread
        </button>
      </div>
    </div>
  )
}

function ParticipantPicker({ members, loading, selected, onChange }) {
  const [open, setOpen] = useState(false)
  const selectedIds = new Set(selected.map((member) => member.user_id))

  const toggle = (member) => {
    if (selectedIds.has(member.user_id)) {
      onChange(selected.filter((item) => item.user_id !== member.user_id))
    } else {
      onChange([...selected, { user_id: member.user_id, display_name: member.display_name }])
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="input-field flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="truncate text-sm">
          {selected.length === 0
            ? <span className="text-slate-500">Select team members</span>
            : `${selected.length} selected`}
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {selected.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {selected.map((member) => (
            <span key={member.user_id} className="inline-flex items-center gap-1 rounded-full bg-cyan-500/15 px-2 py-0.5 text-xs text-cyan-100">
              {member.display_name}
              <button type="button" onClick={() => toggle(member)} className="text-cyan-200 hover:text-white">
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {open && (
        <div className="absolute z-20 mt-2 max-h-56 w-full overflow-y-auto rounded-lg border border-white/10 bg-slate-900 p-1 shadow-2xl">
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-cyan-300" />
            </div>
          ) : members.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-slate-400">No other team members found.</div>
          ) : (
            members.map((member) => {
              const checked = selectedIds.has(member.user_id)
              return (
                <button
                  type="button"
                  key={member.user_id}
                  onClick={() => toggle(member)}
                  className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm hover:bg-white/5"
                >
                  <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${checked ? 'border-cyan-400 bg-cyan-500 text-white' : 'border-white/20'}`}>
                    {checked && <Check className="h-3 w-3" />}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-slate-100">{member.display_name}</span>
                  {member.role === 'admin' && (
                    <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300">Supervisor</span>
                  )}
                </button>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function NewThreadModal({ clients, currentUser, onClose, onCreated }) {
  const [form, setForm] = useState({
    thread_type: 'direct_message',
    title: '',
    client_id: '',
    purpose: '',
    initial_message: '',
  })
  const [participants, setParticipants] = useState([])
  const [teamMembers, setTeamMembers] = useState([])
  const [teamLoading, setTeamLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const isAdmin = currentUser?.role === 'admin'
  const selectedClient = clients.find((client) => client.client_id === form.client_id)

  useEffect(() => {
    let cancelled = false
    const loadTeam = async () => {
      setTeamLoading(true)
      try {
        const result = await messagesAPI.listCaseManagers()
        if (!cancelled) setTeamMembers(result.case_managers || [])
      } catch (error) {
        if (!cancelled) {
          setTeamMembers([])
          toast.error(error?.message || 'Failed to load team members')
        }
      } finally {
        if (!cancelled) setTeamLoading(false)
      }
    }
    loadTeam()
    return () => {
      cancelled = true
    }
  }, [])

  const set = (key) => (event) => {
    setForm((current) => ({ ...current, [key]: event.target.value }))
  }

  const handleCreate = async () => {
    if (form.thread_type === 'announcement' && !isAdmin) {
      toast.error('Only supervisors/admins can create announcements')
      return
    }
    if (form.thread_type === 'direct_message' && participants.length === 0) {
      toast.error('Direct messages need a staff recipient')
      return
    }
    if (form.thread_type === 'client_thread' && !form.client_id) {
      toast.error('Choose a client for this thread')
      return
    }
    setSaving(true)
    try {
      const payload = {
        thread_type: form.thread_type,
        title: form.title.trim() || undefined,
        client_id: form.thread_type === 'client_thread' ? form.client_id : undefined,
        purpose: form.purpose.trim() || undefined,
        participants: form.thread_type === 'announcement' ? [] : participants,
        initial_message: form.initial_message.trim() || undefined,
      }
      const result = await messagesAPI.createThread(payload)
      toast.success('Thread created')
      onCreated(result.thread)
    } catch (error) {
      toast.error(error?.message || 'Failed to create thread')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-lg border border-white/10 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-white">New Thread</h2>
            <p className="text-sm text-slate-400">Create an internal Ember conversation.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-300 hover:bg-white/10">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-4 px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Thread type</span>
              <select className="input-field w-full" value={form.thread_type} onChange={set('thread_type')}>
                {THREAD_TYPES.map((type) => (
                  <option key={type.id} value={type.id} disabled={type.id === 'announcement' && !isAdmin}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">Title</span>
              <input className="input-field w-full" value={form.title} onChange={set('title')} placeholder="Optional custom title" />
            </label>
          </div>

          {form.thread_type === 'client_thread' && (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-400">Client</span>
                <select className="input-field w-full" value={form.client_id} onChange={set('client_id')}>
                  <option value="">Select a client</option>
                  {clients.map((client) => (
                    <option key={client.client_id} value={client.client_id}>
                      {client.full_name || `${client.first_name || ''} ${client.last_name || ''}`.trim() || client.client_id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-slate-400">Purpose</span>
                <input className="input-field w-full" value={form.purpose} onChange={set('purpose')} placeholder="Housing plan, appointment, benefits" />
              </label>
              {selectedClient && (
                <div className="sm:col-span-2 rounded-lg border border-cyan-400/20 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100">
                  Client thread title defaults to {selectedClient.full_name || selectedClient.client_id} plus the purpose.
                </div>
              )}
            </div>
          )}

          {form.thread_type !== 'announcement' && (
            <div className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">
                {form.thread_type === 'direct_message' ? 'Recipients' : 'Participants'}
              </span>
              <ParticipantPicker
                members={teamMembers}
                loading={teamLoading}
                selected={participants}
                onChange={setParticipants}
              />
              <p className="mt-1.5 text-[11px] text-slate-500">
                You are added automatically. Pick one or more team members to include.
              </p>
            </div>
          )}

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-400">Initial message</span>
            <textarea
              className="input-field h-24 w-full resize-none"
              value={form.initial_message}
              onChange={set('initial_message')}
              placeholder="Write the first message"
            />
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-white/10 px-5 py-4">
          <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
          <button type="button" onClick={handleCreate} disabled={saving} className="btn-primary gap-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Messages() {
  const { profile } = useAuth()
  const navigate = useNavigate()
  const [threads, setThreads] = useState([])
  const [messages, setMessages] = useState([])
  const [clients, setClients] = useState([])
  const [selectedThreadId, setSelectedThreadId] = useState('')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [composer, setComposer] = useState('')
  const [loading, setLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [showNewThread, setShowNewThread] = useState(false)

  const selectedThread = threads.find((thread) => thread.id === selectedThreadId)
  const isAdmin = profile?.role === 'admin'

  const loadThreads = useCallback(async () => {
    try {
      const result = await messagesAPI.listThreads()
      const nextThreads = result.threads || []
      setThreads(nextThreads)
      setSelectedThreadId((current) => current || nextThreads[0]?.id || '')
    } catch (error) {
      toast.error(error?.message || 'Failed to load threads')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadClients = useCallback(async () => {
    try {
      const result = await clientsAPI.getAll()
      setClients(result.clients || [])
    } catch (error) {
      console.warn('Client list unavailable for messages', error)
    }
  }, [])

  const loadMessages = useCallback(async (threadId) => {
    if (!threadId) return
    setMessagesLoading(true)
    try {
      const result = await messagesAPI.listMessages(threadId)
      setMessages(result.messages || [])
      await messagesAPI.markRead(threadId)
      await loadThreads()
    } catch (error) {
      toast.error(error?.message || 'Failed to load messages')
    } finally {
      setMessagesLoading(false)
    }
  }, [loadThreads])

  useEffect(() => {
    loadThreads()
    loadClients()
  }, [loadClients, loadThreads])

  useEffect(() => {
    if (selectedThreadId) {
      loadMessages(selectedThreadId)
    } else {
      setMessages([])
    }
  }, [loadMessages, selectedThreadId])

  const filteredThreads = useMemo(() => {
    const term = search.trim().toLowerCase()
    return threads.filter((thread) => {
      if (filter !== 'all' && thread.thread_type !== filter) return false
      if (!term) return true
      return [
        thread.title,
        thread.client_name,
        thread.last_message?.body,
        ...(thread.participants || []).map((participant) => participant.display_name || participant.user_id),
      ].filter(Boolean).some((value) => String(value).toLowerCase().includes(term))
    })
  }, [filter, search, threads])

  const handleSend = async (event) => {
    event.preventDefault()
    const body = composer.trim()
    if (!body || !selectedThread) return
    if (selectedThread.thread_type === 'announcement' && !isAdmin) {
      toast.error('Only supervisors/admins can post announcement messages')
      return
    }
    setSending(true)
    try {
      await messagesAPI.sendMessage(selectedThread.id, body)
      setComposer('')
      await loadMessages(selectedThread.id)
      toast.success('Message sent')
    } catch (error) {
      toast.error(error?.message || 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  const handleCreated = async (thread) => {
    setShowNewThread(false)
    await loadThreads()
    setSelectedThreadId(thread.id)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto flex max-w-[96rem] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-lg border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-100">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Internal Ember communication
            </div>
            <h1 className="text-2xl font-semibold tracking-normal text-white">Messages</h1>
          </div>
          <button type="button" onClick={() => setShowNewThread(true)} className="btn-primary gap-2 self-start md:self-auto">
            <Plus className="h-4 w-4" />
            New Thread
          </button>
        </div>

        <div className="rounded-lg border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          Messages are internal to Ember. Do not send sensitive client information through external apps.
        </div>

        <div className="grid min-h-[40rem] overflow-hidden rounded-lg border border-white/10 bg-slate-900/80 lg:grid-cols-[22rem_1fr]">
          <aside className="border-b border-white/10 bg-slate-950/40 lg:border-b-0 lg:border-r">
            <div className="space-y-3 border-b border-white/10 p-4">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  className="input-field w-full pl-9"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search threads"
                />
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {THREAD_FILTERS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setFilter(item.id)}
                    className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      filter === item.id
                        ? 'border-cyan-300/40 bg-cyan-500/20 text-cyan-100'
                        : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="max-h-[34rem] overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-cyan-300" />
                </div>
              ) : filteredThreads.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-slate-400">No matching threads.</div>
              ) : (
                filteredThreads.map((thread) => (
                  <button
                    type="button"
                    key={thread.id}
                    onClick={() => setSelectedThreadId(thread.id)}
                    className={`block w-full border-b border-white/5 px-4 py-3 text-left transition-colors ${
                      selectedThreadId === thread.id ? 'bg-cyan-500/10' : 'hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 text-sm font-semibold text-white">
                          <span className="text-cyan-200"><ThreadIcon type={thread.thread_type} /></span>
                          <span className="truncate">{thread.title}</span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                          <span>{typeLabel[thread.thread_type] || thread.thread_type}</span>
                          {thread.client_name && (
                            <span className="rounded bg-cyan-500/15 px-1.5 py-0.5 text-cyan-100">{thread.client_name}</span>
                          )}
                        </div>
                        <p className="mt-2 line-clamp-2 text-xs text-slate-400">
                          {thread.last_message?.body || 'No messages yet'}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <span className="text-[11px] text-slate-500">{formatTime(thread.updated_at)}</span>
                        {thread.unread_count > 0 && (
                          <span className="rounded-full bg-orange-500 px-2 py-0.5 text-xs font-bold text-white">{thread.unread_count}</span>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>

          <section className="min-w-0">
            {!selectedThread ? (
              <EmptyState onCreate={() => setShowNewThread(true)} />
            ) : (
              <div className="flex h-full min-h-[40rem] flex-col">
                <div className="border-b border-white/10 px-5 py-4">
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div className="min-w-0">
                      <div className="flex min-w-0 items-center gap-2">
                        <span className="text-cyan-200"><ThreadIcon type={selectedThread.thread_type} /></span>
                        <h2 className="truncate text-lg font-semibold text-white">{selectedThread.title}</h2>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                        <span className="rounded bg-white/10 px-2 py-1">{typeLabel[selectedThread.thread_type]}</span>
                        {selectedThread.client_name && (
                          <span className="rounded bg-cyan-500/15 px-2 py-1 text-cyan-100">{selectedThread.client_name}</span>
                        )}
                        <span>{(selectedThread.participants || []).length} participant(s)</span>
                      </div>
                    </div>
                    {selectedThread.client_id && (
                      <button
                        type="button"
                        onClick={() => navigate(`/client/${selectedThread.client_id}`)}
                        className="btn-secondary gap-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Open Client Record
                      </button>
                    )}
                  </div>
                </div>

                <div className="flex-1 space-y-3 overflow-y-auto px-5 py-5">
                  {messagesLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="h-6 w-6 animate-spin text-cyan-300" />
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-white/15 p-8 text-center text-sm text-slate-400">
                      No messages in this thread yet.
                    </div>
                  ) : (
                    messages.map((message) => {
                      const isMine = message.sender_id === profile?.case_manager_id || message.sender_id === profile?.firebase_uid
                      return (
                        <div key={message.id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[42rem] rounded-lg border px-4 py-3 ${
                            isMine
                              ? 'border-cyan-300/20 bg-cyan-500/15'
                              : 'border-white/10 bg-slate-800'
                          }`}>
                            <div className="mb-1 flex items-center gap-2 text-xs text-slate-400">
                              <span className="font-medium text-slate-200">{message.sender_name || message.sender_id}</span>
                              <span>{formatTime(message.created_at)}</span>
                            </div>
                            <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-100">{message.body}</p>
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>

                <form onSubmit={handleSend} className="border-t border-white/10 p-4">
                  {selectedThread.thread_type === 'announcement' && !isAdmin ? (
                    <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-3 text-sm text-slate-300">
                      <Bell className="h-4 w-4 text-amber-300" />
                      Announcements are read-only for case managers.
                    </div>
                  ) : (
                    <div className="flex gap-3">
                      <textarea
                        className="input-field min-h-[3rem] flex-1 resize-none"
                        value={composer}
                        onChange={(event) => setComposer(event.target.value)}
                        placeholder="Type an internal message"
                      />
                      <button type="submit" disabled={sending || !composer.trim()} className="btn-primary h-12 gap-2 self-end">
                        {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        Send
                      </button>
                    </div>
                  )}
                </form>
              </div>
            )}
          </section>
        </div>
      </div>

      {showNewThread && (
        <NewThreadModal
          clients={clients}
          currentUser={profile}
          onClose={() => setShowNewThread(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}

