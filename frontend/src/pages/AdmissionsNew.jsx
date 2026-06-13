import { useMemo, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ClipboardCheck,
  ArrowLeft,
  ArrowRight,
  Info,
  AlertCircle,
  Loader2,
  UserPlus,
  Users,
} from 'lucide-react'
import { apiFetch } from '../api/config'
import ClientSelector from '../components/ClientSelector'
import { useAuth } from '../contexts/AuthContext'
import { buildSharedProfile, buildSharedProfileFromClient } from '../utils/admissionsProfile'

const EMPTY_NEW_CLIENT = {
  first_name: '',
  last_name: '',
  date_of_birth: '',
  phone: '',
  email: '',
  address: '',
  city: '',
  state: 'CA',
  zip_code: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  emergency_contact_relationship: '',
  intake_date: '',
  program_type: '',
  insurance_provider: '',
  insurance_plan_name: '',
  insurance_member_id: '',
}

function OptionCard({ active, icon: Icon, title, description, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'flex items-start gap-3 rounded-2xl border p-4 text-left transition-colors',
        active
          ? 'bg-cyan-500/12 border-cyan-500/30'
          : 'bg-white/4 border-white/10 hover:bg-white/6',
      ].join(' ')}
    >
      <div className={`rounded-xl p-2 ${active ? 'bg-cyan-500/20' : 'bg-white/8'}`}>
        <Icon className={`h-4 w-4 ${active ? 'text-cyan-200' : 'text-gray-300'}`} />
      </div>
      <div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="mt-1 text-xs leading-relaxed text-gray-400">{description}</p>
      </div>
    </button>
  )
}

function Field({ label, required = false, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-gray-300">
        {label}
        {required && <span className="ml-1 text-rose-400">*</span>}
      </span>
      {children}
    </label>
  )
}

const inputClassName =
  'w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/40 focus:border-cyan-500/30 transition-colors'

