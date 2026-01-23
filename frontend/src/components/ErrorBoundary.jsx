import React from 'react'
import { AlertTriangle } from 'lucide-react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    })
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      // Use the component's theme if provided, otherwise use default
      const isDarkTheme = this.props.darkTheme || false
      
      return (
        <div className={`min-h-screen flex items-center justify-center ${isDarkTheme ? 'bg-gray-900' : 'bg-gray-50'}`}>
          <div className={`max-w-md w-full rounded-lg shadow-lg p-6 ${isDarkTheme ? 'bg-gray-800' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="h-8 w-8 text-red-500" />
              <h2 className={`text-xl font-semibold ${isDarkTheme ? 'text-white' : 'text-gray-900'}`}>
                Something went wrong
              </h2>
            </div>
            
            <div className="space-y-4">
              <p className={isDarkTheme ? 'text-gray-300' : 'text-gray-600'}>
                The application encountered an error. Please check the console for details.
              </p>
              
              {this.state.error && (
                <div className={`border rounded-lg p-4 ${isDarkTheme ? 'bg-red-900/30 border-red-800' : 'bg-red-50 border-red-200'}`}>
                  <h3 className={`font-medium mb-2 ${isDarkTheme ? 'text-red-400' : 'text-red-800'}`}>
                    Error Details:
                  </h3>
                  <p className={`text-sm font-mono ${isDarkTheme ? 'text-red-300' : 'text-red-700'}`}>
                    {this.state.error.toString()}
                  </p>
                </div>
              )}
              
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Reload Page
              </button>
              
              <button
                onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                className={`w-full py-2 px-4 rounded-lg transition-colors ${
                  isDarkTheme 
                    ? 'bg-gray-700 text-white hover:bg-gray-600' 
                    : 'bg-gray-600 text-white hover:bg-gray-700'
                }`}
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary