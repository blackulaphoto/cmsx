import React from 'react'
import { 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  Clock, 
  DollarSign, 
  Calendar,
  FileText,
  ChevronRight
} from 'lucide-react'

const AssessmentResults = ({ 
  assessmentResult, 
  onStartApplication, 
  onRetakeAssessment,
  compact = false 
}) => {
  if (!assessmentResult) return null

  const getStatusConfig = (status) => {
    switch (status) {
      case 'eligible':
        return {
          icon: CheckCircle,
          color: 'green',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          iconColor: 'text-green-600',
          title: 'Eligible',
          description: 'You qualify for this program'
        }
      case 'partially_eligible':
        return {
          icon: AlertCircle,
          color: 'yellow',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800',
          iconColor: 'text-yellow-600',
          title: 'Partially Eligible',
          description: 'Additional information may be needed'
        }
      case 'not_eligible':
        return {
          icon: XCircle,
          color: 'red',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          iconColor: 'text-red-600',
          title: 'Not Eligible',
          description: 'You do not currently qualify'
        }
      default:
        return {
          icon: Clock,
          color: 'blue',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          iconColor: 'text-blue-600',
          title: 'Needs Review',
          description: 'Assessment requires case manager review'
        }
    }
  }

  const statusConfig = getStatusConfig(assessmentResult.eligibility_status)
  const StatusIcon = statusConfig.icon

  // Compact version for program cards
  if (compact) {
    return (
      <div className={`${statusConfig.bgColor} ${statusConfig.borderColor} border rounded-lg p-3 mt-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <StatusIcon className={`h-4 w-4 ${statusConfig.iconColor}`} />
            <span className={`text-sm font-medium ${statusConfig.textColor}`}>
              {statusConfig.title}
            </span>
            <span className="text-xs text-gray-500">
              ({assessmentResult.confidence_score.toFixed(0)}%)
            </span>
          </div>
          
          {assessmentResult.estimated_benefit_amount && (
            <div className="flex items-center space-x-1 text-xs text-gray-600">
              <DollarSign className="h-3 w-3" />
              <span>${assessmentResult.estimated_benefit_amount}/mo</span>
            </div>
          )}
        </div>
        
        {assessmentResult.eligibility_status === 'eligible' && (
          <button
            onClick={onStartApplication}
            className="w-full mt-2 px-3 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
          >
            Start Application
          </button>
        )}
        
        {assessmentResult.eligibility_status !== 'eligible' && (
          <button
            onClick={onRetakeAssessment}
            className="w-full mt-2 px-3 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 transition-colors"
          >
            Retake Assessment
          </button>
        )}
      </div>
    )
  }

  // Full detailed version
  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className={`${statusConfig.bgColor} ${statusConfig.borderColor} border-2 rounded-xl p-6`}>
        <div className="flex items-center space-x-4">
          <StatusIcon className={`h-8 w-8 ${statusConfig.iconColor}`} />
          <div>
            <h3 className={`text-xl font-bold ${statusConfig.textColor}`}>
              {statusConfig.title}
            </h3>
            <p className={`${statusConfig.textColor} opacity-80 mt-1`}>
              {statusConfig.description}
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Confidence Score: {assessmentResult.confidence_score.toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {assessmentResult.estimated_benefit_amount && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <DollarSign className="h-6 w-6 text-green-600" />
              <div>
                <h4 className="font-semibold text-green-800">Monthly Benefit</h4>
                <p className="text-xl font-bold text-green-600">
                  ${assessmentResult.estimated_benefit_amount}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
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
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="font-semibold text-green-800 mb-3 flex items-center">
            <CheckCircle className="h-5 w-5 mr-2" />
            Qualifying Factors ({assessmentResult.qualifying_factors.length})
          </h4>
          <ul className="space-y-1">
            {assessmentResult.qualifying_factors.slice(0, 3).map((factor, index) => (
              <li key={index} className="text-green-700 text-sm flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                {factor}
              </li>
            ))}
            {assessmentResult.qualifying_factors.length > 3 && (
              <li className="text-green-600 text-sm italic">
                +{assessmentResult.qualifying_factors.length - 3} more factors
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Disqualifying Factors */}
      {assessmentResult.disqualifying_factors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="font-semibold text-red-800 mb-3 flex items-center">
            <XCircle className="h-5 w-5 mr-2" />
            Issues to Address ({assessmentResult.disqualifying_factors.length})
          </h4>
          <ul className="space-y-1">
            {assessmentResult.disqualifying_factors.slice(0, 3).map((factor, index) => (
              <li key={index} className="text-red-700 text-sm flex items-start">
                <span className="text-red-500 mr-2">✗</span>
                {factor}
              </li>
            ))}
            {assessmentResult.disqualifying_factors.length > 3 && (
              <li className="text-red-600 text-sm italic">
                +{assessmentResult.disqualifying_factors.length - 3} more issues
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Missing Information */}
      {assessmentResult.missing_information.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-semibold text-yellow-800 mb-3 flex items-center">
            <AlertCircle className="h-5 w-5 mr-2" />
            Additional Information Needed
          </h4>
          <ul className="space-y-1">
            {assessmentResult.missing_information.slice(0, 3).map((info, index) => (
              <li key={index} className="text-yellow-700 text-sm flex items-start">
                <span className="text-yellow-500 mr-2">!</span>
                {info}
              </li>
            ))}
            {assessmentResult.missing_information.length > 3 && (
              <li className="text-yellow-600 text-sm italic">
                +{assessmentResult.missing_information.length - 3} more items
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Required Documents */}
      {assessmentResult.required_documents.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-800 mb-3 flex items-center">
            <FileText className="h-5 w-5 mr-2" />
            Required Documents
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {assessmentResult.required_documents.slice(0, 6).map((doc, index) => (
              <div key={index} className="text-blue-700 text-sm flex items-start">
                <span className="text-blue-500 mr-2">📄</span>
                {doc}
              </div>
            ))}
          </div>
          {assessmentResult.required_documents.length > 6 && (
            <p className="text-blue-600 text-sm italic mt-2">
              +{assessmentResult.required_documents.length - 6} more documents
            </p>
          )}
        </div>
      )}

      {/* Next Steps */}
      {assessmentResult.next_steps.length > 0 && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h4 className="font-semibold text-purple-800 mb-3 flex items-center">
            <ChevronRight className="h-5 w-5 mr-2" />
            Recommended Next Steps
          </h4>
          <ol className="space-y-2">
            {assessmentResult.next_steps.slice(0, 4).map((step, index) => (
              <li key={index} className="text-purple-700 text-sm flex items-start">
                <span className="text-purple-500 mr-2 font-semibold min-w-[1.5rem]">
                  {index + 1}.
                </span>
                {step}
              </li>
            ))}
            {assessmentResult.next_steps.length > 4 && (
              <li className="text-purple-600 text-sm italic">
                +{assessmentResult.next_steps.length - 4} more steps
              </li>
            )}
          </ol>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <button
          onClick={onRetakeAssessment}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
        >
          Retake Assessment
        </button>
        
        {assessmentResult.eligibility_status === 'eligible' && (
          <button
            onClick={onStartApplication}
            className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl hover:from-green-600 hover:to-emerald-600 font-medium"
          >
            <CheckCircle className="h-4 w-4" />
            <span>Start Application</span>
          </button>
        )}
      </div>
    </div>
  )
}

export default AssessmentResults