export default function AdmissionsNew() {
  const navigate = useNavigate()
  const { profile } = useAuth()
  const [mode, setMode] = useState('existing')
  const [selectedClient, setSelectedClient] = useState(null)
  const [newClient, setNewClient] = useState(EMPTY_NEW_CLIENT)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const sharedProfilePreview = useMemo(() => {
    if (mode === 'existing') {
      return selectedClient ? buildSharedProfileFromClient(selectedClient) : {}
    }
    return buildSharedProfile({
      first_name: newClient.first_name,
      last_name: newClient.last_name,
      date_of_birth: newClient.date_of_birth,
      phone: newClient.phone,
      email: newClient.email,
      address: newClient.address,
      city: newClient.city,
      state: newClient.state,
      zip: newClient.zip_code,
      emergency_contact_name: newClient.emergency_contact_name,
      emergency_contact_phone: newClient.emergency_contact_phone,
      emergency_contact_relationship: newClient.emergency_contact_relationship,
      admission_date: newClient.intake_date,
      program: newClient.program_type,
      insurance_provider: newClient.insurance_provider,
      insurance_plan_name: newClient.insurance_plan_name,
      insurance_member_id: newClient.insurance_member_id,
    })
  }, [mode, newClient, selectedClient])

  const handleClientSelect = (client) => {
    setSelectedClient(client)
    setError(null)
  }

  const handleNewClientChange = (field, value) => {
    setNewClient((current) => ({ ...current, [field]: value }))
    setError(null)
  }

  const createClientFromAdmissions = async () => {
    if (!newClient.first_name.trim() || !newClient.last_name.trim()) {
      throw new Error('First name and last name are required to create a client from Admissions.')
    }

    const response = await apiFetch('/api/clients', {
      method: 'POST',
      body: JSON.stringify({
        first_name: newClient.first_name.trim(),
        last_name: newClient.last_name.trim(),
        date_of_birth: newClient.date_of_birth || null,
        phone: newClient.phone || null,
        email: newClient.email || null,
        address: newClient.address || null,
        city: newClient.city || null,
        state: newClient.state || 'CA',
        zip_code: newClient.zip_code || null,
        emergency_contact_name: newClient.emergency_contact_name || null,
        emergency_contact_phone: newClient.emergency_contact_phone || null,
        emergency_contact_relationship: newClient.emergency_contact_relationship || null,
        intake_date: newClient.intake_date || null,
        program_type: newClient.program_type || null,
        case_manager_id: profile?.case_manager_id || 'cm_admissions',
      }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || `Client creation failed (${response.status})`)
    }
    return data.client
  }

  const handleStartPacket = async () => {
    setLoading(true)
    setError(null)
    try {
      const client =
        mode === 'existing'
          ? selectedClient
          : await createClientFromAdmissions()

      if (!client?.client_id) {
        throw new Error('Admissions could not resolve a client record for this packet.')
      }

      const sharedProfile = mode === 'existing'
        ? buildSharedProfileFromClient(client)
        : sharedProfilePreview

      const res = await apiFetch('/api/admissions/packets', {
        method: 'POST',
        body: JSON.stringify({
          client_id: client.client_id,
          client_name: client.full_name || `${client.first_name || ''} ${client.last_name || ''}`.trim(),
          shared_profile: sharedProfile,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || `Admissions packet start failed (${res.status})`)
      }
      navigate(`/admissions/${client.client_id}`)
    } catch (err) {
      setError(err.message || 'Failed to start admission packet.')
    } finally {
      setLoading(false)
    }
  }

  const canStart =
    mode === 'existing'
      ? Boolean(selectedClient?.client_id)
      : Boolean(newClient.first_name.trim() && newClient.last_name.trim())

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <Link
          to="/admissions"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 transition-colors hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Admissions
        </Link>

        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 p-2.5 shadow-lg shadow-cyan-500/25">
            <ClipboardCheck className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Start Full Admission</h1>
            <p className="text-sm text-gray-400">
              Open the advanced intake packet for an existing client or create a new client directly here.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-4">
          <Info className="mt-0.5 h-4 w-4 flex-shrink-0 text-cyan-400" />
          <p className="text-sm leading-relaxed text-cyan-200">
            Quick Intake remains available, but it is no longer required. Admissions now seeds the full packet and shared client autofill directly.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <OptionCard
            active={mode === 'existing'}
            icon={Users}
            title="Select Existing Client"
            description="Attach the packet to an existing CMSX client and autofill from that profile."
            onClick={() => setMode('existing')}
          />
          <OptionCard
            active={mode === 'new'}
            icon={UserPlus}
            title="Create New Client"
            description="Capture core demographics here, create the client automatically, and continue the full packet."
            onClick={() => setMode('new')}
          />
        </div>

        {mode === 'existing' ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-white">Use information from selected client</h2>
              <p className="mt-1 text-xs text-gray-400">
                Selecting a client preloads packet demographics, contact information, and any existing core profile data.
              </p>
            </div>

            <ClientSelector
              selectedClientId={null}
              onClientSelect={handleClientSelect}
              showCreateNew={false}
              showViewDashboard={false}
              placeholder="Search for an existing client..."
            />

            {selectedClient && (
              <div className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/8 p-3">
                <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 text-sm font-semibold text-white">
                  {(selectedClient.first_name?.[0] || '?').toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-white">
                    {selectedClient.first_name} {selectedClient.last_name}
                  </p>
                  <p className="truncate text-xs text-gray-400">
                    ID: {selectedClient.client_id}
                    {selectedClient.date_of_birth ? ` · DOB: ${selectedClient.date_of_birth}` : ''}
                  </p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 space-y-5">
            <div>
              <h2 className="text-sm font-semibold text-white">Create new client in Admissions</h2>
              <p className="mt-1 text-xs text-gray-400">
                The client record is created from this intake flow, then the full packet opens with the same shared profile data.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Field label="First name" required>
                <input
                  value={newClient.first_name}
                  onChange={(event) => handleNewClientChange('first_name', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Last name" required>
                <input
                  value={newClient.last_name}
                  onChange={(event) => handleNewClientChange('last_name', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Date of birth">
                <input
                  type="date"
                  value={newClient.date_of_birth}
                  onChange={(event) => handleNewClientChange('date_of_birth', event.target.value)}
                  className={`${inputClassName} [color-scheme:dark]`}
                />
              </Field>
              <Field label="Admission date">
                <input
                  type="date"
                  value={newClient.intake_date}
                  onChange={(event) => handleNewClientChange('intake_date', event.target.value)}
                  className={`${inputClassName} [color-scheme:dark]`}
                />
              </Field>
              <Field label="Phone">
                <input
                  value={newClient.phone}
                  onChange={(event) => handleNewClientChange('phone', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Email">
                <input
                  value={newClient.email}
                  onChange={(event) => handleNewClientChange('email', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Address">
                <input
                  value={newClient.address}
                  onChange={(event) => handleNewClientChange('address', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Program">
                <input
                  value={newClient.program_type}
                  onChange={(event) => handleNewClientChange('program_type', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="City">
                <input
                  value={newClient.city}
                  onChange={(event) => handleNewClientChange('city', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="State">
                <input
                  value={newClient.state}
                  onChange={(event) => handleNewClientChange('state', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="ZIP">
                <input
                  value={newClient.zip_code}
                  onChange={(event) => handleNewClientChange('zip_code', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Emergency contact">
                <input
                  value={newClient.emergency_contact_name}
                  onChange={(event) => handleNewClientChange('emergency_contact_name', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Emergency contact phone">
                <input
                  value={newClient.emergency_contact_phone}
                  onChange={(event) => handleNewClientChange('emergency_contact_phone', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Emergency relationship">
                <input
                  value={newClient.emergency_contact_relationship}
                  onChange={(event) => handleNewClientChange('emergency_contact_relationship', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Insurance provider">
                <input
                  value={newClient.insurance_provider}
                  onChange={(event) => handleNewClientChange('insurance_provider', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Plan name">
                <input
                  value={newClient.insurance_plan_name}
                  onChange={(event) => handleNewClientChange('insurance_plan_name', event.target.value)}
                  className={inputClassName}
                />
              </Field>
              <Field label="Policy / member ID">
                <input
                  value={newClient.insurance_member_id}
                  onChange={(event) => handleNewClientChange('insurance_member_id', event.target.value)}
                  className={inputClassName}
                />
              </Field>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-300">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        <div className="rounded-2xl border border-white/10 bg-white/4 p-5">
          <p className="text-sm font-medium text-white">Autofill packet fields from client profile</p>
          <p className="mt-1 text-xs text-gray-400">
            Shared identity, contact, insurance, emergency contact, program, and admission date values will preload across the packet. Form-specific edits stay local unless you explicitly refresh them from the shared profile.
          </p>
        </div>

        <button
          onClick={handleStartPacket}
          disabled={!canStart || loading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-3 text-sm font-medium text-white shadow-lg shadow-cyan-500/20 transition-all duration-300 hover:from-cyan-400 hover:to-blue-500 hover:shadow-cyan-500/35 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}
          {loading ? 'Opening packet...' : mode === 'existing' ? 'Open Admission Packet' : 'Create Client and Open Packet'}
          {!loading && <ArrowRight className="ml-auto h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}
