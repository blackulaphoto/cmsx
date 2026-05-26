import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Activity,
  Building2,
  CalendarClock,
  ExternalLink,
  HeartPulse,
  MapPin,
  Phone,
  PlusCircle,
  Search,
  Shield,
  Stethoscope,
  Syringe,
  User,
  CheckCircle2,
  Clock3,
} from 'lucide-react'
import toast from 'react-hot-toast'

import ClientSelector from '../components/ClientSelector'
import LocationSelector from '../components/LocationSelector'
import { apiFetch } from '../api/config'

const MEDICAL_PATHS = [
  {
    key: 'medi-cal',
    label: 'Medi-Cal Providers',
    description: 'Doctors and clinics accepting Medi-Cal with city and specialty filters.',
    icon: Stethoscope,
    gradient: 'from-cyan-500 to-blue-500',
  },
  {
    key: 'private-insurance',
    label: 'Private Insurance',
    description: 'Programs and treatment options that accept private insurance.',
    icon: Shield,
    gradient: 'from-emerald-500 to-teal-500',
  },
  {
    key: 'dental-urgent',
    label: 'Dental & Urgent Care',
    description: 'Urgent dental care and fast-access clinic style resources.',
    icon: Activity,
    gradient: 'from-amber-500 to-orange-500',
  },
  {
    key: 'suboxone-mat',
    label: 'Suboxone & MAT',
    description: 'Medication-assisted treatment and recovery support options.',
    icon: Syringe,
    gradient: 'from-pink-500 to-rose-500',
  },
  {
    key: 'treatment-centers',
    label: 'Treatment Centers',
    description: 'Residential, outpatient, detox, and higher-acuity treatment programs.',
    icon: HeartPulse,
    gradient: 'from-purple-500 to-indigo-500',
  },
]

const APPOINTMENT_STATUS_OPTIONS = ['scheduled', 'completed', 'cancelled', 'no_show']
const REFERRAL_STATUS_OPTIONS = ['Identified', 'Called', 'Scheduled', 'Completed']

