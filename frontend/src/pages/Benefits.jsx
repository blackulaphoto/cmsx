import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Heart, FileText, CheckCircle, Clock, DollarSign, Users, AlertCircle, Plus, Search, User, Sparkles, Zap, TrendingUp, Shield, Award, Target } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import BenefitsAssessmentModal from '../components/BenefitsAssessmentModal'
import AssessmentResults from '../components/AssessmentResults'
import { apiFetch } from '../api/config'
import toast from 'react-hot-toast'

const BENEFIT_APPLICATION_LINKS = {
  'SNAP/CalFresh': {
    label: 'CalFresh application',
    url: 'https://benefitscal.com/'
  },
  'SNAP': {
    label: 'CalFresh application',
    url: 'https://benefitscal.com/'
  },
  'Medicaid/Medi-Cal': {
    label: 'Covered California / Medi-Cal application',
    url: 'https://www.coveredca.com/'
  },
  'Medicaid': {
    label: 'Covered California / Medi-Cal application',
    url: 'https://www.coveredca.com/'
  },
  'SSI': {
    label: 'SSA SSI application',
    url: 'https://www.ssa.gov/ssi'
  },
  'SSDI': {
    label: 'SSA SSDI application',
    url: 'https://www.ssa.gov/benefits/disability/'
  },
  'Housing Vouchers/Section 8': {
    label: 'HACLA Section 8 / housing assistance',
    url: 'https://www.hacla.org/en/about-section-8'
  },
  'TANF': {
    label: 'CalWORKs / cash aid application',
    url: 'https://benefitscal.com/'
  },
  'WIC': {
    label: 'California WIC application',
    url: 'https://myfamily.wic.ca.gov/'
  },
  'LIHEAP': {
    label: 'LIHEAP information and application',
    url: 'https://www.csd.ca.gov/Pages/LIHEAPProgram.aspx'
  }
}

