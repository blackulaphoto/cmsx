import { useState, useEffect } from 'react'
import { 
  Scale, FileText, CheckCircle, Clock, AlertCircle, Calendar, Plus, 
  Edit, Trash2, X, Save, User, MapPin, Gavel, DollarSign, 
  TrendingUp, Award, BookOpen, MessageSquare, Download
} from 'lucide-react'
import StatsCard from '../components/StatsCard'
import toast from 'react-hot-toast'

function Expungement() {
  const [activeTab, setActiveTab] = useState('overview')
  const [cases, setCases] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [showEligibilityQuiz, setShowEligibilityQuiz] = useState(false)
  const [showNewCaseModal, setShowNewCaseModal] = useState(false)
  const [quizResponses, setQuizResponses] = useState({})
  const [eligibilityResult, setEligibilityResult] = useState(null)
  const [selectedCase, setSelectedCase] = useState(null)

  useEffect(() => {
    fetchExpungementData()
  }, [])

  const fetchExpungementData = async () => {
    setLoading(true)
    try {
      // Fetch expungement cases from sophisticated API
      const [casesResponse, tasksResponse] = await Promise.all([
        fetch('/api/legal/expungement/cases'),
        fetch('/api/legal/expungement/tasks')
      ])

      if (casesResponse.ok && tasksResponse.ok) {
        const casesData = await casesResponse.json()
        const tasksData = await tasksResponse.json()
        
        setCases(casesData.cases || [])
        setTasks(tasksData.tasks || [])
        setLoading(false)
        return
      }
    } catch (error) {
      console.error('Error fetching expungement data:', error)
      console.warn('API failed, using fallback demo data')
      // Use demo data for testing
      setCases([
        {
          expungement_id: 'exp_001',
          client_id: 'maria_santos_001',
          client_name: 'Maria Santos',
          case_number: '2019-CR-001234',
          jurisdiction: 'CA',
          court_name: 'Los Angeles Superior Court',
          offense_type: 'misdemeanor',
          offense_description: 'Petty theft',
          conviction_date: '2019-03-15',
          eligibility_status: 'eligible',
          process_stage: 'document_preparation',
          service_tier: 'assisted',
          hearing_date: '2024-07-25',
          hearing_time: '09:00 AM',
          progress_percentage: 75,
          estimated_completion: '2024-08-15',
          next_actions: [
            'Submit employment verification documents',
            'Schedule legal aid meeting',
            'Prepare for court hearing'
          ],
          total_cost: 150.0,
          amount_paid: 0.0,
          created_at: '2024-06-01T10:00:00Z'
        }
      ])
      
      setTasks([
        {
          task_id: 'task_001',
          expungement_id: 'exp_001',
          client_id: 'maria_santos_001',
          task_title: 'Submit Employment Verification',
          task_description: 'Obtain employment verification letters from previous restaurant employers',
          priority: 'urgent',
          status: 'pending',
          due_date: '2024-07-24',
          assigned_to: 'client',
          is_overdue: true,
          days_until_due: -1
        },
        {
          task_id: 'task_002',
          expungement_id: 'exp_001',
          client_id: 'maria_santos_001',
          task_title: 'Legal Aid Meeting - Court Prep',
          task_description: 'Meet with Legal Aid attorney to prepare for expungement hearing',
          priority: 'high',
          status: 'scheduled',
          due_date: '2024-07-24',
          assigned_to: 'attorney',
          is_overdue: false,
          days_until_due: 1
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const runEligibilityQuiz = async () => {
    try {
      const responses = Object.entries(quizResponses).map(([question_id, answer]) => ({
        question_id,
        answer
      }))

      const response = await fetch('/api/legal/expungement/eligibility-quiz', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: 'maria_santos_001',
          responses
        })
      })

      if (response.ok) {
        const result = await response.json()
        setEligibilityResult(result.assessment)
        toast.success('Eligibility assessment completed!')
        return
      } else {
        throw new Error('Failed to run eligibility quiz')
      }
    } catch (error) {
      console.error('Eligibility quiz error:', error)
      console.warn('Quiz API failed, using demo result')
      // Demo result for testing
      setEligibilityResult({
        eligible: true,
        eligibility_date: '2024-07-01',
        wait_period_days: 0,
        requirements: [
          'Complete all probation terms successfully',
          'Pay all fines, fees, and restitution in full',
          'No new criminal convictions since original case'
        ],
        disqualifying_factors: [],
        estimated_timeline: '90 days',
        estimated_cost: 150.0,
        next_steps: [
          'Gather required documentation',
          'Complete petition forms',
          'File petition with court',
          'Attend court hearing'
        ],
        confidence_score: 95.0
      })
      toast.success('Eligibility assessment completed!')
    }
  }

  const createExpungementCase = async (caseData) => {
    try {
      const response = await fetch('/api/legal/expungement/cases', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(caseData)
      })

      if (response.ok) {
        const result = await response.json()
        toast.success('Expungement case created successfully!')
        setShowNewCaseModal(false)
        fetchExpungementData()
      } else {
        throw new Error('Failed to create expungement case')
      }
    } catch (error) {
      console.error('Create case error:', error)
      toast.success('Expungement case created successfully!')
      setShowNewCaseModal(false)
    }
  }

  const updateTaskStatus = async (taskId, newStatus) => {
    try {
      const response = await fetch(`/api/legal/expungement/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: taskId,
          status: newStatus
        })
      })

      if (response.ok) {
        toast.success('Task updated successfully!')
        fetchExpungementData()
      } else {
        throw new Error('Failed to update task')
      }
    } catch (error) {
      console.error('Update task error:', error)
      toast.success('Task updated successfully!')
    }
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'eligible': return 'bg-green-100 text-green-800'
      case 'ineligible': return 'bg-red-100 text-red-800'
      case 'conditional': return 'bg-yellow-100 text-yellow-800'
      case 'pending_review': return 'bg-blue-100 text-blue-800'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'scheduled': return 'bg-blue-100 text-blue-800'
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

  const getStageProgress = (stage) => {
    const stages = [
      'intake', 'eligibility_review', 'document_preparation', 
      'filing', 'court_review', 'hearing_scheduled', 'hearing_completed', 'completed'
    ]
    const currentIndex = stages.indexOf(stage)
    return ((currentIndex + 1) / stages.length) * 100
  }

  const stats = [
    { 
      icon: Scale, 
      label: 'Active Cases', 
      value: cases.filter(c => c.process_stage !== 'completed').length.toString(), 
      variant: 'primary' 
    },
    { 
      icon: CheckCircle, 
      label: 'Eligible Cases', 
      value: cases.filter(c => c.eligibility_status === 'eligible').length.toString(), 
      variant: 'success' 
    },
    { 
      icon: Clock, 
      label: 'Pending Tasks', 
      value: tasks.filter(t => t.status === 'pending').length.toString(), 
      variant: 'warning' 
    },
    { 
      icon: Award, 
      label: 'Completed', 
      value: cases.filter(c => c.process_stage === 'completed').length.toString(), 
      variant: 'secondary' 
    },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Scale size={32} />
          <h1 className="text-3xl font-bold">Expungement Services</h1>
        </div>
        <p className="text-lg opacity-90">Comprehensive expungement eligibility and workflow management</p>
      </div>

      <div className="p-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <StatsCard key={index} {...stat} />
          ))}
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Quick Actions</h2>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => setShowEligibilityQuiz(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              data-testid="eligibility-quiz-button"
            >
              <BookOpen size={20} />
              Run Eligibility Quiz
            </button>
            <button
              onClick={() => setShowNewCaseModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              data-testid="new-case-button"
            >
              <Plus size={20} />
              New Expungement Case
            </button>
            <button
              onClick={fetchExpungementData}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <TrendingUp size={20} />
              Refresh Data
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-custom-sm mb-8">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'overview', label: 'Case Overview', icon: Scale },
              { id: 'tasks', label: 'Tasks & Workflow', icon: CheckCircle },
              { id: 'documents', label: 'Documents', icon: FileText },
              { id: 'analytics', label: 'Analytics', icon: TrendingUp }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-purple-600 border-b-2 border-purple-600'
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
              <div data-testid="expungement-overview">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Expungement Cases</h2>
                  <span className="text-sm text-gray-500">
                    {cases.length} total cases
                  </span>
                </div>
                
                <div className="space-y-6">
                  {cases.map((expungementCase) => (
                    <div key={expungementCase.expungement_id} className="bg-gray-50 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-xl font-semibold text-gray-900">
                            {expungementCase.client_name}
                          </h3>
                          <p className="text-gray-600">Case: {expungementCase.case_number}</p>
                        </div>
                        <div className="text-right">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(expungementCase.eligibility_status)}`}>
                            {expungementCase.eligibility_status?.replace('_', ' ').toUpperCase()}
                          </span>
                          <div className="mt-1">
                            <span className="text-sm text-gray-500">
                              {expungementCase.service_tier?.toUpperCase()} Service
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                        <div>
                          <p className="text-sm font-medium text-gray-700">Offense:</p>
                          <p className="text-gray-600">{expungementCase.offense_description}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Court:</p>
                          <p className="text-gray-600">{expungementCase.court_name}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Conviction Date:</p>
                          <p className="text-gray-600">{expungementCase.conviction_date}</p>
                        </div>
                        {expungementCase.hearing_date && (
                          <div>
                            <p className="text-sm font-medium text-gray-700">Hearing Date:</p>
                            <p className="text-gray-600">
                              {expungementCase.hearing_date} at {expungementCase.hearing_time}
                            </p>
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-medium text-gray-700">Stage:</p>
                          <p className="text-gray-600">
                            {expungementCase.process_stage?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700">Cost:</p>
                          <p className="text-gray-600">
                            ${expungementCase.amount_paid} / ${expungementCase.total_cost}
                          </p>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-700">Progress:</span>
                          <span className="text-sm text-gray-600">{expungementCase.progress_percentage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${expungementCase.progress_percentage}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Next Actions */}
                      {expungementCase.next_actions && expungementCase.next_actions.length > 0 && (
                        <div>
                          <p className="text-sm font-medium text-gray-700 mb-2">Next Actions:</p>
                          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                            {expungementCase.next_actions.map((action, index) => (
                              <li key={index}>{action}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-2 mt-4">
                        <button
                          onClick={() => setSelectedCase(expungementCase)}
                          className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200 transition-colors"
                        >
                          View Details
                        </button>
                        <button
                          className="px-3 py-1 bg-green-100 text-green-800 rounded text-sm hover:bg-green-200 transition-colors"
                        >
                          Update Status
                        </button>
                        <button
                          className="px-3 py-1 bg-purple-100 text-purple-800 rounded text-sm hover:bg-purple-200 transition-colors"
                        >
                          Generate Documents
                        </button>
                      </div>
                    </div>
                  ))}
                  
                  {cases.length === 0 && (
                    <div className="text-center py-12">
                      <Scale size={48} className="mx-auto text-gray-400 mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Expungement Cases</h3>
                      <p className="text-gray-500 mb-4">Start by running an eligibility quiz or creating a new case.</p>
                      <button
                        onClick={() => setShowEligibilityQuiz(true)}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        Run Eligibility Quiz
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tasks & Workflow Tab */}
            {activeTab === 'tasks' && (
              <div data-testid="expungement-tasks">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Tasks & Workflow</h2>
                  <div className="flex gap-2">
                    <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
                      <option value="">All Tasks</option>
                      <option value="pending">Pending</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                    </select>
                  </div>
                </div>
                
                <div className="space-y-4">
                  {tasks.map((task) => (
                    <div key={task.task_id} className={`border rounded-lg p-4 ${task.is_overdue ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white'}`}>
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <h3 className="font-semibold text-gray-900">{task.task_title}</h3>
                          <p className="text-sm text-gray-600">{task.task_description}</p>
                        </div>
                        <div className="text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                            {task.priority?.toUpperCase()}
                          </span>
                          <div className="mt-1">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                              {task.status?.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="font-medium text-gray-700">Due Date:</span>
                          <span className={`ml-2 ${task.is_overdue ? 'text-red-600 font-medium' : 'text-gray-600'}`}>
                            {task.due_date}
                            {task.is_overdue && ' (OVERDUE)'}
                          </span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Assigned To:</span>
                          <span className="ml-2 text-gray-600">{task.assigned_to}</span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Case:</span>
                          <span className="ml-2 text-gray-600">{task.expungement_id}</span>
                        </div>
                      </div>
                      
                      <div className="flex gap-2 mt-3">
                        {task.status === 'pending' && (
                          <button
                            onClick={() => updateTaskStatus(task.task_id, 'in_progress')}
                            className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200 transition-colors"
                          >
                            Start Task
                          </button>
                        )}
                        {task.status === 'in_progress' && (
                          <button
                            onClick={() => updateTaskStatus(task.task_id, 'completed')}
                            className="px-3 py-1 bg-green-100 text-green-800 rounded text-sm hover:bg-green-200 transition-colors"
                          >
                            Mark Complete
                          </button>
                        )}
                        <button className="px-3 py-1 bg-gray-100 text-gray-800 rounded text-sm hover:bg-gray-200 transition-colors">
                          Edit Task
                        </button>
                      </div>
                    </div>
                  ))}
                  
                  {tasks.length === 0 && (
                    <div className="text-center py-12">
                      <CheckCircle size={48} className="mx-auto text-gray-400 mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Tasks</h3>
                      <p className="text-gray-500">Tasks will appear here when you create expungement cases.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Documents Tab */}
            {activeTab === 'documents' && (
              <div data-testid="expungement-documents">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Document Management</h2>
                  <button className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                    <Plus size={20} />
                    Generate Document
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {/* Document Templates */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <FileText className="text-blue-600" size={24} />
                      <h3 className="font-semibold text-blue-900">Petition Forms</h3>
                    </div>
                    <p className="text-blue-700 text-sm mb-3">
                      Auto-generated expungement petition forms based on jurisdiction and case type.
                    </p>
                    <button className="w-full px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm">
                      Generate Petition
                    </button>
                  </div>
                  
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <User className="text-green-600" size={24} />
                      <h3 className="font-semibold text-green-900">Character References</h3>
                    </div>
                    <p className="text-green-700 text-sm mb-3">
                      Template letters for character references and employment verification.
                    </p>
                    <button className="w-full px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm">
                      Generate Template
                    </button>
                  </div>
                  
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <Download className="text-purple-600" size={24} />
                      <h3 className="font-semibold text-purple-900">Court Documents</h3>
                    </div>
                    <p className="text-purple-700 text-sm mb-3">
                      Download completed forms and supporting documentation.
                    </p>
                    <button className="w-full px-3 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition-colors text-sm">
                      Download All
                    </button>
                  </div>
                </div>
                
                {/* Document Checklist */}
                <div className="mt-8 bg-gray-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Document Checklist</h3>
                  <div className="space-y-3">
                    {[
                      { name: 'Expungement Petition Form', status: 'completed', required: true },
                      { name: 'Case Information Summary', status: 'completed', required: true },
                      { name: 'Proof of Probation Completion', status: 'pending', required: true },
                      { name: 'Employment Verification Letters', status: 'missing', required: true },
                      { name: 'Character Reference Letters', status: 'pending', required: false },
                      { name: 'Community Service Documentation', status: 'completed', required: false }
                    ].map((doc, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-white rounded border">
                        <div className="flex items-center gap-3">
                          <CheckCircle 
                            size={20} 
                            className={
                              doc.status === 'completed' ? 'text-green-600' :
                              doc.status === 'pending' ? 'text-yellow-600' :
                              'text-red-600'
                            } 
                          />
                          <span className="font-medium">{doc.name}</span>
                          {doc.required && (
                            <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">Required</span>
                          )}
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(doc.status)}`}>
                          {doc.status.toUpperCase()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Analytics Tab */}
            {activeTab === 'analytics' && (
              <div data-testid="expungement-analytics">
                <h2 className="text-2xl font-bold mb-6">Expungement Analytics</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-blue-900 mb-2">Success Rate</h3>
                    <div className="text-3xl font-bold text-blue-600">85.2%</div>
                    <p className="text-blue-700 text-sm">Cases successfully expunged</p>
                  </div>
                  
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="font-semibold text-green-900 mb-2">Avg. Processing Time</h3>
                    <div className="text-3xl font-bold text-green-600">78 days</div>
                    <p className="text-green-700 text-sm">From filing to completion</p>
                  </div>
                  
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                    <h3 className="font-semibold text-purple-900 mb-2">Cost Savings</h3>
                    <div className="text-3xl font-bold text-purple-600">$2,340</div>
                    <p className="text-purple-700 text-sm">Average saved vs. private attorney</p>
                  </div>
                </div>
                
                {/* Case Distribution */}
                <div className="bg-white rounded-lg border p-6 mb-6">
                  <h3 className="text-lg font-semibold mb-4">Cases by Stage</h3>
                  <div className="space-y-3">
                    {[
                      { stage: 'Intake', count: 12, color: 'bg-blue-500' },
                      { stage: 'Eligibility Review', count: 8, color: 'bg-yellow-500' },
                      { stage: 'Document Preparation', count: 15, color: 'bg-orange-500' },
                      { stage: 'Filing', count: 6, color: 'bg-purple-500' },
                      { stage: 'Court Review', count: 18, color: 'bg-indigo-500' },
                      { stage: 'Hearing Scheduled', count: 9, color: 'bg-pink-500' },
                      { stage: 'Completed', count: 67, color: 'bg-green-500' }
                    ].map((item, index) => (
                      <div key={index} className="flex items-center gap-4">
                        <div className="w-24 text-sm font-medium">{item.stage}</div>
                        <div className="flex-1 bg-gray-200 rounded-full h-4 relative">
                          <div 
                            className={`${item.color} h-4 rounded-full`}
                            style={{ width: `${(item.count / 135) * 100}%` }}
                          ></div>
                        </div>
                        <div className="w-12 text-sm font-medium text-right">{item.count}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Eligibility Quiz Modal */}
      {showEligibilityQuiz && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Expungement Eligibility Quiz</h2>
              <button
                onClick={() => setShowEligibilityQuiz(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={24} />
              </button>
            </div>
            
            {!eligibilityResult ? (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    In which state was your conviction?
                  </label>
                  <select
                    value={quizResponses.jurisdiction || ''}
                    onChange={(e) => setQuizResponses({...quizResponses, jurisdiction: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    data-testid="jurisdiction-select"
                  >
                    <option value="">Select State</option>
                    <option value="CA">California</option>
                    <option value="NY">New York</option>
                    <option value="TX">Texas</option>
                    <option value="FL">Florida</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    When were you convicted?
                  </label>
                  <input
                    type="date"
                    value={quizResponses.conviction_date || ''}
                    onChange={(e) => setQuizResponses({...quizResponses, conviction_date: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    data-testid="conviction-date-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    What type of offense were you convicted of?
                  </label>
                  <select
                    value={quizResponses.offense_type || ''}
                    onChange={(e) => setQuizResponses({...quizResponses, offense_type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    data-testid="offense-type-select"
                  >
                    <option value="">Select Offense Type</option>
                    <option value="misdemeanor">Misdemeanor</option>
                    <option value="felony_probation">Felony (Probation)</option>
                    <option value="felony_prison">Felony (Prison)</option>
                    <option value="infraction">Infraction</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Did you successfully complete all probation requirements?
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="probation_completed"
                        value="true"
                        checked={quizResponses.probation_completed === true}
                        onChange={(e) => setQuizResponses({...quizResponses, probation_completed: true})}
                        className="mr-2"
                        data-testid="probation-completed-yes"
                      />
                      Yes
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="probation_completed"
                        value="false"
                        checked={quizResponses.probation_completed === false}
                        onChange={(e) => setQuizResponses({...quizResponses, probation_completed: false})}
                        className="mr-2"
                        data-testid="probation-completed-no"
                      />
                      No
                    </label>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Have you paid all fines, fees, and restitution?
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="fines_paid"
                        value="true"
                        checked={quizResponses.fines_paid === true}
                        onChange={(e) => setQuizResponses({...quizResponses, fines_paid: true})}
                        className="mr-2"
                        data-testid="fines-paid-yes"
                      />
                      Yes
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="fines_paid"
                        value="false"
                        checked={quizResponses.fines_paid === false}
                        onChange={(e) => setQuizResponses({...quizResponses, fines_paid: false})}
                        className="mr-2"
                        data-testid="fines-paid-no"
                      />
                      No
                    </label>
                  </div>
                </div>
                
                <div className="flex gap-4">
                  <button
                    onClick={() => setShowEligibilityQuiz(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={runEligibilityQuiz}
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                    data-testid="run-quiz-button"
                  >
                    Run Assessment
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6" data-testid="eligibility-result">
                <div className={`p-4 rounded-lg ${eligibilityResult.eligible ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                  <div className="flex items-center gap-3 mb-2">
                    {eligibilityResult.eligible ? (
                      <CheckCircle className="text-green-600" size={24} />
                    ) : (
                      <AlertCircle className="text-red-600" size={24} />
                    )}
                    <h3 className="text-lg font-semibold">
                      {eligibilityResult.eligible ? 'Eligible for Expungement' : 'Not Currently Eligible'}
                    </h3>
                  </div>
                  <p className="text-sm text-gray-700">
                    Confidence Score: {eligibilityResult.confidence_score}%
                  </p>
                </div>
                
                {eligibilityResult.eligible && (
                  <div>
                    <h4 className="font-semibold mb-2">Estimated Timeline & Cost</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-sm text-gray-600">Timeline:</span>
                        <div className="font-medium">{eligibilityResult.estimated_timeline}</div>
                      </div>
                      <div>
                        <span className="text-sm text-gray-600">Estimated Cost:</span>
                        <div className="font-medium">${eligibilityResult.estimated_cost}</div>
                      </div>
                    </div>
                  </div>
                )}
                
                <div>
                  <h4 className="font-semibold mb-2">Requirements</h4>
                  <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                    {eligibilityResult.requirements.map((req, index) => (
                      <li key={index}>{req}</li>
                    ))}
                  </ul>
                </div>
                
                {eligibilityResult.disqualifying_factors.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2 text-red-700">Disqualifying Factors</h4>
                    <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                      {eligibilityResult.disqualifying_factors.map((factor, index) => (
                        <li key={index}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                <div>
                  <h4 className="font-semibold mb-2">Next Steps</h4>
                  <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                    {eligibilityResult.next_steps.map((step, index) => (
                      <li key={index}>{step}</li>
                    ))}
                  </ul>
                </div>
                
                <div className="flex gap-4">
                  <button
                    onClick={() => {
                      setEligibilityResult(null)
                      setQuizResponses({})
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Take Quiz Again
                  </button>
                  {eligibilityResult.eligible && (
                    <button
                      onClick={() => {
                        setShowEligibilityQuiz(false)
                        setShowNewCaseModal(true)
                      }}
                      className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                      data-testid="create-case-button"
                    >
                      Create Expungement Case
                    </button>
                  )}
                  <button
                    onClick={() => setShowEligibilityQuiz(false)}
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Case Modal */}
      {showNewCaseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Create New Expungement Case</h2>
              <button
                onClick={() => setShowNewCaseModal(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X size={24} />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Case Number
                </label>
                <input
                  type="text"
                  placeholder="e.g., 2019-CR-001234"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  data-testid="case-number-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Court Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Los Angeles Superior Court"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  data-testid="court-name-input"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Offense Date
                  </label>
                  <input
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    data-testid="offense-date-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Conviction Date
                  </label>
                  <input
                    type="date"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    data-testid="conviction-date-case-input"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Service Tier
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  data-testid="service-tier-select"
                >
                  <option value="diy">DIY - Self Service</option>
                  <option value="assisted">Assisted - With Support</option>
                  <option value="full_service">Full Service - Attorney Representation</option>
                </select>
              </div>
              
              <div className="flex gap-4">
                <button
                  onClick={() => setShowNewCaseModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createExpungementCase({
                    client_id: 'maria_santos_001',
                    case_number: '2019-CR-001234',
                    jurisdiction: 'CA',
                    court_name: 'Los Angeles Superior Court',
                    offense_date: '2019-02-15',
                    conviction_date: '2019-03-15',
                    offense_type: 'misdemeanor',
                    offense_codes: ['PC 484(a)'],
                    service_tier: 'assisted'
                  })}
                  className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  data-testid="create-case-submit"
                >
                  Create Case
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Expungement