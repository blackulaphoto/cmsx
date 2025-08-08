import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { 
  ArrowLeft, 
  User, 
  Phone, 
  Mail, 
  MapPin, 
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Home,
  Briefcase,
  DollarSign,
  Scale,
  Building2,
  MessageSquare,
  Edit,
  Plus,
  ExternalLink,
  TrendingUp,
  Target,
  Shield
} from 'lucide-react'
import toast from 'react-hot-toast'

const ClientDashboard = () => {
  const { clientId } = useParams()
  const navigate = useNavigate()
  const [clientData, setClientData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (clientId) {
      fetchClientData()
    }
  }, [clientId])

  const fetchClientData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/clients/${clientId}/unified-view`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setClientData(data.client_data)
        } else {
          throw new Error(data.message || 'Failed to fetch client data')
        }
      } else {
        throw new Error('Failed to fetch client data')
      }
    } catch (error) {
      console.error('Error fetching client data:', error)
      toast.error('Failed to load client data')
      // Mock data for development
      setClientData({
        client: {
          client_id: clientId,
          first_name: 'Maria',
          last_name: 'Santos',
          phone: '(555) 987-6543',
          email: 'maria.santos@email.com',
          address: '123 Main St, Los Angeles, CA 90210',
          date_of_birth: '1985-03-15',
          risk_level: 'high',
          case_status: 'active',
          case_manager_id: 'cm_001',
          intake_date: '2024-06-20',
          created_at: '2024-06-20T10:00:00Z',
          updated_at: '2024-07-20T15:30:00Z'
        },
        housing: {
          status: 'Transitional - 30 days remaining',
          applications: [
            {
              property_name: 'Sunrise Apartments',
              status: 'pending',
              applied_date: '2024-07-15',
              follow_up_date: '2024-07-25'
            }
          ],
          profile: {
            max_rent: 1200,
            bedroom_preference: 1,
            preferred_counties: ['Los Angeles', 'Orange']
          }
        },
        employment: {
          status: 'Unemployed - Last job 2019',
          applications: [
            {
              job_title: 'Warehouse Associate',
              company: 'ABC Logistics',
              status: 'applied',
              applied_date: '2024-07-18'
            }
          ],
          resumes: [
            {
              resume_name: 'General Resume',
              created_at: '2024-07-10',
              download_url: '/api/resumes/download/123'
            }
          ]
        },
        benefits: {
          status: 'SNAP active, Medicaid pending',
          applications: [
            {
              benefit_type: 'SNAP',
              status: 'approved',
              approval_amount: 250
            },
            {
              benefit_type: 'Medicaid',
              status: 'pending',
              submitted_date: '2024-07-01'
            }
          ]
        },
        legal: {
          status: 'Expungement hearing: Next Tuesday',
          cases: [
            {
              case_type: 'expungement',
              status: 'active',
              court_name: 'Los Angeles Superior Court',
              next_date: '2024-07-23'
            }
          ]
        },
        services: {
          referrals: [
            {
              service_type: 'Mental Health',
              provider_name: 'Community Health Center',
              status: 'engaged',
              referral_date: '2024-06-25'
            }
          ]
        },
        tasks: [
          {
            title: 'Follow up on housing application',
            due_date: '2024-07-25',
            priority: 'high',
            status: 'pending'
          },
          {
            title: 'Prepare for expungement hearing',
            due_date: '2024-07-23',
            priority: 'urgent',
            status: 'pending'
          }
        ],
        appointments: [
          {
            appointment_type: 'Court Hearing',
            provider_name: 'Los Angeles Superior Court',
            appointment_date: '2024-07-23T09:00:00Z',
            status: 'scheduled'
          }
        ],
        case_notes: [
          {
            note_type: 'Contact',
            content: 'Client is motivated and making good progress. Discussed housing options.',
            created_at: '2024-07-20T14:00:00Z',
            created_by: 'cm_001'
          }
        ],
        goals: [
          {
            goal_type: 'housing',
            description: 'Secure permanent housing',
            status: 'in_progress'
          },
          {
            goal_type: 'employment',
            description: 'Find stable employment',
            status: 'pending'
          }
        ],
        barriers: [
          {
            barrier_type: 'housing',
            description: 'Limited affordable housing options',
            severity: 'high'
          }
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  const getRiskLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'inactive': return 'bg-gray-100 text-gray-800'
      case 'urgent': return 'bg-red-100 text-red-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'completed': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'urgent': return 'bg-red-100 text-red-800'
      case 'high': return 'bg-orange-100 text-orange-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading client data...</p>
        </div>
      </div>
    )
  }

  if (!clientData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Client Not Found</h2>
          <p className="text-gray-600 mb-4">The requested client could not be found.</p>
          <button
            onClick={() => navigate('/case-management')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Case Management
          </button>
        </div>
      </div>
    )
  }

  const { client } = clientData

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'housing', label: 'Housing', icon: Home },
    { id: 'employment', label: 'Employment', icon: Briefcase },
    { id: 'benefits', label: 'Benefits', icon: DollarSign },
    { id: 'legal', label: 'Legal', icon: Scale },
    { id: 'services', label: 'Services', icon: Building2 },
    { id: 'tasks', label: 'Tasks', icon: CheckCircle },
    { id: 'notes', label: 'Notes', icon: FileText }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/case-management')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-gray-600" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {client.first_name} {client.last_name}
                </h1>
                <p className="text-gray-600">Client ID: {client.client_id}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskLevelColor(client.risk_level)}`}>
                {client.risk_level} Risk
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(client.case_status)}`}>
                {client.case_status}
              </span>
              <button className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Edit className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Client Info Bar */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <Phone className="h-4 w-4 text-gray-400" />
              <span>{client.phone || 'No phone'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Mail className="h-4 w-4 text-gray-400" />
              <span>{client.email || 'No email'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <MapPin className="h-4 w-4 text-gray-400" />
              <span>{client.address || 'No address'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4 text-gray-400" />
              <span>Intake: {formatDate(client.intake_date)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex space-x-8 overflow-x-auto">
            {tabs.map((tab) => {
              const IconComponent = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-2 border-b-2 font-medium text-sm whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <IconComponent className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Quick Stats */}
            <div className="lg:col-span-2 space-y-6">
              {/* Status Overview */}
              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Status Overview</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Home className="h-6 w-6 text-blue-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-600">Housing</p>
                        <p className="text-sm text-gray-900">{clientData.housing?.status || 'Unknown'}</p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Briefcase className="h-6 w-6 text-green-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-600">Employment</p>
                        <p className="text-sm text-gray-900">{clientData.employment?.status || 'Unknown'}</p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <DollarSign className="h-6 w-6 text-purple-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-600">Benefits</p>
                        <p className="text-sm text-gray-900">{clientData.benefits?.status || 'Unknown'}</p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-orange-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Scale className="h-6 w-6 text-orange-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-600">Legal</p>
                        <p className="text-sm text-gray-900">{clientData.legal?.status || 'No active cases'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Goals & Barriers */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-sm border">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Target className="h-5 w-5 text-green-600 mr-2" />
                    Goals
                  </h3>
                  <div className="space-y-3">
                    {clientData.goals?.map((goal, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{goal.description}</p>
                          <p className="text-sm text-gray-600 capitalize">{goal.goal_type}</p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(goal.status)}`}>
                          {goal.status}
                        </span>
                      </div>
                    )) || <p className="text-gray-500">No goals set</p>}
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-sm border">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Shield className="h-5 w-5 text-red-600 mr-2" />
                    Barriers
                  </h3>
                  <div className="space-y-3">
                    {clientData.barriers?.map((barrier, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{barrier.description}</p>
                          <p className="text-sm text-gray-600 capitalize">{barrier.barrier_type}</p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(barrier.severity)}`}>
                          {barrier.severity}
                        </span>
                      </div>
                    )) || <p className="text-gray-500">No barriers identified</p>}
                  </div>
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Urgent Tasks */}
              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Clock className="h-5 w-5 text-red-600 mr-2" />
                  Urgent Tasks
                </h3>
                <div className="space-y-3">
                  {clientData.tasks?.filter(task => task.priority === 'urgent' || task.priority === 'high').map((task, index) => (
                    <div key={index} className="p-3 bg-red-50 rounded-lg">
                      <p className="font-medium text-gray-900">{task.title}</p>
                      <p className="text-sm text-gray-600">Due: {formatDate(task.due_date)}</p>
                      <span className={`inline-block mt-2 px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                        {task.priority}
                      </span>
                    </div>
                  )) || <p className="text-gray-500">No urgent tasks</p>}
                </div>
              </div>

              {/* Upcoming Appointments */}
              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <Calendar className="h-5 w-5 text-blue-600 mr-2" />
                  Upcoming Appointments
                </h3>
                <div className="space-y-3">
                  {clientData.appointments?.map((appointment, index) => (
                    <div key={index} className="p-3 bg-blue-50 rounded-lg">
                      <p className="font-medium text-gray-900">{appointment.appointment_type}</p>
                      <p className="text-sm text-gray-600">{appointment.provider_name}</p>
                      <p className="text-sm text-gray-600">{formatDateTime(appointment.appointment_date)}</p>
                    </div>
                  )) || <p className="text-gray-500">No upcoming appointments</p>}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
                <div className="space-y-2">
                  <Link
                    to={`/housing?client=${clientId}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="flex items-center">
                      <Home className="h-4 w-4 text-gray-600 mr-2" />
                      Housing Search
                    </span>
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </Link>
                  <Link
                    to={`/jobs?client=${clientId}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="flex items-center">
                      <Briefcase className="h-4 w-4 text-gray-600 mr-2" />
                      Job Search
                    </span>
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </Link>
                  <Link
                    to={`/benefits?client=${clientId}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="flex items-center">
                      <DollarSign className="h-4 w-4 text-gray-600 mr-2" />
                      Benefits
                    </span>
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </Link>
                  <Link
                    to={`/legal?client=${clientId}`}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="flex items-center">
                      <Scale className="h-4 w-4 text-gray-600 mr-2" />
                      Legal Services
                    </span>
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Other tab content would go here */}
        {activeTab === 'housing' && (
          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Housing Information</h3>
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Current Status</h4>
                <p className="text-gray-600">{clientData.housing?.status || 'Unknown'}</p>
              </div>
              {clientData.housing?.applications && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Applications</h4>
                  <div className="space-y-2">
                    {clientData.housing.applications.map((app, index) => (
                      <div key={index} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{app.property_name}</p>
                            <p className="text-sm text-gray-600">Applied: {formatDate(app.applied_date)}</p>
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                            {app.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Add similar content for other tabs */}
      </div>
    </div>
  )
}

export default ClientDashboard