function Benefits() {
  const [searchParams] = useSearchParams()
  const [selectedClient, setSelectedClient] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [applications, setApplications] = useState([])
  const [applicationDocuments, setApplicationDocuments] = useState({})
  const [applicationUploadFiles, setApplicationUploadFiles] = useState({})
  const [applicationUploadMeta, setApplicationUploadMeta] = useState({})
  const [loading, setLoading] = useState(false)
  const [assessmentData, setAssessmentData] = useState({
    client_id: '',
    age: '',
    medical_conditions: [],
    work_history: [],
    current_income: 0,
    years_out_of_work: 0,
    condition_duration_months: 0,
    expected_duration_12_months: false,
    currently_working: false,
    last_job_title: '',
    treating_sources: [],
    medications: [],
    recent_tests: [],
    hospitalizations_last_12_months: 0,
    needs_help_daily_activities: false,
    functional_limitations: {}
  })
  const [eligibilityData, setEligibilityData] = useState({
    client_id: '',
    household_size: 1,
    monthly_income: 0,
    is_disabled: false,
    is_veteran: false,
    has_children: false,
    age: null,
    is_pregnant: false,
    needs_food_assistance: false,
    needs_healthcare: false,
    housing_unstable: false,
    utility_shutoff_risk: false,
    unemployed: false,
  })

  const [assessmentResults, setAssessmentResults] = useState(null)
  const [eligibilityResults, setEligibilityResults] = useState(null)
  
  // New assessment system state
  const [showAssessmentModal, setShowAssessmentModal] = useState(false)
  const [selectedProgram, setSelectedProgram] = useState(null)
  const [programAssessments, setProgramAssessments] = useState({}) // Store assessment results by program

  const calculateAgeFromDateOfBirth = (dateOfBirth) => {
    if (!dateOfBirth) return null

    const parsedDate = new Date(dateOfBirth)
    if (Number.isNaN(parsedDate.getTime())) return null

    const today = new Date()
    let age = today.getFullYear() - parsedDate.getFullYear()
    const monthDiff = today.getMonth() - parsedDate.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < parsedDate.getDate())) {
      age -= 1
    }

    return age >= 0 ? age : null
  }

  const parseMultilineInput = (value) =>
    value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)

  const formatSelectedClientName = () => {
    if (!selectedClient) return ''
    return `${selectedClient.first_name || ''} ${selectedClient.last_name || ''}`.trim()
  }

  // Load applications on component mount
  useEffect(() => {
    fetchApplications()
  }, [selectedClient?.client_id])

  useEffect(() => {
    const selectedClientId = selectedClient?.client_id || ''
    const selectedClientAge = calculateAgeFromDateOfBirth(selectedClient?.date_of_birth)

    setAssessmentData((prev) => ({
      ...prev,
      client_id: selectedClientId,
      age: selectedClientAge ?? prev.age
    }))

    setEligibilityData((prev) => ({
      ...prev,
      client_id: selectedClientId,
      age: selectedClientAge ?? prev.age
    }))
  }, [selectedClient])

  // Backup URL parameter reading - fallback if ClientSelector doesn't sync
  useEffect(() => {
    const clientId = searchParams.get('client')
    if (clientId && !selectedClient) {
      apiFetch(`/api/clients/${encodeURIComponent(clientId)}?module=case_management`)
        .then((response) => {
          if (!response.ok) throw new Error('Client not found')
          return response.json()
        })
        .then((data) => {
          if (data?.client) setSelectedClient(data.client)
        })
        .catch((error) => {
          console.error('Failed to load client from URL:', error)
        })
    }
  }, [searchParams, selectedClient])

  const fetchApplications = async () => {
    try {
      const clientQuery = selectedClient?.client_id
        ? `?client_id=${encodeURIComponent(selectedClient.client_id)}`
        : ''
      const response = await apiFetch(`/api/benefits/applications${clientQuery}`)
      if (response.ok) {
        const data = await response.json()
        const loadedApplications = data.applications || []
        setApplications(loadedApplications)
        if (loadedApplications.length > 0) {
          await fetchApplicationDocuments(loadedApplications)
        } else {
          setApplicationDocuments({})
        }
      }
    } catch (error) {
      console.error('Error fetching applications:', error)
    }
  }

  const fetchApplicationDocuments = async (apps = applications) => {
    try {
      const responses = await Promise.all(
        apps.map(async (app) => {
          const response = await apiFetch(`/api/benefits/applications/${encodeURIComponent(app.application_id)}/documents`)
          if (!response.ok) {
            throw new Error(`Failed to load documents for ${app.benefit_type}`)
          }
          const data = await response.json()
          return [app.application_id, data.documents || []]
        })
      )

      setApplicationDocuments(Object.fromEntries(responses))
    } catch (error) {
      console.error('Error fetching benefits documents:', error)
    }
  }

  const handleDisabilityAssessment = async () => {
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }

    if (!assessmentData.age) {
      toast.error('Please enter age')
      return
    }

    setLoading(true)
    try {
      const derivedWorkHistory = assessmentData.last_job_title
        ? [{
            job_title: assessmentData.last_job_title,
            years_worked: Math.max(0, 10 - (assessmentData.years_out_of_work || 0)),
          }]
        : assessmentData.work_history

      const response = await apiFetch('/api/benefits/assess-disability', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...assessmentData,
          work_history: derivedWorkHistory,
        })
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
    if (!selectedClient?.client_id) {
      toast.error('Please select a client first')
      return
    }

    setLoading(true)
    try {
      const response = await apiFetch('/api/benefits/eligibility-check', {
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
    
    toast.success(`Screening completed for ${selectedProgram}`)
    setShowAssessmentModal(false)
  }

  const getBenefitApplicationLink = (benefitType) => {
    return BENEFIT_APPLICATION_LINKS[benefitType] || null
  }

  const createBenefitReminder = async (application) => {
    if (!application?.client_id) {
      toast.error('This application is missing a client ID')
      return
    }

    const followUpDate = application.follow_up_date || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)
    const reminderText = `${application.benefit_type}: ${application.next_action_required || 'Follow up on application status'}`

    try {
      const response = await apiFetch('/api/reminders/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: application.client_id,
          reminder_text: reminderText,
          due_date: followUpDate,
          case_manager_id: selectedClient?.case_manager_id || 'default_cm',
          priority: 'High',
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create follow-up reminder')
      }

      toast.success(`Reminder created for ${application.benefit_type}`)
    } catch (error) {
      console.error('Reminder creation error:', error)
      toast.error(error?.message || 'Failed to create reminder')
    }
  }

  const uploadBenefitDocument = async (application) => {
    const file = applicationUploadFiles[application.application_id]
    if (!file) {
      toast.error('Choose a file first')
      return
    }

    const meta = applicationUploadMeta[application.application_id] || {}

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', meta.document_type || 'Supporting Document')
      formData.append('document_status', meta.document_status || 'Received')
      formData.append('notes', meta.notes || '')

      const response = await apiFetch(`/api/benefits/applications/${encodeURIComponent(application.application_id)}/documents/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to upload benefits document')
      }

      toast.success(`Uploaded document for ${application.benefit_type}`)
      setApplicationUploadFiles((prev) => {
        const next = { ...prev }
        delete next[application.application_id]
        return next
      })
      await fetchApplicationDocuments()
      await fetchApplications()
    } catch (error) {
      console.error('Upload benefits document error:', error)
      toast.error(error?.message || 'Failed to upload benefits document')
    }
  }

  const getApplicationClientLabel = (application) => {
    const fullName = selectedClient
      ? `${selectedClient.first_name || ''} ${selectedClient.last_name || ''}`.trim()
      : ''

    if (selectedClient?.client_id && application.client_id === selectedClient.client_id && fullName) {
      return fullName
    }

    if (application.client_name && application.client_name !== 'Unknown Client') {
      return application.client_name
    }

    return application.client_id || 'Client record unavailable'
  }

  const handleStartApplication = (programName) => {
    const assessment = programAssessments[programName]
    if (!assessment) {
      toast.error('Please complete assessment first')
      return
    }
    
    if (assessment.eligibility_status !== 'eligible') {
      toast.error('This screening does not show a strong likely match yet. Review the details before starting an application.')
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
      const response = await apiFetch('/api/benefits/start-application', {
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
        const destination = getBenefitApplicationLink(benefitType)
        toast.success(`${benefitType} application started!`)
        await fetchApplications()
        setActiveTab('applications')

        if (destination?.url) {
          window.open(destination.url, '_blank', 'noopener,noreferrer')
          toast.success(`Opened ${destination.label}`, { duration: 5000 })
        } else {
          toast(`No official application link is configured for ${benefitType} yet. The case was tracked in Applications.`, {
            duration: 5000,
            icon: '⚠️'
          })
        }
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

  const disabilityFunctionalLimitationOptions = [
    { key: 'standing', label: 'Standing / walking for extended periods' },
    { key: 'lifting', label: 'Lifting, carrying, or reaching' },
    { key: 'sitting', label: 'Sitting for long periods' },
    { key: 'using_hands', label: 'Using hands, typing, or repetitive motion' },
    { key: 'concentration', label: 'Concentration, pace, or memory' },
    { key: 'social_interaction', label: 'Getting along with supervisors, coworkers, or the public' },
    { key: 'attendance', label: 'Keeping a regular schedule and consistent attendance' },
    { key: 'stress_tolerance', label: 'Handling stress or change in routine' },
  ]

  const eligibilityFlagOptions = [
    { key: 'is_disabled', label: 'Has disability or serious health limitation' },
    { key: 'is_veteran', label: 'Military veteran' },
    { key: 'has_children', label: 'Has dependent children' },
    { key: 'is_pregnant', label: 'Pregnant or recently postpartum' },
    { key: 'needs_food_assistance', label: 'Needs food assistance' },
    { key: 'needs_healthcare', label: 'Needs health coverage or urgent medical access' },
    { key: 'housing_unstable', label: 'Homeless or housing unstable' },
    { key: 'utility_shutoff_risk', label: 'Utility shutoff or energy burden risk' },
    { key: 'unemployed', label: 'Currently unemployed' },
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
    { icon: CheckCircle, label: 'Approved', value: applications.filter(app => app.application_status === 'approved').length.toString(), variant: 'success' },
    { icon: Clock, label: 'Pending', value: applications.filter(app => app.application_status === 'pending').length.toString(), variant: 'warning' },
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
                <p className="text-gray-300 text-lg">Preliminary benefits screening and application tracking</p>
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
                { id: 'assessment', label: 'Disability Pre-Screen', icon: FileText, gradient: 'from-blue-500 to-cyan-500' },
                { id: 'eligibility', label: 'Benefits Screening', icon: CheckCircle, gradient: 'from-emerald-500 to-green-500' },
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

                  <div className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                    These program surveys are preliminary screenings only. They help case managers identify likely matches and missing information, but they are not final eligibility determinations by the agency.
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
                              Start Screening
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
                              Retake Screening
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
                    <h2 className="text-2xl font-bold text-white">SSI / SSDI Pre-Screen</h2>
                  </div>

                  <div className="mb-6 rounded-2xl border border-blue-400/30 bg-blue-500/10 p-4 text-sm text-blue-100">
                    This is a case-manager pre-screen modeled around SSA intake factors like duration, work activity, treatment evidence, and functional limitations. It does not approve disability benefits by itself.
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Selected Client
                        </label>
                        <input
                          type="text"
                          value={formatSelectedClientName()}
                          readOnly
                          className="w-full px-4 py-3 bg-white/5 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Select a client above"
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
                          Condition duration (months)
                        </label>
                        <input
                          type="number"
                          value={assessmentData.condition_duration_months}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, condition_duration_months: parseInt(e.target.value, 10) || 0 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="How long has the condition limited work?"
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

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="flex items-center gap-3 text-sm text-gray-300">
                          <input
                            type="checkbox"
                            checked={assessmentData.expected_duration_12_months}
                            onChange={(e) => setAssessmentData(prev => ({ ...prev, expected_duration_12_months: e.target.checked }))}
                            className="h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-400 rounded bg-white/10"
                          />
                          Expected to last at least 12 months
                        </label>

                        <label className="flex items-center gap-3 text-sm text-gray-300">
                          <input
                            type="checkbox"
                            checked={assessmentData.currently_working}
                            onChange={(e) => setAssessmentData(prev => ({ ...prev, currently_working: e.target.checked }))}
                            className="h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-400 rounded bg-white/10"
                          />
                          Currently working
                        </label>
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

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Last job title
                        </label>
                        <input
                          type="text"
                          value={assessmentData.last_job_title}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, last_job_title: e.target.value }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Most recent job or work role"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Hospitalizations in the last 12 months
                        </label>
                        <input
                          type="number"
                          value={assessmentData.hospitalizations_last_12_months}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, hospitalizations_last_12_months: parseInt(e.target.value, 10) || 0 }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          min="0"
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

                  <div className="mt-8 grid grid-cols-1 xl:grid-cols-2 gap-8">
                    <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm p-6 rounded-2xl border border-white/20">
                      <label className="block text-sm font-medium text-gray-300 mb-4">
                        Functional limitations (Select all that apply)
                      </label>
                      <div className="space-y-3">
                        {disabilityFunctionalLimitationOptions.map((item) => (
                          <label key={item.key} className="flex items-center group cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!assessmentData.functional_limitations?.[item.key]}
                              onChange={(e) => setAssessmentData(prev => ({
                                ...prev,
                                functional_limitations: {
                                  ...(prev.functional_limitations || {}),
                                  [item.key]: e.target.checked,
                                },
                              }))}
                              className="mr-3 h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-400 rounded bg-white/10"
                            />
                            <span className="text-sm text-gray-300 group-hover:text-white transition-colors">{item.label}</span>
                          </label>
                        ))}

                        <label className="mt-4 flex items-center gap-3 text-sm text-gray-300">
                          <input
                            type="checkbox"
                            checked={assessmentData.needs_help_daily_activities}
                            onChange={(e) => setAssessmentData(prev => ({ ...prev, needs_help_daily_activities: e.target.checked }))}
                            className="h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-400 rounded bg-white/10"
                          />
                          Needs help with daily activities such as bathing, dressing, shopping, or transportation
                        </label>
                      </div>
                    </div>

                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Treating providers / clinics
                        </label>
                        <textarea
                          rows={4}
                          value={assessmentData.treating_sources.join('\n')}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, treating_sources: parseMultilineInput(e.target.value) }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="One provider or clinic per line"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Medications
                        </label>
                        <textarea
                          rows={3}
                          value={assessmentData.medications.join('\n')}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, medications: parseMultilineInput(e.target.value) }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="List current medications or key side effects"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Recent tests / imaging / lab work
                        </label>
                        <textarea
                          rows={3}
                          value={assessmentData.recent_tests.join('\n')}
                          onChange={(e) => setAssessmentData(prev => ({ ...prev, recent_tests: parseMultilineInput(e.target.value) }))}
                          className="w-full px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="MRI, hospital discharge, psychiatric eval, bloodwork, etc."
                        />
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
                      {loading ? 'Processing Pre-Screen...' : 'Run Disability Pre-Screen'}
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
                          <h3 className="text-xl font-bold text-blue-200">SSI / SSDI Pre-Screen Summary</h3>
                        </div>

                        {assessmentResults.disclaimer && (
                          <div className="mb-6 rounded-2xl border border-blue-400/30 bg-blue-500/10 p-4 text-sm text-blue-100">
                            {assessmentResults.disclaimer}
                          </div>
                        )}

                        {assessmentResults.screening_checkpoints?.length > 0 && (
                          <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {assessmentResults.screening_checkpoints.map((checkpoint) => (
                              <div key={checkpoint.label} className="rounded-xl border border-white/15 bg-white/5 p-4">
                                <div className="mb-2 flex items-center justify-between gap-3">
                                  <h4 className="font-semibold text-white">{checkpoint.label}</h4>
                                  <span className={`rounded-full border px-3 py-1 text-xs font-medium ${
                                    checkpoint.status === 'meets'
                                      ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
                                      : 'border-amber-400/30 bg-amber-500/10 text-amber-200'
                                  }`}>
                                    {checkpoint.status === 'meets' ? 'Looks documented' : 'Needs review'}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-300">{checkpoint.detail}</p>
                              </div>
                            ))}
                          </div>
                        )}
                        
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

              {/* Benefits Screening Tab */}
              {activeTab === 'eligibility' && (
                <div>
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-emerald-500 to-green-500 rounded-lg">
                      <CheckCircle className="h-6 w-6 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Benefits Screening</h2>
                  </div>

                  <div className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                    Use this quick screening to estimate likely benefit matches. Final approval depends on agency review, verification, and current program rules.
                  </div>
                  
                  <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/20 mb-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                          Selected Client
                        </label>
                        <input
                          type="text"
                          value={formatSelectedClientName()}
                          readOnly
                          className="w-full px-4 py-3 bg-white/5 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-gray-400 transition-all duration-300"
                          placeholder="Select a client above"
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
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {eligibilityFlagOptions.map((item) => (
                            <label key={item.key} className="flex items-center group cursor-pointer">
                              <input
                                type="checkbox"
                                checked={!!eligibilityData[item.key]}
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
                      {loading ? 'Running Screening...' : 'Run Screening'}
                    </button>
                  </div>

                  {/* Eligibility Results */}
                  {eligibilityResults && (
                    <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/5 backdrop-blur-xl border border-green-500/20 rounded-2xl p-8">
                      <div className="flex items-center gap-3 mb-6">
                      <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                          <CheckCircle className="h-5 w-5 text-white" />
                        </div>
                        <h3 className="text-xl font-bold text-green-200">Screening Results</h3>
                      </div>
                      {eligibilityResults.screening_profile && (
                        <div className="mb-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-green-100">
                          Income is approximately {eligibilityResults.screening_profile.income_percentage_of_poverty}% of the federal poverty level for a household of {eligibilityResults.screening_profile.household_size}.
                        </div>
                      )}
                      <div className="space-y-4">
                        {(eligibilityResults.eligible_programs || []).map((program, index) => (
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
                      <div>
                        <h2 className="text-2xl font-bold text-white">Benefits Applications</h2>
                        <p className="text-sm text-orange-200">
                          {selectedClient
                            ? `Showing tracked applications for ${selectedClient.first_name} ${selectedClient.last_name}`
                            : 'Showing tracked applications across the caseload'}
                        </p>
                      </div>
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
                      <p className="text-gray-400">
                        {selectedClient
                          ? 'No tracked applications yet for the selected client'
                          : 'Start by completing an assessment or eligibility check'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {applications.map((app, index) => (
                        <div key={index} className="group bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-xl border border-white/20 rounded-2xl p-6 hover:border-white/30 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-orange-500/10">
                          <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white group-hover:text-orange-200 transition-colors">{app.benefit_type}</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium border ${
                              app.application_status === 'approved' ? 'bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 border-green-500/30' :
                              app.application_status === 'pending' ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 text-yellow-300 border-yellow-500/30' :
                              'bg-gradient-to-r from-red-500/20 to-pink-500/20 text-red-300 border-red-500/30'
                            }`}>
                              {app.application_status || 'pending'}
                            </span>
                          </div>
                          <p className="text-orange-400 font-semibold mb-2">Client: {getApplicationClientLabel(app)}</p>
                          <p className="text-gray-300 mb-2">Applied: {new Date(app.created_at).toLocaleDateString()}</p>
                          <p className="text-gray-300 mb-2">Current step: {app.current_step || 'Application created'}</p>
                          <p className="text-amber-200 mb-2">Next action: {app.next_action_required || 'Review required documents and filing steps'}</p>
                          <p className="text-gray-400 mb-2">Follow up by: {app.follow_up_date || 'Not set'}</p>
                          {app.notes && <p className="text-gray-300">Notes: {app.notes}</p>}
                          <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
                            <div className="flex items-center justify-between gap-4 mb-3">
                              <div>
                                <h4 className="text-sm font-semibold text-white">Supporting documents</h4>
                                <p className="text-xs text-gray-400">Upload verifications, ID, income proofs, medical records, or agency letters for this application.</p>
                              </div>
                              <span className="text-xs text-orange-200">{(applicationDocuments[app.application_id] || []).length} uploaded</span>
                            </div>

                            {(applicationDocuments[app.application_id] || []).length > 0 ? (
                              <div className="space-y-2 mb-4">
                                {(applicationDocuments[app.application_id] || []).map((doc) => (
                                  <div key={doc.document_id} className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 rounded-xl border border-white/10 bg-black/10 px-4 py-3">
                                    <div>
                                      <p className="text-sm font-medium text-white">{doc.document_type}</p>
                                      <p className="text-xs text-gray-400">
                                        {doc.file_name || 'Uploaded document'} {doc.uploaded_at ? `• ${new Date(doc.uploaded_at).toLocaleDateString()}` : ''}
                                      </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">
                                        {doc.document_status || 'Received'}
                                      </span>
                                      <button
                                        onClick={() => window.open(`/api/benefits/documents/${encodeURIComponent(doc.document_id)}/download`, '_blank', 'noopener,noreferrer')}
                                        className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white transition-all duration-300 hover:bg-white/20"
                                      >
                                        <FileText className="h-4 w-4" />
                                        Download
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="mb-4 text-sm text-gray-400">No supporting documents uploaded yet.</p>
                            )}

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                              <input
                                type="text"
                                value={applicationUploadMeta[app.application_id]?.document_type || ''}
                                onChange={(e) => setApplicationUploadMeta((prev) => ({
                                  ...prev,
                                  [app.application_id]: {
                                    ...(prev[app.application_id] || {}),
                                    document_type: e.target.value,
                                  },
                                }))}
                                placeholder="Document type"
                                className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-white placeholder-gray-400"
                              />
                              <select
                                value={applicationUploadMeta[app.application_id]?.document_status || 'Received'}
                                onChange={(e) => setApplicationUploadMeta((prev) => ({
                                  ...prev,
                                  [app.application_id]: {
                                    ...(prev[app.application_id] || {}),
                                    document_status: e.target.value,
                                  },
                                }))}
                                className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-white"
                              >
                                <option value="Received" className="bg-gray-900">Received</option>
                                <option value="Pending Review" className="bg-gray-900">Pending Review</option>
                                <option value="Submitted" className="bg-gray-900">Submitted</option>
                              </select>
                              <input
                                type="file"
                                onChange={(e) => setApplicationUploadFiles((prev) => ({
                                  ...prev,
                                  [app.application_id]: e.target.files?.[0] || null,
                                }))}
                                className="block w-full text-sm text-gray-300 file:mr-4 file:rounded-lg file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-white hover:file:bg-white/20"
                              />
                            </div>
                            <textarea
                              rows="2"
                              value={applicationUploadMeta[app.application_id]?.notes || ''}
                              onChange={(e) => setApplicationUploadMeta((prev) => ({
                                ...prev,
                                [app.application_id]: {
                                  ...(prev[app.application_id] || {}),
                                  notes: e.target.value,
                                },
                              }))}
                              placeholder="Document notes or what still needs to be submitted"
                              className="mb-3 w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-white placeholder-gray-400"
                            />
                            <button
                              onClick={() => uploadBenefitDocument(app)}
                              className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-5 py-3 text-sm font-medium text-white transition-all duration-300 hover:bg-white/20"
                            >
                              <Plus className="h-4 w-4" />
                              Upload Supporting Document
                            </button>
                          </div>
                          <div className="mt-4 flex flex-wrap gap-3">
                            {getBenefitApplicationLink(app.benefit_type) && (
                              <button
                                onClick={() => window.open(getBenefitApplicationLink(app.benefit_type).url, '_blank', 'noopener,noreferrer')}
                                className="group/btn inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white rounded-xl font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-orange-500/25"
                              >
                                <Search className="h-4 w-4 group-hover/btn:scale-110 transition-transform duration-300" />
                                Open Application Site
                              </button>
                            )}
                            <button
                              onClick={() => createBenefitReminder(app)}
                              className="group/btn inline-flex items-center gap-2 px-5 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-xl font-medium transition-all duration-300"
                            >
                              <Clock className="h-4 w-4 group-hover/btn:scale-110 transition-transform duration-300" />
                              Create Follow-up Reminder
                            </button>
                          </div>
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
