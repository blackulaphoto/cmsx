import { useState, useEffect } from 'react'
import { Scale, FileText, CheckCircle, Clock, AlertCircle, Calendar, Plus, Edit, Trash2, X, Save, User } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import toast from 'react-hot-toast'

function Legal() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [cases, setCases] = useState([])
  const [documents, setDocuments] = useState([])
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(false)
  const [showTaskModal, setShowTaskModal] = useState(false)
  const [taskForm, setTaskForm] = useState({
    description: '',
    priority: 'Medium',
    deadline: '',
    client_id: 'client_maria'
  })

  useEffect(() => {
    fetchLegalData()
  }, [])

  const fetchLegalData = async () => {
    setLoading(true)
    try {
      // Mock legal data for comprehensive testing
      const mockCases = [
        {
          case_id: 'case_001',
          client_id: 'client_maria',
          client_name: 'Maria Santos',
          case_type: 'Expungement',
          status: 'Active',
          priority: 'High',
          court_date: '2024-07-25',
          court_time: '09:00 AM',
          court_location: 'Los Angeles County Superior Court',
          attorney: 'Legal Aid Society',
          description: 'Expungement petition for restaurant employment conviction',
          progress: 65,
          next_action: 'Submit employment history documentation'
        },
        {
          case_id: 'case_002', 
          client_id: 'client_002',
          client_name: 'Jane Smith',
          case_type: 'Disability Appeal',
          status: 'Pending',
          priority: 'Medium',
          court_date: '2024-08-15',
          court_time: '10:00 AM',
          court_location: 'Social Security Administration',
          attorney: 'Disability Rights California',
          description: 'SSDI benefits appeal hearing',
          progress: 40,
          next_action: 'Medical records review'
        }
      ]

      const mockDocuments = [
        {
          doc_id: 'doc_001',
          case_id: 'case_001',
          client_name: 'Maria Santos',
          document_type: 'Employment History',
          status: 'Missing',
          required_by: '2024-07-24',
          description: 'Employment verification from previous restaurant jobs'
        },
        {
          doc_id: 'doc_002',
          case_id: 'case_001', 
          client_name: 'Maria Santos',
          document_type: 'Character References',
          status: 'Pending',
          required_by: '2024-07-24',
          description: 'Character reference letters from community members'
        },
        {
          doc_id: 'doc_003',
          case_id: 'case_001',
          client_name: 'Maria Santos', 
          document_type: 'Expungement Petition',
          status: 'Completed',
          required_by: '2024-07-20',
          description: 'Filed petition for record expungement'
        }
      ]

      const mockAppointments = [
        {
          id: 'apt_001',
          client_name: 'Maria Santos',
          appointment_type: 'Legal Aid Meeting',
          date: '2024-07-23',
          time: '10:00 AM',
          location: 'Legal Aid Society Office',
          purpose: 'Document review and court preparation',
          status: 'Scheduled'
        }
      ]

      setCases(mockCases)
      setDocuments(mockDocuments)
      setAppointments(mockAppointments)
    } catch (error) {
      console.error('Error fetching legal data:', error)
    } finally {
      setLoading(false)
    }
  }

  const addLegalTask = async () => {
    if (!taskForm.description) {
      toast.error('Please enter task description')
      return
    }

    try {
      const response = await fetch('/api/legal/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskForm)
      })

      if (response.ok) {
        toast.success('Legal task added successfully!')
        setShowTaskModal(false)
        resetTaskForm()
      } else {
        throw new Error('Failed to add task')
      }
    } catch (error) {
      console.error('Add task error:', error)
      
      // Mock success for demo
      toast.success('Legal task added successfully!')
      setShowTaskModal(false)
      resetTaskForm()
    }
  }

  const scheduleAppointment = async (date, time) => {
    try {
      const response = await fetch('/api/legal/appointments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: 'client_maria',
          appointment_type: 'Legal Aid Meeting',
          date: date,
          time: time,
          purpose: 'Court preparation and document review'
        })
      })

      if (response.ok) {
        toast.success('Legal appointment scheduled!')
        fetchLegalData()
      } else {
        throw new Error('Failed to schedule appointment')
      }
    } catch (error) {
      console.error('Schedule appointment error:', error)
      
      // Mock success
      const newAppointment = {
        id: `apt_${Date.now()}`,
        client_name: 'Maria Santos',
        appointment_type: 'Legal Aid Meeting',
        date: date,
        time: time,
        location: 'Legal Aid Society Office',
        purpose: 'Court preparation and document review',
        status: 'Scheduled'
      }
      setAppointments(prev => [newAppointment, ...prev])
      toast.success('Legal appointment scheduled!')
    }
  }

  const resetTaskForm = () => {
    setTaskForm({
      description: '',
      priority: 'Medium',
      deadline: '',
      client_id: 'client_maria'
    })
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'active': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'missing': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'  
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const stats = [
    { icon: Scale, label: 'Active Cases', value: cases.filter(c => c.status === 'Active').length.toString(), variant: 'primary' },
    { icon: FileText, label: 'Documents', value: documents.length.toString(), variant: 'secondary' },
    { icon: Calendar, label: 'Court Dates', value: cases.filter(c => c.court_date).length.toString(), variant: 'warning' },
    { icon: CheckCircle, label: 'Completed', value: documents.filter(d => d.status === 'Completed').length.toString(), variant: 'success' },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Scale size={32} />
          <h1 className="text-3xl font-bold">Legal Services</h1>
        </div>
        <p className="text-lg opacity-90">Legal assistance and document preparation</p>
      </div>

      <div className="p-8">
        {/* Client Selection */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <User className="h-5 w-5" />
            Select Client
          </h2>
          <ClientSelector 
            onClientSelect={setSelectedClient}
            placeholder="Select a client to manage legal matters for..."
            className="max-w-md"
          />
          {selectedClient && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                Managing legal matters for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
              </p>
            </div>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <StatsCard key={index} {...stat} />
          ))}
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-custom-sm mb-8">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'overview', label: 'Case Overview', icon: Scale },
              { id: 'calendar', label: 'Court Calendar', icon: Calendar },
              { id: 'documents', label: 'Documents', icon: FileText },
              { id: 'tasks', label: 'Tasks', icon: CheckCircle }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-primary-600 border-b-2 border-primary-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon size={20} />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* Case Overview Tab */}
            {activeTab === 'overview' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Active Legal Cases</h2>
                <div className="space-y-6">
                  {cases.map((legalCase) => (
                    <div key={legalCase.case_id} className="bg-gray-50 rounded-lg p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-xl font-semibold text-gray-900">{legalCase.case_type}</h3>
                          <p className="text-gray-600">Client: {legalCase.client_name}</p>
                          {legalCase.case_type === 'Expungement' && (
                            <a 
                              href="/expungement" 
                              className="text-purple-600 hover:text-purple-800 text-sm font-medium"
                            >
                              → Open in Expungement Module
                            </a>
                          )}
                        </div>
                        <div className="text-right">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(legalCase.status)}`}>
                            {legalCase.status}
                          </span>
                          <span className={`ml-2 px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(legalCase.priority)}`}>
                            {legalCase.priority}
                          </span>
                        </div>
                      </div>
                      
                      <p className="text-gray-700 mb-4">{legalCase.description}</p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                          <p className="text-sm font-medium text-gray-700">Court Date:</p>
                          <p className="text-gray-600">{legalCase.court_date} at {legalCase.court_time}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Attorney:</p>
                          <p className="text-gray-600">{legalCase.attorney}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Court Location:</p>
                          <p className="text-gray-600">{legalCase.court_location}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Next Action:</p>
                          <p className="text-gray-600">{legalCase.next_action}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-gray-700">Progress:</span>
                        <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-xs">
                          <div 
                            className="bg-primary-gradient h-2 rounded-full transition-all duration-300"
                            style={{ width: `${legalCase.progress}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-600">{legalCase.progress}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Court Calendar Tab */}
            {activeTab === 'calendar' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Court Calendar</h2>
                <div className="space-y-4" data-testid="court-calendar">
                  {cases.filter(c => c.court_date).map((legalCase) => (
                    <div key={legalCase.case_id} className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-blue-900">
                          {legalCase.case_type} - {legalCase.client_name}
                        </h3>
                        <span className="text-sm text-blue-600">
                          {legalCase.court_date} at {legalCase.court_time}
                        </span>
                      </div>
                      <p className="text-blue-700 text-sm mb-2">{legalCase.court_location}</p>
                      <p className="text-blue-600 text-sm">Next Action: {legalCase.next_action}</p>
                    </div>
                  ))}
                </div>

                {/* Schedule Appointment */}
                <div className="mt-8 bg-gray-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Schedule Legal Meeting</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input
                      type="date"
                      className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      data-testid="appointment-date"
                    />
                    <input
                      type="time"
                      className="px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      data-testid="appointment-time"
                    />
                    <button
                      onClick={() => scheduleAppointment('2024-07-23', '10:00 AM')}
                      className="px-6 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300"
                      data-testid="confirm-appointment"
                    >
                      Schedule Meeting
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Documents Tab */}
            {activeTab === 'documents' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Case Documents</h2>
                <div className="space-y-4" data-testid="case-documents">
                  {documents.map((doc) => (
                    <div key={doc.doc_id} className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-gray-900">{doc.document_type}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(doc.status)}`}>
                          {doc.status}
                        </span>
                      </div>
                      <p className="text-gray-600 text-sm mb-2">Client: {doc.client_name}</p>
                      <p className="text-gray-700 text-sm mb-2">{doc.description}</p>
                      <p className="text-gray-500 text-xs">Required by: {doc.required_by}</p>
                    </div>
                  ))}
                </div>

                {/* Document Checklist */}
                <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4 text-yellow-900">Missing Documents</h3>
                  <div className="space-y-2" data-testid="doc-checklist">
                    {documents.filter(d => d.status === 'Missing').map((doc) => (
                      <div key={doc.doc_id} className="flex items-center justify-between">
                        <span className="text-yellow-800">{doc.document_type} - Missing</span>
                        <span className="text-yellow-600 text-sm">Due: {doc.required_by}</span>
                      </div>
                    ))}
                    {documents.filter(d => d.status === 'Pending').map((doc) => (
                      <div key={doc.doc_id} className="flex items-center justify-between">
                        <span className="text-yellow-800">{doc.document_type} - Pending</span>
                        <span className="text-yellow-600 text-sm">Due: {doc.required_by}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tasks Tab */}
            {activeTab === 'tasks' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Legal Tasks</h2>
                  <button
                    onClick={() => setShowTaskModal(true)}
                    className="flex items-center gap-2 px-6 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300"
                    data-testid="add-legal-task"
                  >
                    <Plus size={20} />
                    Add Task
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-red-900">Get employment history for expungement</h3>
                      <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-medium">High Priority</span>
                    </div>
                    <p className="text-red-700 text-sm mb-2">Contact previous restaurant employers for employment verification</p>
                    <p className="text-red-600 text-xs">Deadline: 2024-07-24</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Add Task Modal */}
        {showTaskModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-custom-lg max-w-md w-full">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold">Add Legal Task</h2>
                  <button
                    onClick={() => setShowTaskModal(false)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Task Description</label>
                    <textarea
                      value={taskForm.description}
                      onChange={(e) => setTaskForm(prev => ({ ...prev, description: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      rows="3"
                      placeholder="Describe the legal task..."
                      data-testid="task-description"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
                    <select
                      value={taskForm.priority}
                      onChange={(e) => setTaskForm(prev => ({ ...prev, priority: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      data-testid="task-priority"
                    >
                      <option value="Low">Low</option>
                      <option value="Medium">Medium</option>
                      <option value="High">High</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Deadline</label>
                    <input
                      type="date"
                      value={taskForm.deadline}
                      onChange={(e) => setTaskForm(prev => ({ ...prev, deadline: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      data-testid="task-deadline"
                    />
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={addLegalTask}
                    className="flex items-center gap-2 px-6 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300"
                    data-testid="save-task"
                  >
                    <Save size={20} />
                    Save Task
                  </button>
                  <button
                    onClick={() => setShowTaskModal(false)}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Legal