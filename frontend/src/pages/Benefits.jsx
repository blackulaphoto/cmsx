import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Heart, FileText, CheckCircle, Clock, DollarSign, Users, AlertCircle, Plus, Search, User, Sparkles, Zap, TrendingUp, Shield, Award, Target } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import BenefitsAssessmentModal from '../components/BenefitsAssessmentModal'
import AssessmentResults from '../components/AssessmentResults'
import toast from 'react-hot-toast'

function Benefits() {
  const [searchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(false)
  const [assessmentData, setAssessmentData] = useState({
    client_id: '',
    age: '',
    medical_conditions: [],
    work_history: [],
    current_income: 0,
    years_out_of_work: 0,
    functional_limitations: {}
  })
  const [eligibilityData, setEligibilityData] = useState({
    client_id: '',
    household_size: 1,
    monthly_income: 0,
    is_disabled: false,
    is_veteran: false,
    has_children: false,
    age: null
  })

  const [assessmentResults, setAssessmentResults] = useState(null)
  const [eligibilityResults, setEligibilityResults] = useState(null)
  
  // New assessment system state
  const [showAssessmentModal, setShowAssessmentModal] = useState(false)
  const [selectedProgram, setSelectedProgram] = useState(null)
  const [programAssessments, setProgramAssessments] = useState({}) // Store assessment results by program

  // Load applications on component mount
  useEffect(() => {
    fetchApplications()
  }, [])

  // Backup URL parameter reading - fallback if ClientSelector doesn't sync
  useEffect(() => {
    const clientId = searchParams.get('client')
    if (clientId && !selectedClient) {
      // Set mock client data as fallback
      const mockClient = {
        client_id: clientId,
        first_name: 'Maria',
        last_name: 'Santos',
        phone: '(555) 987-6543',
        email: 'maria.santos@email.com',
        risk_level: 'high',
        case_status: 'active'
      }
      setSelectedClient(mockClient)
    }
  }, [searchParams, selectedClient])

  const fetchApplications = async () => {
    try {
      const response = await fetch('/api/benefits/applications')
      if (response.ok) {
        const data = await response.json()
        setApplications(data.applications || [])
      }
    } catch (error) {
      console.error('Error fetching applications:', error)
    }
  }

  const handleDisabilityAssessment = async () => {
    if (!assessmentData.client_id || !assessmentData.age) {
      toast.error('Please fill in Client ID and Age')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/benefits/assess-disability', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(assessmentData)
      })

      if (response.ok) {
        const data = await response.json()
        setAssessmentResults(data)
        toast.success('Disability assessment completed!')
      } else {
        throw new Error('Assessment failed')
      }
    } catch (error) {
      toast.error('Assessment failed. Please try again.')
      console.error('Assessment error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleEligibilityCheck = async () => {
    if (!eligibilityData.client_id) {
      toast.error('Please enter Client ID')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/benefits/eligibility-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(eligibilityData)
      })

      if (response.ok) {
        const data = await response.json()
        setEligibilityResults(data)
        toast.success('Eligibility check completed!')
      } else {
        throw new Error('Eligibility check failed')
      }
    } catch (error) {
      toast.error('Eligibility check failed. Please try again.')
      console.error('Eligibility error:', error)
    } finally {
      setLoading(false)
    }
  }

  // New assessment system functions
  const handleCheckEligibility = (programName) => {
    if (!selectedClient) {
      toast.error('Please select a client first')
      return
    }
    
    setSelectedProgram(programName)
    setShowAssessmentModal(true)
  }

  const handleAssessmentComplete = (assessmentResult) => {
    // Store the assessment result for this program
    setProgramAssessments(prev => ({
      ...prev,
      [selectedProgram]: assessmentResult
    }))
    
    toast.success(`Assessment completed for ${selectedProgram}`)
    setShowAssessmentModal(false)
  }

  const handleStartApplication = (programName) => {
    const assessment = programAssessments[programName]
    if (!assessment) {
      toast.error('Please complete assessment first')
      return
    }
    
    if (assessment.eligibility_status !== 'eligible') {
      toast.error('Assessment shows you may not be eligible. Please consult with a case manager.')
      return
    }
    
    startApplication(programName, assessment)
  }

  const handleRetakeAssessment = (programName) => {
    setSelectedProgram(programName)
    setShowAssessmentModal(true)
  }

  const startApplication = async (benefitType, assessmentData = null) => {
    const clientId = selectedClient?.client_id || assessmentData?.client_id || eligibilityData.client_id
    if (!clientId) {
      toast.error('Please select a client first')
      return
    }

    try {
      const response = await fetch('/api/benefits/start-application', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          benefit_type: benefitType,
          assessment_data: assessmentData || assessmentResults || eligibilityResults
        })
      })

      if (response.ok) {
        const data = await response.json()
        toast.success(`${benefitType} application started!`)
        fetchApplications() // Refresh applications list
      } else {
        throw new Error('Application start failed')
      }
    } catch (error) {
      toast.error('Failed to start application')
      console.error('Application error:', error)
    }
  }

  const medicalConditions = [
    // Mental Health Conditions
    'Depression/Anxiety',
    'PTSD',
    'Bipolar Disorder',
    'Schizophrenia',
    'Autism Spectrum Disorder',
    
    // Musculoskeletal Conditions
    'Chronic Back Pain',
    'Arthritis',
    'Spinal Disorders',
    'Joint Problems',
    'Fibromyalgia',
    
    // Cardiovascular Conditions
    'Heart Disease',
    'Congestive Heart Failure',
    'High Blood Pressure',
    
    // Respiratory Conditions
    'COPD',
    'Asthma',
    'Pulmonary Fibrosis',
    'Sleep Apnea',
    
    // Neurological Conditions
    'Epilepsy/Seizures',
    'Multiple Sclerosis',
    'Parkinson\'s Disease',
    'Stroke',
    'Traumatic Brain Injury',
    
    // Endocrine/Metabolic
    'Diabetes with Complications',
    'Thyroid Disorders',
    
    // Cancer/Neoplastic
    'Cancer (Any Type)',
    
    // Digestive System
    'Inflammatory Bowel Disease',
    'Crohn\'s Disease',
    'Liver Disease',
    
    // Immune System
    'Lupus',
    'HIV/AIDS',
    'Chronic Fatigue Syndrome',
    
    // Vision/Hearing
    'Vision Impairment/Blindness',
    'Hearing Impairment/Deafness',
    
    // Kidney/Genitourinary
    'Chronic Kidney Disease',
    'Kidney Failure requiring Dialysis',
    
    // Blood/Hematological
    'Chronic Anemia',
    'Blood Disorders',
    
    // Skin Disorders
    'Severe Skin Conditions',
    
    // Substance Use
    'Substance Use Disorder (in recovery)',
    
    // Other
    'Chronic Pain Syndrome',
    'Learning Disabilities',
    'Physical Injuries/Amputations',
    'Other Medical Condition'
  ]

  const benefitPrograms = [
    { name: 'SNAP/CalFresh', description: 'Monthly food assistance benefits for eligible households', icon: '🎁', gradient: 'from-green-500 to-emerald-500' },
    { name: 'Medicaid/Medi-Cal', description: 'Comprehensive healthcare coverage for low-income individuals', icon: '🏥', gradient: 'from-blue-500 to-cyan-500' },
    { name: 'SSI', description: 'Monthly income for disabled, blind, or elderly individuals', icon: '💰', gradient: 'from-yellow-500 to-amber-500' },
    { name: 'SSDI', description: 'Disability benefits based on work history and contributions', icon: '🛡️', gradient: 'from-purple-500 to-indigo-500' },
    { name: 'Housing Vouchers/Section 8', description: 'Rental assistance vouchers for affordable housing', icon: '🏠', gradient: 'from-orange-500 to-red-500' },
    { name: 'TANF', description: 'Temporary cash assistance for families with children', icon: '👨‍👩‍👧‍👦', gradient: 'from-pink-500 to-rose-500' },
    { name: 'WIC', description: 'Nutrition program for pregnant women, infants, and children', icon: '🍼', gradient: 'from-teal-500 to-cyan-500' },
    { name: 'LIHEAP', description: 'Low-income home energy assistance program', icon: '⚡', gradient: 'from-indigo-500 to-blue-500' }
  ]

  const stats = [
    { icon: FileText, label: 'Active Applications', value: applications.length.toString(), variant: 'primary' },
    { icon: CheckCircle, label: 'Approved', value: applications.filter(app => app.status === 'approved').length.toString(), variant: 'success' },
    { icon: Clock, label: 'Pending', value: applications.filter(app => app.status === 'pending').length.toString(), variant: 'warning' },
    { icon: DollarSign, label: 'Monthly Benefits', value: '$1,240', variant: 'secondary' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 animate-fade-in">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-rose-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-pink-500 to-rose-500 rounded-xl shadow-lg">
                <Heart className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-pink-200 to-rose-200 bg-clip-text text-transparent">
                  Benefits & Support
                </h1>
                <p className="text-gray-300 text-lg">Access to government benefits and support services</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Client Selection - FIXED with proper z-index */}
          <div className="group bg-white/5 backdrop-blur-xl p-6 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl hover:shadow-pink-500/20 mb-8 relative z-20">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2 text-white">
              <div className="p-2 bg-gradient-to-r from-pink-500 to-rose-500 rounded-lg">
                <User className="h-5 w-5 text-white" />
              </div>
              Select Client
            </h2>
            <ClientSelector 
              onClientSelect={setSelectedClient}
              placeholder="Select a client to manage benefits for..."
              className="max-w-md relative z-30"
            />
            {selectedClient && (
              <div className="mt-3 p-4 bg-gradient-to-r from-pink-500/20 to-rose-500/20 backdrop-blur-sm rounded-xl border border-pink-500/30">
                <p className="text-sm text-pink-200">
                  Managing benefits for: <strong className="text-white">{selectedClient.first_name} {selectedClient.last_name}</strong>
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
                { id: 'overview', label: 'Overview', icon: Heart, gradient: 'from-pink-500 to-rose-500' },
                { id: 'assessment', label: 'Disability Assessment', icon: FileText, gradient: 'from-blue-500 to-cyan-500' },
                { id: 'eligibility', label: 'Eligibility Check', icon: CheckCircle, gradient: 'from-emerald-500 to-green-500' },
                { id: 'applications', label: 'Applications', icon: Clock, gradient: 'from-orange-500 to-amber-500' }
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
              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-pink-500 to-rose-500 rounded-lg">
                      <Sparkles className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Available Benefit Programs</h2>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {benefitPrograms.map((program, index) => {
                      const assessment = programAssessments[program.name]
                      const hasAssessment = !!assessment
                      const isEligible = assessment?.eligibility_status === 'eligible'
                      
                      return (
                        <div key={index} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-pink-500/10">
                          <div className="flex items-center gap-4 mb-4">
                            <div className={`p-3 bg-gradient-to-r ${program.gradient} rounded-xl shadow-lg`}>
                              <span className="text-2xl">{program.icon}</span>
                            </div>
                            <h3 className="text-xl font-bold text-white group-hover:text-pink-200 transition-colors">{program.name}</h3>
                          </div>
                          <p className="text-gray-300 mb-4 leading-relaxed">{program.description}</p>
                          
                          {/* Assessment Status */}
                          {hasAssessment && (
                            <AssessmentResults 
                              assessmentResult={assessment}
                              onStartApplication={() => handleStartApplication(program.name)}
                              onRetakeAssessment={() => handleRetakeAssessment(program.name)}
                              compact={true}
                            />
                          )}
                          
                          {/* Action Button */}
                          {!hasAssessment ? (
                            <button
                              onClick={() => handleCheckEligibility(program.name)}
                              className={`group/btn w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r ${program.gradient} hover:from-pink-500 hover:to-rose-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-pink-500/25`}
                            >
                              <Search className="h-5 w-5 group-hover/btn:scale-110 transition-transform duration-300" />
                              Check Eligibility
                            </button>
                          ) : isEligible ? (
                            <button
                              onClick={() => handleStartApplication(program.name)}
                              className="group/btn w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-green-500/25 mt-3"
                            >
                              <Plus className="h-5 w-5 group-hover/btn:scale-110 transition-transform duration-300" />
                              Start Application
                            </button>
                          ) : (
                            <button
                              onClick={() => handleRetakeAssessment(program.name)}
                              className="group/btn w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-gray-500/25 mt-3"
                            >
                              <Search className="h-5 w-5 group-hover/btn:scale-110 transition-transform duration-300" />
                              Retake Assessment
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Disability Assessment Tab */}
              {activeTab === 'assessment' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                      <Shield className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Disability Assessment Tool</h2>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Client ID
                        </label>
                        <input
                          type="text"
                          value={assessmentData.client_id}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, client_id: e.target.value }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Enter client ID"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Age
                        </label>
                        <input
                          type="number"
                          value={assessmentData.age}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, age: parseInt(e.target.value) || '' }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Enter age"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Current Monthly Income ($)
                        </label>
                        <input
                          type="number"
                          value={assessmentData.current_income}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, current_income: parseFloat(e.target.value) || 0 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Enter monthly income"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Years Out of Work
                        </label>
                        <input
                          type="number"
                          value={assessmentData.years_out_of_work}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, years_out_of_work: parseInt(e.target.value) || 0 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Years unable to work"
                        />
                      </div>
                    </div>

                    <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-6 rounded-2xl border border-white/20">
                      <label className="block text-sm font-medium text-gray-300 mb-4">
                        Medical Conditions (Select all that apply)
                      </label>
                      <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar pr-2">
                        {medicalConditions.map((condition, index) => (
                          <label key={index} className="flex items-center group cursor-pointer">
                            <input
                              type="checkbox"
                              checked={assessmentData.medical_conditions.includes(condition)}
                              onChange={(e) => {
                                const conditions = [...assessmentData.medical_conditions]
                                if (e.target.checked) {
                                  conditions.push(condition)
                                } else {
                                  const idx = conditions.indexOf(condition)
                                  if (idx > -1) conditions.splice(idx, 1)
                                }
                                setAssessmentData(prev => ({ ...prev, medical_conditions: conditions }))
                              }}
                              className="mr-3 h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-400 rounded bg-white/10"
                            />
                            <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{condition}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-8">
                    <button
                      onClick={handleDisabilityAssessment}
                      disabled={loading}
                      className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-blue-500/25 disabled:opacity-50 disabled:hover:scale-100"
                    >
                      <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                        <Target className="h-5 w-5" />
                      </div>
                      {loading ? 'Processing Assessment...' : 'Run Disability Assessment'}
                    </button>
                  </div>

                  {/* Assessment Results */}
                  {assessmentResults && (
                    <div className="mt-8 space-y-6">
                      <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/5 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-8">
                        <div className="flex items-center gap-3 mb-6">
                          <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg">
                            <Award className="h-5 w-5 text-white" />
                          </div>
                          <h3 className="text-xl font-bold text-blue-200">Assessment Results Summary</h3>
                        </div>
                        
                        {/* SSI and SSDI Eligibility */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                          {assessmentResults.assessment?.ssi_eligibility && (
                            <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                              <div className="flex items-center justify-between mb-4">
                                <h4 className="font-bold text-white">SSI Eligibility</h4>
                                <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                                  assessmentResults.assessment.ssi_eligibility.eligible 
                                    ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30' 
                                    : 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
                                }`}>
                                  {assessmentResults.assessment.ssi_eligibility.eligible ? 'Eligible' : 'Not Eligible'}
                                </span>
                              </div>
                              {assessmentResults.assessment.ssi_eligibility.eligible && (
                                <p className="text-sm text-gray-300 mb-3">
                                  Estimated monthly benefit: <span className="font-bold text-green-400">
                                    ${assessmentResults.assessment.ssi_eligibility.estimated_monthly_benefit}
                                  </span>
                                </p>
                              )}
                              <p className="text-xs text-gray-400">
                                Confidence: {assessmentResults.assessment.ssi_eligibility.confidence_level}
                              </p>
                            </div>
                          )}
                          
                          {assessmentResults.assessment?.ssdi_eligibility && (
                            <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                              <div className="flex items-center justify-between mb-4">
                                <h4 className="font-bold text-white">SSDI Eligibility</h4>
                                <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                                  assessmentResults.assessment.ssdi_eligibility.eligible 
                                    ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30' 
                                    : 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
                                }`}>
                                  {assessmentResults.assessment.ssdi_eligibility.eligible ? 'Eligible' : 'Not Eligible'}
                                </span>
                              </div>
                              {assessmentResults.assessment.ssdi_eligibility.eligible && (
                                <p className="text-sm text-gray-300 mb-3">
                                  Estimated monthly benefit: <span className="font-bold text-green-400">
                                    ${assessmentResults.assessment.ssdi_eligibility.estimated_monthly_benefit}
                                  </span>
                                </p>
                              )}
                              <p className="text-xs text-gray-400">
                                Work Credits: {assessmentResults.assessment.ssdi_eligibility.work_credits} / {assessmentResults.assessment.ssdi_eligibility.credits_needed} needed
                              </p>
                            </div>
                          )}
                        </div>

                        {/* Medical Conditions Found */}
                        {assessmentResults.assessment?.medical_assessment?.matching_conditions && (
                          <div className="mb-6">
                            <h4 className="font-bold text-blue-200 mb-4 flex items-center gap-2">
                              <Heart className="h-4 w-4 text-pink-400" />
                              Qualifying Medical Conditions Found
                            </h4>
                            <div className="space-y-4">
                              {assessmentResults.assessment.medical_assessment.matching_conditions.map((condition, index) => (
                                <div key={index} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl p-6 border-l-4 border-blue-400">
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                      <h5 className="font-bold text-white mb-2">{condition.name}</h5>
                                      <p className="text-sm text-gray-300 mb-3">SSA Listing: {condition.ssa_listing} | Category: {condition.category}</p>
                                      <p className="text-sm text-green-400 font-medium">
                                        Approval Rate: {Math.round(condition.approval_rate * 100)}% | Match Type: {condition.match_type || 'direct'}
                                      </p>
                                      {condition.original_condition && (
                                        <p className="text-xs text-blue-400">Originally: {condition.original_condition}</p>
                                      )}
                                    </div>
                                  </div>
                                  {condition.severity_criteria && (
                                    <div className="mt-4">
                                      <p className="text-xs font-medium text-gray-300 mb-2">Key Severity Criteria:</p>
                                      <ul className="text-xs text-gray-400 list-disc list-inside space-y-1">
                                        {condition.severity_criteria.slice(0, 3).map((criteria, idx) => (
                                          <li key={idx}>{criteria}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                            
                            <div className="mt-4 p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 backdrop-blur-sm rounded-xl border border-blue-500/30">
                              <p className="text-sm text-blue-200">
                                <span className="font-bold">Overall Approval Probability:</span> {' '}
                                <span className="text-lg font-bold text-cyan-300">
                                  {Math.round(assessmentResults.assessment.medical_assessment.estimated_approval_probability * 100)}%
                                </span>
                              </p>
                              <p className="text-xs text-blue-300 mt-1">
                                {assessmentResults.assessment.medical_assessment.affected_body_systems} body system(s) affected • {' '}
                                {assessmentResults.assessment.medical_assessment.condition_count} qualifying condition(s)
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Recommendations */}
                        {assessmentResults.assessment?.recommendations && (
                          <div className="mb-6">
                            <h4 className="font-bold text-blue-200 mb-4 flex items-center gap-2">
                              <Zap className="h-4 w-4 text-yellow-400" />
                              Recommendations
                            </h4>
                            <div className="space-y-3">
                              {assessmentResults.assessment.recommendations.map((rec, index) => (
                                <div key={index} className="flex items-start gap-3 p-4 bg-gradient-to-r from-white/5 to-white/10 backdrop-blur-sm rounded-xl border border-white/10">
                                  <span className="text-blue-400 mt-0.5">•</span>
                                  <span className="text-sm text-gray-300" dangerouslySetInnerHTML={{__html: rec}} />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Next Steps */}
                        {assessmentResults.assessment?.next_steps && (
                          <div className="mb-6">
                            <h4 className="font-bold text-blue-200 mb-4 flex items-center gap-2">
                              <TrendingUp className="h-4 w-4 text-emerald-400" />
                              Next Steps
                            </h4>
                            <div className="space-y-4">
                              {assessmentResults.assessment.next_steps.map((step, index) => (
                                <div key={index} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                                  <div className="flex items-start justify-between mb-3">
                                    <h5 className="font-bold text-white">{step.step}</h5>
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                                      step.priority === 'High' ? 'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30' :
                                      step.priority === 'Medium' ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border-yellow-500/30' :
                                      'bg-gradient-to-r from-gray-500/20 to-slate-500/20 text-gray-300 border-gray-500/30'
                                    }`}>
                                      {step.priority}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-300 mb-2">{step.description}</p>
                                  <p className="text-xs text-gray-400">Estimated Time: {step.estimated_time}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Timeline */}
                        {assessmentResults.assessment?.estimated_timeline && (
                          <div className="p-6 bg-gradient-to-r from-amber-500/10 to-yellow-500/10 backdrop-blur-sm rounded-xl border border-amber-500/20">
                            <h4 className="font-bold text-amber-200 mb-4 flex items-center gap-2">
                              <Clock className="h-4 w-4" />
                              Expected Timeline
                            </h4>
                            <div className="text-sm text-amber-200 space-y-2">
                              <p><span className="font-medium">Initial Decision:</span> {assessmentResults.assessment.estimated_timeline.initial_decision}</p>
                              <p><span className="font-medium">Total Process:</span> {assessmentResults.assessment.estimated_timeline.total_process}</p>
                              <p><span className="font-medium">Likelihood:</span> {assessmentResults.assessment.estimated_timeline.likelihood}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Eligibility Check Tab */}
              {activeTab === 'eligibility' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                      <CheckCircle className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Benefits Eligibility Check</h2>
                  </div>
                  
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/20 mb-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Client ID
                        </label>
                        <input
                          type="text"
                          value={eligibilityData.client_id}
                          onChange={(e) => setEligibilityData(prev => ({ ...prev, client_id: e.target.value }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Enter client ID"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Household Size
                        </label>
                        <input
                          type="number"
                          value={eligibilityData.household_size}
                          onChange={(e) => setEligibilityData(prev => ({ ...prev, household_size: parseInt(e.target.value) || 1 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300"
                          min="1"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Monthly Income ($)
                        </label>
                        <input
                          type="number"
                          value={eligibilityData.monthly_income}
                          onChange={(e) => setEligibilityData(prev => ({ ...prev, monthly_income: parseFloat(e.target.value) || 0 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Age (optional)
                        </label>
                        <input
                          type="number"
                          value={eligibilityData.age || ''}
                          onChange={(e) => setEligibilityData(prev => ({ ...prev, age: parseInt(e.target.value) || null }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-white placeholder-gray-400 transition-all duration-300"
                        />
                      </div>

                      <div className="md:col-span-2">
                        <div className="space-y-4">
                          {[
                            { key: 'is_disabled', label: 'Has disability' },
                            { key: 'is_veteran', label: 'Military veteran' },
                            { key: 'has_children', label: 'Has dependent children' }
                          ].map((item) => (
                            <label key={item.key} className="flex items-center group cursor-pointer">
                              <input
                                type="checkbox"
                                checked={eligibilityData[item.key]}
                                onChange={(e) => setEligibilityData(prev => ({ ...prev, [item.key]: e.target.checked }))}
                                className="mr-3 h-4 w-4 text-emerald-500 focus:ring-emerald-400 border-gray-400 rounded bg-white/10"
                              />
                              <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{item.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mb-8">
                    <button
                      onClick={handleEligibilityCheck}
                      disabled={loading}
                      className="group flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-emerald-500/25 disabled:opacity-50 disabled:hover:scale-100"
                    >
                      <div className="p-1 bg-white/20 rounded-lg group-hover:bg-white/30 transition-all duration-300">
                        <Search className="h-5 w-5" />
                      </div>
                      {loading ? 'Checking Eligibility...' : 'Check Eligibility'}
                    </button>
                  </div>

                  {/* Eligibility Results */}
                  {eligibilityResults && (
                    <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 backdrop-blur-xl border border-green-500/20 rounded-2xl p-8">
                      <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                          <CheckCircle className="h-5 w-5 text-white" />
                        </div>
                        <h3 className="text-xl font-bold text-green-200">Eligibility Results</h3>
                      </div>
                      <div className="space-y-4">
                        {eligibilityResults.eligible_programs?.map((program, index) => (
                          <div key={index} className="flex items-center justify-between p-6 bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-sm rounded-xl border border-white/20">
                            <div>
                              <p className="font-bold text-white text-lg">{program.program}</p>
                              <p className="text-sm text-green-300">{program.reason}</p>
                            </div>
                            <CheckCircle className="text-green-400 h-6 w-6" />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Applications Tab */}
              {activeTab === 'applications' && (
                <div>
                  <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-gradient-to-r from-orange-500 to-amber-500 rounded-lg">
                        <FileText className="h-6 w-6 text-white" />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Benefits Applications</h2>
                    </div>
                    <button
                      onClick={fetchApplications}
                      className="group flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25"
                    >
                      <Plus className="h-5 w-5 group-hover:scale-110 transition-transform duration-300" />
                      Refresh
                    </button>
                  </div>

                  {applications.length === 0 ? (
                    <div className="text-center py-16 bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm rounded-2xl border border-white/10">
                      <div className="p-4 bg-gradient-to-r from-orange-500/20 to-amber-500/20 rounded-2xl w-fit mx-auto mb-6">
                        <FileText className="h-12 w-12 text-orange-400" />
                      </div>
                      <h3 className="text-xl font-medium mb-3 text-white">No applications found</h3>
                      <p className="text-gray-400">Start by completing an assessment or eligibility check</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {applications.map((app, index) => (
                        <div key={index} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-orange-500/10">
                          <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white group-hover:text-orange-200 transition-colors">{app.benefit_type}</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                              app.status === 'approved' ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30' :
                              app.status === 'pending' ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border-yellow-500/30' :
                              'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
                            }`}>
                              {app.status}
                            </span>
                          </div>
                          <p className="text-orange-400 font-semibold mb-2">Client: {app.client_id}</p>
                          <p className="text-gray-300 mb-2">Applied: {new Date(app.created_at).toLocaleDateString()}</p>
                          {app.notes && <p className="text-gray-300">Notes: {app.notes}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Assessment Modal */}
      <BenefitsAssessmentModal
        isOpen={showAssessmentModal}
        onClose={() => setShowAssessmentModal(false)}
        program={selectedProgram}
        selectedClient={selectedClient}
        onAssessmentComplete={handleAssessmentComplete}
      />

      {/* Custom Scrollbar Styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(59, 130, 246, 0.5);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(59, 130, 246, 0.7);
        }
      `}</style>
    </div>
  )
}

export default Benefits