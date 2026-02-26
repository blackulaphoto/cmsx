import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, User, ChevronDown, Plus, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'

const ClientSelector = ({ 
  selectedClientId = null, 
  onClientSelect = null, 
  showCreateNew = true,
  showViewDashboard = true,
  placeholder = "Select a client...",
  className = ""
}) => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [selectedClient, setSelectedClient] = useState(null)

  // Initialize from URL params or props
  useEffect(() => {
    const clientFromUrl = searchParams.get('client')
    if (clientFromUrl && !selectedClientId) {
      fetchClientById(clientFromUrl)
    } else if (selectedClientId) {
      fetchClientById(selectedClientId)
    }
  }, [selectedClientId, searchParams])

  // Fetch clients when dropdown opens
  useEffect(() => {
    if (isOpen && clients.length === 0) {
      fetchClients()
    }
  }, [isOpen])

  // Sync selectedClient with parent component when it changes
  useEffect(() => {
    if (selectedClient && onClientSelect) {
      onClientSelect(selectedClient)
    }
  }, [selectedClient, onClientSelect])

  const fetchClients = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/clients?limit=100')
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to fetch clients`)
      }
      
      const data = await response.json()
      if (data.success && Array.isArray(data.clients)) {
        setClients(data.clients)
      } else if (Array.isArray(data.clients)) {
        setClients(data.clients)
      } else {
        throw new Error(data.message || 'Invalid response format')
      }
    } catch (error) {
      console.error('Error fetching clients:', error)
      toast.error(`Failed to load clients: ${error.message}`)
      setClients([])
    } finally {
      setLoading(false)
    }
  }

  const fetchClientById = async (clientId) => {
    try {
      const response = await fetch(`/api/clients/${clientId}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.client) {
          setSelectedClient(data.client)
          return
        }
      }
      setSelectedClient(null)
    } catch (error) {
      console.error('Error fetching client:', error)
      setSelectedClient(null)
    }
  }

  const handleClientSelect = (client) => {
    setSelectedClient(client)
    setIsOpen(false)
    setSearchTerm('')
    
    // Call parent callback if provided
    if (onClientSelect) {
      onClientSelect(client)
    }
    
    // Update URL params
    const currentUrl = new URL(window.location)
    currentUrl.searchParams.set('client', client.client_id)
    window.history.replaceState({}, '', currentUrl)
  }

  const handleCreateNew = () => {
    navigate('/case-management')
    setIsOpen(false)
  }

  const handleViewDashboard = () => {
    if (selectedClient) {
      navigate(`/client/${selectedClient.client_id}`)
    }
  }

  const filteredClients = clients.filter(client => {
    const searchLower = searchTerm.toLowerCase()
    return (
      client.first_name?.toLowerCase().includes(searchLower) ||
      client.last_name?.toLowerCase().includes(searchLower) ||
      client.email?.toLowerCase().includes(searchLower) ||
      client.phone?.includes(searchTerm)
    )
  })

  const getRiskLevelColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className={`relative ${className}`}>
      {/* Selected Client Display / Dropdown Trigger */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between p-3 bg-white border border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <User className="h-5 w-5 text-gray-400" />
          {selectedClient ? (
            <div>
              <p className="font-medium text-gray-900">
                {selectedClient.first_name} {selectedClient.last_name}
              </p>
              <p className="text-sm text-gray-500">{selectedClient.email || selectedClient.phone}</p>
            </div>
          ) : (
            <span className="text-gray-500">{placeholder}</span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {selectedClient && showViewDashboard && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleViewDashboard()
              }}
              className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="View Client Dashboard"
            >
              <ExternalLink className="h-4 w-4" />
            </button>
          )}
          <ChevronDown className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-50 max-h-96 overflow-hidden">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search clients..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>
          </div>

          {/* Create New Client Option */}
          {showCreateNew && (
            <div className="border-b border-gray-200">
              <button
                onClick={handleCreateNew}
                className="w-full flex items-center space-x-3 p-3 text-left hover:bg-gray-50 transition-colors"
              >
                <Plus className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-blue-600">Create New Client</span>
              </button>
            </div>
          )}

          {/* Client List */}
          <div className="max-h-64 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                Loading clients...
              </div>
            ) : filteredClients.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                {searchTerm ? 'No clients found matching your search' : 'No clients available'}
              </div>
            ) : (
              filteredClients.map((client) => (
                <button
                  key={client.client_id}
                  onClick={() => handleClientSelect(client)}
                  className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <User className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">
                        {client.first_name} {client.last_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {client.email || client.phone || 'No contact info'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskLevelColor(client.risk_level)}`}>
                      {client.risk_level}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Overlay to close dropdown */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}

export default ClientSelector