function Medical() {
  const [searchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [activePath, setActivePath] = useState('medi-cal')
  const [city, setCity] = useState('Los Angeles')
  const [search, setSearch] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [providers, setProviders] = useState([])
  const [providersLoading, setProvidersLoading] = useState(false)
  const [appointments, setAppointments] = useState([])
  const [referrals, setReferrals] = useState([])
  const [appointmentsLoading, setAppointmentsLoading] = useState(false)
  const [referralsLoading, setReferralsLoading] = useState(false)
  const [appointmentDraft, setAppointmentDraft] = useState(null)
  const [appointmentForm, setAppointmentForm] = useState({
    appointment_date: '',
    appointment_time: '09:00',
    appointment_type: 'Medical Appointment',
    notes: '',
    create_reminder: true,
  })

  useEffect(() => {
    const clientId = searchParams.get('client')
    if (!clientId) return

    const loadClient = async () => {
      try {
        const response = await apiFetch(`/api/clients/${clientId}`)
        if (!response.ok) return
        const client = await response.json()
        setSelectedClient(client)
      } catch (error) {
        console.error('Medical client preload failed:', error)
      }
    }

    loadClient()
  }, [searchParams])

  useEffect(() => {
    loadProviders(activePath, { notifyEmpty: false })
  }, [activePath])

  useEffect(() => {
    if (selectedClient?.client_id) {
      loadAppointments(selectedClient.client_id)
      loadReferrals(selectedClient.client_id)
    } else {
      setAppointments([])
      setReferrals([])
    }
  }, [selectedClient?.client_id])

  const loadProviders = async (pathKey = activePath, options = {}) => {
    const { notifyEmpty = true } = options
    setProvidersLoading(true)
    try {
      const params = new URLSearchParams({
        category: pathKey,
        city: city || '',
        search: search || '',
        specialty: specialty || '',
        limit: '25',
      })

      const response = await apiFetch(`/api/medical/providers?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load providers')
      }

      const data = await response.json()
      setProviders(data.providers || [])
      if (notifyEmpty && (data.providers || []).length === 0) {
        toast('No providers matched those filters')
      }
    } catch (error) {
      console.error('Medical provider load error:', error)
      toast.error('Failed to load medical providers')
      setProviders([])
    } finally {
      setProvidersLoading(false)
    }
  }

  const loadAppointments = async (clientId) => {
    setAppointmentsLoading(true)
    try {
      const params = new URLSearchParams({ client_id: clientId })
      const response = await apiFetch(`/api/medical/appointments?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load appointments')
      }
      const data = await response.json()
      setAppointments(data.appointments || [])
    } catch (error) {
      console.error('Medical appointments load error:', error)
      toast.error('Failed to load medical appointments')
      setAppointments([])
    } finally {
      setAppointmentsLoading(false)
    }
  }

  const loadReferrals = async (clientId) => {
    setReferralsLoading(true)
    try {
      const params = new URLSearchParams({ client_id: clientId })
      const response = await apiFetch(`/api/medical/referrals?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load referrals')
      }
      const data = await response.json()
      setReferrals(data.referrals || [])
    } catch (error) {
      console.error('Medical referrals load error:', error)
      toast.error('Failed to load medical referrals')
      setReferrals([])
    } finally {
      setReferralsLoading(false)
    }
  }

  const saveReferral = async (provider) => {
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }

    try {
      const response = await apiFetch('/api/medical/referrals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          provider_name: provider.provider_name,
          provider_category: provider.category,
          provider_type: provider.provider_type,
          address: provider.address,
          phone: provider.phone,
          website: provider.website,
          city: provider.city,
          insurance_type: activePath === 'medi-cal' ? 'Medi-Cal' : activePath === 'private-insurance' ? 'Private Insurance' : '',
          notes: provider.description,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to save referral')
      }

      toast.success(`Saved referral for ${selectedClient.first_name}`)
      loadReferrals(selectedClient.client_id)
    } catch (error) {
      console.error('Save medical referral error:', error)
      toast.error('Failed to save referral')
    }
  }

  const scheduleAppointment = async () => {
    if (!selectedClient?.client_id || !appointmentDraft) {
      toast.error('Select a client and provider first')
      return
    }
    if (!appointmentForm.appointment_date || !appointmentForm.appointment_time) {
      toast.error('Appointment date and time are required')
      return
    }

    try {
      const response = await apiFetch('/api/medical/appointments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          case_manager_id: selectedClient.case_manager_id || 'default_cm',
          provider_name: appointmentDraft.provider_name,
          location: appointmentDraft.address,
          appointment_date: appointmentForm.appointment_date,
          appointment_time: appointmentForm.appointment_time,
          appointment_type: appointmentForm.appointment_type,
          notes: appointmentForm.notes,
          create_reminder: appointmentForm.create_reminder,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to schedule appointment')
      }

      toast.success('Medical appointment scheduled')
      setAppointmentDraft(null)
      setAppointmentForm({
        appointment_date: '',
        appointment_time: '09:00',
        appointment_type: 'Medical Appointment',
        notes: '',
        create_reminder: true,
      })
      loadAppointments(selectedClient.client_id)
    } catch (error) {
      console.error('Schedule medical appointment error:', error)
      toast.error('Failed to schedule appointment')
    }
  }

  const updateAppointmentStatus = async (appointmentId, status) => {
    try {
      const response = await apiFetch(`/api/medical/appointments/${appointmentId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!response.ok) {
        throw new Error('Failed to update appointment')
      }
      if (selectedClient?.client_id) {
        loadAppointments(selectedClient.client_id)
      }
      toast.success('Appointment updated')
    } catch (error) {
      console.error('Update appointment status error:', error)
      toast.error('Failed to update appointment')
    }
  }

  const updateReferralStatus = async (referralId, referralStatus) => {
    try {
      const response = await apiFetch(`/api/medical/referrals/${referralId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referral_status: referralStatus }),
      })
      if (!response.ok) {
        throw new Error('Failed to update referral')
      }
      if (selectedClient?.client_id) {
        loadReferrals(selectedClient.client_id)
      }
      toast.success('Referral updated')
    } catch (error) {
      console.error('Update referral status error:', error)
      toast.error('Failed to update referral')
    }
  }

  const activePathMeta = MEDICAL_PATHS.find((path) => path.key === activePath)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-xl shadow-lg">
                <Stethoscope className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent">
                  Medical Access
                </h1>
                <p className="text-gray-300 text-lg">
                  Book appointments, track referrals, and coordinate healthcare for clients.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-3 text-white">
              <div className="p-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector
              onClientSelect={setSelectedClient}
              placeholder="Select a client to coordinate healthcare for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                <p className="text-sm text-blue-200">
                  Coordinating care for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
                </p>
                {selectedClient.medical_conditions && (
                  <p className="mt-2 text-xs text-blue-100">
                    Medical conditions: {selectedClient.medical_conditions}
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-r from-teal-500 to-cyan-500 rounded-lg">
                <HeartPulse className="h-6 w-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">Healthcare Paths</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
              {MEDICAL_PATHS.map((path) => {
                const Icon = path.icon
                const active = activePath === path.key
                return (
                  <button
                    key={path.key}
                  type="button"
                  onClick={() => setActivePath(path.key)}
                    className={`text-left p-5 rounded-2xl border transition-all duration-300 ${
                      active
                        ? `bg-gradient-to-r ${path.gradient} border-white/40 shadow-xl text-white`
                        : 'bg-white/5 border-white/10 text-gray-200 hover:bg-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className={`inline-flex p-3 rounded-xl mb-4 ${active ? 'bg-white/20' : 'bg-white/10'}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="font-semibold mb-2">{path.label}</h3>
                    <p className={`text-sm ${active ? 'text-white/85' : 'text-gray-400'}`}>{path.description}</p>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg">
                <Search className="h-6 w-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">{activePathMeta?.label}</h2>
                <p className="text-gray-400">{activePathMeta?.description}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">City</label>
                <LocationSelector
                  value={city}
                  onChange={setCity}
                  placeholder="Search city or state"
                  className="w-full"
                  inputClassName="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">Search</label>
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Provider name or keyword"
                  className="w-full px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">Specialty</label>
                <input
                  type="text"
                  value={specialty}
                  onChange={(event) => setSpecialty(event.target.value)}
                  placeholder="Psychiatry, dentistry, family medicine..."
                  className="w-full px-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 text-white placeholder-gray-400 transition-all duration-300 hover:bg-white/15"
                />
              </div>

              <div className="flex items-end">
                <button
                  type="button"
                  onClick={() => loadProviders(activePath, { notifyEmpty: true })}
                  disabled={providersLoading}
                  className="w-full px-6 py-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
                >
                  {providersLoading ? 'Loading...' : 'Search Providers'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {providersLoading ? (
                <div className="col-span-full text-center py-16 text-gray-300">Loading providers...</div>
              ) : providers.length === 0 ? (
                <div className="col-span-full text-center py-16 bg-white/5 rounded-2xl border border-white/10">
                  <Building2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-xl font-medium text-white mb-2">No providers found</h3>
                  <p className="text-gray-400">Try another city, specialty, or healthcare path.</p>
                </div>
              ) : (
                providers.map((provider) => (
                  <div key={provider.provider_id} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm p-6 border border-white/20 rounded-2xl">
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <div>
                        <h3 className="text-xl font-semibold text-white">{provider.provider_name}</h3>
                        <p className="text-cyan-200 text-sm mt-1">{provider.provider_type}</p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-medium border border-emerald-500/30 bg-emerald-500/15 text-emerald-200">
                        {activePathMeta?.label}
                      </span>
                    </div>

                    <p className="text-gray-300 text-sm leading-relaxed mb-4">{provider.description}</p>

                    <div className="space-y-3 text-sm text-gray-300 mb-6">
                      {provider.address && (
                        <div className="flex items-start gap-3">
                          <MapPin className="h-4 w-4 text-cyan-400 mt-0.5" />
                          <span>{provider.address}</span>
                        </div>
                      )}
                      {provider.phone && (
                        <div className="flex items-center gap-3">
                          <Phone className="h-4 w-4 text-blue-400" />
                          <span>{provider.phone}</span>
                        </div>
                      )}
                      {provider.extra?.specialties?.length > 0 && (
                        <div className="text-xs text-gray-400">
                          Specialties: {provider.extra.specialties.slice(0, 4).join(', ')}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={() => saveReferral(provider)}
                        className="flex-1 min-w-[150px] px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-medium transition-all duration-300"
                      >
                        Save Referral
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (!selectedClient?.client_id) {
                            toast.error('Please select a client first')
                            return
                          }
                          setAppointmentDraft(provider)
                          setAppointmentForm((prev) => ({
                            ...prev,
                            appointment_type: `Medical - ${provider.provider_type}`,
                          }))
                        }}
                        className="flex-1 min-w-[150px] px-4 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl font-medium transition-all duration-300"
                      >
                        Book Appointment
                      </button>
                      {provider.website ? (
                        <button
                          type="button"
                          onClick={() => window.open(provider.website, '_blank', 'noopener,noreferrer')}
                          className="px-4 py-3 bg-white/10 border border-white/20 text-gray-200 rounded-xl hover:bg-white/20 transition-all duration-300"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            <div className="xl:col-span-1 bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                  <CalendarClock className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">Book Appointment</h2>
                  <p className="text-gray-400 text-sm">Create a tracked medical appointment and reminder.</p>
                </div>
              </div>

              {appointmentDraft ? (
                <div className="space-y-4">
                  <div className="p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-sm text-gray-400 mb-1">Provider</p>
                    <p className="text-white font-semibold">{appointmentDraft.provider_name}</p>
                    <p className="text-xs text-cyan-200 mt-1">{appointmentDraft.provider_type}</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Date</label>
                    <input
                      type="date"
                      value={appointmentForm.appointment_date}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_date: event.target.value }))}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Time</label>
                    <input
                      type="time"
                      value={appointmentForm.appointment_time}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_time: event.target.value }))}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Appointment Type</label>
                    <input
                      type="text"
                      value={appointmentForm.appointment_type}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, appointment_type: event.target.value }))}
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Notes</label>
                    <textarea
                      rows={4}
                      value={appointmentForm.notes}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, notes: event.target.value }))}
                      placeholder="Insurance instructions, what to bring, client concerns..."
                      className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400"
                    />
                  </div>

                  <label className="flex items-center gap-3 text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={appointmentForm.create_reminder}
                      onChange={(event) => setAppointmentForm((prev) => ({ ...prev, create_reminder: event.target.checked }))}
                      className="h-4 w-4 rounded border-white/20 bg-white/10"
                    />
                    Create reminder the day before
                  </label>

                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={scheduleAppointment}
                      className="flex-1 px-4 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl font-medium"
                    >
                      Schedule
                    </button>
                    <button
                      type="button"
                      onClick={() => setAppointmentDraft(null)}
                      className="px-4 py-3 bg-white/10 border border-white/20 text-gray-200 rounded-xl hover:bg-white/20"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 bg-white/5 rounded-2xl border border-white/10">
                  <PlusCircle className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                  <p className="text-white font-medium mb-2">Pick a provider first</p>
                  <p className="text-sm text-gray-400">Use the provider search above, then click <span className="text-cyan-200">Book Appointment</span>.</p>
                </div>
              )}
            </div>

            <div className="xl:col-span-2 grid grid-cols-1 gap-8">
              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Upcoming Medical Appointments</h2>
                    <p className="text-gray-400 text-sm">Track what is booked and what still needs follow-up.</p>
                  </div>
                  <div className="px-3 py-1 bg-white/10 rounded-full text-sm text-gray-300">
                    {appointments.length} tracked
                  </div>
                </div>

                {appointmentsLoading ? (
                  <div className="py-10 text-center text-gray-300">Loading appointments...</div>
                ) : appointments.length === 0 ? (
                  <div className="py-10 text-center bg-white/5 rounded-2xl border border-white/10">
                    <Clock3 className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                    <p className="text-white font-medium">No medical appointments yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {appointments.map((appointment) => (
                      <div key={appointment.appointment_id} className="p-5 bg-white/5 rounded-2xl border border-white/10">
                        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                          <div>
                            <h3 className="text-lg font-semibold text-white">{appointment.provider_name || appointment.appointment_type}</h3>
                            <p className="text-cyan-200 text-sm mt-1">{appointment.appointment_type}</p>
                            <div className="mt-3 text-sm text-gray-300 space-y-1">
                              <p>{appointment.appointment_date} at {appointment.appointment_time || 'TBD'}</p>
                              {appointment.location ? <p>{appointment.location}</p> : null}
                              {appointment.notes ? <p className="text-gray-400">{appointment.notes}</p> : null}
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {APPOINTMENT_STATUS_OPTIONS.map((status) => (
                              <button
                                key={status}
                                type="button"
                                onClick={() => updateAppointmentStatus(appointment.appointment_id, status)}
                                className={`px-3 py-2 rounded-xl text-sm border transition-all duration-300 ${
                                  appointment.status === status
                                    ? 'bg-emerald-500/20 text-emerald-200 border-emerald-500/30'
                                    : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10'
                                }`}
                              >
                                {status.replace('_', ' ')}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/20 shadow-2xl shadow-purple-500/10">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white">Referral Tracker</h2>
                    <p className="text-gray-400 text-sm">Keep provider outreach organized by status.</p>
                  </div>
                  <div className="px-3 py-1 bg-white/10 rounded-full text-sm text-gray-300">
                    {referrals.length} referrals
                  </div>
                </div>

                {referralsLoading ? (
                  <div className="py-10 text-center text-gray-300">Loading referrals...</div>
                ) : referrals.length === 0 ? (
                  <div className="py-10 text-center bg-white/5 rounded-2xl border border-white/10">
                    <CheckCircle2 className="h-10 w-10 text-gray-400 mx-auto mb-4" />
                    <p className="text-white font-medium">No medical referrals saved yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {referrals.map((referral) => (
                      <div key={referral.referral_id} className="p-5 bg-white/5 rounded-2xl border border-white/10">
                        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                          <div>
                            <h3 className="text-lg font-semibold text-white">{referral.provider_name}</h3>
                            <p className="text-cyan-200 text-sm mt-1">{referral.provider_type || referral.provider_category}</p>
                            <div className="mt-3 text-sm text-gray-300 space-y-1">
                              {referral.address ? <p>{referral.address}</p> : null}
                              {referral.phone ? <p>{referral.phone}</p> : null}
                              {referral.notes ? <p className="text-gray-400">{referral.notes}</p> : null}
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {REFERRAL_STATUS_OPTIONS.map((status) => (
                              <button
                                key={status}
                                type="button"
                                onClick={() => updateReferralStatus(referral.referral_id, status)}
                                className={`px-3 py-2 rounded-xl text-sm border transition-all duration-300 ${
                                  referral.referral_status === status
                                    ? 'bg-blue-500/20 text-blue-200 border-blue-500/30'
                                    : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10'
                                }`}
                              >
                                {status}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Medical
