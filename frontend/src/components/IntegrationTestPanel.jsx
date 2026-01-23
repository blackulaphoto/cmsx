import React, { useState, useEffect } from 'react';
import integrationTest from '../utils/integrationTest';

const IntegrationTestPanel = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [summary, setSummary] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  useEffect(() => {
    // Update the summary every second when monitoring is active
    let interval;
    if (isMonitoring) {
      interval = setInterval(() => {
        setSummary(integrationTest.getSummary());
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isMonitoring]);

  const handleStartMonitoring = () => {
    integrationTest.startMonitoring();
    setIsMonitoring(true);
  };

  const handleStopMonitoring = () => {
    integrationTest.stopMonitoring();
    setIsMonitoring(false);
    setSummary(integrationTest.getSummary());
  };

  const handleClearData = () => {
    integrationTest.clearData();
    setSummary(integrationTest.getSummary());
  };

  const handleExportData = () => {
    integrationTest.exportData();
  };

  const handleTogglePanel = () => {
    setIsOpen(!isOpen);
    if (!isOpen && !summary) {
      setSummary(integrationTest.getSummary());
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Toggle Button */}
      <button
        onClick={handleTogglePanel}
        className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 flex items-center gap-2"
      >
        <span className="text-sm font-medium">
          {isOpen ? 'Hide Test Panel' : 'Integration Test'}
        </span>
        {!isOpen && summary && summary.statistics.failedApiCalls > 0 && (
          <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
            {summary.statistics.failedApiCalls}
          </span>
        )}
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="mt-2 bg-slate-900 border border-purple-500/30 rounded-lg shadow-2xl w-[600px] max-w-full overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-800 to-purple-900 px-4 py-3 flex justify-between items-center border-b border-purple-500/30">
            <h3 className="text-white font-medium">Frontend Integration Test</h3>
            <div className="flex gap-2">
              {isMonitoring ? (
                <button
                  onClick={handleStopMonitoring}
                  className="bg-red-500 hover:bg-red-600 text-white text-xs px-3 py-1 rounded"
                >
                  Stop Monitoring
                </button>
              ) : (
                <button
                  onClick={handleStartMonitoring}
                  className="bg-green-500 hover:bg-green-600 text-white text-xs px-3 py-1 rounded"
                >
                  Start Monitoring
                </button>
              )}
              <button
                onClick={handleClearData}
                className="bg-gray-600 hover:bg-gray-700 text-white text-xs px-3 py-1 rounded"
              >
                Clear Data
              </button>
              <button
                onClick={handleExportData}
                className="bg-blue-500 hover:bg-blue-600 text-white text-xs px-3 py-1 rounded"
              >
                Export
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-slate-800 px-4 border-b border-purple-500/30">
            <div className="flex">
              <button
                onClick={() => setActiveTab('summary')}
                className={`px-4 py-2 text-sm font-medium ${
                  activeTab === 'summary'
                    ? 'text-white border-b-2 border-purple-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setActiveTab('errors')}
                className={`px-4 py-2 text-sm font-medium flex items-center gap-1 ${
                  activeTab === 'errors'
                    ? 'text-white border-b-2 border-purple-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Errors
                {summary && summary.errors.length > 0 && (
                  <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {summary.errors.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('api')}
                className={`px-4 py-2 text-sm font-medium flex items-center gap-1 ${
                  activeTab === 'api'
                    ? 'text-white border-b-2 border-purple-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                API Calls
                {summary && summary.statistics.failedApiCalls > 0 && (
                  <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {summary.statistics.failedApiCalls}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('crashes')}
                className={`px-4 py-2 text-sm font-medium flex items-center gap-1 ${
                  activeTab === 'crashes'
                    ? 'text-white border-b-2 border-purple-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Crashes
                {summary && summary.componentCrashes.length > 0 && (
                  <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                    {summary.componentCrashes.length}
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-slate-900 p-4 max-h-[400px] overflow-y-auto text-sm">
            {!summary ? (
              <div className="text-gray-400 text-center py-8">
                Start monitoring to collect data
              </div>
            ) : (
              <>
                {activeTab === 'summary' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-800 p-4 rounded-lg border border-purple-500/20">
                      <h4 className="text-white font-medium mb-2">Statistics</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Total Errors:</span>
                          <span className={`font-medium ${summary.statistics.totalErrors > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {summary.statistics.totalErrors}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Total API Calls:</span>
                          <span className="text-white font-medium">
                            {summary.statistics.totalApiCalls}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Failed API Calls:</span>
                          <span className={`font-medium ${summary.statistics.failedApiCalls > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {summary.statistics.failedApiCalls}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Component Crashes:</span>
                          <span className={`font-medium ${summary.statistics.totalComponentCrashes > 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {summary.statistics.totalComponentCrashes}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="bg-slate-800 p-4 rounded-lg border border-purple-500/20">
                      <h4 className="text-white font-medium mb-2">Status</h4>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${isMonitoring ? 'bg-green-500' : 'bg-gray-500'}`}></div>
                          <span className="text-gray-400">Monitoring:</span>
                          <span className="text-white font-medium">
                            {isMonitoring ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${
                            summary.statistics.failedApiCalls > 0 || 
                            summary.statistics.totalErrors > 0 || 
                            summary.statistics.totalComponentCrashes > 0 
                              ? 'bg-red-500' 
                              : summary.statistics.totalApiCalls > 0 
                                ? 'bg-green-500' 
                                : 'bg-gray-500'
                          }`}></div>
                          <span className="text-gray-400">System Health:</span>
                          <span className="text-white font-medium">
                            {summary.statistics.failedApiCalls > 0 || 
                             summary.statistics.totalErrors > 0 || 
                             summary.statistics.totalComponentCrashes > 0 
                              ? 'Issues Detected' 
                              : summary.statistics.totalApiCalls > 0 
                                ? 'Healthy' 
                                : 'Unknown'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'errors' && (
                  <div>
                    {summary.errors.length === 0 ? (
                      <div className="text-gray-400 text-center py-8">
                        No errors detected
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {summary.errors.map((error, index) => (
                          <div key={index} className="bg-red-900/30 border border-red-500/30 p-3 rounded">
                            <div className="text-gray-400 text-xs mb-1">
                              {new Date(error.timestamp).toLocaleTimeString()}
                            </div>
                            <div className="text-red-300 break-all">
                              {error.message}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'api' && (
                  <div>
                    {summary.apiCalls.length === 0 ? (
                      <div className="text-gray-400 text-center py-8">
                        No API calls detected
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {summary.apiCalls.map((call, index) => (
                          <div 
                            key={index} 
                            className={`border p-3 rounded ${
                              call.success 
                                ? 'bg-green-900/20 border-green-500/30' 
                                : 'bg-red-900/30 border-red-500/30'
                            }`}
                          >
                            <div className="flex justify-between mb-1">
                              <span className={`font-medium ${call.success ? 'text-green-400' : 'text-red-400'}`}>
                                {call.method} {call.status && `(${call.status})`}
                              </span>
                              <span className="text-gray-400 text-xs">
                                {new Date(call.timestamp).toLocaleTimeString()} • {call.duration}ms
                              </span>
                            </div>
                            <div className="text-gray-300 break-all text-xs">
                              {call.url}
                            </div>
                            {call.error && (
                              <div className="text-red-300 text-xs mt-1">
                                Error: {call.error}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'crashes' && (
                  <div>
                    {summary.componentCrashes.length === 0 ? (
                      <div className="text-gray-400 text-center py-8">
                        No component crashes detected
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {summary.componentCrashes.map((crash, index) => (
                          <div key={index} className="bg-red-900/30 border border-red-500/30 p-3 rounded">
                            <div className="flex justify-between mb-1">
                              <span className="text-red-400 font-medium">
                                Component Crash
                              </span>
                              <span className="text-gray-400 text-xs">
                                {new Date(crash.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <div className="text-red-300">
                              {crash.message}
                            </div>
                            {crash.source && (
                              <div className="text-gray-400 text-xs mt-1">
                                {crash.source}:{crash.lineNumber}:{crash.columnNumber}
                              </div>
                            )}
                            {crash.stack && (
                              <div className="text-gray-400 text-xs mt-1 break-all">
                                {crash.stack}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default IntegrationTestPanel;