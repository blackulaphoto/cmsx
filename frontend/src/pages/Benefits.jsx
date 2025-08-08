import { useState, useEffect } from 'react'
import { Heart, FileText, CheckCircle, Clock, DollarSign, Users, AlertCircle, Plus, Search, User } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import ClientSelector from '../components/ClientSelector'
import toast from 'react-hot-toast'

function Benefits() {
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

  // Load applications on component mount
  useEffect(() => {
    fetchApplications()
  }, [])

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

  const startApplication = async (benefitType) => {
    const clientId = assessmentData.client_id || eligibilityData.client_id
    if (!clientId) {
      toast.error('Please complete assessment first')
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
          assessment_data: assessmentResults || eligibilityResults
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
    { name: 'SNAP/CalFresh', description: 'Food assistance program', icon: '🍎' },
    { name: 'Medicaid', description: 'Healthcare coverage', icon: '🏥' },
    { name: 'SSI', description: 'Supplemental Security Income', icon: '💰' },
    { name: 'SSDI', description: 'Social Security Disability Insurance', icon: '🛡️' },
    { name: 'Housing Vouchers', description: 'Housing assistance', icon: '🏠' },
    { name: 'TANF', description: 'Temporary Assistance for Families', icon: '👨‍👩‍👧‍👦' },
    { name: 'WIC', description: 'Women, Infants, and Children nutrition', icon: '🍼' },
    { name: 'Transportation', description: 'Medical/court transportation', icon: '🚌' }
  ]

  const stats = [
    { icon: FileText, label: 'Active Applications', value: applications.length.toString(), variant: 'primary' },
    { icon: CheckCircle, label: 'Approved', value: applications.filter(app => app.status === 'approved').length.toString(), variant: 'success' },
    { icon: Clock, label: 'Pending', value: applications.filter(app => app.status === 'pending').length.toString(), variant: 'warning' },
    { icon: DollarSign, label: 'Monthly Benefits', value: '$1,240', variant: 'secondary' },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Heart size={32} />
          <h1 className="text-3xl font-bold">Benefits & Support</h1>
        </div>
        <p className="text-lg opacity-90">Access to government benefits and support services</p>
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
            placeholder="Select a client to manage benefits for..."
            className="max-w-md"
          />
          {selectedClient && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                Managing benefits for: <strong>{selectedClient.first_name} {selectedClient.last_name}</strong>
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
              { id: 'overview', label: 'Overview', icon: Heart },
              { id: 'assessment', label: 'Disability Assessment', icon: FileText },
              { id: 'eligibility', label: 'Eligibility Check', icon: CheckCircle },
              { id: 'applications', label: 'Applications', icon: Clock }
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
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Available Benefit Programs</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {benefitPrograms.map((program, index) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-6 hover:shadow-custom-sm transition-shadow">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="text-2xl">{program.icon}</span>
                        <h3 className="text-lg font-semibold">{program.name}</h3>
                      </div>
                      <p className="text-gray-600 mb-4">{program.description}</p>
                      <button
                        onClick={() => startApplication(program.name)}
                        className="w-full px-4 py-2 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300"
                      >
                        Start Application
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Disability Assessment Tab */}
            {activeTab === 'assessment' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Disability Assessment Tool</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Client ID
                      </label>
                      <input
                        type="text"
                        value={assessmentData.client_id}
                        onChange={(e) => setAssessmentData(prev => ({ ...prev, client_id: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Enter client ID"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Age
                      </label>
                      <input
                        type="number"
                        value={assessmentData.age}
                        onChange={(e) => setAssessmentData(prev => ({ ...prev, age: parseInt(e.target.value) || '' }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Enter age"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Current Monthly Income ($)
                      </label>
                      <input
                        type="number"
                        value={assessmentData.current_income}
                        onChange={(e) => setAssessmentData(prev => ({ ...prev, current_income: parseFloat(e.target.value) || 0 }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Enter monthly income"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Years Out of Work
                      </label>
                      <input
                        type="number"
                        value={assessmentData.years_out_of_work}
                        onChange={(e) => setAssessmentData(prev => ({ ...prev, years_out_of_work: parseInt(e.target.value) || 0 }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Years unable to work"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Medical Conditions (Select all that apply)
                    </label>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {medicalConditions.map((condition, index) => (
                        <label key={index} className="flex items-center">
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
                            className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-700">{condition}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-6">
                  <button
                    onClick={handleDisabilityAssessment}
                    disabled={loading}
                    className="px-8 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Processing...' : 'Run Disability Assessment'}
                  </button>
                </div>

                {/* Assessment Results */}
                {assessmentResults && (
                  <div className="mt-6 space-y-6">
                    <div className="p-6 bg-blue-50 rounded-xl">
                      <h3 className="text-lg font-semibold mb-4 text-blue-900">Assessment Results Summary</h3>
                      
                      {/* SSI and SSDI Eligibility */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        {assessmentResults.assessment?.ssi_eligibility && (
                          <div className="bg-white rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-semibold text-gray-900">SSI Eligibility</h4>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                                assessmentResults.assessment.ssi_eligibility.eligible 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {assessmentResults.assessment.ssi_eligibility.eligible ? 'Eligible' : 'Not Eligible'}
                              </span>
                            </div>
                            {assessmentResults.assessment.ssi_eligibility.eligible && (
                              <p className="text-sm text-gray-600 mb-2">
                                Estimated monthly benefit: <span className="font-semibold text-green-600">
                                  ${assessmentResults.assessment.ssi_eligibility.estimated_monthly_benefit}
                                </span>
                              </p>
                            )}
                            <p className="text-xs text-gray-500">
                              Confidence: {assessmentResults.assessment.ssi_eligibility.confidence_level}
                            </p>
                          </div>
                        )}
                        
                        {assessmentResults.assessment?.ssdi_eligibility && (
                          <div className="bg-white rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-semibold text-gray-900">SSDI Eligibility</h4>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                                assessmentResults.assessment.ssdi_eligibility.eligible 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {assessmentResults.assessment.ssdi_eligibility.eligible ? 'Eligible' : 'Not Eligible'}
                              </span>
                            </div>
                            {assessmentResults.assessment.ssdi_eligibility.eligible && (
                              <p className="text-sm text-gray-600 mb-2">
                                Estimated monthly benefit: <span className="font-semibold text-green-600">
                                  ${assessmentResults.assessment.ssdi_eligibility.estimated_monthly_benefit}
                                </span>
                              </p>
                            )}
                            <p className="text-xs text-gray-500">
                              Work Credits: {assessmentResults.assessment.ssdi_eligibility.work_credits} / {assessmentResults.assessment.ssdi_eligibility.credits_needed} needed
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Medical Conditions Found */}
                      {assessmentResults.assessment?.medical_assessment?.matching_conditions && (
                        <div className="mb-6">
                          <h4 className="font-semibold text-blue-900 mb-3">Qualifying Medical Conditions Found</h4>
                          <div className="space-y-3">
                            {assessmentResults.assessment.medical_assessment.matching_conditions.map((condition, index) => (
                              <div key={index} className="bg-white rounded-lg p-4 border-l-4 border-blue-400">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <h5 className="font-medium text-gray-900">{condition.name}</h5>
                                    <p className="text-sm text-gray-600 mb-2">SSA Listing: {condition.ssa_listing} | Category: {condition.category}</p>
                                    <p className="text-sm text-green-600 font-medium">
                                      Approval Rate: {Math.round(condition.approval_rate * 100)}% | Match Type: {condition.match_type || 'direct'}
                                    </p>
                                    {condition.original_condition && (
                                      <p className="text-xs text-blue-600">Originally: {condition.original_condition}</p>
                                    )}
                                  </div>
                                </div>
                                {condition.severity_criteria && (
                                  <div className="mt-3">
                                    <p className="text-xs font-medium text-gray-700 mb-1">Key Severity Criteria:</p>
                                    <ul className="text-xs text-gray-600 list-disc list-inside space-y-1">
                                      {condition.severity_criteria.slice(0, 3).map((criteria, idx) => (
                                        <li key={idx}>{criteria}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                          
                          <div className="mt-3 p-3 bg-blue-100 rounded-lg">
                            <p className="text-sm text-blue-800">
                              <span className="font-semibold">Overall Approval Probability:</span> {' '}
                              <span className="text-lg font-bold">
                                {Math.round(assessmentResults.assessment.medical_assessment.estimated_approval_probability * 100)}%
                              </span>
                            </p>
                            <p className="text-xs text-blue-600 mt-1">
                              {assessmentResults.assessment.medical_assessment.affected_body_systems} body system(s) affected • {' '}
                              {assessmentResults.assessment.medical_assessment.condition_count} qualifying condition(s)
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Recommendations */}
                      {assessmentResults.assessment?.recommendations && (
                        <div className="mb-6">
                          <h4 className="font-semibold text-blue-900 mb-3">Recommendations</h4>
                          <div className="space-y-2">
                            {assessmentResults.assessment.recommendations.map((rec, index) => (
                              <div key={index} className="flex items-start gap-2 p-3 bg-white rounded-lg">
                                <span className="text-blue-500 mt-0.5">•</span>
                                <span className="text-sm text-gray-700" dangerouslySetInnerHTML={{__html: rec}} />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Next Steps */}
                      {assessmentResults.assessment?.next_steps && (
                        <div className="mb-6">
                          <h4 className="font-semibold text-blue-900 mb-3">Next Steps</h4>
                          <div className="space-y-3">
                            {assessmentResults.assessment.next_steps.map((step, index) => (
                              <div key={index} className="bg-white rounded-lg p-4">
                                <div className="flex items-start justify-between mb-2">
                                  <h5 className="font-medium text-gray-900">{step.step}</h5>
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                                    step.priority === 'High' ? 'bg-red-100 text-red-800' :
                                    step.priority === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {step.priority}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-600 mb-1">{step.description}</p>
                                <p className="text-xs text-gray-500">Estimated Time: {step.estimated_time}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Timeline */}
                      {assessmentResults.assessment?.estimated_timeline && (
                        <div className="p-4 bg-amber-50 rounded-lg">
                          <h4 className="font-semibold text-amber-900 mb-2">Expected Timeline</h4>
                          <div className="text-sm text-amber-800 space-y-1">
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
                <h2 className="text-2xl font-bold mb-6">Benefits Eligibility Check</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Client ID
                    </label>
                    <input
                      type="text"
                      value={eligibilityData.client_id}
                      onChange={(e) => setEligibilityData(prev => ({ ...prev, client_id: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      placeholder="Enter client ID"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Household Size
                    </label>
                    <input
                      type="number"
                      value={eligibilityData.household_size}
                      onChange={(e) => setEligibilityData(prev => ({ ...prev, household_size: parseInt(e.target.value) || 1 }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      min="1"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Monthly Income ($)
                    </label>
                    <input
                      type="number"
                      value={eligibilityData.monthly_income}
                      onChange={(e) => setEligibilityData(prev => ({ ...prev, monthly_income: parseFloat(e.target.value) || 0 }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Age (optional)
                    </label>
                    <input
                      type="number"
                      value={eligibilityData.age || ''}
                      onChange={(e) => setEligibilityData(prev => ({ ...prev, age: parseInt(e.target.value) || null }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <div className="space-y-3">
                      {[
                        { key: 'is_disabled', label: 'Has disability' },
                        { key: 'is_veteran', label: 'Military veteran' },
                        { key: 'has_children', label: 'Has dependent children' }
                      ].map((item) => (
                        <label key={item.key} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={eligibilityData[item.key]}
                            onChange={(e) => setEligibilityData(prev => ({ ...prev, [item.key]: e.target.checked }))}
                            className="mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-700">{item.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-6">
                  <button
                    onClick={handleEligibilityCheck}
                    disabled={loading}
                    className="px-8 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Checking...' : 'Check Eligibility'}
                  </button>
                </div>

                {/* Eligibility Results */}
                {eligibilityResults && (
                  <div className="mt-6 p-6 bg-green-50 rounded-xl">
                    <h3 className="text-lg font-semibold mb-4 text-green-900">Eligibility Results</h3>
                    <div className="space-y-4">
                      {eligibilityResults.eligible_programs?.map((program, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-white rounded-lg">
                          <div>
                            <p className="font-medium text-green-800">{program.program}</p>
                            <p className="text-sm text-green-600">{program.reason}</p>
                          </div>
                          <CheckCircle className="text-green-500" size={24} />
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
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">Benefits Applications</h2>
                  <button
                    onClick={fetchApplications}
                    className="px-4 py-2 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300"
                  >
                    Refresh
                  </button>
                </div>

                {applications.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <FileText size={48} className="mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium mb-2">No applications found</h3>
                    <p className="text-sm">Start by completing an assessment or eligibility check</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {applications.map((app, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-lg font-semibold">{app.benefit_type}</h3>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            app.status === 'approved' ? 'bg-green-100 text-green-800' :
                            app.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {app.status}
                          </span>
                        </div>
                        <p className="text-gray-600 mb-2">Client: {app.client_id}</p>
                        <p className="text-gray-600 mb-2">Applied: {new Date(app.created_at).toLocaleDateString()}</p>
                        {app.notes && <p className="text-gray-600">Notes: {app.notes}</p>}
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
  )
}

export default Benefits