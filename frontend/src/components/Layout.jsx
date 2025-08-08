import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Users, 
  Home, 
  DollarSign, 
  Scale, 
  FileText, 
  MessageSquare,
  Building2,
  Calendar,
  Briefcase,
  User,
  Bell
} from 'lucide-react';

const Layout = ({ children }) => {
  const location = useLocation();

  const navigationItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/case-management', label: 'Case Management', icon: Users },
    { path: '/housing', label: 'Housing', icon: Home },
    { path: '/benefits', label: 'Benefits', icon: DollarSign },
    { path: '/legal', label: 'Legal', icon: Scale },
    { path: '/resume', label: 'Resume', icon: FileText },
    { path: '/jobs', label: 'Jobs', icon: Briefcase },
    { path: '/services', label: 'Services', icon: Building2 },
    { path: '/ai-chat', label: 'AI Assistant', icon: MessageSquare },
    { path: '/smart-dashboard', label: 'Smart Daily', icon: Calendar }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Users className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Case Management Suite</h1>
              </div>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navigationItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <IconComponent className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* User Menu */}
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Bell className="h-5 w-5 text-gray-600 cursor-pointer hover:text-gray-900" />
                <div className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-4 h-4 text-xs flex items-center justify-center font-semibold">
                  3
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <User className="h-4 w-4 text-blue-600" />
                </div>
                <div className="hidden sm:block">
                  <p className="text-sm font-medium text-gray-900">John Doe</p>
                  <p className="text-xs text-gray-500">Case Manager</p>
                </div>
              </div>
            </div>
          </div>

          {/* Mobile Navigation */}
          <div className="md:hidden border-t border-gray-200">
            <div className="flex overflow-x-auto py-2 space-x-1">
              {navigationItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <IconComponent className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {/* About */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Case Management Suite</h3>
              <p className="text-gray-300 text-sm">
                Comprehensive reentry services platform supporting formerly incarcerated individuals 
                with housing, employment, legal services, and benefits coordination.
              </p>
            </div>

            {/* Services */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Services</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><Link to="/housing" className="hover:text-white">Housing Search</Link></li>
                <li><Link to="/benefits" className="hover:text-white">Benefits Assistance</Link></li>
                <li><Link to="/legal" className="hover:text-white">Legal Services</Link></li>
                <li><Link to="/resume" className="hover:text-white">Resume Builder</Link></li>
                <li><Link to="/jobs" className="hover:text-white">Job Search</Link></li>
              </ul>
            </div>

            {/* Support */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><Link to="/ai-chat" className="hover:text-white">AI Assistant</Link></li>
                <li><Link to="/services" className="hover:text-white">Services Directory</Link></li>
                <li><Link to="/smart-dashboard" className="hover:text-white">Smart Dashboard</Link></li>
                <li><a href="#" className="hover:text-white">Help Center</a></li>
                <li><a href="#" className="hover:text-white">Contact Support</a></li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><a href="#" className="hover:text-white">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white">Terms of Service</a></li>
                <li><a href="#" className="hover:text-white">Data Security</a></li>
                <li><a href="#" className="hover:text-white">Compliance</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-700 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-300 text-sm">
              © 2024 Case Management Suite. All rights reserved.
            </p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a href="#" className="text-gray-300 hover:text-white text-sm">Accessibility</a>
              <a href="#" className="text-gray-300 hover:text-white text-sm">Security</a>
              <a href="#" className="text-gray-300 hover:text-white text-sm">Status</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;