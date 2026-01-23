import { useState, useEffect } from 'react'
import { Eye, Star, Check, FileText } from 'lucide-react'

const TemplateSelector = ({ 
  templates, 
  selectedTemplate, 
  onTemplateSelect,
  onCreateResume,
  selectedClient,
  loading = false
}) => {
  const [templatePreviews, setTemplatePreviews] = useState({})
  const [previewsLoading, setPreviewsLoading] = useState(true)

  useEffect(() => {
    generateTemplateThumbnails()
  }, [templates])

  const generateTemplateThumbnails = async () => {
    setPreviewsLoading(true)
    
    // Generate mock thumbnails for now
    // In a real implementation, you would capture actual template previews
    const previews = {}
    
    templates.forEach(template => {
      previews[template.id] = generateMockThumbnail(template)
    })
    
    setTemplatePreviews(previews)
    setPreviewsLoading(false)
  }

  const generateMockThumbnail = (template) => {
    // Generate SVG thumbnails based on template type
    const thumbnails = {
      classic: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="20" y="20" width="160" height="40" fill="#1e40af" rx="2"/>
          <rect x="30" y="30" width="80" height="8" fill="white" rx="1"/>
          <rect x="30" y="42" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="80" width="160" height="2" fill="#e5e7eb"/>
          <rect x="20" y="100" width="100" height="6" fill="#374151" rx="1"/>
          <rect x="20" y="115" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="125" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="150" width="100" height="6" fill="#374151" rx="1"/>
          <rect x="20" y="165" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="175" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `,
      modern: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="modernGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
            </linearGradient>
          </defs>
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="0" y="0" width="200" height="60" fill="url(#modernGrad)"/>
          <rect x="20" y="15" width="80" height="8" fill="white" rx="1"/>
          <rect x="20" y="30" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="80" width="100" height="6" fill="#667eea" rx="1"/>
          <rect x="20" y="95" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="105" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="130" width="100" height="6" fill="#667eea" rx="1"/>
          <rect x="20" y="145" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="155" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `,
      warehouse: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="0" y="0" width="200" height="50" fill="#f59e0b"/>
          <rect x="20" y="15" width="80" height="8" fill="white" rx="1"/>
          <rect x="20" y="28" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="70" width="100" height="6" fill="#f59e0b" rx="1"/>
          <rect x="20" y="85" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="95" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="120" width="100" height="6" fill="#f59e0b" rx="1"/>
          <rect x="20" y="135" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="145" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `,
      construction: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="0" y="0" width="200" height="50" fill="#dc2626"/>
          <rect x="20" y="15" width="80" height="8" fill="white" rx="1"/>
          <rect x="20" y="28" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="70" width="100" height="6" fill="#dc2626" rx="1"/>
          <rect x="20" y="85" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="95" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="120" width="100" height="6" fill="#dc2626" rx="1"/>
          <rect x="20" y="135" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="145" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `,
      food_service: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="0" y="0" width="200" height="50" fill="#059669"/>
          <rect x="20" y="15" width="80" height="8" fill="white" rx="1"/>
          <rect x="20" y="28" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="70" width="100" height="6" fill="#059669" rx="1"/>
          <rect x="20" y="85" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="95" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="120" width="100" height="6" fill="#059669" rx="1"/>
          <rect x="20" y="135" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="145" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `,
      medical_social: `
        <svg viewBox="0 0 200 260" xmlns="http://www.w3.org/2000/svg">
          <rect width="200" height="260" fill="white" stroke="#e5e7eb" stroke-width="1"/>
          <rect x="0" y="0" width="200" height="50" fill="#7c3aed"/>
          <rect x="20" y="15" width="80" height="8" fill="white" rx="1"/>
          <rect x="20" y="28" width="120" height="6" fill="white" rx="1"/>
          <rect x="20" y="70" width="100" height="6" fill="#7c3aed" rx="1"/>
          <rect x="20" y="85" width="140" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="95" width="120" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="120" width="100" height="6" fill="#7c3aed" rx="1"/>
          <rect x="20" y="135" width="130" height="4" fill="#6b7280" rx="1"/>
          <rect x="20" y="145" width="110" height="4" fill="#6b7280" rx="1"/>
        </svg>
      `
    }
    
    return `data:image/svg+xml;base64,${btoa(thumbnails[template.id] || thumbnails.classic)}`
  }

  const handleTemplateClick = (template) => {
    onTemplateSelect(template)
  }

  const handleCreateResume = (template) => {
    if (onCreateResume) {
      onCreateResume(template)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold">Choose Resume Template</h3>
        <div className="text-sm text-gray-500">
          {templates.length} professional templates available
        </div>
      </div>

      {previewsLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <div key={template.id} className="border rounded-lg p-6 animate-pulse">
              <div className="bg-gray-200 h-48 rounded mb-4"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <div
              key={template.id}
              className={`border rounded-lg p-6 cursor-pointer transition-all hover:shadow-lg ${
                selectedTemplate?.id === template.id
                  ? 'border-blue-500 bg-blue-50 shadow-md ring-2 ring-blue-200'
                  : 'border-gray-200 hover:border-blue-300'
              }`}
              onClick={() => handleTemplateClick(template)}
            >
              {/* Template Thumbnail */}
              <div className="relative mb-4">
                <div className="bg-gray-100 rounded-lg overflow-hidden">
                  <img
                    src={templatePreviews[template.id]}
                    alt={`${template.name} preview`}
                    className="w-full h-48 object-cover"
                  />
                </div>
                {selectedTemplate?.id === template.id && (
                  <div className="absolute top-2 right-2 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
              </div>

              {/* Template Info */}
              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold text-lg flex items-center gap-2">
                    <span className="text-2xl">{template.preview}</span>
                    {template.name}
                  </h4>
                  <p className="text-sm text-gray-600 mt-1">{template.description}</p>
                </div>

                {/* Features */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <Star className="h-4 w-4" />
                    Background Friendly
                  </div>
                  <div className="text-xs text-gray-500">
                    <strong>Best for:</strong> {template.suitableFor.join(', ')}
                  </div>
                </div>

                {/* Action Button */}
                {selectedTemplate?.id === template.id && (
                  <div className="pt-4 border-t border-blue-200">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCreateResume(template)
                      }}
                      disabled={!selectedClient || loading}
                      className="w-full btn-primary flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Creating...
                        </>
                      ) : (
                        <>
                          <FileText className="h-4 w-4" />
                          Create Resume
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!selectedClient && (
        <div className="text-center py-8 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-yellow-800">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="font-medium">Client Selection Required</p>
            <p className="text-sm">Please select a client before choosing a template</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TemplateSelector