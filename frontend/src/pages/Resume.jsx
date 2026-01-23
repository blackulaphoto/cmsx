// ================================================================
// @generated
// @preserve
// @readonly
// DO NOT MODIFY THIS FILE
// Purpose: This module/component/route is production-approved.
// Any changes must be approved by the lead developer.
//
// WARNING: Modifying this file may break the application.
// ================================================================

import { useState, useEffect } from 'react'
import { FileText, Download, Edit, Eye, User, Briefcase, MapPin, Phone, Mail, Star, Plus, Trash2, Save, Target, Search, Zap, Users, Building, Sparkles, Palette } from 'lucide-react'
import toast from 'react-hot-toast'
import PDFService from '../services/pdfService'

// Import new enhanced components
import SearchableDropdown from '../components/SearchableDropdown'
import WorkExperienceForm from '../components/WorkExperienceForm'
import LivePreview from '../components/LivePreview'
import TemplateSelector from '../components/TemplateSelector'
import ResumeModal from '../components/ResumeModal'
import DebugPanel from '../components/DebugPanel'

// Import CSS for layout fixes
import '../styles/ResumeBuilder.css'

function Resume() {
  // Define templates array first, before using it in state initialization
  const templates = [
    {
      id: 'classic',
      name: 'Classic Professional',
      description: 'Traditional corporate layout - ATS friendly',
      preview: '📄',
      gradient: 'from-blue-500 via-blue-600 to-purple-600',
      suitableFor: ['Corporate', 'Finance', 'Legal', 'Traditional Industries'],
      background_friendly: true
    },
    {
      id: 'modern',
      name: 'Modern Professional',
      description: 'Contemporary design with clean layout',
      preview: '🎨',
      gradient: 'from-purple-500 via-violet-600 to-indigo-600',
      suitableFor: ['Technology', 'Marketing', 'Design', 'Startups'],
      background_friendly: true
    },
    {
      id: 'warehouse',
      name: 'Warehouse & Logistics',
      description: 'Optimized for warehouse and manual labor positions',
      preview: '📦',
      gradient: 'from-orange-500 via-amber-600 to-yellow-600',
      suitableFor: ['Warehouse', 'Manufacturing', 'Logistics', 'Manual Labor'],
      background_friendly: true
    },
    {
      id: 'construction',
      name: 'Construction & Trades',
      description: 'Industry-specific template for construction jobs',
      preview: '🔨',
      gradient: 'from-red-500 via-orange-600 to-amber-600',
      suitableFor: ['Construction', 'Trades', 'Engineering', 'Architecture'],
      background_friendly: true
    },
    {
      id: 'food_service',
      name: 'Food Service',
      description: 'Restaurant and hospitality industry focused',
      preview: '🍽️',
      gradient: 'from-emerald-500 via-green-600 to-teal-600',
      suitableFor: ['Restaurants', 'Hospitality', 'Catering', 'Food Service'],
      background_friendly: true
    },
    {
      id: 'medical_social',
      name: 'Medical/Social Worker',
      description: 'Healthcare and social services template',
      preview: '🏥',
      gradient: 'from-teal-500 via-cyan-600 to-blue-600',
      suitableFor: ['Healthcare', 'Social Work', 'Non-Profit', 'Education'],
      background_friendly: true
    }
  ]

  const [selectedClient, setSelectedClient] = useState(null)
  const [availableClients, setAvailableClients] = useState([])
  const [activeTab, setActiveTab] = useState('builder')
  // Guest mode functionality
  const [guestMode, setGuestMode] = useState(false)
  const [guestData, setGuestData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: ''
  })
  const [selectedTemplate, setSelectedTemplate] = useState(() => {
    // Initialize with default template to prevent preview issues
    return templates.find(t => t.id === 'classic') || templates[0] || null
  })
  const [employmentProfile, setEmploymentProfile] = useState({
    work_history: [],
    education: [],
    skills: [],
    certifications: [],
    career_objective: '',
    preferred_industries: []
  })
  const [savedResumes, setSavedResumes] = useState([])
  const [jobApplications, setJobApplications] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedResume, setSelectedResume] = useState(null)
  const [viewingResume, setViewingResume] = useState(null)
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true)

  useEffect(() => {
    fetchAvailableClients()
    checkPDFServiceHealth() // Add this line
    // Ensure we have a default template selected
    if (!selectedTemplate && templates.length > 0) {
      setSelectedTemplate(templates.find(t => t.id === 'classic') || templates[0])
    }
  }, [])

  // Set default template when templates are available
  useEffect(() => {
    if (!selectedTemplate && templates.length > 0) {
      setSelectedTemplate(templates.find(t => t.id === 'classic') || templates[0])
    }
  }, [templates, selectedTemplate])

  useEffect(() => {
    if (selectedClient) {
      fetchEmploymentProfile()
      fetchClientResumes()
      fetchJobApplications()
    }
  }, [selectedClient])

  // Auto-save functionality
  useEffect(() => {
    const effectiveClient = getEffectiveClient()
    if (autoSaveEnabled && effectiveClient && employmentProfile.career_objective) {
      const timeoutId = setTimeout(() => {
        saveEmploymentProfile(true) // true for silent save
      }, 2000) // Auto-save after 2 seconds of inactivity

      return () => clearTimeout(timeoutId)
    }
  }, [employmentProfile, selectedClient, guestData, guestMode, autoSaveEnabled])

  const fetchAvailableClients = async () => {
    try {
      const response = await fetch('/api/resume/clients')
      if (response.ok) {
        const data = await response.json()
        setAvailableClients(data.clients || [])
      }
    } catch (error) {
      console.error('Error fetching clients:', error)
      toast.error('Failed to load clients')
    }
  }

  const fetchEmploymentProfile = async () => {
    if (!selectedClient) return
    
    try {
      const response = await fetch(`/api/resume/profile/${selectedClient.client_id}`)
      if (response.ok) {
        const data = await response.json()
        if (data.profile) {
          setEmploymentProfile(data.profile)
        }
      }
    } catch (error) {
      console.error('Error fetching employment profile:', error)
    }
  }

  const fetchClientResumes = async () => {
    if (!selectedClient) return
    
    try {
      const response = await fetch(`/api/resume/list/${selectedClient.client_id}`)
      if (response.ok) {
        const data = await response.json()
        setSavedResumes(data.resumes || [])
      }
    } catch (error) {
      console.error('Error fetching resumes:', error)
    }
  }

  const fetchJobApplications = async () => {
    if (!selectedClient) return
    
    try {
      const response = await fetch(`/api/resume/applications/${selectedClient.client_id}`)
      if (response.ok) {
        const data = await response.json()
        setJobApplications(data.applications || [])
      }
    } catch (error) {
      console.error('Error fetching job applications:', error)
    }
  }

  const saveEmploymentProfile = async (silent = false) => {
    const effectiveClient = getEffectiveClient()
    if (!effectiveClient) {
      if (!silent) toast.error(guestMode ? 'Please enter guest information first' : 'Please select a client first')
      return
    }

    if (!silent) setLoading(true)
    try {
      const response = await fetch('/api/resume/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: effectiveClient.client_id,
          ...employmentProfile
        })
      })

      if (response.ok) {
        const data = await response.json()
        if (!silent) {
          toast.success('Employment profile saved successfully!')
          setActiveTab('resumes')
        }
      } else {
        throw new Error('Failed to save profile')
      }
    } catch (error) {
      if (!silent) {
        toast.error('Failed to save employment profile')
        console.error('Profile save error:', error)
      }
    } finally {
      if (!silent) setLoading(false)
    }
  }

  const createResume = async () => {
    const effectiveClient = getEffectiveClient()
    if (!effectiveClient) {
      toast.error(guestMode ? 'Please enter guest information first' : 'Please select a client first')
      return
    }

    if (!selectedTemplate) {
      toast.error('Please select a template first')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/resume/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: effectiveClient.client_id,
          template_type: selectedTemplate.id,
          resume_title: `${selectedTemplate.name} Resume for ${effectiveClient.first_name} ${effectiveClient.last_name}`
        })
      })

      if (response.ok) {
        const data = await response.json()
        toast.success('Resume created successfully!')
        fetchClientResumes()
        setActiveTab('resumes')
      } else {
        throw new Error('Failed to create resume')
      }
    } catch (error) {
      toast.error('Failed to create resume')
      console.error('Resume creation error:', error)
    } finally {
      setLoading(false)
    }
  }

  const generatePDF = async (resumeId) => {
    const effectiveClient = getEffectiveClient()
    if (!effectiveClient) {
      toast.error('Client information is missing')
      return
    }

    setLoading(true)
    try {
      // Use the new PDFService for generation and download
      const clientName = `${effectiveClient.first_name}_${effectiveClient.last_name}`
      await PDFService.generateAndDownload(resumeId, clientName)
      
      // Refresh the resume list to update PDF availability status
      await fetchClientResumes()
      
    } catch (error) {
      const userMessage = PDFService.getErrorMessage(error)
      toast.error(userMessage)
      console.error('PDF generation error:', error)
    } finally {
      setLoading(false)
    }
  }

  const optimizeResume = async (resumeId) => {
    setLoading(true)
    try {
      const response = await fetch('/api/resume/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_id: resumeId,
          optimization_type: 'ats_optimization'
        })
      })

      if (response.ok) {
        const data = await response.json()
        toast.success(`Resume optimized! ATS score improved by ${data.ats_score_improvement} points`)
        
        // Refresh resume list to show updated scores
        await fetchClientResumes()
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Optimization failed' }))
        throw new Error(errorData.detail || 'Failed to optimize resume')
      }
    } catch (error) {
      toast.error(`Optimization failed: ${error.message}`)
      console.error('Resume optimization error:', error)
    } finally {
      setLoading(false)
    }
  }

  // Add this new method for PDF-only download (no generation)
  const downloadExistingPDF = async (resumeId) => {
    const effectiveClient = getEffectiveClient()
    if (!effectiveClient) {
      toast.error('Client information is missing')
      return
    }

    setLoading(true)
    try {
      const filename = PDFService.formatFilename(
        effectiveClient.first_name, 
        effectiveClient.last_name, 
        resumeId
      )
      
      await PDFService.downloadPDF(resumeId, filename)
      toast.success('Download completed!')
      
    } catch (error) {
      const userMessage = PDFService.getErrorMessage(error)
      toast.error(userMessage)
      console.error('PDF download error:', error)
    } finally {
      setLoading(false)
    }
  }

  // Enhanced PDF generation for live preview
  const handleGeneratePDFFromPreview = async () => {
    const effectiveClient = getEffectiveClient()
    if (!effectiveClient || !selectedTemplate) {
      toast.error(guestMode ? 'Please enter guest information and select a template first' : 'Please select a client and template first')
      return
    }

    try {
      // First save the profile silently
      await saveEmploymentProfile(true)
      
      // Then create a resume if one doesn't exist
      const resumeTitle = `${selectedTemplate.name} Resume for ${effectiveClient.first_name} ${effectiveClient.last_name}`
      
      const createResponse = await fetch('/api/resume/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: effectiveClient.client_id,
          template_type: selectedTemplate.id,
          resume_title: resumeTitle
        })
      })

      if (createResponse.ok) {
        const createData = await createResponse.json()
        const resumeId = createData.resume_id
        
        // Generate and download PDF
        const clientName = `${effectiveClient.first_name}_${effectiveClient.last_name}`
        await PDFService.generateAndDownload(resumeId, clientName)
        
        // Refresh resume list and switch to resumes tab
        await fetchClientResumes()
        setActiveTab('resumes')
        
        toast.success('Resume created and PDF generated!')
      } else {
        throw new Error('Failed to create resume')
      }
    } catch (error) {
      const userMessage = PDFService.getErrorMessage(error)
      toast.error(userMessage)
      console.error('Error in PDF generation workflow:', error)
    }
  }

  // Add this method to check PDF service health on component mount
  const checkPDFServiceHealth = async () => {
    try {
      const health = await PDFService.healthCheck()
      if (!health.success) {
        console.warn('PDF service health check failed:', health.error)
        // Optionally show a warning to the user
        toast.error('PDF service may be unavailable. Contact support if you experience issues.', {
          duration: 5000
        })
      } else if (!health.details?.weasyprint_available) {
        console.warn('WeasyPrint not available, PDFs will be generated as HTML files')
        toast('PDF generation will create HTML files instead of PDFs', {
          duration: 3000,
          icon: '⚠️'
        })
      }
    } catch (error) {
      console.error('PDF service health check error:', error)
    }
  }

  // Guest mode handlers
  const handleGuestModeToggle = (enabled) => {
    setGuestMode(enabled)
    if (enabled) {
      // Clear selected client when switching to guest mode
      setSelectedClient(null)
    } else {
      // Clear guest data when switching back to client mode
      setGuestData({
        first_name: '',
        last_name: '',
        email: '',
        phone: ''
      })
    }
  }

  const handleGuestDataChange = (field, value) => {
    setGuestData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  // Get effective client (either selected client or guest data)
  const getEffectiveClient = () => {
    if (guestMode) {
      return guestData.first_name && guestData.last_name ? {
        client_id: 'guest',
        first_name: guestData.first_name,
        last_name: guestData.last_name,
        email: guestData.email,
        phone: guestData.phone
      } : null
    }
    return selectedClient
  }

  const addWorkExperience = () => {
    setEmploymentProfile(prev => ({
      ...prev,
      work_history: [...prev.work_history, {
        job_title: '',
        company: '',
        start_date: '',
        end_date: '',
        description: '',
        achievements: []
      }]
    }))
  }

  const updateWorkExperience = (index, field, value) => {
    setEmploymentProfile(prev => ({
      ...prev,
      work_history: prev.work_history.map((exp, i) => 
        i === index ? { ...exp, [field]: value } : exp
      )
    }))
  }

  const removeWorkExperience = (index) => {
    setEmploymentProfile(prev => ({
      ...prev,
      work_history: prev.work_history.filter((_, i) => i !== index)
    }))
  }

  const addSkillCategory = () => {
    setEmploymentProfile(prev => ({
      ...prev,
      skills: [...prev.skills, {
        category: '',
        skill_list: []
      }]
    }))
  }

  const updateSkillCategory = (index, field, value) => {
    setEmploymentProfile(prev => ({
      ...prev,
      skills: prev.skills.map((skill, i) => 
        i === index ? { ...skill, [field]: value } : skill
      )
    }))
  }

  const addSkillToCategory = (categoryIndex, skill) => {
    if (!skill.trim()) return
    
    setEmploymentProfile(prev => ({
      ...prev,
      skills: prev.skills.map((skillCat, i) => 
        i === categoryIndex ? {
          ...skillCat,
          skill_list: [...skillCat.skill_list, skill.trim()]
        } : skillCat
      )
    }))
  }

  const removeSkillFromCategory = (categoryIndex, skillIndex) => {
    setEmploymentProfile(prev => ({
      ...prev,
      skills: prev.skills.map((skillCat, i) => 
        i === categoryIndex ? {
          ...skillCat,
          skill_list: skillCat.skill_list.filter((_, si) => si !== skillIndex)
        } : skillCat
      )
    }))
  }

  // Enhanced client selection handler
  const handleClientSelection = (client) => {
    setSelectedClient(client)
    toast.success(`Selected ${client.first_name} ${client.last_name}`)
  }

  // Enhanced template creation handler
  const handleCreateResume = async (template) => {
    if (!selectedClient) {
      toast.error('Please select a client first')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/resume/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          template_type: template.id,
          resume_title: `${template.name} Resume for ${selectedClient.first_name} ${selectedClient.last_name}`
        })
      })

      if (response.ok) {
        const data = await response.json()
        toast.success('Resume created successfully!')
        fetchClientResumes()
        setActiveTab('resumes')
      } else {
        throw new Error('Failed to create resume')
      }
    } catch (error) {
      toast.error('Failed to create resume')
      console.error('Resume creation error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-1/2 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute -bottom-40 right-1/3 w-80 h-80 bg-pink-500/10 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <div className="bg-black/20 backdrop-blur-xl border-b border-white/10">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center gap-4 mb-2">
              <div className="p-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl shadow-lg">
                <FileText className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent">
                  Resume Builder
                </h1>
                <p className="text-gray-300 text-lg">Create professional resumes with live preview</p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Enhanced Client Selection */}
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 mb-8 p-6 hover:bg-white/10 transition-all duration-300">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg">
                  <User className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-white">
                  {guestMode ? 'Guest Resume' : 'Select Client'}
                </h3>
              </div>
              <div className="flex items-center gap-4">
                {/* Guest Mode Toggle */}
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-medium transition-colors ${!guestMode ? 'text-white' : 'text-gray-400'}`}>
                    Client
                  </span>
                  <button
                    onClick={() => handleGuestModeToggle(!guestMode)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
                      guestMode ? 'bg-purple-600' : 'bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        guestMode ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                  <span className={`text-sm font-medium transition-colors ${guestMode ? 'text-white' : 'text-gray-400'}`}>
                    Guest
                  </span>
                </div>
                {(selectedClient || (guestMode && guestData.first_name && guestData.last_name)) && (
                  <div className="flex items-center gap-2 bg-green-500/20 border border-green-500/30 rounded-full px-4 py-2">
                    <User className="h-4 w-4 text-green-400" />
                    <span className="text-green-400 font-medium">
                      {guestMode 
                        ? `${guestData.first_name} ${guestData.last_name} (Guest)`
                        : `${selectedClient.first_name} ${selectedClient.last_name} selected`
                      }
                    </span>
                  </div>
                )}
              </div>
            </div>
            
            {guestMode ? (
              /* Guest Mode Form */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">First Name *</label>
                  <input
                    type="text"
                    value={guestData.first_name}
                    onChange={(e) => handleGuestDataChange('first_name', e.target.value)}
                    placeholder="Enter first name"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-400/50 text-white placeholder-gray-400 transition-all duration-300 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Last Name *</label>
                  <input
                    type="text"
                    value={guestData.last_name}
                    onChange={(e) => handleGuestDataChange('last_name', e.target.value)}
                    placeholder="Enter last name"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-400/50 text-white placeholder-gray-400 transition-all duration-300 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
                  <input
                    type="email"
                    value={guestData.email}
                    onChange={(e) => handleGuestDataChange('email', e.target.value)}
                    placeholder="Enter email address"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-400/50 text-white placeholder-gray-400 transition-all duration-300 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Phone</label>
                  <input
                    type="tel"
                    value={guestData.phone}
                    onChange={(e) => handleGuestDataChange('phone', e.target.value)}
                    placeholder="Enter phone number"
                    className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500/50 focus:border-purple-400/50 text-white placeholder-gray-400 transition-all duration-300 outline-none"
                  />
                </div>
              </div>
            ) : (
              /* Client Selection Dropdown */
              <SearchableDropdown
                options={availableClients}
                placeholder="Search and select client..."
                onSelect={handleClientSelection}
                displayField={(client) => `${client.first_name} ${client.last_name} - ${client.email}`}
                showThumbnail={true}
                value={selectedClient}
                className="max-w-md"
              />
            )}
          </div>

          {/* Navigation Tabs */}
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 mb-8 overflow-hidden">
            <div className="flex border-b border-white/10 bg-black/20">
              {[
                { id: 'builder', label: 'Resume Builder', icon: Edit, gradient: 'from-blue-500 to-purple-500' },
                { id: 'templates', label: 'Templates', icon: Palette, gradient: 'from-purple-500 to-pink-500' },
                { id: 'resumes', label: 'My Resumes', icon: FileText, gradient: 'from-emerald-500 to-teal-500' },
                { id: 'applications', label: 'Job Applications', icon: Building, gradient: 'from-orange-500 to-red-500' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group flex items-center gap-3 px-8 py-6 font-medium transition-all duration-300 relative overflow-hidden ${
                    activeTab === tab.id
                      ? 'text-white bg-gradient-to-r ' + tab.gradient
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {activeTab === tab.id && (
                    <div className={`absolute inset-0 bg-gradient-to-r ${tab.gradient} opacity-100`}></div>
                  )}
                  <div className="relative z-10 flex items-center gap-3">
                    <tab.icon size={20} />
                    <span className="font-semibold">{tab.label}</span>
                  </div>
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/30"></div>
                  )}
                </button>
              ))}
            </div>

            <div className="p-8">
              {/* Enhanced Resume Builder Tab with Split Screen */}
              {activeTab === 'builder' && (
                <div className="tab-content layout-stable" data-tab="builder">
                  {!getEffectiveClient() ? (
                    <div className="text-center py-20 text-gray-400">
                      <div className="bg-gradient-to-r from-gray-500/10 to-purple-500/10 rounded-2xl p-12 border border-white/10">
                        <User className="h-20 w-20 mx-auto mb-6 opacity-50 text-gray-500" />
                        <h3 className="text-2xl font-medium mb-4 text-white">
                          {guestMode ? 'Enter Guest Information' : 'Select a Client to Begin'}
                        </h3>
                        <p className="text-lg">
                          {guestMode 
                            ? 'Fill in the guest information above to start building a resume'
                            : 'Choose a client from the dropdown above to start building their resume'
                          }
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="split-screen-layout grid grid-cols-1 xl:grid-cols-5 gap-8">
                      {/* Left Panel - Enhanced Form (60% width) */}
                      <div className="xl:col-span-3 space-y-8">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
                              <Briefcase className="h-5 w-5 text-white" />
                            </div>
                            <h3 className="text-2xl font-semibold text-white">
                              Employment Profile for {getEffectiveClient().first_name} {getEffectiveClient().last_name}
                            </h3>
                          </div>
                          <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 text-sm text-gray-300">
                              <input
                                type="checkbox"
                                checked={autoSaveEnabled}
                                onChange={(e) => setAutoSaveEnabled(e.target.checked)}
                                className="rounded bg-white/10 border-white/20 text-purple-500 focus:ring-purple-500"
                              />
                              Auto-save
                            </label>
                            <button
                              onClick={() => saveEmploymentProfile()}
                              disabled={loading}
                              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3 rounded-xl hover:from-green-400 hover:to-emerald-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105 hover:shadow-lg hover:shadow-green-500/25"
                            >
                              <Save className="h-4 w-4" />
                              {loading ? 'Saving...' : 'Save Profile'}
                            </button>
                          </div>
                        </div>

                        {/* Career Objective */}
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6 hover:bg-white/10 transition-all duration-300">
                          <label className="block text-lg font-medium text-white mb-4 flex items-center gap-2">
                            <Target className="h-5 w-5 text-purple-400" />
                            Career Objective
                          </label>
                          <textarea
                            value={employmentProfile.career_objective}
                            onChange={(e) => setEmploymentProfile(prev => ({
                              ...prev,
                              career_objective: e.target.value
                            }))}
                            placeholder="Brief statement about career goals and objectives..."
                            className="w-full p-4 bg-white/5 border border-white/20 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder-gray-400 resize-none"
                            rows={4}
                          />
                        </div>

                        {/* Enhanced Work Experience Form */}
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6 hover:bg-white/10 transition-all duration-300">
                          <WorkExperienceForm
                            workHistory={employmentProfile.work_history}
                            onChange={(workHistory) => setEmploymentProfile(prev => ({
                              ...prev,
                              work_history: workHistory
                            }))}
                          />
                        </div>

                        {/* Enhanced Skills Section */}
                        <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 p-6 hover:bg-white/10 transition-all duration-300">
                          <div className="flex items-center justify-between mb-6">
                            <h4 className="text-xl font-medium flex items-center gap-2 text-white">
                              <Star className="h-5 w-5 text-yellow-400" />
                              Skills
                            </h4>
                            <button
                              onClick={addSkillCategory}
                              className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-2 rounded-xl hover:from-purple-400 hover:to-pink-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105"
                            >
                              <Plus className="h-4 w-4" />
                              Add Category
                            </button>
                          </div>
                          
                          {employmentProfile.skills.map((skillCat, index) => (
                            <div key={index} className="bg-white/5 border border-white/20 rounded-xl p-6 mb-4 hover:bg-white/10 transition-all duration-300">
                              <input
                                type="text"
                                placeholder="Skill Category (e.g., Technical Skills, Soft Skills)"
                                value={skillCat.category}
                                onChange={(e) => updateSkillCategory(index, 'category', e.target.value)}
                                className="w-full p-3 bg-white/5 border border-white/20 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder-gray-400 mb-4"
                              />
                              
                              <div className="flex flex-wrap gap-2 mb-4">
                                {skillCat.skill_list.map((skill, skillIndex) => (
                                  <span
                                    key={skillIndex}
                                    className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-300 px-3 py-2 rounded-full text-sm flex items-center gap-2 border border-blue-500/30 hover:from-blue-500/30 hover:to-purple-500/30 transition-all duration-300"
                                  >
                                    {skill}
                                    <button
                                      onClick={() => removeSkillFromCategory(index, skillIndex)}
                                      className="text-blue-300 hover:text-white transition-colors"
                                    >
                                      ×
                                    </button>
                                  </span>
                                ))}
                              </div>
                              
                              <div className="flex gap-2">
                                <input
                                  type="text"
                                  placeholder="Add a skill..."
                                  className="flex-1 p-3 bg-white/5 border border-white/20 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-white placeholder-gray-400"
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') {
                                      addSkillToCategory(index, e.target.value)
                                      e.target.value = ''
                                    }
                                  }}
                                />
                                <button
                                  onClick={(e) => {
                                    const input = e.target.previousElementSibling
                                    addSkillToCategory(index, input.value)
                                    input.value = ''
                                  }}
                                  className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-lg hover:from-green-400 hover:to-emerald-400 transition-all duration-300 font-medium"
                                >
                                  Add
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Right Panel - Live Preview (40% width) */}
                      <div className="xl:col-span-2">
                        <div className="sticky top-8">
                          <div className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden">
                            <LivePreview
                              employmentProfile={employmentProfile}
                              selectedTemplate={selectedTemplate}
                              selectedClient={getEffectiveClient()}
                              onGeneratePDF={handleGeneratePDFFromPreview}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Enhanced Templates Tab */}
              {activeTab === 'templates' && (
                <div className="tab-content layout-stable" data-tab="templates">
                  <div className="flex items-center gap-3 mb-8">
                    <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg">
                      <Palette className="h-5 w-5 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Choose Resume Template</h2>
                    <div className="px-3 py-1 bg-gradient-to-r from-pink-500 to-purple-500 rounded-full">
                      <span className="text-xs font-medium text-white">6 Professional Templates</span>
                    </div>
                  </div>
                  
                  <TemplateSelector
                    templates={templates}
                    selectedTemplate={selectedTemplate}
                    onTemplateSelect={setSelectedTemplate}
                    onCreateResume={handleCreateResume}
                    selectedClient={getEffectiveClient()}
                    loading={loading}
                  />
                </div>
              )}

              {/* Enhanced Resumes Tab */}
              {activeTab === 'resumes' && (
                <div className="tab-content layout-stable" data-tab="resumes">
                  {!getEffectiveClient() ? (
                    <div className="text-center py-20 text-gray-400">
                      <div className="bg-gradient-to-r from-gray-500/10 to-purple-500/10 rounded-2xl p-12 border border-white/10">
                        <FileText className="h-20 w-20 mx-auto mb-6 opacity-50 text-gray-500" />
                        <h3 className="text-2xl font-medium mb-4 text-white">
                          {guestMode ? 'Enter guest information first' : 'Please select a client first'}
                        </h3>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-lg">
                            <FileText className="h-5 w-5 text-white" />
                          </div>
                          <h3 className="text-2xl font-semibold text-white">
                            Resumes for {getEffectiveClient().first_name} {getEffectiveClient().last_name}
                            {guestMode && <span className="text-purple-400 ml-2">(Guest)</span>}
                          </h3>
                        </div>
                        <button
                          onClick={() => setActiveTab('templates')}
                          className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-3 rounded-xl hover:from-blue-400 hover:to-purple-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105 hover:shadow-lg hover:shadow-blue-500/25"
                        >
                          <Plus className="h-4 w-4" />
                          Create New Resume
                        </button>
                      </div>
                      
                      {savedResumes.length === 0 ? (
                        <div className="text-center py-16 bg-gradient-to-r from-gray-500/10 to-purple-500/10 rounded-2xl border-2 border-dashed border-white/20">
                          <FileText className="h-20 w-20 mx-auto mb-6 opacity-50 text-gray-500" />
                          <h4 className="text-xl font-medium mb-4 text-white">No resumes created yet</h4>
                          <p className="mb-6 text-gray-400">Create your first professional resume</p>
                          <button
                            onClick={() => setActiveTab('templates')}
                            className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-xl hover:from-purple-400 hover:to-pink-400 transition-all duration-300 font-medium hover:scale-105"
                          >
                            Create First Resume
                          </button>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                          {savedResumes.map((resume) => (
                            <div key={resume.resume_id} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:bg-white/10 hover:border-white/20 transition-all duration-300 hover:scale-105 hover:shadow-xl">
                              <div className="flex items-start justify-between mb-4">
                                <div className="flex-1">
                                  <h4 className="font-semibold text-lg mb-2 text-white">{resume.resume_title}</h4>
                                  <p className="text-sm text-gray-400 capitalize mb-2">{resume.template_type} Template</p>
                                  <p className="text-xs text-gray-500">
                                    Created: {new Date(resume.created_at).toLocaleDateString()}
                                  </p>
                                </div>
                                <div className="flex items-center gap-1 bg-yellow-500/20 border border-yellow-500/30 px-3 py-1 rounded-full">
                                  <Star className="h-4 w-4 text-yellow-400" />
                                  <span className="text-sm font-medium text-yellow-400">{resume.ats_score || 0}</span>
                                </div>
                              </div>
                              
                              <div className="grid grid-cols-3 gap-2 mb-4">
                                <button
                                  onClick={() => setViewingResume(resume)}
                                  className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30 text-blue-300 hover:from-blue-500/30 hover:to-purple-500/30 px-3 py-2 rounded-lg flex items-center justify-center gap-1 text-sm transition-all duration-300 hover:scale-105"
                                >
                                  <Eye className="h-4 w-4" />
                                  View
                                </button>
                                <button
                                  onClick={() => generatePDF(resume.resume_id)}
                                  disabled={loading}
                                  className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-500/30 text-green-300 hover:from-green-500/30 hover:to-emerald-500/30 px-3 py-2 rounded-lg flex items-center justify-center gap-1 text-sm transition-all duration-300 hover:scale-105"
                                >
                                  <Download className="h-4 w-4" />
                                  PDF
                                </button>
                                <button
                                  onClick={() => optimizeResume(resume.resume_id)}
                                  disabled={loading}
                                  className="bg-gradient-to-r from-orange-500/20 to-yellow-500/20 border border-orange-500/30 text-orange-300 hover:from-orange-500/30 hover:to-yellow-500/30 px-3 py-2 rounded-lg flex items-center justify-center gap-1 text-sm transition-all duration-300 hover:scale-105"
                                >
                                  <Zap className="h-4 w-4" />
                                  Optimize
                                </button>
                              </div>
                              
                              <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-white/10">
                                <span>Applications: {resume.job_applications_count || 0}</span>
                                <span className={`px-2 py-1 rounded-full ${resume.pdf_available ? 'bg-green-500/20 border border-green-500/30 text-green-400' : 'bg-gray-500/20 border border-gray-500/30 text-gray-400'}`}>
                                  {resume.pdf_available ? 'PDF Ready' : 'No PDF'}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Job Applications Tab */}
              {activeTab === 'applications' && (
                <div>
                  {!selectedClient ? (
                    <div className="text-center py-20 text-gray-400">
                      <div className="bg-gradient-to-r from-gray-500/10 to-purple-500/10 rounded-2xl p-12 border border-white/10">
                        <Building className="h-20 w-20 mx-auto mb-6 opacity-50 text-gray-500" />
                        <h3 className="text-2xl font-medium mb-4 text-white">Please select a client first</h3>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-3 mb-8">
                        <div className="p-2 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg">
                          <Building className="h-5 w-5 text-white" />
                        </div>
                        <h3 className="text-2xl font-semibold text-white">
                          Job Applications for {selectedClient.first_name} {selectedClient.last_name}
                        </h3>
                      </div>
                      
                      {jobApplications.length === 0 ? (
                        <div className="text-center py-16 bg-gradient-to-r from-gray-500/10 to-purple-500/10 rounded-2xl border border-white/10">
                          <Building className="h-20 w-20 mx-auto mb-6 opacity-50 text-gray-500" />
                          <p className="text-gray-400 text-lg">No job applications yet</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {jobApplications.map((app) => (
                            <div key={app.application_id} className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300">
                              <div className="flex items-start justify-between">
                                <div>
                                  <h4 className="font-medium text-white text-lg">{app.job_title}</h4>
                                  <p className="text-gray-300">{app.company_name}</p>
                                  <p className="text-sm text-gray-400 mt-2">
                                    Applied: {new Date(app.applied_date).toLocaleDateString()}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                                    app.application_status === 'submitted' ? 'bg-blue-500/20 border border-blue-500/30 text-blue-400' :
                                    app.application_status === 'under_review' ? 'bg-yellow-500/20 border border-yellow-500/30 text-yellow-400' :
                                    app.application_status === 'interview' ? 'bg-green-500/20 border border-green-500/30 text-green-400' :
                                    'bg-gray-500/20 border border-gray-500/30 text-gray-400'
                                  }`}>
                                    {app.application_status}
                                  </span>
                                  <div className="text-sm text-gray-400 mt-2">
                                    Match: {app.match_score}%
                                  </div>
                                </div>
                              </div>
                              
                              <div className="mt-4 text-sm text-gray-300 bg-white/5 rounded-lg p-3 border border-white/10">
                                Resume: {app.resume_title}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Resume Viewing Modal */}
          {viewingResume && (
            <ResumeModal
              resume={viewingResume}
              client={getEffectiveClient()}
              onClose={() => setViewingResume(null)}
              onDownload={generatePDF}
              onOptimize={optimizeResume}
            />
          )}

          {/* Debug Panel (Development Only) */}
          <DebugPanel
            selectedClient={getEffectiveClient()}
            employmentProfile={employmentProfile}
            selectedTemplate={selectedTemplate}
            activeTab={activeTab}
          />
        </div>
      </div>
    </div>
  )
}

export default Resume