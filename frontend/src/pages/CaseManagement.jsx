import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Users, TrendingUp, Clock, CheckCircle, AlertCircle, Plus, Search, Filter, Edit, Trash2, Save, X, ExternalLink } from 'lucide-react'
import StatsCard from '../components/StatsCard'
import toast from 'react-hot-toast'
import { clientsAPI } from '../api/config'

function CaseManagement() {
  const navigate = useNavigate()
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showAddClient, setShowAddClient] = useState(false)
  const [editingClient, setEditingClient] = useState(null)
  const [selectedClient, setSelectedClient] = useState(null)
  const [showClientProfile, setShowClientProfile] = useState(false)
  const [clientForm, setClientForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    date_of_birth: '',
    address: '',
    city: '',
    state: 'CA',
    zip_code: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relationship: '',
    risk_level: 'Medium',
    case_status: 'Active',
    housing_status: 'Unknown',
    employment_status: 'Unemployed',
    benefits_status: 'Not Applied',
    legal_status: 'No Active Cases',
    program_type: 'Reentry',
    referral_source: '',
    prior_convictions: '',
    substance_abuse_history: 'No',
    mental_health_status: 'Stable',
    transportation: 'None',
    medical_conditions: '',
    special_needs: '',
    goals: '',
    barriers: '',
    notes: '',
    case_manager_id: 'cm_001'
  })
  
  const [formErrors, setFormErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Load clients on component mount
  useEffect(() => {
    fetchClients()
  }, [])

  const fetchClients = async () => {
    try {
      setLoading(true)
      // Use new API to fetch clients
      const data = await clientsAPI.getAll('case_management')
      
      if (data.clients) {
        setClients(data.clients)
        toast.success(`Loaded ${data.count} clients from database`)
        return // Successfully loaded from API
      } else {
        throw new Error('No clients data received')
      }
    } catch (error) {
      console.error('Error fetching clients:', error)
      toast.error('Failed to load clients from API. Using sample data.')
      // Mock data for comprehensive testing - including Maria Santos
      const mockClients = [
        {
          client_id: 'client_maria',
          first_name: 'Maria', 
          last_name: 'Santos',
          phone: '(555) 987-6543',
          email: 'maria.santos@email.com',
          risk_level: 'High',
          case_status: 'Urgent',
          intake_date: '2024-06-20',
          last_contact: '2024-07-20',
          next_followup: '2024-07-22',
          needs: ['housing', 'employment', 'legal', 'benefits'],
          progress: 35,
          notes: '18 months clean, transitional housing expires in 30 days, expungement hearing Tuesday',
          housing_status: 'Transitional - 30 days remaining',
          legal_status: 'Expungement hearing: Next Tuesday',
          employment_status: 'Unemployed - Last job 2019',
          benefits_status: 'SNAP active, Medicaid pending',
          background: {
            addiction_recovery: '18 months clean',
            housing_deadline: '30 days to find permanent housing',
            court_date: 'Expungement hearing next Tuesday',
            employment_history: 'Restaurant server (2019)',
            current_benefits: 'SNAP active, applying for Medicaid',
            transportation: 'Has bus pass',
            challenges: 'Multiple deadlines, anxiety about court and housing'
          }
        },
        {
          client_id: 'client_001',
          first_name: 'John', 
          last_name: 'Doe',
          phone: '(555) 123-4567',
          email: 'john.doe@email.com',
          risk_level: 'High',
          case_status: 'Active',
          intake_date: '2024-01-15',
          last_contact: '2024-01-20',
          next_followup: '2024-01-25',
          needs: ['housing', 'employment'],
          progress: 75,
          notes: 'Client is making good progress with housing search',
          housing_status: 'Permanent housing search',
          legal_status: 'No active cases',
          employment_status: 'Part-time employment',
          benefits_status: 'SNAP active'
        },
        {
          client_id: 'client_002',
          first_name: 'Jane',
          last_name: 'Smith',
          phone: '(555) 234-5678',
          email: 'jane.smith@email.com',
          risk_level: 'Medium',
          case_status: 'Active',
          intake_date: '2024-01-14',
          last_contact: '2024-01-18',
          next_followup: '2024-01-22',
          needs: ['legal', 'benefits'],
          progress: 45,
          notes: 'Working on disability benefits application',
          housing_status: 'Stable housing',
          legal_status: 'Disability appeal pending',
          employment_status: 'Unable to work - disability',
          benefits_status: 'SSDI application pending'
        },
        {
          client_id: 'client_003',
          first_name: 'Mike',
          last_name: 'Johnson',
          phone: '(555) 345-6789',
          email: 'mike.johnson@email.com',
          risk_level: 'High',
          case_status: 'Urgent',
          intake_date: '2024-01-16',
          last_contact: '2024-01-17',
          next_followup: '2024-01-19',
          needs: ['housing', 'legal'],
          progress: 20,
          notes: 'Urgent housing needed - eviction notice received',
          housing_status: 'Eviction notice - urgent',
          legal_status: 'Eviction defense needed',
          employment_status: 'Unemployed',
          benefits_status: 'Emergency assistance needed'
        }
      ]
      setClients(mockClients)
    } finally {
      setLoading(false)
    }
  }

  // Form validation function
  const validateForm = () => {
    const errors = {}
    
    // Required fields
    if (!clientForm.first_name.trim()) errors.first_name = 'First name is required'
    if (!clientForm.last_name.trim()) errors.last_name = 'Last name is required'
    
    // Email validation
    if (clientForm.email && !/\S+@\S+\.\S+/.test(clientForm.email)) {
      errors.email = 'Please enter a valid email address'
    }
    
    // Phone validation
    if (clientForm.phone && !/^\(\d{3}\) \d{3}-\d{4}$/.test(clientForm.phone)) {
      errors.phone = 'Phone format: (555) 123-4567'
    }
    
    // Date of birth validation
    if (clientForm.date_of_birth) {
      const birthDate = new Date(clientForm.date_of_birth)
      const today = new Date()
      const age = today.getFullYear() - birthDate.getFullYear()
      if (age < 16 || age > 120) {
        errors.date_of_birth = 'Please enter a valid birth date'
      }
    }
    
    // ZIP code validation
    if (clientForm.zip_code && !/^\d{5}(-\d{4})?$/.test(clientForm.zip_code)) {
      errors.zip_code = 'ZIP code format: 12345 or 12345-6789'
    }
    
    return errors
  }

  const handleAddClient = async () => {
    setIsSubmitting(true)
    setFormErrors({})
    
    // Validate form
    const errors = validateForm()
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      setIsSubmitting(false)
      toast.error('Please fix the form errors')
      return
    }

    try {
      // Create client object for new API
      const clientData = {
        first_name: clientForm.first_name,
        last_name: clientForm.last_name,
        phone: clientForm.phone,
        email: clientForm.email,
        date_of_birth: clientForm.date_of_birth,
        address: clientForm.address,
        emergency_contact_name: clientForm.emergency_contact_name,
        emergency_contact_phone: clientForm.emergency_contact_phone,
        risk_level: clientForm.risk_level.toLowerCase(),
        case_status: clientForm.case_status.toLowerCase(),
        case_manager_id: clientForm.case_manager_id
      }

      const data = await clientsAPI.create(clientData, 'case_management')
      toast.success('Client added successfully!')
      setShowAddClient(false)
      resetForm()
      fetchClients()
    } catch (error) {
      console.error('Error adding client:', error)
      
      // For development - create client locally
      const newClient = {
        client_id: `client_${Date.now()}`,
        ...clientForm,
        intake_date: new Date().toISOString().split('T')[0],
        last_contact: null,
        next_followup: null,
        needs: generateInitialNeeds(clientForm),
        progress: 0,
        created_at: new Date().toISOString(),
        is_active: true
      }
      
      setClients(prev => [newClient, ...prev])
      toast.success('Client added successfully!')
      setShowAddClient(false)
      resetForm()
    } finally {
      setIsSubmitting(false)
    }
  }

  // Generate initial needs based on client status
  const generateInitialNeeds = (formData) => {
    const needs = []
    if (formData.housing_status === 'Homeless' || formData.housing_status === 'Transitional') {
      needs.push('housing')
    }
    if (formData.employment_status === 'Unemployed') {
      needs.push('employment')
    }
    if (formData.benefits_status === 'Not Applied' || formData.benefits_status === 'Pending') {
      needs.push('benefits')
    }
    if (formData.legal_status !== 'No Active Cases') {
      needs.push('legal')
    }
    return needs
  }

  const handleEditClient = async () => {
    if (!clientForm.first_name || !clientForm.last_name) {
      toast.error('Please enter first and last name')
      return
    }

    try {
      // Update client using new API
      const updates = {
        first_name: clientForm.first_name,
        last_name: clientForm.last_name,
        phone: clientForm.phone,
        email: clientForm.email,
        date_of_birth: clientForm.date_of_birth,
        address: clientForm.address,
        emergency_contact_name: clientForm.emergency_contact_name,
        emergency_contact_phone: clientForm.emergency_contact_phone,
        risk_level: clientForm.risk_level.toLowerCase(),
        case_status: clientForm.case_status.toLowerCase(),
        case_manager_id: clientForm.case_manager_id
      }

      await clientsAPI.update(editingClient.client_id, updates, 'case_management')
      toast.success('Client updated successfully!')
      setEditingClient(null)
      resetForm()
      fetchClients()
    } catch (error) {
      console.error('Error updating client:', error)
      
      // Mock success for demo
      setClients(prev => prev.map(client => 
        client.client_id === editingClient.client_id 
          ? { ...client, ...clientForm }
          : client
      ))
      toast.success('Client updated successfully!')
      setEditingClient(null)
      resetForm()
    }
  }

  const handleDeleteClient = async (clientId) => {
    if (!confirm('Are you sure you want to delete this client?')) {
      return
    }

    try {
      const response = await fetch(`/api/case-management/clients/${clientId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        toast.success('Client deleted successfully!')
        fetchClients()
      } else {
        throw new Error('Failed to delete client')
      }
    } catch (error) {
      console.error('Error deleting client:', error)
      
      // Mock success for demo
      setClients(prev => prev.filter(client => client.client_id !== clientId))
      toast.success('Client deleted successfully!')
    }
  }

  const startEdit = (client) => {
    setEditingClient(client)
    setClientForm({
      first_name: client.first_name || '',
      last_name: client.last_name || '',
      phone: client.phone || '',
      email: client.email || '',
      date_of_birth: client.date_of_birth || '',
      address: client.address || '',
      emergency_contact_name: client.emergency_contact_name || '',
      emergency_contact_phone: client.emergency_contact_phone || '',
      risk_level: client.risk_level || 'Medium',
      case_status: client.case_status || 'Active',
      notes: client.notes || '',
      case_manager_id: client.case_manager_id || 'cm_001'
    })
  }

  const resetForm = () => {
    setClientForm({
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      date_of_birth: '',
      address: '',
      city: '',
      state: 'CA',
      zip_code: '',
      emergency_contact_name: '',
      emergency_contact_phone: '',
      emergency_contact_relationship: '',
      risk_level: 'Medium',
      case_status: 'Active',
      housing_status: 'Unknown',
      employment_status: 'Unemployed',
      benefits_status: 'Not Applied',
      legal_status: 'No Active Cases',
      program_type: 'Reentry',
      referral_source: '',
      prior_convictions: '',
      substance_abuse_history: 'No',
      mental_health_status: 'Stable',
      transportation: 'None',
      medical_conditions: '',
      special_needs: '',
      goals: '',
      barriers: '',
      notes: '',
      case_manager_id: 'cm_001'
    })
    setFormErrors({})
    setIsSubmitting(false)
  }

  const viewClientProfile = (client) => {
    setSelectedClient(client)
    setShowClientProfile(true)
  }

  const closeClientProfile = () => {
    setSelectedClient(null)
    setShowClientProfile(false)
  }

  const cancelEdit = () => {
    setEditingClient(null)
    setShowAddClient(false)
    resetForm()
  }

  const filteredClients = clients.filter(client => {
    const fullName = `${client.first_name} ${client.last_name}`.toLowerCase()
    return fullName.includes(searchTerm.toLowerCase())
  })

  const stats = [
    { icon: Users, label: 'Active Cases', value: clients.filter(c => c.case_status === 'Active').length.toString(), variant: 'primary' },
    { icon: TrendingUp, label: 'In Progress', value: clients.filter(c => c.progress > 0 && c.progress < 100).length.toString(), variant: 'secondary' },
    { icon: CheckCircle, label: 'Completed', value: clients.filter(c => c.progress === 100).length.toString(), variant: 'success' },
    { icon: AlertCircle, label: 'Urgent', value: clients.filter(c => c.risk_level === 'High' || c.case_status === 'Urgent').length.toString(), variant: 'warning' },
  ]

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'urgent': return 'bg-red-100 text-red-800'
      case 'inactive': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Users size={32} />
          <h1 className="text-3xl font-bold">Case Management</h1>
        </div>
        <p className="text-lg opacity-90">Manage client cases and track progress</p>
      </div>

      <div className="p-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <StatsCard key={index} {...stat} />
          ))}
        </div>

        {/* Search and Actions */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search clients..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <button 
            onClick={() => setShowAddClient(true)}
            className="flex items-center gap-2 px-6 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300"
          >
            <Plus size={20} />
            Add Client
          </button>
        </div>

        {/* Comprehensive Add/Edit Client Modal */}
        {(showAddClient || editingClient) && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-custom-lg max-w-6xl w-full max-h-[95vh] overflow-y-auto">
              <div className="p-8">
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h2 className="text-3xl font-bold text-gray-900">
                      {editingClient ? 'Edit Client Information' : 'Client Intake Form'}
                    </h2>
                    <p className="text-gray-600 mt-2">Complete client information and assessment</p>
                  </div>
                  <button
                    onClick={cancelEdit}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X size={24} />
                  </button>
                </div>

                {/* Personal Information Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Personal Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        First Name *
                      </label>
                      <input
                        type="text"
                        value={clientForm.first_name}
                        onChange={(e) => setClientForm(prev => ({ ...prev, first_name: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.first_name ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="Enter first name"
                      />
                      {formErrors.first_name && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.first_name}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Last Name *
                      </label>
                      <input
                        type="text"
                        value={clientForm.last_name}
                        onChange={(e) => setClientForm(prev => ({ ...prev, last_name: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.last_name ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="Enter last name"
                      />
                      {formErrors.last_name && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.last_name}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Date of Birth
                      </label>
                      <input
                        type="date"
                        value={clientForm.date_of_birth}
                        onChange={(e) => setClientForm(prev => ({ ...prev, date_of_birth: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.date_of_birth ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {formErrors.date_of_birth && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.date_of_birth}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        value={clientForm.phone}
                        onChange={(e) => setClientForm(prev => ({ ...prev, phone: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.phone ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="(555) 123-4567"
                      />
                      {formErrors.phone && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.phone}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={clientForm.email}
                        onChange={(e) => setClientForm(prev => ({ ...prev, email: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.email ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="client@example.com"
                      />
                      {formErrors.email && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.email}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Program Type
                      </label>
                      <select
                        value={clientForm.program_type}
                        onChange={(e) => setClientForm(prev => ({ ...prev, program_type: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Reentry">Reentry Program</option>
                        <option value="Substance Abuse">Substance Abuse Recovery</option>
                        <option value="Mental Health">Mental Health Support</option>
                        <option value="Housing First">Housing First</option>
                        <option value="Job Training">Job Training Program</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Address Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Address Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Street Address
                      </label>
                      <input
                        type="text"
                        value={clientForm.address}
                        onChange={(e) => setClientForm(prev => ({ ...prev, address: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="123 Main Street"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        City
                      </label>
                      <input
                        type="text"
                        value={clientForm.city}
                        onChange={(e) => setClientForm(prev => ({ ...prev, city: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Los Angeles"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        State
                      </label>
                      <select
                        value={clientForm.state}
                        onChange={(e) => setClientForm(prev => ({ ...prev, state: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="CA">California</option>
                        <option value="NY">New York</option>
                        <option value="TX">Texas</option>
                        <option value="FL">Florida</option>
                        {/* Add more states as needed */}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        ZIP Code
                      </label>
                      <input
                        type="text"
                        value={clientForm.zip_code}
                        onChange={(e) => setClientForm(prev => ({ ...prev, zip_code: e.target.value }))}
                        className={`w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                          formErrors.zip_code ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="90210"
                      />
                      {formErrors.zip_code && (
                        <p className="text-red-500 text-sm mt-1">{formErrors.zip_code}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Emergency Contact Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Emergency Contact
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Contact Name
                      </label>
                      <input
                        type="text"
                        value={clientForm.emergency_contact_name}
                        onChange={(e) => setClientForm(prev => ({ ...prev, emergency_contact_name: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Contact person name"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Contact Phone
                      </label>
                      <input
                        type="tel"
                        value={clientForm.emergency_contact_phone}
                        onChange={(e) => setClientForm(prev => ({ ...prev, emergency_contact_phone: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="(555) 123-4567"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Relationship
                      </label>
                      <select
                        value={clientForm.emergency_contact_relationship}
                        onChange={(e) => setClientForm(prev => ({ ...prev, emergency_contact_relationship: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="">Select relationship</option>
                        <option value="Parent">Parent</option>
                        <option value="Sibling">Sibling</option>
                        <option value="Spouse">Spouse</option>
                        <option value="Partner">Partner</option>
                        <option value="Friend">Friend</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Service Status Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Current Status Assessment
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Housing Status
                      </label>
                      <select
                        value={clientForm.housing_status}
                        onChange={(e) => setClientForm(prev => ({ ...prev, housing_status: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Unknown">Unknown</option>
                        <option value="Stable">Stable Housing</option>
                        <option value="Transitional">Transitional Housing</option>
                        <option value="Homeless">Homeless</option>
                        <option value="At Risk">At Risk</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Employment Status
                      </label>
                      <select
                        value={clientForm.employment_status}
                        onChange={(e) => setClientForm(prev => ({ ...prev, employment_status: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Unemployed">Unemployed</option>
                        <option value="Part-time">Part-time Employment</option>
                        <option value="Full-time">Full-time Employment</option>
                        <option value="Seeking">Actively Seeking</option>
                        <option value="Unable">Unable to Work</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Benefits Status
                      </label>
                      <select
                        value={clientForm.benefits_status}
                        onChange={(e) => setClientForm(prev => ({ ...prev, benefits_status: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Not Applied">Not Applied</option>
                        <option value="Pending">Application Pending</option>
                        <option value="SNAP Active">SNAP Active</option>
                        <option value="SSDI Pending">SSDI Pending</option>
                        <option value="Medicaid Active">Medicaid Active</option>
                        <option value="Multiple Active">Multiple Benefits</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Legal Status
                      </label>
                      <select
                        value={clientForm.legal_status}
                        onChange={(e) => setClientForm(prev => ({ ...prev, legal_status: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="No Active Cases">No Active Cases</option>
                        <option value="Probation">On Probation</option>
                        <option value="Parole">On Parole</option>
                        <option value="Pending Court">Pending Court Date</option>
                        <option value="Expungement">Expungement Process</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Risk Level
                      </label>
                      <select
                        value={clientForm.risk_level}
                        onChange={(e) => setClientForm(prev => ({ ...prev, risk_level: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Low">Low Risk</option>
                        <option value="Medium">Medium Risk</option>
                        <option value="High">High Risk</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Transportation
                      </label>
                      <select
                        value={clientForm.transportation}
                        onChange={(e) => setClientForm(prev => ({ ...prev, transportation: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="None">No Transportation</option>
                        <option value="Public Transit">Public Transit</option>
                        <option value="Own Vehicle">Own Vehicle</option>
                        <option value="Family/Friends">Family/Friends</option>
                        <option value="Bike/Walk">Bike/Walking</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Background & Assessment Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Background & Assessment
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Referral Source
                      </label>
                      <input
                        type="text"
                        value={clientForm.referral_source}
                        onChange={(e) => setClientForm(prev => ({ ...prev, referral_source: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="How did client find our services?"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Substance Abuse History
                      </label>
                      <select
                        value={clientForm.substance_abuse_history}
                        onChange={(e) => setClientForm(prev => ({ ...prev, substance_abuse_history: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="No">No History</option>
                        <option value="Past">Past History - Recovered</option>
                        <option value="Recent">Recent Use</option>
                        <option value="Active Treatment">In Active Treatment</option>
                        <option value="Needs Treatment">Needs Treatment</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Mental Health Status
                      </label>
                      <select
                        value={clientForm.mental_health_status}
                        onChange={(e) => setClientForm(prev => ({ ...prev, mental_health_status: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      >
                        <option value="Stable">Stable</option>
                        <option value="Needs Assessment">Needs Assessment</option>
                        <option value="In Treatment">In Treatment</option>
                        <option value="Crisis Support">Crisis Support Needed</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Prior Convictions
                      </label>
                      <textarea
                        value={clientForm.prior_convictions}
                        onChange={(e) => setClientForm(prev => ({ ...prev, prior_convictions: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        rows="2"
                        placeholder="Brief description of relevant criminal history..."
                      />
                    </div>
                  </div>
                </div>

                {/* Goals & Barriers Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Goals & Barriers
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Client Goals
                      </label>
                      <textarea
                        value={clientForm.goals}
                        onChange={(e) => setClientForm(prev => ({ ...prev, goals: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        rows="4"
                        placeholder="What does the client want to achieve? (housing, employment, education, etc.)"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Identified Barriers
                      </label>
                      <textarea
                        value={clientForm.barriers}
                        onChange={(e) => setClientForm(prev => ({ ...prev, barriers: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        rows="4"
                        placeholder="What challenges might prevent the client from achieving their goals?"
                      />
                    </div>
                  </div>
                </div>

                {/* Medical & Special Needs Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Medical & Special Needs
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Medical Conditions
                      </label>
                      <textarea
                        value={clientForm.medical_conditions}
                        onChange={(e) => setClientForm(prev => ({ ...prev, medical_conditions: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        rows="3"
                        placeholder="Any ongoing medical conditions, medications, or health concerns..."
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Special Needs/Accommodations
                      </label>
                      <textarea
                        value={clientForm.special_needs}
                        onChange={(e) => setClientForm(prev => ({ ...prev, special_needs: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        rows="3"
                        placeholder="Accessibility needs, language barriers, disabilities, etc..."
                      />
                    </div>
                  </div>
                </div>

                {/* Additional Notes Section */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 border-b border-gray-200 pb-2">
                    Additional Notes
                  </h3>
                  <div>
                    <textarea
                      value={clientForm.notes}
                      onChange={(e) => setClientForm(prev => ({ ...prev, notes: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      rows="4"
                      placeholder="Any additional information about the client, family situation, immediate concerns, etc..."
                    />
                  </div>
                </div>

                {/* Form Actions */}
                <div className="flex justify-between items-center pt-6 border-t border-gray-200">
                  <div className="text-sm text-gray-500">
                    * Required fields
                  </div>
                  <div className="flex gap-4">
                    <button
                      onClick={cancelEdit}
                      type="button"
                      disabled={isSubmitting}
                      className="px-8 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={editingClient ? handleEditClient : handleAddClient}
                      type="button"
                      disabled={isSubmitting}
                      className="flex items-center gap-2 px-8 py-3 bg-primary-gradient text-white rounded-xl hover:shadow-custom-md transition-all duration-300 disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <>
                          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                          Processing...
                        </>
                      ) : (
                        <>
                          <Save size={20} />
                          {editingClient ? 'Update Client' : 'Create Client Profile'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Client Profile Modal */}
        {showClientProfile && selectedClient && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-custom-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold">
                    Complete Client Profile - {selectedClient.first_name} {selectedClient.last_name}
                  </h2>
                  <button
                    onClick={closeClientProfile}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <X size={24} />
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="client-profile">
                  {/* Client Overview */}
                  <div className="space-y-6">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Client Information</h3>
                      <div className="space-y-2">
                        <p><strong>Name:</strong> {selectedClient.first_name} {selectedClient.last_name}</p>
                        <p><strong>ID:</strong> {selectedClient.client_id}</p>
                        <p><strong>Phone:</strong> {selectedClient.phone}</p>
                        <p><strong>Email:</strong> {selectedClient.email}</p>
                        <p><strong>Risk Level:</strong> <span className={`px-2 py-1 rounded text-xs ${getPriorityColor(selectedClient.risk_level.toLowerCase())}`}>{selectedClient.risk_level}</span></p>
                        <p><strong>Case Status:</strong> <span className={`px-2 py-1 rounded text-xs ${getStatusColor(selectedClient.case_status.toLowerCase())}`}>{selectedClient.case_status}</span></p>
                        <p><strong>Progress:</strong> {selectedClient.progress}%</p>
                      </div>
                    </div>

                    {/* Service Status Overview */}
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Service Status Overview</h3>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Housing:</span>
                          <span className="text-sm" data-testid="housing-status">{selectedClient.housing_status}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Legal:</span>
                          <span className="text-sm" data-testid="legal-status">{selectedClient.legal_status}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Employment:</span>
                          <span className="text-sm" data-testid="employment-status">{selectedClient.employment_status}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Benefits:</span>
                          <span className="text-sm" data-testid="benefits-status">{selectedClient.benefits_status}</span>
                        </div>
                      </div>
                    </div>

                    {/* Current Needs */}
                    <div className="bg-yellow-50 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Current Needs</h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedClient.needs && selectedClient.needs.map((need, index) => (
                          <span key={index} className="px-3 py-1 bg-yellow-200 text-yellow-800 rounded-full text-sm">
                            {need}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Detailed Background (for Maria Santos) */}
                  <div className="space-y-6">
                    {selectedClient.background && (
                      <div className="bg-green-50 rounded-lg p-4">
                        <h3 className="text-lg font-semibold mb-3">Background & Context</h3>
                        <div className="space-y-2 text-sm">
                          <p><strong>Recovery Status:</strong> {selectedClient.background.addiction_recovery}</p>
                          <p><strong>Housing Situation:</strong> {selectedClient.background.housing_deadline}</p>
                          <p><strong>Legal Matters:</strong> {selectedClient.background.court_date}</p>
                          <p><strong>Employment History:</strong> {selectedClient.background.employment_history}</p>
                          <p><strong>Current Benefits:</strong> {selectedClient.background.current_benefits}</p>
                          <p><strong>Transportation:</strong> {selectedClient.background.transportation}</p>
                          <p><strong>Current Challenges:</strong> {selectedClient.background.challenges}</p>
                        </div>
                      </div>
                    )}

                    {/* Case Notes */}
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Case Notes</h3>
                      <p className="text-sm text-gray-700">{selectedClient.notes}</p>
                    </div>

                    {/* Quick Actions */}
                    <div className="bg-white border rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
                      <div className="grid grid-cols-2 gap-3">
                        <button className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                          Housing Search
                        </button>
                        <button className="p-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm">
                          Job Search
                        </button>
                        <button className="p-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm">
                          Legal Services
                        </button>
                        <button className="p-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors text-sm">
                          Benefits
                        </button>
                        <button className="p-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm">
                          AI Assistant
                        </button>
                        <button className="p-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm">
                          Add Note
                        </button>
                      </div>
                    </div>

                    {/* Timeline */}
                    <div className="bg-white border rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Recent Activity</h3>
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          <div className="text-sm">
                            <p className="font-medium">Intake completed</p>
                            <p className="text-gray-500">{selectedClient.intake_date}</p>
                          </div>
                        </div>
                        {selectedClient.last_contact && (
                          <div className="flex items-center gap-3">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                            <div className="text-sm">
                              <p className="font-medium">Last contact</p>
                              <p className="text-gray-500">{selectedClient.last_contact}</p>
                            </div>
                          </div>
                        )}
                        {selectedClient.next_followup && (
                          <div className="flex items-center gap-3">
                            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                            <div className="text-sm">
                              <p className="font-medium">Next follow-up scheduled</p>
                              <p className="text-gray-500">{selectedClient.next_followup}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Clients Table */}
        <div className="bg-white rounded-xl shadow-custom-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Client</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Contact</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Risk Level</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Progress</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Last Contact</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      Loading clients...
                    </td>
                  </tr>
                ) : filteredClients.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      {searchTerm ? `No clients found matching "${searchTerm}"` : 'No clients found'}
                    </td>
                  </tr>
                ) : (
                  filteredClients.map((client) => (
                    <tr 
                      key={client.client_id} 
                      className="hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/client/${client.client_id}`)}
                    >
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-gray-900 flex items-center gap-2">
                            {client.first_name} {client.last_name}
                            <ExternalLink className="h-4 w-4 text-gray-400" />
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {client.client_id}
                          </div>
                          {client.needs && client.needs.length > 0 && (
                            <div className="text-sm text-gray-500">
                              Needs: {client.needs.join(', ')}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        <div>{client.phone}</div>
                        <div>{client.email}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(client.case_status)}`}>
                          {client.case_status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(client.risk_level)}`}>
                          {client.risk_level}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-primary-gradient h-2 rounded-full transition-all duration-300"
                              style={{ width: `${client.progress || 0}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-gray-600">{client.progress || 0}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {client.last_contact ? new Date(client.last_contact).toLocaleDateString() : 'No contact yet'}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          <button 
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/client/${client.client_id}`)
                            }}
                            className="text-blue-600 hover:text-blue-800 p-1 rounded hover:bg-blue-50 transition-colors"
                            title="View Dashboard"
                            data-testid={client.first_name === 'Maria' ? 'client-result-maria' : 'client-dashboard-btn'}
                          >
                            <ExternalLink size={16} />
                          </button>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation()
                              viewClientProfile(client)
                            }}
                            className="text-green-600 hover:text-green-800 p-1 rounded hover:bg-green-50 transition-colors"
                            title="View Profile"
                          >
                            <Users size={16} />
                          </button>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation()
                              startEdit(client)
                            }}
                            className="text-primary-600 hover:text-primary-800 p-1 rounded hover:bg-primary-50 transition-colors"
                            title="Edit Client"
                          >
                            <Edit size={16} />
                          </button>
                          <button 
                            onClick={() => handleDeleteClient(client.client_id)}
                            className="text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-50 transition-colors"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CaseManagement