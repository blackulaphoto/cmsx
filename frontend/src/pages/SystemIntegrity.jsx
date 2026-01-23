import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, Database, RefreshCw, Server, Shield, Wrench, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '../api/config'

function SystemIntegrity() {
  const [loading, setLoading] = useState(true)
  const [checking, setChecking] = useState(false)
  const [repairing, setRepairing] = useState(false)
  const [integrityStatus, setIntegrityStatus] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetchIntegrityStatus()
  }, [])

  const fetchIntegrityStatus = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE_URL}/api/system/integrity/status`)
      
      if (response.ok) {
        const data = await response.json()
        setIntegrityStatus(data.data)
        fetchRecommendations()
      } else {
        toast.error('Failed to fetch integrity status')
      }
    } catch (error) {
      console.error('Error fetching integrity status:', error)
      toast.error('Error fetching integrity status')
    } finally {
      setLoading(false)
    }
  }

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/system/integrity/recommendations`)
      
      if (response.ok) {
        const data = await response.json()
        setRecommendations(data.recommendations || [])
      } else {
        toast.error('Failed to fetch recommendations')
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error)
    }
  }

  const runIntegrityCheck = async () => {
    try {
      setChecking(true)
      toast.loading('Running integrity check...')
      
      const response = await fetch(`${API_BASE_URL}/api/system/integrity/check`, {
        method: 'POST'
      })
      
      if (response.ok) {
        toast.dismiss()
        toast.success('Integrity check started')
        
        // Poll for results
        const pollInterval = setInterval(async () => {
          const statusResponse = await fetch(`${API_BASE_URL}/api/system/integrity/status`)
          if (statusResponse.ok) {
            const data = await statusResponse.json()
            if (data.last_check && (!integrityStatus || data.last_check !== integrityStatus.timestamp)) {
              clearInterval(pollInterval)
              setIntegrityStatus(data.data)
              fetchRecommendations()
              toast.success('Integrity check completed')
              setChecking(false)
            }
          }
        }, 2000)
        
        // Stop polling after 30 seconds
        setTimeout(() => {
          clearInterval(pollInterval)
          if (checking) {
            setChecking(false)
            fetchIntegrityStatus()
            toast.success('Integrity check completed')
          }
        }, 30000)
      } else {
        toast.dismiss()
        toast.error('Failed to start integrity check')
        setChecking(false)
      }
    } catch (error) {
      console.error('Error running integrity check:', error)
      toast.dismiss()
      toast.error('Error running integrity check')
      setChecking(false)
    }
  }

  const repairSynchronization = async () => {
    try {
      setRepairing(true)
      toast.loading('Repairing client synchronization...')
      
      const response = await fetch(`${API_BASE_URL}/api/system/integrity/repair/sync`, {
        method: 'POST'
      })
      
      if (response.ok) {
        toast.dismiss()
        toast.success('Repair started')
        
        // Wait a bit and then refresh
        setTimeout(() => {
          fetchIntegrityStatus()
          setRepairing(false)
          toast.success('Repair completed')
        }, 5000)
      } else {
        toast.dismiss()
        toast.error('Failed to start repair')
        setRepairing(false)
      }
    } catch (error) {
      console.error('Error repairing synchronization:', error)
      toast.dismiss()
      toast.error('Error repairing synchronization')
      setRepairing(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ok':
        return <CheckCircle className="h-6 w-6 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />
      case 'error':
        return <XCircle className="h-6 w-6 text-red-500" />
      default:
        return <Database className="h-6 w-6 text-gray-500" />
    }
  }

  const renderOverview = () => {
    if (!integrityStatus) return null

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">System Integrity Status</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(integrityStatus.status)}
              <span className="capitalize font-medium">
                {integrityStatus.status === 'ok' ? 'Healthy' : integrityStatus.status}
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Databases</h4>
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold">
                  {Object.values(integrityStatus.databases).filter(Boolean).length} / {Object.keys(integrityStatus.databases).length}
                </span>
                {Object.values(integrityStatus.databases).every(Boolean) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                )}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Tables</h4>
              <div className="flex items-center justify-between">
                <span className="text-2xl font-bold">
                  {Object.values(integrityStatus.tables).reduce((acc, tables) => 
                    acc + Object.values(tables).filter(Boolean).length, 0)} / 
                  {Object.values(integrityStatus.tables).reduce((acc, tables) => 
                    acc + Object.keys(tables).length, 0)}
                </span>
                {Object.values(integrityStatus.tables).every(tables => 
                  Object.values(tables).every(Boolean)
                ) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                )}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Synchronization</h4>
              <div className="flex items-center justify-between">
                <span className="capitalize text-2xl font-bold">
                  {integrityStatus.synchronization.status}
                </span>
                {getStatusIcon(integrityStatus.synchronization.status)}
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-1">Permissions</h4>
              <div className="flex items-center justify-between">
                <span className="capitalize text-2xl font-bold">
                  {integrityStatus.permissions.status}
                </span>
                {getStatusIcon(integrityStatus.permissions.status)}
              </div>
            </div>
          </div>
        </div>
        
        {recommendations.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium mb-4">Recommended Actions</h3>
            <div className="space-y-4">
              {recommendations.map((rec, index) => (
                <div key={index} className="flex items-start p-4 border border-gray-200 rounded-lg">
                  <div className="mr-4 mt-1">
                    {rec.severity === 'critical' && <XCircle className="h-5 w-5 text-red-500" />}
                    {rec.severity === 'high' && <AlertTriangle className="h-5 w-5 text-orange-500" />}
                    {rec.severity === 'medium' && <AlertTriangle className="h-5 w-5 text-yellow-500" />}
                    {rec.severity === 'low' && <AlertTriangle className="h-5 w-5 text-blue-500" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">{rec.action}</h4>
                      <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 capitalize">
                        {rec.severity}
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm mt-1">{rec.issue}</p>
                    {rec.repair_method !== 'manual' && (
                      <button
                        className="mt-2 px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
                        onClick={() => {
                          if (rec.repair_method === 'repair_client_synchronization') {
                            repairSynchronization()
                          }
                        }}
                        disabled={repairing}
                      >
                        {repairing ? 'Repairing...' : 'Repair Now'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderDatabases = () => {
    if (!integrityStatus) return null

    return (
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium">Database Status</h3>
          <p className="text-gray-500 text-sm mt-1">
            Status of all 9 databases in the architecture
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Database
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tables
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Clients
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sync Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Object.entries(integrityStatus.databases).map(([dbName, exists]) => {
                const tableStatus = integrityStatus.tables[dbName] || {}
                const syncStatus = integrityStatus.synchronization.databases[dbName] || {}
                
                return (
                  <tr key={dbName}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Database className="h-5 w-5 text-gray-400 mr-2" />
                        <span className="font-medium">{dbName}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {exists ? (
                          <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500 mr-2" />
                        )}
                        <span>{exists ? 'Available' : 'Missing'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {tableStatus && Object.keys(tableStatus).length > 0 ? (
                        <span>
                          {Object.values(tableStatus).filter(Boolean).length} / {Object.keys(tableStatus).length}
                        </span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {syncStatus && syncStatus.client_count !== undefined ? (
                        <span>{syncStatus.client_count}</span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {syncStatus && syncStatus.status ? (
                        <div className="flex items-center">
                          {getStatusIcon(syncStatus.status)}
                          <span className="ml-2 capitalize">{syncStatus.status}</span>
                        </div>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  const renderSynchronization = () => {
    if (!integrityStatus) return null
    const syncStatus = integrityStatus.synchronization

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Client Synchronization Status</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(syncStatus.status)}
              <span className="capitalize font-medium">
                {syncStatus.status}
              </span>
            </div>
          </div>
          
          <p className="text-gray-600 mb-4">
            Client data should be synchronized across all databases. Core clients is the master database.
          </p>
          
          {syncStatus.issues && syncStatus.issues.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-red-600 mb-2">Synchronization Issues</h4>
              <ul className="list-disc pl-5 space-y-1">
                {syncStatus.issues.map((issue, index) => (
                  <li key={index} className="text-gray-600">{issue}</li>
                ))}
              </ul>
            </div>
          )}
          
          <button
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={repairSynchronization}
            disabled={repairing || syncStatus.status === 'ok'}
          >
            {repairing ? (
              <span className="flex items-center">
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Repairing...
              </span>
            ) : (
              'Repair Synchronization'
            )}
          </button>
        </div>
        
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium">Database Client Counts</h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Database
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Client Count
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Missing Clients
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Extra Clients
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(syncStatus.databases).map(([dbName, status]) => (
                  <tr key={dbName}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <Database className="h-5 w-5 text-gray-400 mr-2" />
                        <span className="font-medium">{dbName}</span>
                        {dbName === 'core_clients' && (
                          <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                            MASTER
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {status.client_count !== undefined ? (
                        <span>{status.client_count}</span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {status.missing_count !== undefined ? (
                        <span className={status.missing_count > 0 ? 'text-red-600' : ''}>
                          {status.missing_count}
                        </span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {status.extra_count !== undefined ? (
                        <span className={status.extra_count > 0 ? 'text-yellow-600' : ''}>
                          {status.extra_count}
                        </span>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {getStatusIcon(status.status || 'unknown')}
                        <span className="ml-2 capitalize">{status.status || 'unknown'}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  const renderPermissions = () => {
    if (!integrityStatus) return null
    const permStatus = integrityStatus.permissions

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Database Access Permissions</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(permStatus.status)}
              <span className="capitalize font-medium">
                {permStatus.status}
              </span>
            </div>
          </div>
          
          <p className="text-gray-600 mb-4">
            The Case Management module has ADMIN access to core_clients.db, while other modules have READ_ONLY access.
            The AI Assistant has FULL CRUD access to all databases.
          </p>
          
          {permStatus.issues && permStatus.issues.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-red-600 mb-2">Permission Issues</h4>
              <ul className="list-disc pl-5 space-y-1">
                {permStatus.issues.map((issue, index) => (
                  <li key={index} className="text-gray-600">{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium">Permission Test Results</h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Module
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Database
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Permission
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Expected
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actual
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {permStatus.tests.map((test, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium">{test.module}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {test.database}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="capitalize">{test.permission}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {test.expected ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {test.actual ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {test.passed ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Passed
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Integrity</h1>
          <p className="text-gray-600 mt-1">
            Monitor and maintain database integrity across the 9-database architecture
          </p>
        </div>
        
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={runIntegrityCheck}
          disabled={checking}
        >
          {checking ? (
            <>
              <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
              Checking...
            </>
          ) : (
            <>
              <RefreshCw className="h-5 w-5 mr-2" />
              Run Integrity Check
            </>
          )}
        </button>
      </div>
      
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          <div className="mb-6 border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                className={`mr-8 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'overview'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('overview')}
              >
                Overview
              </button>
              <button
                className={`mr-8 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'databases'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('databases')}
              >
                Databases
              </button>
              <button
                className={`mr-8 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'sync'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('sync')}
              >
                Synchronization
              </button>
              <button
                className={`mr-8 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'permissions'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab('permissions')}
              >
                Permissions
              </button>
            </nav>
          </div>
          
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'databases' && renderDatabases()}
          {activeTab === 'sync' && renderSynchronization()}
          {activeTab === 'permissions' && renderPermissions()}
        </>
      )}
    </div>
  )
}

export default SystemIntegrity