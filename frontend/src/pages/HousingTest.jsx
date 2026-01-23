import { useState } from 'react'
import { Home, Search, Target, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

function HousingTest() {
  const [testResults, setTestResults] = useState({})
  const [testing, setTesting] = useState(false)

  const runTest = async (testName, testFunction) => {
    setTestResults(prev => ({ ...prev, [testName]: 'running' }))
    try {
      const result = await testFunction()
      setTestResults(prev => ({ ...prev, [testName]: result ? 'success' : 'failed' }))
      return result
    } catch (error) {
      console.error(`Test ${testName} failed:`, error)
      setTestResults(prev => ({ ...prev, [testName]: 'failed' }))
      return false
    }
  }

  const testBasicHousingSearch = async () => {
    const params = new URLSearchParams({
      query: 'apartment rental',
      location: 'Los Angeles, CA',
      page: '1',
      per_page: '5'
    })
    
    const response = await fetch(`http://localhost:8000/api/housing/search?${params}`)
    const data = await response.json()
    
    return data.success && data.housing_listings && data.housing_listings.length > 0
  }

  const testCaseManagerSearch = async () => {
    const params = new URLSearchParams({
      query: 'apartment rental',
      location: 'Los Angeles, CA',
      client_id: 'test_client',
      client_budget: '1500'
    })
    
    const response = await fetch(`http://localhost:8000/api/housing/case-manager-search?${params}`)
    const data = await response.json()
    
    return data.success && data.case_manager_view && data.results && data.results.length > 0
  }

  const testCaseManagerDashboard = async () => {
    const response = await fetch(`http://localhost:8000/api/housing/case-manager-dashboard`)
    const data = await response.json()
    
    return data.success && data.quick_searches && data.quick_searches.length > 0
  }

  const runAllTests = async () => {
    setTesting(true)
    setTestResults({})
    
    const tests = [
      { name: 'Basic Housing Search', func: testBasicHousingSearch },
      { name: 'Case Manager Search', func: testCaseManagerSearch },
      { name: 'Case Manager Dashboard', func: testCaseManagerDashboard }
    ]
    
    let allPassed = true
    for (const test of tests) {
      const result = await runTest(test.name, test.func)
      if (!result) allPassed = false
    }
    
    setTesting(false)
    
    if (allPassed) {
      toast.success('All housing API tests passed!')
    } else {
      toast.error('Some tests failed - check the results below')
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="text-green-500" size={20} />
      case 'failed':
        return <AlertCircle className="text-red-500" size={20} />
      case 'running':
        return <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
      default:
        return <div className="w-5 h-5 bg-gray-300 rounded-full"></div>
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="bg-primary-gradient text-white p-8">
        <div className="flex items-center gap-4 mb-2">
          <Home size={32} />
          <h1 className="text-3xl font-bold">Housing API Integration Test</h1>
        </div>
        <p className="text-lg opacity-90">Test all housing search endpoints and functionality</p>
      </div>

      <div className="p-8">
        {/* Test Controls */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">API Integration Tests</h2>
            <button
              onClick={runAllTests}
              disabled={testing}
              className="px-6 py-2 bg-primary-gradient text-white rounded-lg hover:shadow-custom-sm transition-all duration-300 disabled:opacity-50 flex items-center gap-2"
            >
              <Search size={16} />
              {testing ? 'Running Tests...' : 'Run All Tests'}
            </button>
          </div>
          
          {/* Test Results */}
          <div className="space-y-3">
            {[
              'Basic Housing Search',
              'Case Manager Search', 
              'Case Manager Dashboard'
            ].map((testName) => (
              <div key={testName} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                <span className="font-medium">{testName}</span>
                <div className="flex items-center gap-2">
                  {getStatusIcon(testResults[testName])}
                  <span className="text-sm text-gray-600 capitalize">
                    {testResults[testName] || 'Not run'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white rounded-xl shadow-custom-sm p-6">
          <h2 className="text-xl font-semibold mb-4">Quick Navigation</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a
              href="/housing"
              className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
            >
              <Home size={24} className="mx-auto mb-2 text-primary-600" />
              <div className="font-medium">Basic Housing Search</div>
              <div className="text-sm text-gray-600">Standard search interface</div>
            </a>
            
            <a
              href="/housing/case-manager"
              className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
            >
              <Target size={24} className="mx-auto mb-2 text-primary-600" />
              <div className="font-medium">Case Manager Tools</div>
              <div className="text-sm text-gray-600">Enhanced workflow features</div>
            </a>
            
            <div className="p-4 border border-gray-200 rounded-lg bg-gray-50 text-center">
              <CheckCircle size={24} className="mx-auto mb-2 text-green-600" />
              <div className="font-medium">API Tests</div>
              <div className="text-sm text-gray-600">Current page</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HousingTest