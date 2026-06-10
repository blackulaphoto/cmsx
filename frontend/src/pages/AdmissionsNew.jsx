import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  ClipboardCheck,
  Zap,
  ArrowLeft,
  ArrowRight,
  Info,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { apiFetch } from '../api/config'
import ClientSelector from '../components/ClientSelector'

export default function AdmissionsNew() {
  const navigate = useNavigate()
  const [selectedClient, setSelectedClient] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleClientSelect = (client) => {
    setSelectedClient(client)
    setError(null)
  }

  const handleStartPacket = async () => {
    if (!selectedClient?.client_id) {
      setError('Please select a client first.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await apiFetch('/api/admissions/packets', {
        method: 'POST',
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          client_name: `${selectedClient.first_name || ''} ${selectedClient.last_name || ''}`.trim(),
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error ${res.status}`)
      }
      navigate(`/admissions/${selectedClient.client_id}`)
    } catch (err) {
      setError(err.message || 'Failed to start admission packet.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Back link */}
        <Link
          to="/admissions"
          className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Admissions
        </Link>

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25">
            <ClipboardCheck className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Start Full Admission</h1>
            <p className="text-sm text-gray-400">
              Select a client to open or create their admissions packet
            </p>
          </div>
        </div>

        {/* Info banner */}
        <div className="flex items-start gap-3 p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
          <Info className="h-4 w-4 text-cyan-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-cyan-200 leading-relaxed">
            The Full Admission Packet tracks all required forms, consents, signatures, and
            clinical screenings in CMSX. If a packet already exists for the selected client,
            it will be reopened — no duplicate is created.
          </p>
        </div>

        {/* Client selector card */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white">Select Client</h2>

          <ClientSelector
            selectedClientId={null}
            onClientSelect={handleClientSelect}
            showCreateNew={true}
            showViewDashboard={false}
            placeholder="Search for an existing client…"
          />

          {selectedClient && (
            <div className="flex items-center gap-3 p-3 rounded-xl bg-white/8 border border-white/15">
              <div className="w-9 h-9 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                {(selectedClient.first_name?.[0] || '?').toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {selectedClient.first_name} {selectedClient.last_name}
                </p>
                <p className="text-xs text-gray-400 truncate">
                  ID: {selectedClient.client_id}
                  {selectedClient.date_of_birth ? ` · DOB: ${selectedClient.date_of_birth}` : ''}
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <button
            onClick={handleStartPacket}
            disabled={!selectedClient || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:from-cyan-400 hover:to-blue-500 transition-all duration-300 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/35"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ClipboardCheck className="h-4 w-4" />
            )}
            {loading ? 'Opening packet…' : 'Open Admission Packet'}
            {!loading && <ArrowRight className="h-4 w-4 ml-auto" />}
          </button>
        </div>

        {/* Quick intake alt path */}
        <div className="bg-white/3 border border-white/8 rounded-2xl p-5">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-r from-yellow-500 to-orange-500 flex-shrink-0">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white mb-1">Need to create a new client first?</p>
              <p className="text-xs text-gray-400 mb-3">
                Use Quick Intake to add a client to CMSX, then come back here to start their full admission packet.
              </p>
              <Link
                to="/case-management"
                className="inline-flex items-center gap-1.5 text-xs text-orange-300 hover:text-orange-200 transition-colors"
              >
                <Zap className="h-3 w-3" />
                Open Quick Intake in Case Management
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
