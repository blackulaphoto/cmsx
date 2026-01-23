import { useState, useEffect } from 'react'
import { FileText } from 'lucide-react'

function ResumeMinimal() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [availableClients, setAvailableClients] = useState([])
  const [activeTab, setActiveTab] = useState('builder')

  // Mock data for testing
  useEffect(() => {
    setAvailableClients([
      { client_id: '1', first_name: 'John', last_name: 'Doe', email: 'john@example.com' },
      { client_id: '2', first_name: 'Jane', last_name: 'Smith', email: 'jane@example.com' }
    ])
  }, [])

  const handleClientSelection = (client) => {
    setSelectedClient(client)
    console.log('Selected client:', client)
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <FileText size={32} />
          <h1 className="text-3xl font-bold">Resume Builder</h1>
        </div>
        <p className="text-lg opacity-90">Create professional resumes with live preview</p>
      </div>

      <div className="p-8">
        {/* Client Selection */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Select Client</h2>
          <select 
            onChange={(e) => {
              const client = availableClients.find(c => c.client_id === e.target.value)
              if (client) handleClientSelection(client)
            }}
            className="w-full max-w-md p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select a client...</option>
            {availableClients.map(client => (
              <option key={client.client_id} value={client.client_id}>
                {client.first_name} {client.last_name} - {client.email}
              </option>
            ))}
          </select>
          
          {selectedClient && (
            <div className="mt-2 text-green-600">
              ✓ {selectedClient.first_name} {selectedClient.last_name} selected
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-8">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'builder', label: 'Resume Builder' },
              { id: 'templates', label: 'Templates' },
              { id: 'resumes', label: 'My Resumes' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'builder' && (
              <div>
                {!selectedClient ? (
                  <div className="text-center py-16 text-gray-500">
                    <FileText className="h-16 w-16 mx-auto mb-4 opacity-50" />
                    <h3 className="text-xl font-medium mb-2">Select a Client to Begin</h3>
                    <p>Choose a client from the dropdown above to start building their resume</p>
                  </div>
                ) : (
                  <div className="flex flex-col lg:flex-row gap-8 min-h-[600px]">
                    {/* Left Panel - Form */}
                    <div className="flex-1 lg:w-3/5 space-y-6">
                      <div className="bg-white border border-gray-200 rounded-lg p-6">
                        <h3 className="text-lg font-semibold mb-4">Career Objective</h3>
                        <textarea
                          placeholder="Brief statement about career goals and objectives..."
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          rows={3}
                        />
                      </div>

                      <div className="bg-white border border-gray-200 rounded-lg p-6">
                        <h3 className="text-lg font-semibold mb-4">Work Experience</h3>
                        <p className="text-gray-600">Work experience form will be here</p>
                      </div>

                      <div className="bg-white border border-gray-200 rounded-lg p-6">
                        <h3 className="text-lg font-semibold mb-4">Skills</h3>
                        <p className="text-gray-600">Skills form will be here</p>
                      </div>
                    </div>

                    {/* Right Panel - Preview */}
                    <div className="flex-1 lg:w-2/5">
                      <div className="h-full bg-white border border-gray-200 rounded-lg p-6">
                        <h3 className="text-lg font-semibold mb-4">Live Preview</h3>
                        <div className="h-96 bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center">
                          <div className="text-center">
                            <FileText className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                            <p className="text-gray-500">Resume preview will appear here</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'templates' && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Templates</h3>
                <p>Template selection will be here</p>
              </div>
            )}

            {activeTab === 'resumes' && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Saved Resumes</h3>
                <p>Saved resumes will be here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ResumeMinimal