import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import integrationTest from '../utils/integrationTest';
import IntegrationTestPanel from '../components/IntegrationTestPanel';

const IntegrationAudit = () => {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(false);

  // Start monitoring when the component mounts
  useEffect(() => {
    integrationTest.startMonitoring();
    setIsMonitoring(true);

    // Clean up when the component unmounts
    return () => {
      integrationTest.stopMonitoring();
    };
  }, []);

  // Run a comprehensive test of all pages
  const runComprehensiveTest = async () => {
    setIsLoading(true);
    integrationTest.clearData();

    // Define all the routes to test
    const routes = [
      { path: '/', name: 'Dashboard' },
      { path: '/case-management', name: 'Case Management' },
      { path: '/housing', name: 'Housing' },
      { path: '/benefits', name: 'Benefits' },
      { path: '/legal', name: 'Legal' },
      { path: '/resume', name: 'Resume' },
      { path: '/jobs', name: 'Jobs' },
      { path: '/services', name: 'Services' },
      { path: '/ai-chat', name: 'AI Assistant' },
      { path: '/smart-dashboard', name: 'Smart Daily' },
    ];

    // Create an iframe to load each route
    const iframe = document.createElement('iframe');
    iframe.style.width = '1200px';
    iframe.style.height = '800px';
    iframe.style.position = 'absolute';
    iframe.style.left = '-9999px';
    document.body.appendChild(iframe);

    // Test each route
    for (const route of routes) {
      try {
        // Update status
        setTestResults(prev => ({
          ...prev,
          currentTest: route.name,
          progress: routes.indexOf(route) / routes.length * 100
        }));

        // Load the route in the iframe
        const url = `${window.location.origin}${route.path}`;
        await new Promise((resolve, reject) => {
          iframe.onload = resolve;
          iframe.onerror = reject;
          iframe.src = url;

          // Set a timeout to resolve after 5 seconds in case the page hangs
          setTimeout(resolve, 5000);
        });

        // Wait a bit for any async operations to complete
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (error) {
        console.error(`Error testing ${route.name}:`, error);
      }
    }

    // Clean up
    document.body.removeChild(iframe);
    
    // Get the test results
    const summary = integrationTest.getSummary();
    setTestResults({
      timestamp: new Date().toISOString(),
      summary,
      routes,
      currentTest: 'Complete',
      progress: 100
    });
    
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent">
            Frontend Integration Audit
          </h1>
          <p className="text-gray-300 mt-2">
            Test and verify frontend integration with backend services
          </p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10 mb-6">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'dashboard'
                ? 'text-white border-b-2 border-purple-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('comprehensive')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'comprehensive'
                ? 'text-white border-b-2 border-purple-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Comprehensive Test
          </button>
          <button
            onClick={() => setActiveTab('manual')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'manual'
                ? 'text-white border-b-2 border-purple-500'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Manual Testing
          </button>
        </div>

        {/* Content */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-white/10 p-6 shadow-xl">
          {activeTab === 'dashboard' && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                {/* Monitoring Status */}
                <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4">
                  <h3 className="text-lg font-medium mb-4">Monitoring Status</h3>
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-4 h-4 rounded-full ${isMonitoring ? 'bg-green-500' : 'bg-gray-500'}`}></div>
                    <span className="text-gray-300">
                      {isMonitoring ? 'Monitoring Active' : 'Monitoring Inactive'}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {isMonitoring ? (
                      <button
                        onClick={() => {
                          integrationTest.stopMonitoring();
                          setIsMonitoring(false);
                        }}
                        className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
                      >
                        Stop Monitoring
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          integrationTest.startMonitoring();
                          setIsMonitoring(true);
                        }}
                        className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
                      >
                        Start Monitoring
                      </button>
                    )}
                    <button
                      onClick={() => integrationTest.clearData()}
                      className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
                    >
                      Clear Data
                    </button>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4">
                  <h3 className="text-lg font-medium mb-4">Quick Actions</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => runComprehensiveTest()}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <>
                          <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Running...
                        </>
                      ) : (
                        'Run Comprehensive Test'
                      )}
                    </button>
                    <button
                      onClick={() => integrationTest.exportData()}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg transition-colors"
                    >
                      Export Results
                    </button>
                    <Link
                      to="/"
                      className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-3 rounded-lg transition-colors flex items-center justify-center"
                    >
                      Go to Dashboard
                    </Link>
                    <Link
                      to="/case-management"
                      className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-3 rounded-lg transition-colors flex items-center justify-center"
                    >
                      Go to Case Management
                    </Link>
                  </div>
                </div>
              </div>

              {/* Test Results */}
              {testResults && (
                <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4 mt-6">
                  <h3 className="text-lg font-medium mb-4">Test Results</h3>
                  
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-400 mb-1">
                      <span>Progress</span>
                      <span>{Math.round(testResults.progress)}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2.5">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2.5 rounded-full" 
                        style={{ width: `${testResults.progress}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <h4 className="text-gray-400 text-sm mb-2">Summary</h4>
                      <div className="bg-slate-800 p-3 rounded border border-white/5">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="text-gray-400">Total Errors:</div>
                          <div className={testResults.summary.statistics.totalErrors > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.totalErrors}
                          </div>
                          
                          <div className="text-gray-400">Failed API Calls:</div>
                          <div className={testResults.summary.statistics.failedApiCalls > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.failedApiCalls}
                          </div>
                          
                          <div className="text-gray-400">Component Crashes:</div>
                          <div className={testResults.summary.statistics.totalComponentCrashes > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.totalComponentCrashes}
                          </div>
                          
                          <div className="text-gray-400">Total API Calls:</div>
                          <div className="text-white">
                            {testResults.summary.statistics.totalApiCalls}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-gray-400 text-sm mb-2">Status</h4>
                      <div className="bg-slate-800 p-3 rounded border border-white/5">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="text-gray-400">Current Test:</div>
                          <div className="text-white">
                            {testResults.currentTest}
                          </div>
                          
                          <div className="text-gray-400">Timestamp:</div>
                          <div className="text-white">
                            {new Date(testResults.timestamp).toLocaleTimeString()}
                          </div>
                          
                          <div className="text-gray-400">Overall Status:</div>
                          <div className={
                            testResults.summary.statistics.failedApiCalls > 0 || 
                            testResults.summary.statistics.totalErrors > 0 || 
                            testResults.summary.statistics.totalComponentCrashes > 0 
                              ? 'text-red-400' 
                              : 'text-green-400'
                          }>
                            {testResults.summary.statistics.failedApiCalls > 0 || 
                             testResults.summary.statistics.totalErrors > 0 || 
                             testResults.summary.statistics.totalComponentCrashes > 0 
                              ? 'Issues Detected' 
                              : 'All Tests Passed'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Failed API Calls */}
                  {testResults.summary.apiCalls.filter(call => !call.success).length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-red-400 text-sm mb-2">Failed API Calls</h4>
                      <div className="bg-red-900/30 border border-red-500/30 rounded p-3 max-h-60 overflow-y-auto">
                        {testResults.summary.apiCalls.filter(call => !call.success).map((call, index) => (
                          <div key={index} className="mb-2 pb-2 border-b border-red-500/20 last:border-0 last:mb-0 last:pb-0">
                            <div className="flex justify-between text-sm">
                              <span className="text-red-400 font-medium">{call.method} {call.status && `(${call.status})`}</span>
                              <span className="text-gray-400">{new Date(call.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <div className="text-gray-300 text-xs break-all">{call.url}</div>
                            {call.error && <div className="text-red-300 text-xs mt-1">Error: {call.error}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Console Errors */}
                  {testResults.summary.errors.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-red-400 text-sm mb-2">Console Errors</h4>
                      <div className="bg-red-900/30 border border-red-500/30 rounded p-3 max-h-60 overflow-y-auto">
                        {testResults.summary.errors.map((error, index) => (
                          <div key={index} className="mb-2 pb-2 border-b border-red-500/20 last:border-0 last:mb-0 last:pb-0">
                            <div className="text-gray-400 text-xs">{new Date(error.timestamp).toLocaleTimeString()}</div>
                            <div className="text-red-300 text-sm break-all">{error.message}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'comprehensive' && (
            <div>
              <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4 mb-6">
                <h3 className="text-lg font-medium mb-4">Comprehensive Test</h3>
                <p className="text-gray-300 mb-4">
                  This test will automatically navigate through all pages in the application and collect data on errors, API calls, and component crashes.
                </p>
                <button
                  onClick={runComprehensiveTest}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg transition-colors flex items-center gap-2"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Running Comprehensive Test...
                    </>
                  ) : (
                    'Start Comprehensive Test'
                  )}
                </button>
              </div>

              {/* Test Progress */}
              {isLoading && (
                <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4 mb-6">
                  <h3 className="text-lg font-medium mb-4">Test Progress</h3>
                  <div className="mb-4">
                    <div className="flex justify-between text-sm text-gray-400 mb-1">
                      <span>Testing: {testResults?.currentTest || 'Initializing...'}</span>
                      <span>{testResults ? Math.round(testResults.progress) : 0}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2.5">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2.5 rounded-full" 
                        style={{ width: `${testResults ? testResults.progress : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Test Results (same as in dashboard tab) */}
              {testResults && !isLoading && (
                <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4">
                  <h3 className="text-lg font-medium mb-4">Test Results</h3>
                  
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <h4 className="text-gray-400 text-sm mb-2">Summary</h4>
                      <div className="bg-slate-800 p-3 rounded border border-white/5">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="text-gray-400">Total Errors:</div>
                          <div className={testResults.summary.statistics.totalErrors > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.totalErrors}
                          </div>
                          
                          <div className="text-gray-400">Failed API Calls:</div>
                          <div className={testResults.summary.statistics.failedApiCalls > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.failedApiCalls}
                          </div>
                          
                          <div className="text-gray-400">Component Crashes:</div>
                          <div className={testResults.summary.statistics.totalComponentCrashes > 0 ? 'text-red-400' : 'text-green-400'}>
                            {testResults.summary.statistics.totalComponentCrashes}
                          </div>
                          
                          <div className="text-gray-400">Total API Calls:</div>
                          <div className="text-white">
                            {testResults.summary.statistics.totalApiCalls}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-gray-400 text-sm mb-2">Status</h4>
                      <div className="bg-slate-800 p-3 rounded border border-white/5">
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div className="text-gray-400">Timestamp:</div>
                          <div className="text-white">
                            {new Date(testResults.timestamp).toLocaleTimeString()}
                          </div>
                          
                          <div className="text-gray-400">Overall Status:</div>
                          <div className={
                            testResults.summary.statistics.failedApiCalls > 0 || 
                            testResults.summary.statistics.totalErrors > 0 || 
                            testResults.summary.statistics.totalComponentCrashes > 0 
                              ? 'text-red-400' 
                              : 'text-green-400'
                          }>
                            {testResults.summary.statistics.failedApiCalls > 0 || 
                             testResults.summary.statistics.totalErrors > 0 || 
                             testResults.summary.statistics.totalComponentCrashes > 0 
                              ? 'Issues Detected' 
                              : 'All Tests Passed'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Failed API Calls */}
                  {testResults.summary.apiCalls.filter(call => !call.success).length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-red-400 text-sm mb-2">Failed API Calls</h4>
                      <div className="bg-red-900/30 border border-red-500/30 rounded p-3 max-h-60 overflow-y-auto">
                        {testResults.summary.apiCalls.filter(call => !call.success).map((call, index) => (
                          <div key={index} className="mb-2 pb-2 border-b border-red-500/20 last:border-0 last:mb-0 last:pb-0">
                            <div className="flex justify-between text-sm">
                              <span className="text-red-400 font-medium">{call.method} {call.status && `(${call.status})`}</span>
                              <span className="text-gray-400">{new Date(call.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <div className="text-gray-300 text-xs break-all">{call.url}</div>
                            {call.error && <div className="text-red-300 text-xs mt-1">Error: {call.error}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Console Errors */}
                  {testResults.summary.errors.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-red-400 text-sm mb-2">Console Errors</h4>
                      <div className="bg-red-900/30 border border-red-500/30 rounded p-3 max-h-60 overflow-y-auto">
                        {testResults.summary.errors.map((error, index) => (
                          <div key={index} className="mb-2 pb-2 border-b border-red-500/20 last:border-0 last:mb-0 last:pb-0">
                            <div className="text-gray-400 text-xs">{new Date(error.timestamp).toLocaleTimeString()}</div>
                            <div className="text-red-300 text-sm break-all">{error.message}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'manual' && (
            <div>
              <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4 mb-6">
                <h3 className="text-lg font-medium mb-4">Manual Testing</h3>
                <p className="text-gray-300 mb-4">
                  Navigate through the application manually to test specific features and interactions. The integration test panel will track errors, API calls, and component crashes.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                  {[
                    { path: '/', name: 'Dashboard' },
                    { path: '/case-management', name: 'Case Management' },
                    { path: '/housing', name: 'Housing' },
                    { path: '/benefits', name: 'Benefits' },
                    { path: '/legal', name: 'Legal' },
                    { path: '/resume', name: 'Resume' },
                    { path: '/jobs', name: 'Jobs' },
                    { path: '/services', name: 'Services' },
                    { path: '/ai-chat', name: 'AI Assistant' },
                    { path: '/smart-dashboard', name: 'Smart Daily' },
                  ].map((route) => (
                    <Link
                      key={route.path}
                      to={route.path}
                      className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-3 rounded-lg transition-colors text-center"
                    >
                      {route.name}
                    </Link>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900/80 rounded-lg border border-purple-500/20 p-4">
                <h3 className="text-lg font-medium mb-4">Testing Instructions</h3>
                <ol className="list-decimal list-inside space-y-2 text-gray-300">
                  <li>Click on any of the links above to navigate to that page</li>
                  <li>Interact with the page components and features</li>
                  <li>Check the Integration Test Panel for any errors or failed API calls</li>
                  <li>Return to this page to continue testing other pages</li>
                  <li>When finished, export the results using the "Export Results" button</li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Integration Test Panel */}
      <IntegrationTestPanel />
    </div>
  );
};

export default IntegrationAudit;