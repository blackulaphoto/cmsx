import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Users, 
  Home, 
  DollarSign, 
  Scale, 
  FileText, 
  MessageSquare,
  Building2,
  Calendar,
  TrendingUp,
  AlertCircle
} from 'lucide-react'

const Dashboard = () => {
  const [dashboardStats, setDashboardStats] = useState({
    total_clients: 0,
    active_clients: 0,
    high_risk_clients: 0,
    recent_intakes: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardStats()
  }, [])

  const fetchDashboardStats = async () => {
    try {
      const caseManagerId = 'cm_001' // This would come from auth context
      const response = await fetch(`/api/case-management/dashboard/${caseManagerId}`)
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          setDashboardStats(data.statistics)
        }
      }
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const moduleCards = [
    {
      title: 'Case Management',
      description: 'Manage client cases, track progress, and maintain case notes',
      path: '/case-management',
      icon: Users,
      color: 'bg-blue-500',
      stats: `${dashboardStats.active_clients} Active Cases`
    },
    {
      title: 'Housing Search',
      description: 'Find affordable housing options and transitional programs',
      path: '/housing',
      icon: Home,
      color: 'bg-green-500',
      stats: 'Search Available'
    },
    {
      title: 'Benefits Assistant',
      description: 'Apply for SNAP, SSDI, Medicaid, and other assistance programs',
      path: '/benefits',
      icon: DollarSign,
      color: 'bg-purple-500',
      stats: 'Multiple Programs'
    },
    {
      title: 'Legal Services',
      description: 'Expungement, court dates, and legal document assistance',
      path: '/legal',
      icon: Scale,
      color: 'bg-orange-500',
      stats: 'Legal Aid Available'
    },
    {
      title: 'Resume Builder',
      description: 'AI-powered resume creation tailored for second chance employment',
      path: '/resume',
      icon: FileText,
      color: 'bg-indigo-500',
      stats: 'ATS Optimized'
    },
    {
      title: 'AI Assistant',
      description: 'Get help with applications, advice, and case planning',
      path: '/ai-chat',
      icon: MessageSquare,
      color: 'bg-pink-500',
      stats: '24/7 Available'
    },
    {
      title: 'Services Directory',
      description: 'Comprehensive directory of local support services',
      path: '/services',
      icon: Building2,
      color: 'bg-teal-500',
      stats: 'Local Resources'
    },
    {
      title: 'Smart Daily Dashboard',
      description: 'Prioritized daily tasks and intelligent recommendations',
      path: '/smart-dashboard',
      icon: Calendar,
      color: 'bg-cyan-500',
      stats: 'AI Powered'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Case Management Suite</h1>
              <p className="text-gray-600 mt-1">Comprehensive reentry services platform</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Case Manager</p>
                <p className="font-semibold">John Doe</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Total Clients</p>
                <p className="text-2xl font-bold text-gray-900">
                  {loading ? '...' : dashboardStats.total_clients}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Active Cases</p>
                <p className="text-2xl font-bold text-gray-900">
                  {loading ? '...' : dashboardStats.active_clients}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-center">
              <div className="p-3 bg-red-100 rounded-lg">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">High Risk</p>
                <p className="text-2xl font-bold text-gray-900">
                  {loading ? '...' : dashboardStats.high_risk_clients}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border">
            <div className="flex items-center">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Calendar className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">Recent Intakes</p>
                <p className="text-2xl font-bold text-gray-900">
                  {loading ? '...' : dashboardStats.recent_intakes}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Modules Grid */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Available Services</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {moduleCards.map((module, index) => {
              const IconComponent = module.icon
              return (
                <Link
                  key={index}
                  to={module.path}
                  className="group bg-white p-6 rounded-xl shadow-sm border hover:shadow-lg transition-all duration-300 hover:scale-[1.02]"
                >
                  <div className="flex flex-col h-full">
                    <div className="flex items-center mb-4">
                      <div className={`p-3 ${module.color} rounded-lg`}>
                        <IconComponent className="h-6 w-6 text-white" />
                      </div>
                      <div className="ml-3 flex-1">
                        <h3 className="font-semibold text-gray-900 group-hover:text-gray-700">
                          {module.title}
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">{module.stats}</p>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 group-hover:text-gray-700 flex-grow">
                      {module.description}
                    </p>
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <span className="text-sm font-medium text-blue-600 group-hover:text-blue-700">
                        Access Module →
                      </span>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-12 bg-white p-6 rounded-xl shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-4">
            <Link
              to="/case-management"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Add New Client
            </Link>
            <Link
              to="/smart-dashboard"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              View Today's Tasks
            </Link>
            <Link
              to="/housing"
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              Search Housing
            </Link>
            <Link
              to="/resume"
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
            >
              Build Resume
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard