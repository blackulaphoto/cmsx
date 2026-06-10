import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Users,
  Home,
  DollarSign,
  Scale,
  FileText,
  ClipboardList,
  MessageSquare,
  Building2,
  Calendar,
  Briefcase,
  User,
  Bell,
  Flame,
  Sparkles,
  Heart,
  BarChart3,
  Stethoscope,
  Contact,
  ChevronDown,
  BookOpen,
  Brain,
  ClipboardCheck,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Layout = ({ children }) => {
  const location = useLocation();
  const { profile, logout } = useAuth();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const canAccessSupervisorMode = profile?.role === 'admin';
  const displayName = profile?.full_name || 'Signed in user'
  const displayRole = canAccessSupervisorMode ? 'Admin / Supervisor' : 'Case Manager'

  const navigationItems = [
    { path: '/', label: 'Dashboard', icon: Home, gradient: 'from-blue-500 to-cyan-500' },
    { path: '/case-management', label: 'Case Management', icon: Users, gradient: 'from-purple-500 to-indigo-500' },
    { path: '/admissions', label: 'Admissions', icon: ClipboardCheck, gradient: 'from-cyan-500 to-blue-600' },
    { path: '/documentation', label: 'Documentation', icon: ClipboardList, gradient: 'from-cyan-500 to-blue-500' },
    { path: '/housing', label: 'Housing', icon: Home, gradient: 'from-blue-500 to-cyan-500' },
    { path: '/sober-living', label: 'Sober Living', icon: Home, gradient: 'from-teal-500 to-emerald-500' },
    { path: '/groups', label: 'Groups', icon: BookOpen, gradient: 'from-teal-400 to-cyan-500' },
    { path: '/sober-living-directory', label: 'Sober Directory', icon: Building2, gradient: 'from-teal-500 to-cyan-500' },
    { path: '/benefits', label: 'Benefits', icon: Heart, gradient: 'from-pink-500 to-rose-500' },
    { path: '/medical', label: 'Medical', icon: Stethoscope, gradient: 'from-teal-500 to-cyan-500' },
    { path: '/rolodex', label: 'Rolodex', icon: Contact, gradient: 'from-cyan-500 to-sky-500' },
    { path: '/legal', label: 'Legal', icon: Scale, gradient: 'from-indigo-500 to-purple-500' },
    { path: '/fmla', label: 'FMLA', icon: ClipboardList, gradient: 'from-cyan-500 to-sky-500' },
    { path: '/ur', label: 'UR', icon: Bell, gradient: 'from-amber-500 to-orange-500' },
    { path: '/resume', label: 'Resume', icon: FileText, gradient: 'from-emerald-500 to-green-500' },
    { path: '/jobs', label: 'Jobs', icon: Briefcase, gradient: 'from-emerald-500 to-green-500' },
    { path: '/supervisor-dashboard', label: 'Supervisor', icon: BarChart3, gradient: 'from-cyan-500 to-blue-500' },
    { path: '/services', label: 'Services', icon: Building2, gradient: 'from-orange-500 to-amber-500' },
    { path: '/ai-chat', label: 'AI Assistant', icon: MessageSquare, gradient: 'from-yellow-500 to-amber-500' },
    { path: '/smart-dashboard', label: 'Smart Daily', icon: Calendar, gradient: 'from-purple-500 to-pink-500' },
    { path: '/treatment-plan', label: 'Treatment Plan', icon: Brain, gradient: 'from-emerald-500 to-cyan-500' }
  ];
  const visibleNavigationItems = navigationItems.filter((item) => canAccessSupervisorMode || item.path !== '/supervisor-dashboard');
  const primaryNavigationItems = visibleNavigationItems.slice(0, 6);
  const secondaryNavigationItems = visibleNavigationItems.slice(6);
  const hasActiveSecondaryItem = secondaryNavigationItems.some((item) => location.pathname === item.path);

  useEffect(() => {
    setIsMoreOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen w-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* REDESIGNED HEADER */}
      <header className="w-full bg-gradient-to-r from-slate-900/95 via-purple-900/95 to-slate-900/95 backdrop-blur-xl border-b border-white/10 text-white sticky top-0 z-50 shadow-2xl shadow-purple-500/20">
        {/* Animated Background Elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-4 -right-20 w-40 h-40 bg-orange-500/5 rounded-full blur-2xl animate-pulse"></div>
          <div className="absolute -top-4 -left-20 w-40 h-40 bg-pink-500/5 rounded-full blur-2xl animate-pulse delay-1000"></div>
        </div>

        <div className="relative z-10 w-full max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-3 lg:gap-4 min-h-16 py-3">
            {/* Logo */}
            <Link to="/" className="flex min-w-0 items-center gap-3 group cursor-pointer">
              <div className="relative flex-shrink-0">
                {/* Ember Logo with Glow Effect */}
                <div className="bg-gradient-to-r from-orange-500 via-red-500 to-pink-500 p-2 rounded-xl shadow-lg group-hover:shadow-2xl group-hover:shadow-orange-500/50 transition-all duration-500 group-hover:scale-110">
                  <Flame className="h-6 w-6 text-white" />
                </div>
                {/* Floating Sparkles */}
                <div className="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                  <Sparkles className="h-3 w-3 text-yellow-400 animate-pulse" />
                </div>
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-xl font-bold bg-gradient-to-r from-white via-orange-200 to-pink-200 bg-clip-text text-transparent group-hover:from-orange-300 group-hover:via-red-300 group-hover:to-pink-300 transition-all duration-500">
                  Ember
                </h1>
                <p className="hidden sm:block text-xs text-gray-400 group-hover:text-gray-300 transition-colors duration-300">
                  Case Management Suite
                </p>
              </div>
            </Link>

            {/* Navigation - Desktop */}
            <nav className="hidden xl:flex items-center gap-1 min-w-0 flex-1 justify-center">
              {primaryNavigationItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`group flex items-center gap-2 px-3 2xl:px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:scale-105 hover:shadow-lg hover:shadow-purple-500/25 border border-transparent hover:border-white/20 ${
                      isActive ? 'bg-white/10 border-white/20' : ''
                    }`}
                  >
                    <div className={`p-1 bg-gradient-to-r ${item.gradient} rounded-md transition-all duration-300`}>
                      <IconComponent className="h-3 w-3 text-white" />
                    </div>
                    <span className={`group-hover:text-purple-200 transition-colors duration-300 ${isActive ? 'text-white' : 'text-gray-300'}`}>
                      {item.label}
                    </span>
                  </Link>
                );
              })}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsMoreOpen((current) => !current)}
                  className={`group flex items-center gap-2 px-3 2xl:px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 hover:bg-white/10 hover:backdrop-blur-md hover:shadow-lg hover:shadow-purple-500/25 border border-transparent hover:border-white/20 ${
                    hasActiveSecondaryItem || isMoreOpen ? 'bg-white/10 border-white/20 text-white' : 'text-gray-300'
                  }`}
                >
                  <span className="text-sm">More</span>
                  <ChevronDown className={`h-4 w-4 transition-transform duration-200 ${isMoreOpen ? 'rotate-180' : ''}`} />
                </button>
                {isMoreOpen && (
                  <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-white/15 bg-slate-950/95 p-2 shadow-2xl shadow-purple-900/50 backdrop-blur-xl">
                    <div className="grid gap-1">
                      {secondaryNavigationItems.map((item) => {
                        const IconComponent = item.icon;
                        const isActive = location.pathname === item.path;
                        return (
                          <Link
                            key={item.path}
                            to={item.path}
                            className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-200 hover:bg-white/10 ${
                              isActive ? 'bg-white/10 text-white' : 'text-gray-300'
                            }`}
                          >
                            <div className={`p-1 bg-gradient-to-r ${item.gradient} rounded-md flex-shrink-0`}>
                              <IconComponent className="h-3 w-3 text-white" />
                            </div>
                            <span className="truncate">{item.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </nav>

            {/* User Menu */}
            <div className="flex min-w-0 items-center justify-end gap-2 lg:gap-3">
              {/* Notifications */}
              <div className="group relative hidden sm:block cursor-pointer flex-shrink-0">
                <div className="p-2 rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 transition-all duration-300 hover:bg-white/10 hover:border-white/20 hover:scale-110 hover:shadow-lg hover:shadow-orange-500/25">
                  <Bell className="h-4 w-4 text-white group-hover:text-orange-200 transition-colors duration-300" />
                </div>
                {/* Notification Badge */}
                <div className="absolute -top-1 -right-1 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full w-4 h-4 text-xs flex items-center justify-center font-bold shadow-lg animate-pulse">
                  3
                </div>
              </div>

              {/* User Avatar */}
              <div className="group relative min-w-0 max-w-[10rem] sm:max-w-[13rem] lg:max-w-[15rem] cursor-pointer">
                <div className="flex items-center gap-2 p-2 rounded-lg bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur-sm border border-white/20 transition-all duration-300 hover:from-purple-500/30 hover:to-pink-500/30 hover:border-white/30 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/25">
                  <div className="w-6 h-6 rounded-md bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                    <User className="h-3 w-3 text-white" />
                  </div>
                  <div className="min-w-0 hidden sm:block">
                    <p className="truncate text-xs font-medium text-white">{displayName}</p>
                    <p className="truncate text-xs text-gray-400">{displayRole}</p>
                  </div>
                </div>
                {/* User Status Indicator */}
                <div className="absolute -bottom-0.5 -left-0.5 w-2 h-2 bg-gradient-to-r from-green-400 to-emerald-400 rounded-full border border-slate-900 shadow-lg"></div>
              </div>
              <button className="rounded-lg border border-white/10 px-3 py-2 text-xs text-white flex-shrink-0" onClick={logout}>
                Logout
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          <div className="xl:hidden border-t border-white/10">
            <div className="flex overflow-x-auto py-2 gap-1 -mx-4 sm:-mx-6 px-4 sm:px-6 scrollbar-none" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
              {navigationItems.map((item) => {
                const IconComponent = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`group flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-300 hover:bg-white/10 border border-transparent hover:border-white/20 ${
                      isActive ? 'bg-white/10 border-white/20 text-white' : 'text-gray-300'
                    }`}
                  >
                    <div className={`p-1 bg-gradient-to-r ${item.gradient} rounded-md flex-shrink-0`}>
                      <IconComponent className="h-3 w-3 text-white" />
                    </div>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full min-w-0">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gradient-to-r from-slate-900 to-purple-900 text-white border-t border-white/10">
        <div className="max-w-[90rem] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
            {/* About */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Flame className="h-5 w-5 text-orange-400" />
                Ember
              </h3>
              <p className="text-gray-300 text-sm">
                Comprehensive reentry services platform supporting formerly incarcerated individuals 
                with housing, employment, legal services, and benefits coordination.
              </p>
            </div>

            {/* Services */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Services</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><Link to="/housing" className="hover:text-white transition-colors">Housing Search</Link></li>
                <li><Link to="/benefits" className="hover:text-white transition-colors">Benefits Assistance</Link></li>
                <li><Link to="/medical" className="hover:text-white transition-colors">Medical Access</Link></li>
                <li><Link to="/rolodex" className="hover:text-white transition-colors">Case Manager Rolodex</Link></li>
                <li><Link to="/documentation" className="hover:text-white transition-colors">Documentation Center</Link></li>
                <li><Link to="/legal" className="hover:text-white transition-colors">Legal Services</Link></li>
                <li><Link to="/resume" className="hover:text-white transition-colors">Resume Builder</Link></li>
                <li><Link to="/jobs" className="hover:text-white transition-colors">Job Search</Link></li>
              </ul>
            </div>

            {/* Support */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><Link to="/ai-chat" className="hover:text-white transition-colors">AI Assistant</Link></li>
                <li><Link to="/services" className="hover:text-white transition-colors">Services Directory</Link></li>
                <li><Link to="/smart-dashboard" className="hover:text-white transition-colors">Smart Dashboard</Link></li>
                <li><a href="#" className="hover:text-white transition-colors">Help Center</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Contact Support</a></li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Data Security</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Compliance</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-white/10 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-300 text-sm">
              © 2024 Ember Case Management Suite. All rights reserved.
            </p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a href="#" className="text-gray-300 hover:text-white text-sm transition-colors">Accessibility</a>
              <a href="#" className="text-gray-300 hover:text-white text-sm transition-colors">Security</a>
              <a href="#" className="text-gray-300 hover:text-white text-sm transition-colors">Status</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
