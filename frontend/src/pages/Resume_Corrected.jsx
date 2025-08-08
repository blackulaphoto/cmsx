import { useState, useEffect } from 'react'
import { FileText, Download, Edit, Eye, User, Briefcase, MapPin, Phone, Mail, Star, Plus, Trash2, Save, Target, Search, Zap, Users, Building } from 'lucide-react'
import toast from 'react-hot-toast'

function Resume() {
  const [selectedClient, setSelectedClient] = useState(null)
  const [availableClients, setAvailableClients] = useState([])
  const [activeTab, setActiveTab] = useState('clients')
  const [selectedTemplate, setSelectedTemplate] = useState(null)
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

  const templates = [
    {
      id: 'classic',
      name: 'Classic Professional',
      description: 'Traditional corporate layout - ATS friendly',
      preview: '📄',
      suitableFor: ['Corporate', 'Finance', 'Legal', 'Traditional Industries'],
      background_friendly: true
    },
    {
      id: 'modern',
      name: 'Modern Professional',
      description: 'Contemporary design with clean layout',
      preview: '🎨',
      suitableFor: ['Technology', 'Marketing', 'Design', 'Startups'],
      background_friendly: true
    },
    {
      id: 'warehouse',
      name: 'Warehouse & Logistics',
      description: 'Optimized for warehouse and manual labor positions',
      preview: '📦',
      suitableFor: ['Warehouse', 'Manufacturing', 'Logistics', 'Manual Labor'],
      background_friendly: true
    },
    {
      id: 'construction',
      name: 'Construction & Trades',
      description: 'Industry-specific template for construction jobs',
      preview: '🔨',
      suitableFor: ['Construction', 'Trades', 'Engineering', 'Architecture'],
      background_friendly: true
    },
    {
      id: 'food_service',
      name: 'Food Service',
      description: 'Restaurant and hospitality industry focused',
      preview: '🍽️',
      suitableFor: ['Restaurants', 'Hospitality', 'Catering', 'Food Service'],
      background_friendly: true
    },
    {
      id: 'medical_social',
      name: 'Medical/Social Worker',
      description: 'Healthcare and social services template',
      preview: '🏥',
      suitableFor: ['Healthcare', 'Social Work', 'Non-Profit', 'Education'],
      background_friendly: true
    }
  ]

  useEffect(() => {
    fetchAvailableClients()
  }, [])

  useEffect(() => {
    if (selectedClient) {
      fetchEmploymentProfile()
      fetchClientResumes()
      fetchJobApplications()
    }
  }, [selectedClient])

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

  const saveEmploymentProfile = async () => {
    if (!selectedClient) {
      toast.error('Please select a client first')
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/resume/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: selectedClient.client_id,
          ...employmentProfile
        })
      })

      if (response.ok) {
        const data = await response.json()
        toast.success('Employment profile saved successfully!')
        setActiveTab('resumes')
      } else {
        throw new Error('Failed to save profile')
      }
    } catch (error) {
      toast.error('Failed to save employment profile')
      console.error('Profile save error:', error)
    } finally {
      setLoading(false)
    }
  }

  const createResume = async () => {
    if (!selectedClient) {
      toast.error('Please select a client first')
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
          client_id: selectedClient.client_id,
          template_type: selectedTemplate.id,
          resume_title: `${selectedTemplate.name} Resume for ${selectedClient.first_name} ${selectedClient.last_name}`
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
    setLoading(true)
    try {
      const response = await fetch(`/api/resume/generate-pdf/${resumeId}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        toast.success('PDF generated successfully!')
        
        // Download the PDF
        const downloadResponse = await fetch(`/api/resume/download/${resumeId}`)
        if (downloadResponse.ok) {
          const blob = await downloadResponse.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `resume_${selectedClient.first_name}_${selectedClient.last_name}.pdf`
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          document.body.removeChild(a)
        }
      } else {
        throw new Error('Failed to generate PDF')
      }
    } catch (error) {
      toast.error('Failed to generate PDF')
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
        fetchClientResumes()
      } else {
        throw new Error('Failed to optimize resume')
      }
    } catch (error) {
      toast.error('Failed to optimize resume')
      console.error('Resume optimization error:', error)
    } finally {
      setLoading(false)
    }
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

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <FileText size={32} />
          <h1 className="text-3xl font-bold">Resume Builder</h1>
        </div>
        <p className="text-lg opacity-90">Create professional resumes aligned with employment profiles</p>
      </div>

      <div className="p-8">
        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-custom-sm mb-8">
          <div className="flex border-b border-gray-200">
            {[
              { id: 'clients', label: 'Select Client', icon: Users },
              { id: 'profile', label: 'Employment Profile', icon: User },
              { id: 'templates', label: 'Templates', icon: Eye },
              { id: 'resumes', label: 'Resumes', icon: FileText },
              { id: 'applications', label: 'Job Applications', icon: Building }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="p-6">
            {/* Client Selection Tab */}
            {activeTab === 'clients' && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Select Client</h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {availableClients.map((client) => (
                    <div
                      key={client.client_id}
                      onClick={() => {
                        setSelectedClient(client)
                        setActiveTab('profile')
                        toast.success(`Selected ${client.first_name} ${client.last_name}`)
                      }}
                      className={`p-4 border rounded-lg cursor-pointer transition-all hover:shadow-md ${
                        selectedClient?.client_id === client.client_id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <h4 className="font-medium">{client.first_name} {client.last_name}</h4>
                          <p className="text-sm text-gray-600">{client.email}</p>
                          <div className="flex items-center gap-4 mt-1">
                            <span className="text-xs text-gray-500">
                              {client.active_resumes} resume{client.active_resumes !== 1 ? 's' : ''}
                            </span>
                            {client.has_resume && (
                              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                Has Resume
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {availableClients.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No active clients found</p>
                  </div>
                )}
              </div>
            )}

            {/* Employment Profile Tab */}
            {activeTab === 'profile' && (
              <div>
                {!selectedClient ? (
                  <div className="text-center py-8 text-gray-500">
                    <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Please select a client first</p>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-xl font-semibold">
                        Employment Profile for {selectedClient.first_name} {selectedClient.last_name}
                      </h3>
                      <button
                        onClick={saveEmploymentProfile}
                        disabled={loading}
                        className="btn-primary flex items-center gap-2"
                      >
                        <Save className="h-4 w-4" />
                        {loading ? 'Saving...' : 'Save Profile'}
                      </button>
                    </div>

                    {/* Career Objective */}
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Career Objective
                      </label>
                      <textarea
                        value={employmentProfile.career_objective}
                        onChange={(e) => setEmploymentProfile(prev => ({
                          ...prev,
                          career_objective: e.target.value
                        }))}
                        placeholder="Brief statement about career goals and objectives..."
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows={3}
                      />
                    </div>

                    {/* Work History */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-medium">Work History</h4>
                        <button
                          onClick={addWorkExperience}
                          className="btn-secondary flex items-center gap-2"
                        >
                          <Plus className="h-4 w-4" />
                          Add Experience
                        </button>
                      </div>
                      
                      {employmentProfile.work_history.map((exp, index) => (
                        <div key={index} className="border border-gray-200 rounded-lg p-4 mb-4">
                          <div className="flex justify-between items-start mb-4">
                            <h5 className="font-medium">Experience #{index + 1}</h5>
                            <button
                              onClick={() => removeWorkExperience(index)}
                              className="text-red-600 hover:text-red-800"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <input
                              type="text"
                              placeholder="Job Title"
                              value={exp.job_title}
                              onChange={(e) => updateWorkExperience(index, 'job_title', e.target.value)}
                              className="input-field"
                            />
                            <input
                              type="text"
                              placeholder="Company Name"
                              value={exp.company}
                              onChange={(e) => updateWorkExperience(index, 'company', e.target.value)}
                              className="input-field"
                            />
                            <input
                              type="text"
                              placeholder="Start Date (YYYY-MM)"
                              value={exp.start_date}
                              onChange={(e) => updateWorkExperience(index, 'start_date', e.target.value)}
                              className="input-field"
                            />
                            <input
                              type="text"
                              placeholder="End Date (YYYY-MM or Present)"
                              value={exp.end_date}
                              onChange={(e) => updateWorkExperience(index, 'end_date', e.target.value)}
                              className="input-field"
                            />
                          </div>
                          
                          <textarea
                            placeholder="Job description and key responsibilities..."
                            value={exp.description}
                            onChange={(e) => updateWorkExperience(index, 'description', e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={3}
                          />
                        </div>
                      ))}
                    </div>

                    {/* Skills */}
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-medium">Skills</h4>
                        <button
                          onClick={addSkillCategory}
                          className="btn-secondary flex items-center gap-2"
                        >
                          <Plus className="h-4 w-4" />
                          Add Skill Category
                        </button>
                      </div>
                      
                      {employmentProfile.skills.map((skillCat, index) => (
                        <div key={index} className="border border-gray-200 rounded-lg p-4 mb-4">
                          <input
                            type="text"
                            placeholder="Skill Category (e.g., Technical Skills, Soft Skills)"
                            value={skillCat.category}
                            onChange={(e) => updateSkillCategory(index, 'category', e.target.value)}
                            className="input-field mb-3"
                          />
                          
                          <div className="flex flex-wrap gap-2 mb-3">
                            {skillCat.skill_list.map((skill, skillIndex) => (
                              <span
                                key={skillIndex}
                                className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center gap-2"
                              >
                                {skill}
                                <button
                                  onClick={() => removeSkillFromCategory(index, skillIndex)}
                                  className="text-blue-600 hover:text-blue-800"
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
                              className="input-field flex-1"
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
                              className="btn-secondary"
                            >
                              Add
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Templates Tab */}
            {activeTab === 'templates' && (
              <div>
                <h3 className="text-xl font-semibold mb-4">Choose Resume Template</h3>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      onClick={() => setSelectedTemplate(template)}
                      className={`border rounded-lg p-6 cursor-pointer transition-all hover:shadow-lg ${
                        selectedTemplate?.id === template.id
                          ? 'border-blue-500 bg-blue-50 shadow-md'
                          : 'border-gray-200 hover:border-blue-300'
                      }`}
                    >
                      <div className="text-center mb-4">
                        <div className="text-4xl mb-2">{template.preview}</div>
                        <h4 className="font-semibold text-lg">{template.name}</h4>
                        <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm text-green-600">
                          <Star className="h-4 w-4" />
                          Background Friendly
                        </div>
                        <div className="text-xs text-gray-500">
                          <strong>Best for:</strong> {template.suitableFor.join(', ')}
                        </div>
                      </div>
                      
                      {selectedTemplate?.id === template.id && (
                        <div className="mt-4 pt-4 border-t border-blue-200">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              createResume()
                            }}
                            disabled={!selectedClient || loading}
                            className="w-full btn-primary"
                          >
                            {loading ? 'Creating...' : 'Create Resume'}
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Resumes Tab */}
            {activeTab === 'resumes' && (
              <div>
                {!selectedClient ? (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Please select a client first</p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">
                      Resumes for {selectedClient.first_name} {selectedClient.last_name}
                    </h3>
                    
                    {savedResumes.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No resumes created yet</p>
                        <button
                          onClick={() => setActiveTab('templates')}
                          className="btn-primary mt-4"
                        >
                          Create First Resume
                        </button>
                      </div>
                    ) : (
                      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {savedResumes.map((resume) => (
                          <div key={resume.resume_id} className="border border-gray-200 rounded-lg p-4">
                            <div className="flex items-start justify-between mb-3">
                              <div>
                                <h4 className="font-medium">{resume.resume_title}</h4>
                                <p className="text-sm text-gray-600">{resume.template_type}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                  Created: {new Date(resume.created_at).toLocaleDateString()}
                                </p>
                              </div>
                              <div className="flex items-center gap-1">
                                <Star className="h-4 w-4 text-yellow-500" />
                                <span className="text-sm font-medium">{resume.ats_score || 0}</span>
                              </div>
                            </div>
                            
                            <div className="flex gap-2">
                              <button
                                onClick={() => generatePDF(resume.resume_id)}
                                disabled={loading}
                                className="btn-secondary flex-1 flex items-center justify-center gap-2"
                              >
                                <Download className="h-4 w-4" />
                                PDF
                              </button>
                              <button
                                onClick={() => optimizeResume(resume.resume_id)}
                                disabled={loading}
                                className="btn-primary flex-1 flex items-center justify-center gap-2"
                              >
                                <Zap className="h-4 w-4" />
                                Optimize
                              </button>
                            </div>
                            
                            <div className="mt-3 text-xs text-gray-500">
                              Applications: {resume.job_applications_count || 0}
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
                  <div className="text-center py-8 text-gray-500">
                    <Building className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Please select a client first</p>
                  </div>
                ) : (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">
                      Job Applications for {selectedClient.first_name} {selectedClient.last_name}
                    </h3>
                    
                    {jobApplications.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <Building className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No job applications yet</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {jobApplications.map((app) => (
                          <div key={app.application_id} className="border border-gray-200 rounded-lg p-4">
                            <div className="flex items-start justify-between">
                              <div>
                                <h4 className="font-medium">{app.job_title}</h4>
                                <p className="text-gray-600">{app.company_name}</p>
                                <p className="text-sm text-gray-500 mt-1">
                                  Applied: {new Date(app.applied_date).toLocaleDateString()}
                                </p>
                              </div>
                              <div className="text-right">
                                <span className={`px-2 py-1 rounded-full text-xs ${
                                  app.application_status === 'submitted' ? 'bg-blue-100 text-blue-800' :
                                  app.application_status === 'under_review' ? 'bg-yellow-100 text-yellow-800' :
                                  app.application_status === 'interview' ? 'bg-green-100 text-green-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {app.application_status}
                                </span>
                                <div className="text-sm text-gray-500 mt-1">
                                  Match: {app.match_score}%
                                </div>
                              </div>
                            </div>
                            
                            <div className="mt-3 text-sm text-gray-600">
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
      </div>
    </div>
  )
}

export default Resume