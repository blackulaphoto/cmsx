import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  AlertTriangle,
  ShieldAlert,
  ClipboardList,
  Scale,
  Heart,
  RefreshCw,
  ArrowRight,
  CalendarClock,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { apiFetch } from '../api/config'

const emptyOverview = {
  team_summary: {
    case_manager_count: 0,
    total_clients: 0,
    high_risk_clients: 0,
    clients_with_barriers: 0,
    overdue_reminders: 0,
    open_benefits_applications: 0,
    active_legal_cases: 0,
    active_fmla_cases: 0,
  },
  case_managers: [],
  alerts: {
    highest_overdue_workloads: [],
    highest_risk_caseloads: [],
  },
}

function SupervisorDashboard() {
  const [overview, setOverview] = useState(emptyOverview)
  const [loading, setLoading] = useState(true)

  const loadOverview = async () => {
    try {
      setLoading(true)
      const response = await apiFetch('/api/dashboard/supervisor/overview?supervisor_id=supervisor')
      if (!response.ok) {
        throw new Error('Failed to load supervisor reporting')
      }
      const data = await response.json()
      setOverview(data.overview || emptyOverview)
    } catch (error) {
      console.error('Supervisor overview error:', error)
      toast.error(error?.message || 'Failed to load supervisor reporting')
      setOverview(emptyOverview)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  const summaryCards = [
    {
      label: 'Case Managers',
      value: overview.team_summary.case_manager_count,
      icon: Users,
      gradient: 'from-cyan-500 to-blue-600',
    },
    {
      label: 'Total Clients',
      value: overview.team_summary.total_clients,
      icon: ClipboardList,
      gradient: 'from-blue-500 to-indigo-600',
    },
    {
      label: 'High Risk Clients',
      value: overview.team_summary.high_risk_clients,
      icon: ShieldAlert,
      gradient: 'from-rose-500 to-red-600',
    },
    {
      label: 'Overdue Reminders',
      value: overview.team_summary.overdue_reminders,
      icon: AlertTriangle,
      gradient: 'from-amber-500 to-orange-600',
    },
    {
      label: 'Open Benefits',
      value: overview.team_summary.open_benefits_applications,
      icon: Heart,
      gradient: 'from-violet-500 to-purple-600',
    },
    {
      label: 'Active Legal',
      value: overview.team_summary.active_legal_cases,
      icon: Scale,
      gradient: 'from-emerald-500 to-green-600',
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent">
                  Supervisor Dashboard
                </h1>
                <p className="mt-2 text-gray-300 text-lg">
                  Cross-module oversight for caseload risk, overdue work, and team follow-through.
                </p>
              </div>
              <button
                onClick={loadOverview}
                className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-5 py-3 text-white transition-all duration-300 hover:bg-white/20"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
            {summaryCards.map((card) => (
              <div key={card.label} className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
                <div className="flex items-center justify-between mb-4">
                  <div className={`rounded-xl bg-gradient-to-r ${card.gradient} p-3 shadow-lg`}>
                    <card.icon className="h-6 w-6 text-white" />
                  </div>
                  <span className="text-3xl font-bold text-white">{card.value}</span>
                </div>
                <p className="text-sm text-gray-300">{card.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 mb-8">
            <div className="xl:col-span-2 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-white">Team Caseload View</h2>
                  <p className="text-sm text-gray-400">Each case manager’s cross-module workload and risk profile.</p>
                </div>
                <Link
                  to="/smart-dashboard"
                  className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm text-white transition-all duration-300 hover:bg-white/20"
                >
                  Open Smart Daily
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>

              <div className="space-y-4">
                {overview.case_managers.map((manager) => (
                  <div key={manager.case_manager_id} className="rounded-2xl border border-white/10 bg-black/10 p-5">
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-4">
                      <div>
                        <h3 className="text-xl font-semibold text-white">{manager.case_manager_name}</h3>
                        <p className="text-sm text-gray-400">{manager.case_manager_id}</p>
                      </div>
                      <div className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200">
                        Completion score: {manager.completion_rate}%
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Clients</p>
                        <p className="text-lg font-semibold text-white">{manager.total_clients}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">High risk</p>
                        <p className="text-lg font-semibold text-rose-300">{manager.high_risk_clients}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Overdue</p>
                        <p className="text-lg font-semibold text-amber-300">{manager.overdue_reminders}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Barriers</p>
                        <p className="text-lg font-semibold text-white">{manager.clients_with_barriers}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Benefits</p>
                        <p className="text-lg font-semibold text-white">{manager.open_benefits_applications}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Legal</p>
                        <p className="text-lg font-semibold text-white">{manager.active_legal_cases}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">FMLA</p>
                        <p className="text-lg font-semibold text-white">{manager.active_fmla_cases}</p>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <p className="text-gray-400">Recent intakes</p>
                        <p className="text-lg font-semibold text-white">{manager.recent_intakes}</p>
                      </div>
                    </div>
                  </div>
                ))}

                {!loading && overview.case_managers.length === 0 && (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-6 text-gray-300">
                    No case manager workload data is available yet.
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
                <h2 className="mb-4 text-xl font-bold text-white">Highest Overdue Workloads</h2>
                <div className="space-y-3">
                  {overview.alerts.highest_overdue_workloads.map((manager) => (
                    <div key={`overdue-${manager.case_manager_id}`} className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4">
                      <p className="font-medium text-white">{manager.case_manager_name}</p>
                      <p className="text-sm text-amber-200">{manager.overdue_reminders} overdue reminders</p>
                    </div>
                  ))}
                  {!loading && overview.alerts.highest_overdue_workloads.length === 0 && (
                    <p className="text-sm text-gray-400">No overdue workload alerts right now.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
                <h2 className="mb-4 text-xl font-bold text-white">Highest Risk Caseloads</h2>
                <div className="space-y-3">
                  {overview.alerts.highest_risk_caseloads.map((manager) => (
                    <div key={`risk-${manager.case_manager_id}`} className="rounded-xl border border-rose-400/20 bg-rose-500/10 p-4">
                      <p className="font-medium text-white">{manager.case_manager_name}</p>
                      <p className="text-sm text-rose-200">{manager.high_risk_clients} high-risk clients</p>
                    </div>
                  ))}
                  {!loading && overview.alerts.highest_risk_caseloads.length === 0 && (
                    <p className="text-sm text-gray-400">No high-risk caseload alerts right now.</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
                <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-white">
                  <CalendarClock className="h-5 w-5 text-cyan-300" />
                  Next Actions
                </h2>
                <div className="space-y-3 text-sm text-gray-300">
                  <p>Review case managers with the highest overdue reminder counts first.</p>
                  <p>Use the Legal and Benefits modules to spot stalled applications or unresolved filings.</p>
                  <p>Use the client timeline to review barrier-heavy caseloads before staffing decisions.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SupervisorDashboard
