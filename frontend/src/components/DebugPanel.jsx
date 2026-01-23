import { useState } from 'react'
import { Bug, ChevronDown, ChevronUp } from 'lucide-react'

const DebugPanel = ({ 
  selectedClient, 
  employmentProfile, 
  selectedTemplate, 
  activeTab 
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  // Only show in development
  if (process.env.NODE_ENV === 'production') {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 text-white rounded-lg shadow-lg z-50 max-w-md">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 p-3 w-full text-left hover:bg-gray-800 rounded-lg"
      >
        <Bug className="h-4 w-4" />
        <span className="font-medium">Debug Panel</span>
        {isExpanded ? <ChevronUp className="h-4 w-4 ml-auto" /> : <ChevronDown className="h-4 w-4 ml-auto" />}
      </button>
      
      {isExpanded && (
        <div className="p-4 border-t border-gray-700 text-xs space-y-3 max-h-96 overflow-y-auto">
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Active Tab</h4>
            <p className="text-gray-300">{activeTab}</p>
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Selected Client</h4>
            <p className="text-gray-300">
              {selectedClient ? `${selectedClient.first_name} ${selectedClient.last_name}` : 'None'}
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Selected Template</h4>
            <p className="text-gray-300">
              {selectedTemplate ? `${selectedTemplate.name} (${selectedTemplate.id})` : 'None'}
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Career Objective</h4>
            <p className="text-gray-300 break-words">
              {employmentProfile.career_objective || 'Empty'}
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Work History</h4>
            <p className="text-gray-300">
              {employmentProfile.work_history?.length || 0} entries
            </p>
            {employmentProfile.work_history?.map((job, index) => (
              <div key={index} className="ml-2 text-gray-400">
                • {job.job_title || 'No title'} at {job.company || 'No company'}
              </div>
            ))}
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Skills</h4>
            <p className="text-gray-300">
              {employmentProfile.skills?.length || 0} categories
            </p>
            {employmentProfile.skills?.map((skillCat, index) => (
              <div key={index} className="ml-2 text-gray-400">
                • {skillCat.category}: {skillCat.skill_list?.length || 0} skills
              </div>
            ))}
          </div>
          
          <div>
            <h4 className="font-semibold text-yellow-400 mb-1">Preview Status</h4>
            <div className="space-y-1">
              <p className="text-gray-300">
                Client: {selectedClient ? '✅' : '❌'}
              </p>
              <p className="text-gray-300">
                Template: {selectedTemplate ? '✅' : '❌'}
              </p>
              <p className="text-gray-300">
                Profile Data: {employmentProfile.career_objective ? '✅' : '❌'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DebugPanel