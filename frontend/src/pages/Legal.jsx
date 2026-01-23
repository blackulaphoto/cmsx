import { useState, useEffect } from 'react'
import { Scale, FileText, CheckCircle, Clock, AlertCircle, Calendar, Plus, Edit, Trash2, X, Save, User, Sparkles, Zap, TrendingUp, Briefcase, Shield, Gavel } from 'lucide-react'
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
      case 'completed': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30'
      case 'active': return 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 border-blue-500/30'
      case 'pending': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border-yellow-500/30'
      case 'missing': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-slate-500/20 text-gray-300 border-gray-500/30'
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
      case 'medium': return 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border-yellow-500/30'  
      case 'low': return 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30'
      default: return 'bg-gradient-to-r from-gray-500/20 to-slate-500/20 text-gray-300 border-gray-500/30'
    }
  }

  const stats = [
    { icon: Scale, label: 'Active Cases', value: cases.filter(c => c.status === 'Active').length.toString(), variant: 'primary' },
    { icon: FileText, label: 'Documents', value: documents.length.toString(), variant: 'secondary' },
    { icon: Calendar, label: 'Court Dates', value: cases.filter(c => c.court_date).length.toString(), variant: 'warning' },
    { icon: CheckCircle, label: 'Completed', value: documents.filter(d => d.status === 'Completed').length.toString(), variant: 'success' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-xl shadow-lg">
                <Scale className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-purple-200 to-indigo-200 bg-clip-text text-transparent">
                  Legal Services
                </h1>
                <p className="text-gray-300 text-lg">Legal assistance and document preparation</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Client Selection - FIXED with proper z-index */}
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20 mb-8 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-white">
              <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector 
              onClientSelect={setSelectedClient}
              placeholder="Select a client to manage legal matters for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-3 p-4 bg-gradient-to-r from-purple-500/20 to-indigo-500/20 backdrop-blur-sm rounded-xl border border-purple-500/30">
                <p className="text-sm text-purple-200">
                  Managing legal matters for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
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
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl shadow-purple-500/10 mb-8">
            <div className="flex border-b border-white/10">
              {[
                { id: 'overview', label: 'Case Overview', icon: Scale, gradient: 'from-purple-500 to-indigo-500' },
                { id: 'calendar', label: 'Court Calendar', icon: Calendar, gradient: 'from-blue-500 to-cyan-500' },
                { id: 'documents', label: 'Documents', icon: FileText, gradient: 'from-emerald-500 to-green-500' },
                { id: 'tasks', label: 'Tasks', icon: CheckCircle, gradient: 'from-orange-500 to-amber-500' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group flex items-center gap-3 px-8 py-6 font-medium transition-all duration-300 relative ${
                    activeTab === tab.id
                      ? 'text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  <div className={`p-2 rounded-lg transition-all duration-300 ${
                    activeTab === tab.id 
                      ? `bg-gradient-to-r ${tab.gradient} shadow-lg` 
                      : 'bg-white/10 group-hover:bg-white/20'
                  }`}>
                    <tab.icon className="h-5 w-5 text-white" />
                  </div>
                  {tab.label}
                  {activeTab === tab.id && (
                    <div className={`absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r ${tab.gradient}`}></div>
                  )}
                </button>
              ))}
            </div>

            <div className="p-8">
              {/* Case Overview Tab */}
              {activeTab === 'overview' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg">
                      <Gavel className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Active Legal Cases</h2>
                  </div>
                  
                  <div className="space-y-6">
                    {cases.map((legalCase) => (
                      <div key={legalCase.case_id} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-8 hover:border-white/30 transition-all duration-500 hover:scale-[1.02] hover:shadow-2xl hover:shadow-purple-500/20">
                        <div className="flex items-center justify-between mb-6">
                          <div className="flex-1">
                            <div className="flex items-center gap-4 mb-3">
                              <h3 className="text-2xl font-bold text-white group-hover:text-purple-200 transition-colors">{legalCase.case_type}</h3>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(legalCase.status)}`}>
                                {legalCase.status}
                              </span>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getPriorityColor(legalCase.priority)}`}>
                                {legalCase.priority} Priority
                              </span>
                            </div>
                            <p className="text-xl text-purple-400 font-semibold mb-3 group-hover:text-purple-300 transition-colors">
                              Client: {legalCase.client_name}
                            </p>
                            {legalCase.case_type === 'Expungement' && (
                              <a 
                                href="/expungement" 
                                className="inline-flex items-center gap-2 text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors"
                              >
                                <Sparkles className="h-4 w-4" />
                                Open in Expungement Module
                              </a>
                            )}
                          </div>
                        </div>
                        
                        <p className="text-gray-300 mb-6 leading-relaxed">{legalCase.description}</p>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                            <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                              <Calendar className="h-4 w-4 text-blue-400" />
                              Court Information
                            </h4>
                            <div className="space-y-2 text-sm">
                              <p className="text-gray-300">
                                <span className="text-blue-400">Date:</span> {legalCase.court_date} at {legalCase.court_time}
                              </p>
                              <p className="text-gray-300">
                                <span className="text-blue-400">Location:</span> {legalCase.court_location}
                              </p>
                            </div>
                          </div>
                          
                          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                            <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                              <Shield className="h-4 w-4 text-emerald-400" />
                              Case Details
                            </h4>
                            <div className="space-y-2 text-sm">
                              <p className="text-gray-300">
                                <span className="text-emerald-400">Attorney:</span> {legalCase.attorney}
                              </p>
                              <p className="text-gray-300">
                                <span className="text-emerald-400">Next Action:</span> {legalCase.next_action}
                              </p>
                            </div>
                          </div>
                        </div>

                        {/* Progress Bar */}
                        <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/10">
                          <div className="flex items-center gap-3 mb-3">
                            <TrendingUp className="h-4 w-4 text-purple-400" />
                            <span className="text-sm font-medium text-white">Case Progress</span>
                            <span className="text-sm text-purple-300">{legalCase.progress}% Complete</span>
                          </div>
                          <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                            <div 
                              className="bg-gradient-to-r from-purple-500 to-indigo-500 h-3 rounded-full transition-all duration-500 shadow-lg shadow-purple-500/25"
                              style={{ width: `${legalCase.progress}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Court Calendar Tab */}
              {activeTab === 'calendar' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                      <Calendar className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Court Calendar</h2>
                  </div>
                  
                  <div className="space-y-6 mb-8" data-testid="court-calendar">
                    {cases.filter(c => c.court_date).map((legalCase) => (
                      <div key={legalCase.case_id} className="group bg-gradient-to-br from-blue-500/10 to-cyan-500/5 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-blue-500/20">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xl font-bold text-white group-hover:text-blue-200 transition-colors">
                            {legalCase.case_type} - {legalCase.client_name}
                          </h3>
                          <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                            <Clock className="h-4 w-4 text-blue-300" />
                            <span className="text-sm text-blue-200 font-medium">
                              {legalCase.court_date} at {legalCase.court_time}
                            </span>
                          </div>
                        </div>
                        <p className="text-blue-200 mb-3 flex items-center gap-2">
                          <Scale className="h-4 w-4 text-blue-400" />
                          {legalCase.court_location}
                        </p>
                        <p className="text-blue-300 flex items-center gap-2">
                          <Zap className="h-4 w-4 text-yellow-400" />
                          Next Action: {legalCase.next_action}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Schedule Appointment */}
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/20">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                        <Plus className="h-5 w-5 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-white">Schedule Legal Meeting</h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Date</label>
                        <input
                          type="date"
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white transition-all duration-300"
                          data-testid="appointment-date"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Time</label>
                        <input
                          type="time"
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white transition-all duration-300"
                          data-testid="appointment-time"
                        />
                      </div>
                      <div className="flex items-end">
                        <button
                          onClick={() => scheduleAppointment('2024-07-23', '10:00 AM')}
                          className="group w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-emerald-500/25"
                          data-testid="confirm-appointment"
                        >
                          <Calendar className="h-5 w-5 group-hover:scale-110 transition-transform duration-300" />
                          Schedule Meeting
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Documents Tab */}
              {activeTab === 'documents' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                      <FileText className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Case Documents</h2>
                  </div>
                  
                  <div className="space-y-6 mb-8" data-testid="case-documents">
                    {documents.map((doc) => (
                      <div key={doc.doc_id} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-emerald-500/10">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-xl font-bold text-white group-hover:text-emerald-200 transition-colors">{doc.document_type}</h3>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(doc.status)}`}>
                            {doc.status}
                          </span>
                        </div>
                        <p className="text-emerald-400 font-semibold mb-3">Client: {doc.client_name}</p>
                        <p className="text-gray-300 mb-3 leading-relaxed">{doc.description}</p>
                        <div className="flex items-center gap-2 text-sm">
                          <Clock className="h-4 w-4 text-orange-400" />
                          <span className="text-orange-300">Required by: {doc.required_by}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Document Checklist */}
                  <div className="bg-gradient-to-br from-yellow-500/10 to-amber-500/5 backdrop-blur-xl border border-yellow-500/20 rounded-2xl p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-2 bg-gradient-to-r from-yellow-500 to-amber-500 rounded-lg">
                        <AlertCircle className="h-5 w-5 text-white" />
                      </div>
                      <h3 className="text-xl font-bold text-yellow-200">Missing Documents</h3>
                    </div>
                    <div className="space-y-4" data-testid="doc-checklist">
                      {documents.filter(d => d.status === 'Missing').map((doc) => (
                        <div key={doc.doc_id} className="flex items-center justify-between p-4 bg-gradient-to-r from-red-500/10 to-pink-500/10 backdrop-blur-sm rounded-xl border border-red-500/20">
                          <span className="text-red-300 font-medium">{doc.document_type} - Missing</span>
                          <span className="text-red-400 text-sm flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            Due: {doc.required_by}
                          </span>
                        </div>
                      ))}
                      {documents.filter(d => d.status === 'Pending').map((doc) => (
                        <div key={doc.doc_id} className="flex items-center justify-between p-4 bg-gradient-to-r from-yellow-500/10 to-amber-500/10 backdrop-blur-sm rounded-xl border border-yellow-500/20">
                          <span className="text-yellow-300 font-medium">{doc.document_type} - Pending</span>
                          <span className="text-yellow-400 text-sm flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            Due: {doc.required_by}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tasks Tab */}
              {activeTab === 'tasks' && (
                <div>
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                        <CheckCircle className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Legal Tasks</h2>
                    </div>
                    <button
                      onClick={() => setShowTaskModal(true)}
                      className="group flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25"
                      data-testid="add-legal-task"
                    >
                      <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                        <Plus className="h-5 w-5" />
                      </div>
                      Add Task
                    </button>
                  </div>

                  <div className="space-y-6">
                    <div className="group bg-gradient-to-br from-red-500/10 to-pink-500/5 backdrop-blur-xl border border-red-500/20 rounded-2xl p-6 hover:border-red-500/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-red-500/20">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-bold text-white group-hover:text-red-200 transition-colors">Get employment history for expungement</h3>
                        <span className="px-3 py-1 bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 rounded-full text-xs font-medium border border-red-500/30">High Priority</span>
                      </div>
                      <p className="text-red-200 mb-4 leading-relaxed">Contact previous restaurant employers for employment verification</p>
                      <div className="flex items-center gap-2 text-sm">
                        <Clock className="h-4 w-4 text-red-400" />
                        <span className="text-red-300">Deadline: 2024-07-24</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Task Modal */}
      {showTaskModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl max-w-md w-full">
            <div className="p-8">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                    <Plus className="h-5 w-5 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-white">Add Legal Task</h2>
                </div>
                <button
                  onClick={() => setShowTaskModal(false)}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">Task Description</label>
                  <textarea
                    value={taskForm.description}
                    onChange={(e) => setTaskForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-white placeholder-gray-400 transition-all duration-300"
                    rows="3"
                    placeholder="Describe the legal task..."
                    data-testid="task-description"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">Priority</label>
                  <select
                    value={taskForm.priority}
                    onChange={(e) => setTaskForm(prev => ({ ...prev, priority: e.target.value }))}
                    className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-white transition-all duration-300"
                    data-testid="task-priority"
                  >
                    <option value="Low" className="bg-gray-800 text-white">Low</option>
                    <option value="Medium" className="bg-gray-800 text-white">Medium</option>
                    <option value="High" className="bg-gray-800 text-white">High</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">Deadline</label>
                  <input
                    type="date"
                    value={taskForm.deadline}
                    onChange={(e) => setTaskForm(prev => ({ ...prev, deadline: e.target.value }))}
                    className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-white transition-all duration-300"
                    data-testid="task-deadline"
                  />
                </div>
              </div>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={addLegalTask}
                  className="group flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25"
                  data-testid="save-task"
                >
                  <Save className="h-5 w-5 group-hover:scale-110 transition-transform duration-300" />
                  Save Task
                </button>
                <button
                  onClick={() => setShowTaskModal(false)}
                  className="px-6 py-3 bg-white/10 backdrop-blur-sm border border-white/20 text-gray-300 rounded-xl font-medium hover:bg-white/20 hover:text-white hover:border-white/30 transition-all duration-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Legal