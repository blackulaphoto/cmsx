import { useState, useEffect, useRef, useCallback } from 'react'
import { ZoomIn, ZoomOut, Download, Eye, FileText, Loader, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import ResumePreviewComponent from './ResumePreviewComponent'

const LivePreview = ({ 
  employmentProfile, 
  selectedTemplate, 
  selectedClient,
  onGeneratePDF 
}) => {
  const [zoom, setZoom] = useState(0.7)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(Date.now())
  const previewRef = useRef(null)
  const updateTimeoutRef = useRef(null)

  // Debounced preview update to prevent excessive re-renders
  const debouncedUpdate = useCallback(() => {
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current)
    }
    
    updateTimeoutRef.current = setTimeout(() => {
      setLastUpdate(Date.now())
    }, 300) // 300ms debounce
  }, [])

  // Track changes and trigger debounced updates
  useEffect(() => {
    debouncedUpdate()
    
    // Cleanup timeout on unmount
    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current)
      }
    }
  }, [
    employmentProfile?.career_objective,
    employmentProfile?.work_history,
    employmentProfile?.skills,
    employmentProfile?.education,
    employmentProfile?.certifications,
    selectedTemplate?.id,
    selectedClient?.client_id,
    debouncedUpdate
  ])

  const handleZoomIn = () => {
    setZoom(Math.min(zoom + 0.1, 1.5))
  }

  const handleZoomOut = () => {
    setZoom(Math.max(zoom - 0.1, 0.3))
  }

  const handleRefresh = () => {
    setLastUpdate(Date.now())
    toast.success('Preview refreshed')
  }

  const handleGeneratePDF = () => {
    if (!selectedClient || !selectedTemplate) {
      toast.error('Please select a client and template first')
      return
    }
    onGeneratePDF()
  }

  if (!selectedClient || !selectedTemplate) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-gray-500/10 to-purple-500/10 rounded-2xl border-2 border-dashed border-white/20">
        <div className="text-center text-gray-400">
          <FileText className="h-20 w-20 mx-auto mb-6 opacity-50" />
          <p className="text-xl font-medium mb-2 text-white">Resume Preview</p>
          <p className="text-lg">Select a client and template to see live preview</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
      {/* Preview Toolbar */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/20 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
            <Eye className="h-4 w-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-white">Live Preview</span>
            <div className="text-sm text-gray-300">({selectedTemplate.name})</div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-all duration-300"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          
          <span className="text-sm text-gray-300 min-w-[60px] text-center font-medium bg-white/5 px-3 py-1 rounded-lg border border-white/10">
            {Math.round(zoom * 100)}%
          </span>
          
          <button
            onClick={handleZoomIn}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-all duration-300"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          
          <div className="w-px h-6 bg-white/20 mx-2" />
          
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-all duration-300"
            title="Refresh Preview"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={handleGeneratePDF}
            className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-4 py-2 rounded-lg hover:from-green-400 hover:to-emerald-400 transition-all duration-300 flex items-center gap-2 font-medium hover:scale-105 hover:shadow-lg hover:shadow-green-500/25"
          >
            <Download className="h-4 w-4" />
            Generate PDF
          </button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="preview-content-area flex-1 overflow-auto bg-gradient-to-br from-gray-100 to-gray-200 p-6">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Loader className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-600">Generating preview...</p>
            </div>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-red-600 bg-white rounded-xl p-8 shadow-lg">
              <FileText className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="font-medium">Preview Error</p>
              <p className="text-sm">{error}</p>
              <button
                onClick={handleRefresh}
                className="mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : (
          <div 
            ref={previewRef}
            className="resume-preview-document mx-auto bg-white shadow-2xl border border-gray-300"
            style={{ 
              transform: `scale(${zoom})`,
              transformOrigin: 'top center',
              width: '8.5in',
              minHeight: '11in',
              maxWidth: '8.5in'
            }}
          >
            <ResumePreviewComponent
              client={selectedClient}
              profile={employmentProfile}
              template={selectedTemplate.id}
              key={lastUpdate} // Force re-render on updates
            />
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="flex-shrink-0 px-4 py-2 bg-black/20 border-t border-white/10">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-4">
            <span>Template: {selectedTemplate.name}</span>
            <span>Client: {selectedClient.first_name} {selectedClient.last_name}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>Live Updates Active</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LivePreview