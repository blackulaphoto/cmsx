import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  AlertTriangle,
  Settings,
  LifeBuoy,
  ShieldAlert,
  Landmark,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch, messagesAPI } from '../api/config';

const TONE_BADGE = {
  danger: 'bg-red-500/20 text-red-200 border-red-400/30',
  warn: 'bg-amber-500/20 text-amber-100 border-amber-400/30',
  info: 'bg-cyan-500/15 text-cyan-100 border-cyan-400/30',
};
const TONE_WEIGHT = { danger: 0, warn: 1, info: 2 };

const cleanClientName = (name) => {
  const value = (name || '').trim();
  if (!value || value === 'Unknown' || value === 'Unknown Client') return null;
  return value;
};

const Layout = ({ children }) => {
  const location = useLocation();
  const { profile, logout, isSuperAdmin } = useAuth();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const [messagesUnreadCount, setMessagesUnreadCount] = useState(0);
  const [serviceAlerts, setServiceAlerts] = useState([]);
  const [openMenu, setOpenMenu] = useState(null); // 'alerts' | 'user' | null
  const headerControlsRef = useRef(null);
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
    { path: '/messages', label: 'Messages', icon: MessageSquare, gradient: 'from-cyan-500 to-blue-500', badge: messagesUnreadCount },
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

  useEffect(() => {
    let cancelled = false;
    const loadUnread = async () => {
      try {
        const result = await messagesAPI.unreadCount();
        if (!cancelled) {
          setMessagesUnreadCount(Number(result.unread_count || 0));
        }
      } catch (error) {
        if (!cancelled) {
          setMessagesUnreadCount(0);
        }
      }
    };
    if (profile) {
      loadUnread();
    }
    return () => {
      cancelled = true;
    };
  }, [profile, location.pathname]);

  // Build Action Alerts from existing endpoints (reminders + FMLA). Messenger
  // unread is folded in via useMemo so it stays in sync with the messenger badge.
  useEffect(() => {
    let cancelled = false;
    const loadAlerts = async () => {
      const cmId = profile?.case_manager_id;
      if (!cmId) {
        if (!cancelled) setServiceAlerts([]);
        return;
      }
      const next = [];
      try {
        const now = new Date();
        const localDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        const res = await apiFetch(`/api/reminders/prioritized/${encodeURIComponent(cmId)}?date=${localDate}`);
        if (res.ok) {
          const data = await res.json();
          const buckets = data.buckets || {};
          const pushReminder = (task, status, tone) => {
            next.push({
              id: `rem-${task.task_id || task.id}`,
              title: task.title || 'Reminder',
              client: cleanClientName(task.client_name),
              status,
              type: 'Reminder',
              tone,
              to: '/smart-dashboard',
            });
          };
          (buckets.overdue || []).forEach((task) => pushReminder(task, 'Overdue', 'danger'));
          (buckets.today || []).forEach((task) => pushReminder(task, 'Due today', 'warn'));
          (buckets.next_3_days || []).forEach((task) => pushReminder(task, 'Due soon', 'info'));
        }
      } catch (error) {
        // reminders unavailable — skip silently, other sources still populate
      }
      try {
        const res = await apiFetch(`/api/fmla/summary?case_manager_id=${encodeURIComponent(cmId)}`);
        if (res.ok) {
          const f = await res.json();
          if (f.success) {
            if (f.missing_paperwork > 0) {
              next.push({
                id: 'fmla-missing',
                title: 'FMLA paperwork missing',
                client: null,
                status: `${f.missing_paperwork} case${f.missing_paperwork > 1 ? 's' : ''}`,
                type: 'FMLA',
                tone: 'warn',
                to: '/fmla',
              });
            }
            if (f.deadlines_next_7_days > 0) {
              next.push({
                id: 'fmla-deadline',
                title: 'FMLA deadlines this week',
                client: null,
                status: `${f.deadlines_next_7_days} due`,
                type: 'FMLA',
                tone: 'info',
                to: '/fmla',
              });
            }
          }
        }
      } catch (error) {
        // FMLA summary unavailable — skip silently
      }
      if (!cancelled) setServiceAlerts(next);
    };
    if (profile) {
      loadAlerts();
    } else {
      setServiceAlerts([]);
    }
    return () => {
      cancelled = true;
    };
  }, [profile, location.pathname]);

  const alerts = useMemo(() => {
    const list = [...serviceAlerts];
    if (messagesUnreadCount > 0) {
      list.push({
        id: 'msg-unread',
        title: `${messagesUnreadCount} unread message${messagesUnreadCount > 1 ? 's' : ''}`,
        client: null,
        status: 'New',
        type: 'Messages',
        tone: 'info',
        to: '/messages',
      });
    }
    return list.sort((a, b) => (TONE_WEIGHT[a.tone] ?? 3) - (TONE_WEIGHT[b.tone] ?? 3));
  }, [serviceAlerts, messagesUnreadCount]);

  const visibleAlerts = alerts.slice(0, 8);

  // Close dropdowns on outside click or Escape
  useEffect(() => {
    if (!openMenu) return undefined;
    const handleClick = (event) => {
      if (headerControlsRef.current && !headerControlsRef.current.contains(event.target)) {
        setOpenMenu(null);
      }
    };
    const handleKey = (event) => {
      if (event.key === 'Escape') setOpenMenu(null);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [openMenu]);

  // Close dropdowns when navigating
  useEffect(() => {
    setOpenMenu(null);
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
                    {item.badge > 0 && (
                      <span className="ml-0.5 rounded-full bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                        {item.badge > 99 ? '99+' : item.badge}
                      </span>
                    )}
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
                            {item.badge > 0 && (
                              <span className="ml-auto rounded-full bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                                {item.badge > 99 ? '99+' : item.badge}
                              </span>
                            )}
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </nav>

            {/* User Menu */}
            <div ref={headerControlsRef} className="flex min-w-0 items-center justify-end gap-2 lg:gap-3">
              {/* Messenger */}
              <Link
                to="/messages"
                aria-label="Messenger"
                title="Messenger"
                className="group relative cursor-pointer flex-shrink-0"
              >
                <div className={`p-2 rounded-lg backdrop-blur-sm border transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-cyan-500/25 ${
                  location.pathname === '/messages'
                    ? 'bg-white/15 border-white/30'
                    : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                }`}>
                  <MessageSquare className="h-4 w-4 text-white group-hover:text-cyan-200 transition-colors duration-300" />
                </div>
                {/* Unread Badge */}
                {messagesUnreadCount > 0 && (
                  <div className="absolute -top-1 -right-1 bg-gradient-to-r from-cyan-500 to-blue-500 text-white rounded-full min-w-4 h-4 px-1 text-[10px] flex items-center justify-center font-bold shadow-lg">
                    {messagesUnreadCount > 99 ? '99+' : messagesUnreadCount}
                  </div>
                )}
              </Link>

              {/* Notifications / Action Alerts */}
              <div className="relative hidden sm:block flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setOpenMenu((current) => (current === 'alerts' ? null : 'alerts'))}
                  aria-label="Action alerts"
                  aria-expanded={openMenu === 'alerts'}
                  className={`group relative block rounded-lg p-2 backdrop-blur-sm border transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-orange-500/25 ${
                    openMenu === 'alerts' ? 'bg-white/15 border-white/30' : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                  }`}
                >
                  <Bell className="h-4 w-4 text-white group-hover:text-orange-200 transition-colors duration-300" />
                  {alerts.length > 0 && (
                    <span className="absolute -top-1 -right-1 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full min-w-4 h-4 px-1 text-[10px] flex items-center justify-center font-bold shadow-lg">
                      {alerts.length > 99 ? '99+' : alerts.length}
                    </span>
                  )}
                </button>

                {openMenu === 'alerts' && (
                  <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-2xl border border-white/15 bg-slate-950/95 shadow-2xl shadow-purple-900/50 backdrop-blur-xl">
                    <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                      <h3 className="text-sm font-semibold text-white">Action Alerts</h3>
                      {alerts.length > 0 && (
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-slate-300">{alerts.length}</span>
                      )}
                    </div>
                    {visibleAlerts.length === 0 ? (
                      <div className="px-4 py-8 text-center">
                        <p className="text-sm font-medium text-white">No active alerts</p>
                        <p className="mt-1 text-xs text-slate-400">
                          Court dates, reminders, missing paperwork, and deadlines will appear here.
                        </p>
                      </div>
                    ) : (
                      <div className="max-h-[22rem] overflow-y-auto py-1">
                        {visibleAlerts.map((alert) => (
                          <Link
                            key={alert.id}
                            to={alert.to}
                            onClick={() => setOpenMenu(null)}
                            className="flex items-start gap-3 px-4 py-2.5 transition-colors hover:bg-white/5"
                          >
                            <span className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg border ${TONE_BADGE[alert.tone] || TONE_BADGE.info}`}>
                              {alert.type === 'Messages' ? <MessageSquare className="h-3.5 w-3.5" /> : alert.type === 'FMLA' ? <ClipboardList className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center justify-between gap-2">
                                <span className="truncate text-sm font-medium text-white">{alert.title}</span>
                                <span className={`flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${TONE_BADGE[alert.tone] || TONE_BADGE.info}`}>
                                  {alert.status}
                                </span>
                              </span>
                              <span className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-400">
                                <span className="rounded bg-white/10 px-1.5 py-0.5 text-slate-300">{alert.type}</span>
                                {alert.client && <span className="truncate">{alert.client}</span>}
                              </span>
                            </span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* User / Workspace menu */}
              <div className="relative min-w-0 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setOpenMenu((current) => (current === 'user' ? null : 'user'))}
                  aria-label="User menu"
                  aria-expanded={openMenu === 'user'}
                  className={`group flex min-w-0 max-w-[10rem] items-center gap-2 rounded-lg p-2 backdrop-blur-sm border transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/25 sm:max-w-[13rem] lg:max-w-[15rem] ${
                    openMenu === 'user'
                      ? 'from-purple-500/30 to-pink-500/30 border-white/30 bg-gradient-to-r'
                      : 'from-purple-500/20 to-pink-500/20 border-white/20 bg-gradient-to-r hover:from-purple-500/30 hover:to-pink-500/30 hover:border-white/30'
                  }`}
                >
                  <span className="relative flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-gradient-to-r from-purple-500 to-pink-500">
                    <User className="h-3 w-3 text-white" />
                    <span className="absolute -bottom-0.5 -left-0.5 h-2 w-2 rounded-full border border-slate-900 bg-gradient-to-r from-green-400 to-emerald-400 shadow-lg"></span>
                  </span>
                  <span className="min-w-0 hidden text-left sm:block">
                    <span className="block truncate text-xs font-medium text-white">{displayName}</span>
                    <span className="block truncate text-xs text-gray-400">{displayRole}</span>
                  </span>
                  <ChevronDown className={`hidden h-4 w-4 flex-shrink-0 text-gray-400 transition-transform sm:block ${openMenu === 'user' ? 'rotate-180' : ''}`} />
                </button>

                {openMenu === 'user' && (
                  <div className="absolute right-0 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-2xl border border-white/15 bg-slate-950/95 shadow-2xl shadow-purple-900/50 backdrop-blur-xl">
                    <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
                      <span className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-r from-purple-500 to-pink-500">
                        <User className="h-4 w-4 text-white" />
                        <span className="absolute -bottom-0.5 -left-0.5 h-2.5 w-2.5 rounded-full border border-slate-900 bg-gradient-to-r from-green-400 to-emerald-400"></span>
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">{displayName}</p>
                        <p className="truncate text-xs text-gray-400">{displayRole}</p>
                      </div>
                    </div>
                    <div className="grid gap-0.5 p-1.5">
                      <Link to="/profile" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                        <User className="h-4 w-4 text-purple-300" />
                        <span>My Profile</span>
                      </Link>
                      <Link to="/case-management" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                        <Users className="h-4 w-4 text-blue-300" />
                        <span>My Caseload</span>
                      </Link>
                      <Link to="/smart-dashboard" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                        <Calendar className="h-4 w-4 text-pink-300" />
                        <span>Smart Daily</span>
                      </Link>
                      {canAccessSupervisorMode && (
                        <Link to="/supervisor-dashboard" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                          <BarChart3 className="h-4 w-4 text-cyan-300" />
                          <span>Supervisor Dashboard</span>
                        </Link>
                      )}
                      <Link to="/settings" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                        <Settings className="h-4 w-4 text-slate-300" />
                        <span>Settings</span>
                      </Link>
                      <Link to="/support" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                        <LifeBuoy className="h-4 w-4 text-emerald-300" />
                        <span>Help &amp; Support</span>
                      </Link>
                      {isSuperAdmin && (
                        <Link to="/owner" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                          <Landmark className="h-4 w-4 text-amber-300" />
                          <span>Owner Cockpit</span>
                        </Link>
                      )}
                      {isSuperAdmin && (
                        <Link to="/super-admin" onClick={() => setOpenMenu(null)} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-gray-300 transition-colors hover:bg-white/10">
                          <ShieldAlert className="h-4 w-4 text-rose-300" />
                          <span>Super Admin</span>
                        </Link>
                      )}
                    </div>
                    <div className="border-t border-white/10 p-1.5">
                      <button type="button" onClick={() => { setOpenMenu(null); logout(); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-red-200 transition-colors hover:bg-red-500/15">
                        <LogOut className="h-4 w-4" />
                        <span>Logout</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
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
                    {item.badge > 0 && (
                      <span className="rounded-full bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                        {item.badge > 99 ? '99+' : item.badge}
                      </span>
                    )}
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
