import { useState, useEffect } from 'react'
import { X, Download, Zap, Eye, Loader, FileText, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import PDFService from '../services/pdfService'

const ResumeModal = ({ resume, client, onClose, onDownload, onOptimize }) => {
  const [resumeContent, setResumeContent] = useState(null)
  const [htmlPreview, setHtmlPreview] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeView, setActiveView] = useState('structured') // 'structured' or 'preview'

  useEffect(() => {
    if (resume) {
      loadResumeContent()
    }
  }, [resume])

  const loadResumeContent = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Load structured resume data
      const data = await PDFService.viewResume(resume.resume_id)
      setResumeContent(data.resume)
      
      // Also load HTML preview for visual display
      try {
        const previewData = await PDFService.getHTMLPreview(resume.resume_id)
        setHtmlPreview(previewData.html_content)
      } catch (previewError) {
        console.warn('HTML preview failed, using structured view only:', previewError)
      }
      
    } catch (error) {
      console.error('Failed to load resume content:', error)
      setError(PDFService.getErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    try {
      if (resumeContent?.pdf_available) {
        // Download existing PDF
        const filename = PDFService.formatFilename(
          client.first_name, 
          client.last_name, 
          resume.resume_id
        )
        await PDFService.downloadPDF(resume.resume_id, filename)
        toast.success('Download completed!')
      } else {
        // Generate and download PDF
        await onDownload(resume.resume_id)
      }
    } catch (error) {
      const userMessage = PDFService.getErrorMessage(error)
      toast.error(userMessage)
    }
  }

  const handleOptimize = async () => {
    try {
      await onOptimize(resume.resume_id)
      // Reload content to show updated ATS score
      await loadResumeContent()
    } catch (error) {
      const userMessage = PDFService.getErrorMessage(error)
      toast.error(userMessage)
    }
  }

  if (!resume) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 border border-white/20 rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-black/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Resume Viewer</h2>
              <p className="text-gray-300 text-sm">{resume.resume_title}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex bg-white/10 rounded-lg p-1">
              <button
                onClick={() => setActiveView('structured')}
                className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                  activeView === 'structured'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                Data View
              </button>
              <button
                onClick={() => setActiveView('preview')}
                className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                  activeView === 'preview'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
                disabled={!htmlPreview}
              >
                Preview
              </button>
            </div>
            
            {/* Action Buttons */}
            <button
              onClick={handleDownload}
              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-lg hover:from-green-400 hover:to-emerald-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105"
            >
              <Download className="h-4 w-4" />
              {resumeContent?.pdf_available ? 'Download PDF' : 'Generate PDF'}
            </button>
            
            <button
              onClick={handleOptimize}
              className="bg-gradient-to-r from-orange-500 to-yellow-500 text-white px-4 py-2 rounded-lg hover:from-orange-400 hover:to-yellow-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105"
            >
              <Zap className="h-4 w-4" />
              Optimize
            </button>
            
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-2 hover:bg-white/10 rounded-lg transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6" style={{ maxHeight: 'calc(90vh - 120px)' }}>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Loader className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
                <p className="text-gray-300">Loading resume content...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center text-red-400">
                <AlertCircle className="h-12 w-12 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Error Loading Resume</h3>
                <p className="text-sm text-gray-400 mb-4">{error}</p>
                <button
                  onClick={loadResumeContent}
                  className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          ) : activeView === 'structured' ? (
            <StructuredResumeView resumeContent={resumeContent} />
          ) : (
            <HTMLPreviewView htmlContent={htmlPreview} />
          )}
        </div>

        {/* Footer */}
        {resumeContent && (
          <div className="px-6 py-4 border-t border-white/10 bg-black/20">
            <div className="flex items-center justify-between text-sm text-gray-400">
              <div className="flex items-center gap-6">
                <span>Template: {resumeContent.template_type}</span>
                <span>Created: {new Date(resumeContent.created_at).toLocaleDateString()}</span>
                <span className="flex items-center gap-1">
                  ATS Score: 
                  <span className="text-yellow-400 font-semibold">{resumeContent.ats_score || 0}</span>
                </span>
              </div>
              <div className={`px-2 py-1 rounded text-xs ${
                resumeContent.pdf_available 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-gray-500/20 text-gray-400'
              }`}>
                {resumeContent.pdf_available ? 'PDF Available' : 'PDF Not Generated'}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Structured view component
const StructuredResumeView = ({ resumeContent }) => {
  if (!resumeContent) return null

  const { content, client } = resumeContent

  return (
    <div className="space-y-6">
      {/* Client Information */}
      <div className="bg-white/5 rounded-xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Eye className="h-5 w-5 text-blue-400" />
          Client Information
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Name:</span>
            <span className="text-white ml-2">{client.first_name} {client.last_name}</span>
          </div>
          <div>
            <span className="text-gray-400">Email:</span>
            <span className="text-white ml-2">{client.email}</span>
          </div>
          <div>
            <span className="text-gray-400">Phone:</span>
            <span className="text-white ml-2">{client.phone}</span>
          </div>
          <div>
            <span className="text-gray-400">Address:</span>
            <span className="text-white ml-2">{client.address}</span>
          </div>
        </div>
      </div>

      {/* Career Objective */}
      {content.career_objective && (
        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Career Objective</h3>
          <p className="text-gray-300 leading-relaxed">{content.career_objective}</p>
        </div>
      )}

      {/* Work Experience */}
      {content.work_history && content.work_history.length > 0 && (
        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Work Experience</h3>
          <div className="space-y-4">
            {content.work_history.map((job, index) => (
              <div key={index} className="border-l-2 border-blue-500 pl-4">
                <h4 className="font-semibold text-white">{job.job_title || 'Job Title'}</h4>
                <p className="text-blue-400 font-medium">{job.company || 'Company Name'}</p>
                <p className="text-sm text-gray-400 mb-2">
                  {job.start_date || 'Start Date'} - {job.end_date || 'Present'}
                  {job.location && ` • ${job.location}`}
                </p>
                {job.description && (
                  <div className="text-gray-300 text-sm">
                    {job.description.split('\n').map((line, lineIndex) => (
                      line.trim() && (
                        <div key={lineIndex} className="flex items-start gap-2 mb-1">
                          <span className="text-blue-400 mt-1">•</span>
                          <span>{line.trim().replace(/^•\s*/, '')}</span>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skills */}
      {content.skills && content.skills.length > 0 && (
        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Skills</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {content.skills.map((skillCat, index) => (
              <div key={index}>
                <h4 className="font-semibold text-blue-400 mb-2">{skillCat.category || 'Skills'}</h4>
                <div className="flex flex-wrap gap-2">
                  {(skillCat.skill_list || []).map((skill, skillIndex) => (
                    <span
                      key={skillIndex}
                      className="bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-sm border border-blue-500/30"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Education */}
      {content.education && content.education.length > 0 && (
        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Education</h3>
          <div className="space-y-3">
            {content.education.map((edu, index) => (
              <div key={index}>
                <h4 className="font-semibold text-white">{edu.degree || 'Degree'}</h4>
                <p className="text-blue-400">{edu.institution || 'Institution'}</p>
                <p className="text-sm text-gray-400">{edu.graduation_date || 'Year'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Certifications */}
      {content.certifications && content.certifications.length > 0 && (
        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-4">Certifications</h3>
          <div className="space-y-3">
            {content.certifications.map((cert, index) => (
              <div key={index}>
                <h4 className="font-semibold text-white">{cert.name || 'Certification'}</h4>
                <p className="text-blue-400">{cert.issuer || 'Issuer'}</p>
                <p className="text-sm text-gray-400">{cert.date_obtained || 'Date'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// HTML preview component
const HTMLPreviewView = ({ htmlContent }) => {
  if (!htmlContent) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="text-center">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>HTML preview not available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg p-4 shadow-lg">
      <div 
        className="resume-preview"
        dangerouslySetInnerHTML={{ __html: htmlContent }}
        style={{
          fontFamily: 'Arial, sans-serif',
          lineHeight: '1.4',
          color: '#000',
          maxWidth: '8.5in',
          margin: '0 auto'
        }}
      />
    </div>
  )
}

export default ResumeModal