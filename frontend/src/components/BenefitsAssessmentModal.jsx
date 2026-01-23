import React, { useState, useEffect } from 'react'
import { 
  X, 
  ChevronRight, 
  ChevronLeft, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  FileText, 
  DollarSign,
  Users,
  Calendar,
  Phone,
  ExternalLink,
  Loader2
} from 'lucide-react'

const BenefitsAssessmentModal = ({ 
  isOpen, 
  onClose, 
  program, 
  selectedClient, 
  onAssessmentComplete 
}) => {
  const [questions, setQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [responses, setResponses] = useState({})
  const [loading, setLoading] = useState(false)
  const [assessmentResult, setAssessmentResult] = useState(null)
  const [error, setError] = useState(null)
  const [showResults, setShowResults] = useState(false)

  // Load questions when modal opens
  useEffect(() => {
    if (isOpen && program) {
      loadProgramQuestions()
    }
  }, [isOpen, program])

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setQuestions([])
      setCurrentQuestionIndex(0)
      setResponses({})
      setAssessmentResult(null)
      setError(null)
      setShowResults(false)
    }
  }, [isOpen])

  const loadProgramQuestions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Use query parameter route to avoid URL encoding issues with programs containing special characters
      console.log('Loading questions for program:', program)
      const response = await fetch(`/api/benefits/program-questions?program=${encodeURIComponent(program)}`)
      const data = await response.json()
      
      if (data.success) {
        setQuestions(data.questions)
      } else {
        setError('Failed to load assessment questions')
      }
    } catch (err) {
      console.error('Error loading questions:', err)
      setError('Failed to load assessment questions')
    } finally {
      setLoading(false)
    }
  }

  const handleResponseChange = (questionId, value) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }))
  }

  const getCurrentQuestion = () => {
    return questions[currentQuestionIndex]
  }

  const canProceed = () => {
    const currentQuestion = getCurrentQuestion()
    if (!currentQuestion) return false
    
    const response = responses[currentQuestion.id]
    return response !== undefined && response !== ''
  }

  const nextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const previousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const submitAssessment = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/benefits/assess-program-eligibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_id: selectedClient?.client_id || 'unknown',
          program: program,
          responses: responses
        })
      })
      
      const data = await response.json()
      
      if (data.success) {
        setAssessmentResult(data.assessment_result)
        setShowResults(true)
        
        // Notify parent component
        if (onAssessmentComplete) {
          onAssessmentComplete(data.assessment_result)
        }
      } else {
        setError('Assessment failed. Please try again.')
      }
    } catch (err) {
      console.error('Error submitting assessment:', err)
      setError('Assessment failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const renderQuestionInput = (question) => {
    const response = responses[question.id] || ''
    
    switch (question.type) {
      case 'Yes/No':
        return (
          <div className="space-y-3">
            {['yes', 'no'].map(option => (
              <label key={option} className="flex items-center space-x-3 cursor-pointer group">
                <input
                  type="radio"
                  name={question.id}
                  value={option}
                  checked={response === option}
                  onChange={(e) => handleResponseChange(question.id, e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="text-gray-700 group-hover:text-gray-900 capitalize">
                  {option}
                </span>
              </label>
            ))}
          </div>
        )
      
      case 'Multiple Choice':
        return (
          <div className="space-y-3">
            {question.options?.map(option => (
              <label key={option.value} className="flex items-center space-x-3 cursor-pointer group">
                <input
                  type="radio"
                  name={question.id}
                  value={option.value}
                  checked={response === option.value}
                  onChange={(e) => handleResponseChange(question.id, e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="text-gray-700 group-hover:text-gray-900">
                  {option.label}
                </span>
              </label>
            ))}
          </div>
        )
      
      case 'Number':
        return (
          <input
            type="number"
            value={response}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter number"
            min={question.validation?.min || 0}
            max={question.validation?.max}
          />
        )
      
      case 'Currency':
        return (
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <DollarSign className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="number"
              value={response}
              onChange={(e) => handleResponseChange(question.id, e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0.00"
              min="0"
              step="0.01"
            />
          </div>
        )
      
      case 'Percentage':
        return (
          <div className="relative">
            <input
              type="number"
              value={response}
              onChange={(e) => handleResponseChange(question.id, e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter percentage"
              min="0"
              max="100"
            />
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span className="text-gray-400">%</span>
            </div>
          </div>
        )
      
      default:
        return (
          <input
            type="text"
            value={response}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter your answer"
          />
        )
    }
  }

  const getEligibilityStatusColor = (status) => {
    switch (status) {
      case 'eligible':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'partially_eligible':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'not_eligible':
        return 'text-red-600 bg-red-50 border-red-200'
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  const getEligibilityIcon = (status) => {
    switch (status) {
      case 'eligible':
        return <CheckCircle className="h-6 w-6 text-green-600" />
      case 'partially_eligible':
        return <AlertCircle className="h-6 w-6 text-yellow-600" />
      case 'not_eligible':
        return <X className="h-6 w-6 text-red-600" />
      default:
        return <Clock className="h-6 w-6 text-blue-600" />
    }
  }

  const getEligibilityTitle = (status) => {
    switch (status) {
      case 'eligible':
        return 'Eligible'
      case 'partially_eligible':
        return 'Partially Eligible'
      case 'not_eligible':
        return 'Not Eligible'
      default:
        return 'Needs Review'
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Benefits Eligibility Assessment</h2>
              <p className="text-blue-100 mt-1">{program}</p>
              {selectedClient && (
                <p className="text-blue-200 text-sm mt-1">
                  Client: {selectedClient.first_name} {selectedClient.last_name}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading && !showResults && (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
                <p className="text-gray-600">Loading assessment questions...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-center">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2" />
                  <p className="text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Assessment Questions */}
          {!loading && !error && !showResults && questions.length > 0 && (
            <div className="p-6">
              {/* Progress Bar */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Question {currentQuestionIndex + 1} of {questions.length}
                  </span>
                  <span className="text-sm text-gray-500">
                    {Math.round(((currentQuestionIndex + 1) / questions.length) * 100)}% Complete
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
                  />
                </div>
              </div>

              {/* Current Question */}
              {getCurrentQuestion() && (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-start space-x-3 mb-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-semibold text-sm">
                          {currentQuestionIndex + 1}
                        </span>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          {getCurrentQuestion().question}
                        </h3>
                        {getCurrentQuestion().help_text && (
                          <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                            💡 {getCurrentQuestion().help_text}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="ml-11">
                    {renderQuestionInput(getCurrentQuestion())}
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={previousQuestion}
                  disabled={currentQuestionIndex === 0}
                  className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Previous</span>
                </button>

                <div className="flex space-x-3">
                  {currentQuestionIndex === questions.length - 1 ? (
                    <button
                      onClick={submitAssessment}
                      disabled={!canProceed() || loading}
                      className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl hover:from-green-600 hover:to-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Assessing...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4" />
                          <span>Complete Assessment</span>
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={nextQuestion}
                      disabled={!canProceed()}
                      className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                      <span>Next</span>
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Assessment Results */}
          {showResults && assessmentResult && (
            <div className="p-6 space-y-6">
              {/* Status Header */}
              <div className={`rounded-xl border-2 p-6 ${getEligibilityStatusColor(assessmentResult.eligibility_status)}`}>
                <div className="flex items-center space-x-4">
                  {getEligibilityIcon(assessmentResult.eligibility_status)}
                  <div>
                    <h3 className="text-xl font-bold">
                      {getEligibilityTitle(assessmentResult.eligibility_status)}
                    </h3>
                    <p className="text-sm opacity-80 mt-1">
                      Confidence Score: {assessmentResult.confidence_score.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Key Information Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Estimated Benefit */}
                {assessmentResult.estimated_benefit_amount && (
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                    <div className="flex items-center space-x-3">
                      <DollarSign className="h-6 w-6 text-green-600" />
                      <div>
                        <h4 className="font-semibold text-green-800">Estimated Monthly Benefit</h4>
                        <p className="text-2xl font-bold text-green-600">
                          ${assessmentResult.estimated_benefit_amount}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Processing Timeline */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-center space-x-3">
                    <Calendar className="h-6 w-6 text-blue-600" />
                    <div>
                      <h4 className="font-semibold text-blue-800">Processing Time</h4>
                      <p className="text-lg font-medium text-blue-600">
                        {assessmentResult.processing_timeline}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Qualifying Factors */}
              {assessmentResult.qualifying_factors.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <h4 className="font-semibold text-green-800 mb-3 flex items-center">
                    <CheckCircle className="h-5 w-5 mr-2" />
                    Qualifying Factors
                  </h4>
                  <ul className="space-y-2">
                    {assessmentResult.qualifying_factors.map((factor, index) => (
                      <li key={index} className="text-green-700 flex items-start">
                        <span className="text-green-500 mr-2">✓</span>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disqualifying Factors */}
              {assessmentResult.disqualifying_factors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <h4 className="font-semibold text-red-800 mb-3 flex items-center">
                    <X className="h-5 w-5 mr-2" />
                    Disqualifying Factors
                  </h4>
                  <ul className="space-y-2">
                    {assessmentResult.disqualifying_factors.map((factor, index) => (
                      <li key={index} className="text-red-700 flex items-start">
                        <span className="text-red-500 mr-2">✗</span>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Missing Information */}
              {assessmentResult.missing_information.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                  <h4 className="font-semibold text-yellow-800 mb-3 flex items-center">
                    <AlertCircle className="h-5 w-5 mr-2" />
                    Additional Information Needed
                  </h4>
                  <ul className="space-y-2">
                    {assessmentResult.missing_information.map((info, index) => (
                      <li key={index} className="text-yellow-700 flex items-start">
                        <span className="text-yellow-500 mr-2">!</span>
                        {info}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Required Documents */}
              {assessmentResult.required_documents.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <h4 className="font-semibold text-blue-800 mb-3 flex items-center">
                    <FileText className="h-5 w-5 mr-2" />
                    Required Documents
                  </h4>
                  <ul className="space-y-2">
                    {assessmentResult.required_documents.map((doc, index) => (
                      <li key={index} className="text-blue-700 flex items-start">
                        <span className="text-blue-500 mr-2">📄</span>
                        {doc}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Next Steps */}
              {assessmentResult.next_steps.length > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                  <h4 className="font-semibold text-purple-800 mb-3 flex items-center">
                    <ChevronRight className="h-5 w-5 mr-2" />
                    Next Steps
                  </h4>
                  <ol className="space-y-2">
                    {assessmentResult.next_steps.map((step, index) => (
                      <li key={index} className="text-purple-700 flex items-start">
                        <span className="text-purple-500 mr-2 font-semibold">{index + 1}.</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-6 border-t border-gray-200">
                <button
                  onClick={onClose}
                  className="px-6 py-3 text-gray-600 hover:text-gray-800 font-medium"
                >
                  Close Assessment
                </button>
                
                <div className="flex space-x-3">
                  {assessmentResult.eligibility_status === 'eligible' && (
                    <button
                      onClick={() => {
                        // This will be handled by the parent component
                        onClose()
                      }}
                      className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl hover:from-green-600 hover:to-emerald-600 font-medium"
                    >
                      <CheckCircle className="h-4 w-4" />
                      <span>Start Application</span>
                    </button>
                  )}
                  
                  <button
                    onClick={() => {
                      // Reset to take assessment again
                      setShowResults(false)
                      setAssessmentResult(null)
                      setCurrentQuestionIndex(0)
                      setResponses({})
                    }}
                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl hover:from-blue-600 hover:to-purple-600 font-medium"
                  >
                    <span>Retake Assessment</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BenefitsAssessmentModal