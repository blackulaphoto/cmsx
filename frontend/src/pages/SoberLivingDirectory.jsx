import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileSpreadsheet, Filter, Plus, RefreshCw, Search, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import DirectoryListingCard from '../components/DirectoryListingCard'
import { buildListingPayload, defaultListingForm, soberLivingDirectoryApi } from '../utils/soberLivingDirectory'

function SoberLivingDirectory() {
  const [filters, setFilters] = useState({
    search: '',
    city: '',
    population_served: '',
    certification: '',
    accepts_mat: '',
    status: '',
    min_trust_score: '',
  })
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formState, setFormState] = useState(defaultListingForm)
  const [saving, setSaving] = useState(false)
  const [importFile, setImportFile] = useState(null)
  const [importSourceName, setImportSourceName] = useState('CA Sober Living Directory')
  const [importing, setImporting] = useState(false)
  const [importSummary, setImportSummary] = useState(null)

  const loadListings = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await soberLivingDirectoryApi.listListings(filters)
      setListings(data.listings || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadListings()
  }, [])

  const filterOptions = useMemo(() => {
    const cities = Array.from(new Set(listings.map((item) => item.city).filter(Boolean))).sort()
    const populations = Array.from(new Set(listings.map((item) => item.population_served).filter(Boolean))).sort()
    return { cities, populations }
  }, [listings])

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const applyFilters = async (event) => {
    event.preventDefault()
    await loadListings()
  }

  const resetFilters = async () => {
    const resetState = {
      search: '',
      city: '',
      population_served: '',
      certification: '',
      accepts_mat: '',
      status: '',
      min_trust_score: '',
    }
    setFilters(resetState)
    setLoading(true)
    setError('')
    try {
      const data = await soberLivingDirectoryApi.listListings(resetState)
      setListings(data.listings || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!formState.name.trim() || !formState.city.trim()) {
      toast.error('Name and city are required')
      return
    }
    setSaving(true)
    try {
      await soberLivingDirectoryApi.createListing(buildListingPayload(formState))
      toast.success('Sober living listing added')
      setFormState(defaultListingForm)
      setShowCreateForm(false)
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Failed to create listing')
    } finally {
      setSaving(false)
    }
  }

  const handleImport = async (event) => {
    event.preventDefault()
    if (!importFile) {
      toast.error('Choose a CSV or XLSX file to import')
      return
    }
    setImporting(true)
    try {
      const data = await soberLivingDirectoryApi.importListings({
        file: importFile,
        sourceName: importSourceName.trim() || 'Manual directory import',
      })
      setImportSummary(data.summary)
      setImportFile(null)
      toast.success(`Imported ${data.summary.listings_created} new listings`)
      await loadListings()
    } catch (err) {
      toast.error(err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-slate-950/40">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Referral Intelligence</p>
              <h1 className="mt-2 text-3xl font-bold text-white">Sober Living Directory</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                External sober living referral database with manual review, verification tracking, trust scoring, and preservation of stale records.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/sober-living-directory/discovery"
                className="rounded-2xl border border-fuchsia-400/30 bg-fuchsia-500/15 px-4 py-3 text-sm font-medium text-fuchsia-100 transition hover:bg-fuchsia-500/25"
              >
                Discovery
              </Link>
              <Link
                to="/sober-living-directory/review"
                className="rounded-2xl border border-amber-400/30 bg-amber-500/15 px-4 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-500/25"
              >
                Open Review Queue
              </Link>
              <button
                type="button"
                onClick={() => setShowCreateForm((prev) => !prev)}
                className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                <Plus className="h-4 w-4" />
                Add Listing
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-fuchsia-200">Controlled Discovery</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">CCAPP and Oxford connectors live in Discovery Controls</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Manual upload is only one intake path. Public directory connectors for CCAPP Recovery Residences and Oxford House are configured and run from
                the discovery workspace, where every result stays raw and review-gated before it can become a trusted directory listing.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/sober-living-directory/discovery"
                className="rounded-2xl border border-cyan-400/30 bg-cyan-500/15 px-4 py-3 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/25"
              >
                Open Discovery Controls
              </Link>
              <Link
                to="/sober-living-directory/review"
                className="rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/10"
              >
                Review Raw Records
              </Link>
            </div>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <ConnectorCard
              eyebrow="Certification Directory"
              name="CCAPP Recovery Residences"
              description="Bounded public certification-directory discovery. Best for higher-trust recovery residence leads that still require human review."
              bullets={[
                'Run from the Discovery page with a manual job by city and state.',
                'Results land in raw records and duplicate review, never directly in approved listings.',
              ]}
            />
            <ConnectorCard
              eyebrow="Public Recovery Housing Directory"
              name="Oxford House"
              description="Bounded Oxford vacancy discovery for public recovery housing results. Useful for sober living referrals that may not appear in certification lists."
              bullets={[
                'Run from the Discovery page with a manual Oxford job.',
                'Visible public rows are reviewed before approval, and inferred state stays flagged in review.',
              ]}
            />
          </div>
        </section>

        {showCreateForm ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">New Sober Living Listing</h2>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="text-sm text-slate-300 underline underline-offset-4"
              >
                Close
              </button>
            </div>
            <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={handleCreate}>
              <Input label="Name" value={formState.name} onChange={(value) => setFormState((prev) => ({ ...prev, name: value }))} required />
              <Input label="Operator Name" value={formState.operator_name} onChange={(value) => setFormState((prev) => ({ ...prev, operator_name: value }))} />
              <Input label="Phone" value={formState.phone} onChange={(value) => setFormState((prev) => ({ ...prev, phone: value }))} />
              <Input label="Email" value={formState.email} onChange={(value) => setFormState((prev) => ({ ...prev, email: value }))} />
              <Input label="Address" value={formState.address} onChange={(value) => setFormState((prev) => ({ ...prev, address: value }))} />
              <Input label="City" value={formState.city} onChange={(value) => setFormState((prev) => ({ ...prev, city: value }))} required />
              <Input label="State" value={formState.state} onChange={(value) => setFormState((prev) => ({ ...prev, state: value }))} />
              <Input label="Website" value={formState.website} onChange={(value) => setFormState((prev) => ({ ...prev, website: value }))} />
              <Input label="Population Served" value={formState.population_served} onChange={(value) => setFormState((prev) => ({ ...prev, population_served: value }))} />
              <Input label="Certification Status" value={formState.certification_status} onChange={(value) => setFormState((prev) => ({ ...prev, certification_status: value }))} />
              <Input label="Certification Body" value={formState.certification_body} onChange={(value) => setFormState((prev) => ({ ...prev, certification_body: value }))} />
              <Select
                label="Status"
                value={formState.status}
                onChange={(value) => setFormState((prev) => ({ ...prev, status: value }))}
                options={[
                  'pending_review',
                  'approved',
                  'needs_reverification',
                  'use_caution',
                  'do_not_refer',
                  'archived',
                ]}
              />
              <Toggle label="Accepts MAT" checked={formState.accepts_mat} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_mat: value }))} />
              <Toggle label="Accepts Insurance" checked={formState.accepts_insurance} onChange={(value) => setFormState((prev) => ({ ...prev, accepts_insurance: value }))} />
              <Toggle label="Deposit Required" checked={formState.deposit_required} onChange={(value) => setFormState((prev) => ({ ...prev, deposit_required: value }))} />
              <Toggle label="Pets Allowed" checked={formState.pets_allowed} onChange={(value) => setFormState((prev) => ({ ...prev, pets_allowed: value }))} />
              <TextArea label="Notes" value={formState.notes} onChange={(value) => setFormState((prev) => ({ ...prev, notes: value }))} className="md:col-span-2" />
              <TextArea label="Internal Referral Notes" value={formState.internal_referral_notes} onChange={(value) => setFormState((prev) => ({ ...prev, internal_referral_notes: value }))} className="md:col-span-2" />
              <div className="md:col-span-2 xl:col-span-4 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? 'Saving...' : 'Create Listing'}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-cyan-200">
                <FileSpreadsheet className="h-3.5 w-3.5" />
                Phase 2 Import
              </div>
              <h2 className="mt-3 text-xl font-semibold text-white">Import CSV or XLSX into Review Workflow</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Imports land in raw listings first and create or update directory records as <span className="font-medium text-white">pending review</span>. No rows are auto-approved.
              </p>
            </div>
          </div>
          <form className="mt-5 grid gap-4 lg:grid-cols-[1.4fr_1fr_auto]" onSubmit={handleImport}>
            <Input label="Source Name" value={importSourceName} onChange={setImportSourceName} />
            <label className="block">
              <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Import File</span>
              <input
                type="file"
                accept=".xlsx,.csv"
                onChange={(event) => setImportFile(event.target.files?.[0] || null)}
                className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition file:mr-4 file:rounded-xl file:border-0 file:bg-cyan-500 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-cyan-400"
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={importing}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Upload className="h-4 w-4" />
                {importing ? 'Importing...' : 'Run Import'}
              </button>
            </div>
          </form>
          {importSummary ? (
            <div className="mt-5 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <SummaryCard label="Rows Read" value={importSummary.rows_read} />
              <SummaryCard label="Raw Created" value={importSummary.raw_created} />
              <SummaryCard label="New Listings" value={importSummary.listings_created} />
              <SummaryCard label="Updated" value={importSummary.listings_updated} />
              <SummaryCard label="Duplicates" value={importSummary.duplicates_detected} />
              <SummaryCard label="Errors" value={importSummary.errors?.length || 0} danger={Boolean(importSummary.errors?.length)} />
            </div>
          ) : null}
          {importSummary?.errors?.length ? (
            <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">
              {importSummary.errors.slice(0, 5).map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          ) : null}
        </section>

        <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
          <form className="grid gap-3 lg:grid-cols-7" onSubmit={applyFilters}>
            <Input icon={Search} label="Search" value={filters.search} onChange={(value) => handleFilterChange('search', value)} />
            <Select label="City" value={filters.city} onChange={(value) => handleFilterChange('city', value)} options={filterOptions.cities} allowBlank />
            <Select label="Population" value={filters.population_served} onChange={(value) => handleFilterChange('population_served', value)} options={filterOptions.populations} allowBlank />
            <Input label="Certification" value={filters.certification} onChange={(value) => handleFilterChange('certification', value)} />
            <Select label="MAT" value={filters.accepts_mat} onChange={(value) => handleFilterChange('accepts_mat', value)} options={['true', 'false']} allowBlank />
            <Select
              label="Status"
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              options={['pending_review', 'approved', 'needs_reverification', 'use_caution', 'do_not_refer', 'archived']}
              allowBlank
            />
            <Input label="Min Trust" value={filters.min_trust_score} onChange={(value) => handleFilterChange('min_trust_score', value)} type="number" />
            <div className="lg:col-span-7 flex flex-wrap gap-3 pt-1">
              <button type="submit" className="inline-flex items-center gap-2 rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white hover:bg-white/15">
                <Filter className="h-4 w-4" />
                Apply Filters
              </button>
              <button type="button" onClick={resetFilters} className="inline-flex items-center gap-2 rounded-2xl border border-white/15 px-4 py-3 text-sm font-medium text-slate-200 hover:bg-white/10">
                <RefreshCw className="h-4 w-4" />
                Reset
              </button>
            </div>
          </form>
        </section>

        {loading ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-slate-300">Loading sober living directory...</section>
        ) : error ? (
          <section className="rounded-[2rem] border border-red-400/30 bg-red-500/10 p-10 text-center text-red-100">
            Failed to load directory: {error}
          </section>
        ) : listings.length === 0 ? (
          <section className="rounded-[2rem] border border-white/10 bg-white/5 p-10 text-center text-slate-300">
            No sober living listings match the current filters. Add a listing to start the referral directory.
          </section>
        ) : (
          <section className="grid gap-4 lg:grid-cols-2">
            {listings.map((listing) => (
              <DirectoryListingCard key={listing.listing_id} listing={listing} />
            ))}
          </section>
        )}
      </div>
    </div>
  )
}

