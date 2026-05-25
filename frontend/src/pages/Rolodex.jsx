import { useEffect, useMemo, useState } from 'react'
import {
  Building2,
  Contact,
  Edit3,
  ExternalLink,
  Mail,
  MapPin,
  Phone,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  User,
} from 'lucide-react'
import toast from 'react-hot-toast'

import LocationSelector from '../components/LocationSelector'
import { apiFetch } from '../api/config'

const emptyForm = {
  name: '',
  category: 'Treatment Centers',
  custom_category: '',
  organization: '',
  role_title: '',
  phone: '',
  email: '',
  website: '',
  address: '',
  city: 'Los Angeles, CA',
  trusted_status: 'Trusted',
  availability_notes: '',
  referral_notes: '',
  general_notes: '',
}

const categoryIcons = {
  'Treatment Centers': '💊',
  'Primary Care': '🩺',
  'Dental': '🦷',
  'Mental Health': '🧠',
  'Substance Use': '💉',
  'Housing': '🏠',
  'Benefits': '💳',
  'Legal': '⚖️',
  'Employment': '💼',
  'Transportation': '🚌',
  'Hospital / ER': '🏥',
  'Pharmacy': '💊',
  'Support Group': '🤝',
  'General Resource': '📚',
  'Custom': '⭐',
}

