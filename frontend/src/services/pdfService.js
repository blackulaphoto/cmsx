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

import toast from 'react-hot-toast'

/**
 * CORRECTED PDF Service for handling resume PDF generation, download, and viewing
 * Enhanced with better error handling and debugging capabilities
 */
export class PDFService {
  static BASE_URL = '/api/resume'
  
  // Enhanced error checking with detailed logging
  static async makeRequest(url, options = {}) {
    const fullUrl = url.startsWith('http') ? url : `${this.BASE_URL}${url}`
    
    try {
      console.log(`🌐 Making request to: ${fullUrl}`, options)
      
      const response = await fetch(fullUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      })
      
      console.log(`📡 Response status: ${response.status} ${response.statusText}`)
      
      if (!response.ok) {
        let errorData
        try {
          errorData = await response.json()
        } catch (e) {
          errorData = { 
            detail: `HTTP ${response.status}: ${response.statusText}`,
            status: response.status 
          }
        }
        
        console.error('❌ Request failed:', errorData)
        throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`)
      }
      
      // Handle different response types
      const contentType = response.headers.get('content-type')
      
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json()
        console.log('✅ JSON response received:', data)
        return data
      } else if (contentType && (contentType.includes('application/pdf') || contentType.includes('text/html'))) {
        const blob = await response.blob()
        console.log('✅ Binary response received:', blob.size, 'bytes')
        return blob
      } else {
        const text = await response.text()
        console.log('✅ Text response received:', text.substring(0, 100))
        return text
      }
      
    } catch (error) {
      console.error(`❌ Request to ${fullUrl} failed:`, error)
      throw error
    }
  }
  
  static async generatePDF(resumeId) {
    try {
      console.log(`🔄 Starting PDF generation for resume: ${resumeId}`)
      
      const data = await this.makeRequest(`/generate-pdf/${resumeId}`, {
        method: 'POST'
      })
      
      console.log('✅ PDF generation response:', data)
      return data
    } catch (error) {
      console.error('❌ PDF generation failed:', error)
      throw error
    }
  }
  
  static async downloadPDF(resumeId, filename = null) {
    try {
      console.log(`⬇️  Starting download for resume: ${resumeId}`)
      
      const blob = await this.makeRequest(`/download/${resumeId}`)
      
      if (!(blob instanceof Blob)) {
        throw new Error('Download response is not a file')
      }
      
      const url = window.URL.createObjectURL(blob)
      
      // Create download link
      const a = document.createElement('a')
      a.href = url
      a.download = filename || `resume_${resumeId}_${Date.now()}.pdf`
      document.body.appendChild(a)
      a.click()
      
      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      console.log('✅ Download completed successfully')
      return { success: true, message: 'Download completed' }
    } catch (error) {
      console.error('❌ PDF download failed:', error)
      throw error
    }
  }
  
  static async viewResume(resumeId) {
    try {
      console.log(`👁️  Loading resume data for: ${resumeId}`)
      
      const data = await this.makeRequest(`/view/${resumeId}`)
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to load resume data')
      }
      
      console.log('✅ Resume data loaded successfully:', data.resume.title)
      return data
    } catch (error) {
      console.error('❌ Failed to load resume:', error)
      throw error
    }
  }
  
  static async getHTMLPreview(resumeId) {
    try {
      console.log(`🖼️  Loading HTML preview for: ${resumeId}`)
      
      const data = await this.makeRequest(`/preview-html/${resumeId}`)
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to load preview')
      }
      
      console.log('✅ HTML preview loaded successfully')
      return data
    } catch (error) {
      console.error('❌ Failed to load HTML preview:', error)
      throw error
    }
  }
  
  static async generateAndDownload(resumeId, clientName) {
    let toastId = null
    
    try {
      // Step 1: Generate PDF
      toastId = toast.loading('Generating PDF...', { duration: 0 })
      
      const generateResult = await this.generatePDF(resumeId)
      
      if (generateResult.success) {
        toast.success('PDF generated successfully!', { id: toastId })
        
        // Step 2: Download PDF  
        toastId = toast.loading('Starting download...', { duration: 0 })
        
        const filename = this.formatFilename(clientName, null, resumeId)
        await this.downloadPDF(resumeId, filename)
        
        toast.success('Download completed!', { id: toastId })
        
        return generateResult
      } else {
        throw new Error(generateResult.message || 'PDF generation failed')
      }
    } catch (error) {
      if (toastId) {
        toast.error(`PDF Error: ${this.getErrorMessage(error)}`, { id: toastId })
      } else {
        toast.error(`PDF Error: ${this.getErrorMessage(error)}`)
      }
      throw error
    }
  }
  
  static async healthCheck() {
    try {
      console.log('🏥 Checking PDF service health...')
      
      const data = await this.makeRequest('/health')
      
      console.log('✅ Health check completed:', data.status)
      return data
    } catch (error) {
      console.error('❌ PDF service health check failed:', error)
      return { 
        success: false, 
        status: 'unhealthy',
        error: error.message 
      }
    }
  }
  
  /**
   * Enhanced error handling with user-friendly messages and debugging info
   */
  static getErrorMessage(error) {
    const errorMessage = error.message || error.toString()
    
    // Specific error patterns with user-friendly messages
    const errorPatterns = {
      'Resume not found': 'The resume could not be found. Please try refreshing the page.',
      'PDF not generated yet': 'Please generate the PDF first before downloading.',
      'PDF file not found': 'The PDF file is missing. Please regenerate it.',
      'PDF generation failed': 'PDF generation encountered an error. Please try again.',
      'Download failed': 'Download failed. Please check your connection and try again.',
      'Failed to load resume': 'Could not load resume data. Please refresh and try again.',
      'Failed to load preview': 'Preview could not be loaded. Please try again.',
      'Database connection failed': 'Database connection issue. Please contact support.',
      'PDF service not available': 'PDF service is temporarily unavailable. Please try again later.',
      'Template rendering failed': 'Resume template could not be rendered. Please try a different template.',
      'fetch': 'Connection error. Please check your internet connection.',
      'HTTP 404': 'The requested resource was not found.',
      'HTTP 500': 'Server error. Please try again in a moment.',
      'HTTP 503': 'Service temporarily unavailable. Please try again later.'
    }
    
    // Check for specific error patterns
    for (const [pattern, userMessage] of Object.entries(errorPatterns)) {
      if (errorMessage.toLowerCase().includes(pattern.toLowerCase())) {
        return userMessage
      }
    }
    
    // Debug mode - include more technical details in development
    if (process.env.NODE_ENV === 'development') {
      return `Debug: ${errorMessage}`
    }
    
    // Default user-friendly message
    return 'An unexpected error occurred. Please try again or contact support if the problem persists.'
  }
  
  /**
   * Utility method to format client name for filename
   */
  static formatFilename(firstName, lastName, resumeId = null) {
    const name = `${firstName || 'Unknown'}_${lastName || 'Client'}`
    const sanitized = name.replace(/[^a-zA-Z0-9_-]/g, '_').replace(/_{2,}/g, '_')
    const suffix = resumeId ? `_${resumeId}` : ''
    const timestamp = new Date().toISOString().slice(0, 10) // YYYY-MM-DD
    return `resume_${sanitized}${suffix}_${timestamp}.pdf`
  }
  
  /**
   * Check if PDF is available for download
   */
  static async checkPDFAvailable(resumeId) {
    try {
      const resumeData = await this.viewResume(resumeId)
      return resumeData.resume?.pdf_available || false
    } catch (error) {
      console.error('Failed to check PDF availability:', error)
      return false
    }
  }
  
  /**
   * Get clients list for debugging
   */
  static async getClients() {
    try {
      console.log('👥 Loading clients list...')
      
      const data = await this.makeRequest('/clients')
      
      console.log('✅ Clients loaded:', data.total_count)
      return data
    } catch (error) {
      console.error('❌ Failed to load clients:', error)
      throw error
    }
  }

  /**
   * Get resumes for a specific client
   * @param {string} clientId - Client ID
   * @returns {Promise<Object>} Resumes data
   */
  static async getClientResumes(clientId) {
    try {
      console.log(`📋 Loading resumes for client: ${clientId}`)
      
      // Try different possible endpoints for getting client resumes
      const endpoints = [
        `/resumes/${clientId}`,
        `/list/${clientId}`,
        `/client/${clientId}/resumes`
      ]
      
      let lastError = null
      
      for (const endpoint of endpoints) {
        try {
          const data = await this.makeRequest(endpoint)
          console.log(`✅ Resumes loaded from ${endpoint}:`, data.resumes?.length || 0)
          return data
        } catch (error) {
          lastError = error
          console.log(`⚠️ Endpoint ${endpoint} failed, trying next...`)
        }
      }
      
      // If all endpoints fail, throw the last error
      throw lastError || new Error('All resume endpoints failed')
      
    } catch (error) {
      console.error('❌ Failed to load client resumes:', error)
      throw error
    }
  }
  
  /**
   * Generate and download PDF for a resume
   * @param {string} resumeId - Resume ID
   * @param {string} clientName - Client name for filename
   * @returns {Promise<boolean>} Success status
   */
  static async generateAndDownload(resumeId, clientName = 'Resume') {
    try {
      console.log(`🎯 Starting PDF generation for resume: ${resumeId}`)
      
      // Generate PDF
      const generateResponse = await this.makeRequest(`/generate-pdf/${resumeId}`, {
        method: 'POST'
      })
      
      if (!generateResponse.success) {
        throw new Error(generateResponse.error || 'PDF generation failed')
      }
      
      console.log(`✅ PDF generated successfully: ${generateResponse.pdf_path}`)
      
      // Download the generated file
      const downloadUrl = `/api/resume/download/${resumeId}`
      const downloadResponse = await fetch(downloadUrl)
      
      if (!downloadResponse.ok) {
        throw new Error(`Download failed: ${downloadResponse.status}`)
      }
      
      // Check if it's HTML or PDF
      const contentType = downloadResponse.headers.get('content-type')
      const isHtml = contentType && contentType.includes('text/html')
      
      if (isHtml) {
        // Handle HTML file - open for printing
        console.log('📄 HTML file detected - opening for PDF printing')
        return await this.enhanceHTMLForPrinting(resumeId, clientName, downloadResponse)
      } else {
        // Handle actual PDF file
        const blob = await downloadResponse.blob()
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${clientName.replace(/[^a-zA-Z0-9]/g, '_')}_Resume.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        console.log(`📥 PDF download initiated for: ${link.download}`)
        return true
      }
      
    } catch (error) {
      console.error('❌ PDF generation/download failed:', error)
      throw error
    }
  }

  /**
   * Enhanced HTML handling for PDF printing
   * @param {string} resumeId - Resume ID
   * @param {string} clientName - Client name
   * @param {Response} response - Fetch response with HTML content
   * @returns {Promise<boolean>} Success status
   */
  static async enhanceHTMLForPrinting(resumeId, clientName, response) {
    try {
      const htmlContent = await response.text()
      
      // Enhanced HTML with print styles and instructions
      const enhancedHTML = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>${clientName} - Professional Resume</title>
    <style>
        /* Print-optimized styles */
        @media print {
            body { margin: 0; padding: 0; }
            .no-print { display: none !important; }
            .print-instructions { display: none !important; }
        }
        
        @media screen {
            .print-instructions {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #2563eb;
                color: white;
                padding: 15px;
                text-align: center;
                font-family: Arial, sans-serif;
                z-index: 1000;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .print-instructions button {
                background: white;
                color: #2563eb;
                border: none;
                padding: 8px 16px;
                margin: 0 5px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: bold;
            }
            .print-instructions button:hover {
                background: #f1f5f9;
            }
            body { margin-top: 80px; }
        }
    </style>
</head>
<body>
    <div class="print-instructions no-print">
        <div>
            <strong>📄 Ready to Save as PDF!</strong> 
            <button onclick="window.print()">🖨️ Print/Save as PDF</button>
            <button onclick="window.close()">❌ Close</button>
        </div>
        <div style="font-size: 14px; margin-top: 5px;">
            Instructions: Click "Print/Save as PDF" → Choose "Save as PDF" → Click Save
        </div>
    </div>
    ${htmlContent}
    <script>
        // Auto-focus for immediate printing
        window.addEventListener('load', function() {
            // Show instructions for 3 seconds, then auto-print dialog
            setTimeout(function() {
                if (confirm('Ready to save as PDF?\\n\\nClick OK to open print dialog, or Cancel to review first.')) {
                    window.print();
                }
            }, 1500);
        });
        
        // Handle print dialog
        window.addEventListener('beforeprint', function() {
            console.log('🖨️ Opening print dialog for PDF save');
        });
        
        window.addEventListener('afterprint', function() {
            console.log('✅ Print dialog completed');
        });
    </script>
</body>
</html>`
      
      // Open in new window
      const newWindow = window.open('', '_blank', 'width=800,height=1000,scrollbars=yes')
      if (newWindow) {
        newWindow.document.write(enhancedHTML)
        newWindow.document.close()
        
        // Focus the new window
        newWindow.focus()
        
        console.log('✅ Enhanced HTML opened for PDF printing')
        return true
      } else {
        throw new Error('Popup blocked - please allow popups for PDF generation')
      }
      
    } catch (error) {
      console.error('❌ HTML enhancement failed:', error)
      
      // Fallback: direct download of HTML file
      const blob = new Blob([await response.text()], { type: 'text/html' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${clientName.replace(/[^a-zA-Z0-9]/g, '_')}_Resume.html`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      alert('PDF service generated an HTML file.\\n\\nTo convert to PDF:\\n1. Open the downloaded HTML file\\n2. Press Ctrl+P (or Cmd+P on Mac)\\n3. Choose "Save as PDF"\\n4. Click Save')
      
      return true
    }
  }

  /**
   * Debug method to test all endpoints
   */
  static async debugEndpoints() {
    console.log('🔍 Starting endpoint debugging...')
    
    const results = {
      health: null,
      clients: null,
      timestamp: new Date().toISOString()
    }
    
    // Test health endpoint
    try {
      results.health = await this.healthCheck()
      console.log('✅ Health check passed')
    } catch (error) {
      results.health = { error: error.message }
      console.error('❌ Health check failed')
    }
    
    // Test clients endpoint
    try {
      results.clients = await this.getClients()
      console.log('✅ Clients endpoint passed')
    } catch (error) {
      results.clients = { error: error.message }
      console.error('❌ Clients endpoint failed')
    }
    
    console.log('🔍 Debug results:', results)
    return results
  }
  
  /**
   * Initialize service with health check
   */
  static async initialize() {
    console.log('🚀 Initializing PDF Service...')
    
    try {
      const health = await this.healthCheck()
      
      if (health.status === 'healthy') {
        console.log('✅ PDF Service initialized successfully')
        return true
      } else {
        console.warn('⚠️  PDF Service is degraded:', health)
        return false
      }
    } catch (error) {
      console.error('❌ PDF Service initialization failed:', error)
      return false
    }
  }
}

// Auto-initialize in development
if (process.env.NODE_ENV === 'development') {
  PDFService.initialize().then(success => {
    if (success) {
      console.log('🎉 PDF Service ready for development')
    } else {
      console.warn('⚠️  PDF Service may not be fully functional')
    }
  })
}

export default PDFService