function Input({ label, value, onChange, icon: Icon, type = 'text', required = false, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <div className="relative">
        {Icon ? <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" /> : null}
        <input
          type={type}
          value={value}
          required={required}
          onChange={(event) => onChange(event.target.value)}
          className={`w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50 ${Icon ? 'pl-10' : ''}`}
        />
      </div>
    </label>
  )
}

function Select({ label, value, onChange, options = [], allowBlank = false }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      >
        {allowBlank ? <option value="">All</option> : null}
        {options.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll('_', ' ')}
          </option>
        ))}
      </select>
    </label>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-sm text-white">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 rounded border-white/20 bg-slate-900" />
    </label>
  )
}

function TextArea({ label, value, onChange, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
      />
    </label>
  )
}

function SummaryCard({ label, value, danger = false }) {
  return (
    <div className={`rounded-2xl border p-4 ${danger ? 'border-red-400/30 bg-red-500/10' : 'border-white/10 bg-slate-950/35'}`}>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${danger ? 'text-red-100' : 'text-white'}`}>{value}</p>
    </div>
  )
}

function ConnectorCard({ eyebrow, name, description, bullets }) {
  return (
    <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/35 p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-cyan-300">{eyebrow}</p>
      <h3 className="mt-2 text-lg font-semibold text-white">{name}</h3>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
      <ul className="mt-4 space-y-2 text-sm text-slate-200">
        {bullets.map((bullet) => (
          <li key={bullet} className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-2">
            {bullet}
          </li>
        ))}
      </ul>
    </article>
  )
}

export default SoberLivingDirectory