function Rolodex() {
  const [entries, setEntries] = useState([])
  const [categories, setCategories] = useState([])
  const [trustedStatuses, setTrustedStatuses] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [filters, setFilters] = useState({
    category: 'All',
    search: '',
    city: '',
    trusted_status: 'All',
  })
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState('')

  const loadEntries = async (activeFilters = filters) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeFilters.category) params.set('category', activeFilters.category)
      if (activeFilters.search.trim()) params.set('search', activeFilters.search.trim())
      if (activeFilters.city.trim()) params.set('city', activeFilters.city.trim())
      if (activeFilters.trusted_status) params.set('trusted_status', activeFilters.trusted_status)

      const response = await apiFetch(`/api/rolodex?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load rolodex')
      }
      const data = await response.json()
      setEntries(Array.isArray(data.entries) ? data.entries : [])
      setCategories(Array.isArray(data.categories) ? data.categories : [])
      setTrustedStatuses(Array.isArray(data.trusted_statuses) ? data.trusted_statuses : [])
    } catch (error) {
      console.error('Rolodex load failed:', error)
      toast.error('Failed to load rolodex')
      setEntries([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEntries()
  }, [])

  const groupedPreview = useMemo(() => {
    return entries.reduce((acc, entry) => {
      const label = entry.category === 'Custom' && entry.custom_category
        ? entry.custom_category
        : entry.category
      acc[label] = (acc[label] || 0) + 1
      return acc
    }, {})
  }, [entries])

  const handleFilterChange = (field, value) => {
    const nextFilters = { ...filters, [field]: value }
    setFilters(nextFilters)
  }

  const submitFilters = async (event) => {
    event?.preventDefault?.()
    await loadEntries(filters)
  }

  const resetForm = () => {
    setForm(emptyForm)
    setEditingId('')
  }

  const startEdit = (entry) => {
    setEditingId(entry.id)
    setForm({
      name: entry.name || '',
      category: entry.category || 'Treatment Centers',
      custom_category: entry.custom_category || '',
      organization: entry.organization || '',
      role_title: entry.role_title || '',
      phone: entry.phone || '',
      email: entry.email || '',
      website: entry.website || '',
      address: entry.address || '',
      city: entry.city || '',
      trusted_status: entry.trusted_status || 'Trusted',
      availability_notes: entry.availability_notes || '',
      referral_notes: entry.referral_notes || '',
      general_notes: entry.general_notes || '',
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const saveEntry = async (event) => {
    event.preventDefault()
    if (!form.name.trim()) {
      toast.error('Name is required')
      return
    }
    if (form.category === 'Custom' && !form.custom_category.trim()) {
      toast.error('Custom category name is required')
      return
    }

    setSaving(true)
    try {
      const endpoint = editingId ? `/api/rolodex/${editingId}` : '/api/rolodex'
      const method = editingId ? 'PUT' : 'POST'
      const response = await apiFetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to save entry')
      }

      toast.success(editingId ? 'Rolodex entry updated' : 'Rolodex entry added')
      resetForm()
      await loadEntries(filters)
    } catch (error) {
      console.error('Rolodex save failed:', error)
      toast.error(error.message || 'Failed to save entry')
    } finally {
      setSaving(false)
    }
  }

  const deleteEntry = async (entryId) => {
    if (!window.confirm('Delete this rolodex entry?')) return

    try {
      const response = await apiFetch(`/api/rolodex/${entryId}`, { method: 'DELETE' })
      if (!response.ok) {
        throw new Error('Failed to delete entry')
      }
      toast.success('Rolodex entry deleted')
      if (editingId === entryId) resetForm()
      await loadEntries(filters)
    } catch (error) {
      console.error('Rolodex delete failed:', error)
      toast.error('Failed to delete entry')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-4 py-10 text-white">
      <div className="mx-auto max-w-7xl space-y-8">
        <section className="rounded-[32px] border border-white/10 bg-white/5 p-8 shadow-2xl shadow-purple-900/30 backdrop-blur-xl">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-3 rounded-2xl bg-teal-500/15 px-4 py-2 text-sm font-medium text-teal-200">
                <Contact className="h-4 w-4" />
                Case Manager Rolodex
              </div>
              <h1 className="text-4xl font-bold tracking-tight text-white md:text-5xl">
                Trusted contacts and referral shortcuts
              </h1>
              <p className="mt-3 text-lg text-purple-100/80">
                Keep the providers, lawyers, treatment centers, PCPs, dentists, and go-to resources your team actually uses,
                with practical notes like scheduling quirks, intake preferences, and referral tips.
              </p>
            </div>
            <div className="grid min-w-[280px] grid-cols-2 gap-3 rounded-3xl border border-white/10 bg-slate-950/30 p-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Saved contacts</p>
                <p className="mt-2 text-3xl font-semibold text-white">{entries.length}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Active categories</p>
                <p className="mt-2 text-3xl font-semibold text-white">{Object.keys(groupedPreview).length}</p>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-8 xl:grid-cols-[420px_minmax(0,1fr)]">
          <section className="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-xl shadow-purple-900/20 backdrop-blur-xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-white">{editingId ? 'Edit contact' : 'Add trusted contact'}</h2>
                <p className="mt-1 text-sm text-purple-100/70">
                  Save the provider details and the real-world notes your staff actually needs.
                </p>
              </div>
              {editingId ? (
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
                >
                  New entry
                </button>
              ) : null}
            </div>

            <form onSubmit={saveEntry} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">Contact or provider name</label>
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  placeholder="Dr. Maria Lopez, Homeboy Dental, Smith & Associates"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Category</label>
                  <select
                    value={form.category}
                    onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    {(categories.length ? categories : ['Treatment Centers', 'Custom']).map((category) => (
                      <option key={category} value={category} className="bg-slate-900">
                        {category}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Trust status</label>
                  <select
                    value={form.trusted_status}
                    onChange={(event) => setForm((current) => ({ ...current, trusted_status: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    {(trustedStatuses.length ? trustedStatuses : ['Trusted']).map((status) => (
                      <option key={status} value={status} className="bg-slate-900">
                        {status}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {form.category === 'Custom' ? (
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Custom category name</label>
                  <input
                    value={form.custom_category}
                    onChange={(event) => setForm((current) => ({ ...current, custom_category: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="Immigration, Victim Services, Psychiatrist, etc."
                  />
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Organization</label>
                  <input
                    value={form.organization}
                    onChange={(event) => setForm((current) => ({ ...current, organization: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="AltaMed, Downtown Women’s Center, Public Counsel"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Role or specialty</label>
                  <input
                    value={form.role_title}
                    onChange={(event) => setForm((current) => ({ ...current, role_title: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="PCP, intake coordinator, family law attorney"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Phone</label>
                  <input
                    value={form.phone}
                    onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="(213) 555-0192"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Email</label>
                  <input
                    value={form.email}
                    onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="intake@example.org"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">Website</label>
                <input
                  value={form.website}
                  onChange={(event) => setForm((current) => ({ ...current, website: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  placeholder="https://provider-site.org"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">Address</label>
                  <input
                    value={form.address}
                    onChange={(event) => setForm((current) => ({ ...current, address: event.target.value }))}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                    placeholder="123 Main St, Suite 400"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">City</label>
                  <LocationSelector
                    value={form.city}
                    onChange={(value) => setForm((current) => ({ ...current, city: value }))}
                    placeholder="City or ZIP"
                    allowManualEntry
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">Availability notes</label>
                <textarea
                  rows={2}
                  value={form.availability_notes}
                  onChange={(event) => setForm((current) => ({ ...current, availability_notes: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  placeholder="Only works Fridays, ask for Sonia after 1pm, walk-ins before 10am, no calls on Mondays."
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">Referral notes</label>
                <textarea
                  rows={3}
                  value={form.referral_notes}
                  onChange={(event) => setForm((current) => ({ ...current, referral_notes: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  placeholder="Best for DOC clients with Medi-Cal, ask for urgent intake slot, send ROI before faxing packet."
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">General notes</label>
                <textarea
                  rows={4}
                  value={form.general_notes}
                  onChange={(event) => setForm((current) => ({ ...current, general_notes: event.target.value }))}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  placeholder="Any extra context the team should know about this contact."
                />
              </div>

              <button
                type="submit"
                disabled={saving}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-teal-500 to-cyan-500 px-4 py-3 font-semibold text-white transition hover:scale-[1.01] hover:shadow-xl hover:shadow-cyan-900/40 disabled:cursor-not-allowed disabled:opacity-70"
              >
                <Plus className="h-4 w-4" />
                {saving ? 'Saving...' : editingId ? 'Update contact' : 'Add to rolodex'}
              </button>
            </form>
          </section>

          <section className="space-y-6">
            <form
              onSubmit={submitFilters}
              className="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-xl shadow-purple-900/20 backdrop-blur-xl"
            >
              <div className="flex flex-col gap-4 lg:flex-row">
                <div className="flex-1">
                  <label className="mb-2 block text-sm font-medium text-slate-200">Search contacts or notes</label>
                  <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3">
                    <Search className="h-4 w-4 text-slate-400" />
                    <input
                      value={filters.search}
                      onChange={(event) => handleFilterChange('search', event.target.value)}
                      className="w-full bg-transparent text-white outline-none placeholder:text-slate-500"
                      placeholder="Dentist, probation-friendly, Fridays, transportation, legal aid..."
                    />
                  </div>
                </div>
                <div className="lg:w-56">
                  <label className="mb-2 block text-sm font-medium text-slate-200">Category</label>
                  <select
                    value={filters.category}
                    onChange={(event) => handleFilterChange('category', event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    <option value="All" className="bg-slate-900">All</option>
                    {categories.map((category) => (
                      <option key={category} value={category} className="bg-slate-900">{category}</option>
                    ))}
                  </select>
                </div>
                <div className="lg:w-56">
                  <label className="mb-2 block text-sm font-medium text-slate-200">Trust status</label>
                  <select
                    value={filters.trusted_status}
                    onChange={(event) => handleFilterChange('trusted_status', event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                  >
                    <option value="All" className="bg-slate-900">All</option>
                    {trustedStatuses.map((status) => (
                      <option key={status} value={status} className="bg-slate-900">{status}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end">
                <div className="flex-1">
                  <label className="mb-2 block text-sm font-medium text-slate-200">City</label>
                  <LocationSelector
                    value={filters.city}
                    onChange={(value) => handleFilterChange('city', value)}
                    placeholder="All cities"
                    allowManualEntry
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="submit"
                    className="rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 px-5 py-3 font-semibold text-white transition hover:scale-[1.01]"
                  >
                    Search
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const cleared = { category: 'All', search: '', city: '', trusted_status: 'All' }
                      setFilters(cleared)
                      loadEntries(cleared)
                    }}
                    className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 font-semibold text-slate-200 transition hover:bg-white/10"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {Object.keys(groupedPreview).length > 0 ? (
                <div className="mt-5 flex flex-wrap gap-2">
                  {Object.entries(groupedPreview).map(([label, count]) => (
                    <span key={label} className="rounded-full border border-white/10 bg-slate-950/30 px-3 py-1 text-xs text-slate-200">
                      {categoryIcons[label] || '•'} {label} · {count}
                    </span>
                  ))}
                </div>
              ) : null}
            </form>

            <section className="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-xl shadow-purple-900/20 backdrop-blur-xl">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-semibold text-white">Saved rolodex entries</h2>
                  <p className="mt-1 text-sm text-purple-100/70">
                    Your real-world contact list for trusted referrals and quick coordination.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-2 text-sm text-slate-200">
                  {loading ? 'Loading...' : `${entries.length} contact${entries.length === 1 ? '' : 's'}`}
                </div>
              </div>

              {loading ? (
                <div className="rounded-3xl border border-dashed border-white/10 bg-slate-950/20 px-6 py-12 text-center text-slate-300">
                  Loading rolodex entries...
                </div>
              ) : entries.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-white/10 bg-slate-950/20 px-6 py-12 text-center">
                  <Contact className="mx-auto h-12 w-12 text-slate-500" />
                  <h3 className="mt-4 text-xl font-semibold text-white">No trusted contacts saved yet</h3>
                  <p className="mt-2 text-sm text-slate-300">
                    Add the treatment centers, dentists, PCPs, lawyers, and resource contacts your team actually uses.
                  </p>
                </div>
              ) : (
                <div className="grid gap-4 xl:grid-cols-2">
                  {entries.map((entry) => {
                    const categoryLabel = entry.category === 'Custom' && entry.custom_category
                      ? entry.custom_category
                      : entry.category
                    return (
                      <article
                        key={entry.id}
                        className="rounded-3xl border border-white/10 bg-slate-950/25 p-5 transition hover:border-cyan-400/30 hover:bg-slate-950/35"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-cyan-200">
                                {categoryIcons[categoryLabel] || '•'} {categoryLabel}
                              </span>
                              <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs text-emerald-200">
                                <ShieldCheck className="mr-1 inline h-3 w-3" />
                                {entry.trusted_status || 'Trusted'}
                              </span>
                            </div>
                            <h3 className="mt-3 text-xl font-semibold text-white">{entry.name}</h3>
                            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-300">
                              {entry.organization ? <span className="inline-flex items-center gap-1"><Building2 className="h-4 w-4 text-slate-400" />{entry.organization}</span> : null}
                              {entry.role_title ? <span className="inline-flex items-center gap-1"><User className="h-4 w-4 text-slate-400" />{entry.role_title}</span> : null}
                            </div>
                          </div>

                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => startEdit(entry)}
                              className="rounded-xl border border-white/10 bg-white/5 p-2 text-slate-200 transition hover:bg-white/10"
                            >
                              <Edit3 className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => deleteEntry(entry.id)}
                              className="rounded-xl border border-red-400/20 bg-red-500/10 p-2 text-red-200 transition hover:bg-red-500/20"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 space-y-2 text-sm text-slate-200">
                          {entry.phone ? <div className="flex items-start gap-2"><Phone className="mt-0.5 h-4 w-4 text-cyan-300" /><a href={`tel:${entry.phone}`} className="hover:text-white">{entry.phone}</a></div> : null}
                          {entry.email ? <div className="flex items-start gap-2"><Mail className="mt-0.5 h-4 w-4 text-cyan-300" /><a href={`mailto:${entry.email}`} className="break-all hover:text-white">{entry.email}</a></div> : null}
                          {entry.address || entry.city ? <div className="flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4 text-cyan-300" /><span>{[entry.address, entry.city].filter(Boolean).join(', ')}</span></div> : null}
                          {entry.website ? (
                            <div className="flex items-start gap-2">
                              <ExternalLink className="mt-0.5 h-4 w-4 text-cyan-300" />
                              <button
                                type="button"
                                onClick={() => window.open(entry.website, '_blank', 'noopener,noreferrer')}
                                className="break-all text-left text-cyan-200 hover:text-white"
                              >
                                Visit website
                              </button>
                            </div>
                          ) : null}
                        </div>

                        {entry.availability_notes ? (
                          <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200">Availability notes</p>
                            <p className="mt-1 text-sm text-amber-50">{entry.availability_notes}</p>
                          </div>
                        ) : null}

                        {entry.referral_notes ? (
                          <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">Referral notes</p>
                            <p className="mt-1 text-sm text-cyan-50">{entry.referral_notes}</p>
                          </div>
                        ) : null}

                        {entry.general_notes ? (
                          <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">General notes</p>
                            <p className="mt-1 text-sm text-slate-100">{entry.general_notes}</p>
                          </div>
                        ) : null}
                      </article>
                    )
                  })}
                </div>
              )}
            </section>
          </section>
        </div>
      </div>
    </div>
  )
}

export default Rolodex
