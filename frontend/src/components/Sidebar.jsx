import { 
  Users, 
  Home, 
  MessageSquare, 
  Calendar, 
  FileText, 
  Scale, 
  Heart, 
  Briefcase,
  Search,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Database
} from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

function Sidebar() {
  const location = useLocation()

  const menuItems = [
    { icon: Users, label: 'Case Management', path: '/' },
    { icon: Home, label: 'Housing Search', path: '/housing' },
    { icon: Search, label: 'Job Search', path: '/jobs' },
    { icon: MessageSquare, label: 'AI Chat Assistant', path: '/ai-chat' },
    { icon: Calendar, label: 'Smart Daily Dashboard', path: '/smart-daily' },
    { icon: FileText, label: 'Resume Builder', path: '/resume' },
    { icon: Scale, label: 'Legal Services', path: '/legal' },
    { icon: Heart, label: 'Benefits & Support', path: '/benefits' },
    { icon: Briefcase, label: 'Services Directory', path: '/services' },
    { icon: Database, label: 'System Integrity', path: '/system-integrity' },
  ]

  const quickStats = [
    { label: 'Active Cases', value: '24', icon: TrendingUp },
    { label: 'Pending Tasks', value: '12', icon: Clock },
    { label: 'Completed', value: '156', icon: CheckCircle },
    { label: 'Urgent', value: '3', icon: AlertCircle },
  ]

  return (
    <aside className="bg-white rounded-2xl p-6 shadow-custom-sm h-fit sticky top-32">
      {/* Navigation Menu */}
      <div className="mb-8">
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-4">
          Navigation
        </h3>
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-gray-700 font-medium transition-all duration-300 hover:bg-primary-gradient hover:text-white hover:translate-x-1 ${
                    isActive ? 'bg-primary-gradient text-white translate-x-1' : ''
                  }`}
                >
                  <Icon size={20} />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </div>

      {/* Quick Stats */}
      <div className="bg-primary-gradient text-white p-6 rounded-xl">
        <h3 className="text-sm font-bold mb-4">Quick Stats</h3>
        <div className="space-y-3">
          {quickStats.map((stat) => {
            const Icon = stat.icon
            return (
              <div key={stat.label} className="flex justify-between items-center">
                <span className="text-sm opacity-90">{stat.label}</span>
                <div className="flex items-center gap-2">
                  <Icon size={16} />
                  <span className="font-bold text-lg">{stat.value}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar 