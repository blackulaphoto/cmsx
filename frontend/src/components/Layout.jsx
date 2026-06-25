import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Users,
  ClipboardList,
  MessageSquare,
  Calendar,
  User,
  Bell,
  Flame,
  Sparkles,
  BarChart3,
  ChevronDown,
  AlertTriangle,
  Settings,
  LifeBuoy,
  ShieldAlert,
  Landmark,
  LogOut,
  Menu,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch, messagesAPI } from '../api/config';
import AppSidebar from './AppSidebar';
import MobileNavDrawer from './MobileNavDrawer';

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
  const navigate = useNavigate();
  const { profile, logout, isSuperAdmin } = useAuth();
  const [messagesUnreadCount, setMessagesUnreadCount] = useState(0);
  const [serviceAlerts, setServiceAlerts] = useState([]);
  const [openMenu, setOpenMenu] = useState(null); // 'alerts' | 'user' | null
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const headerControlsRef = useRef(null);
  const canAccessSupervisorMode = profile?.role === 'admin';
  const displayName = profile?.full_name || 'Signed in user';
  const displayRole = canAccessSupervisorMode ? 'Admin / Supervisor' : 'Case Manager';

  // Role context for the grouped sidebar surfaces. This preserves the current
  // admin-only gating for Supervisor while keeping owner/super-admin links in
  // the separate account dropdown.
  const roleCtx = { isAdmin: canAccessSupervisorMode, isSuperAdmin };

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
        // reminders unavailable - skip silently, other sources still populate
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
        // FMLA summary unavailable - skip silently
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

  // Close dropdowns on outside click or Escape.
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

  // Close menus when navigating.
  useEffect(() => {
    setOpenMenu(null);
    setMobileDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileDrawerOpen) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKey = (event) => {
      if (event.key === 'Escape') {
        setMobileDrawerOpen(false);
      }
    };

    document.addEventListener('keydown', handleKey);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKey);
    };
  }, [mobileDrawerOpen]);

  const openOwnerCockpit = () => {
    setOpenMenu(null);
    navigate('/owner');
  };

  return (
    <div className="min-h-screen w-full flex flex-col bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-gradient-to-r from-slate-900/95 via-purple-900/95 to-slate-900/95 text-white shadow-2xl shadow-purple-500/20 backdrop-blur-xl">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-4 -right-20 h-40 w-40 animate-pulse rounded-full bg-orange-500/5 blur-2xl"></div>
          <div className="absolute -top-4 -left-20 h-40 w-40 animate-pulse rounded-full bg-pink-500/5 blur-2xl delay-1000"></div>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-[96rem] px-4 sm:px-6 lg:px-8">
          <div className="flex min-h-16 items-center justify-between gap-3 py-3 lg:gap-4">
            <Link to="/" className="group flex min-w-0 items-center gap-3 cursor-pointer">
              <div className="relative flex-shrink-0">
                <div className="rounded-xl bg-gradient-to-r from-ember-flame-start via-ember-flame-mid to-ember-flame-end p-2 shadow-lg transition-all duration-500 group-hover:scale-110 group-hover:shadow-2xl group-hover:shadow-orange-500/50">
                  <Flame className="h-6 w-6 text-white" />
                </div>
                <div className="absolute -top-1 -right-1 opacity-0 transition-opacity duration-500 group-hover:opacity-100">
                  <Sparkles className="h-3 w-3 animate-pulse text-yellow-400" />
                </div>
              </div>
              <div className="min-w-0">
                <h1 className="truncate bg-gradient-to-r from-white via-orange-200 to-pink-200 bg-clip-text text-xl font-bold text-transparent transition-all duration-500 group-hover:from-orange-300 group-hover:via-red-300 group-hover:to-pink-300">
                  Ember
                </h1>
                <p className="hidden text-xs text-gray-400 transition-colors duration-300 group-hover:text-gray-300 sm:block">
                  Case Management Suite
                </p>
              </div>
            </Link>

            <div ref={headerControlsRef} className="flex min-w-0 items-center justify-end gap-2 lg:gap-3">
              <button
                type="button"
                onClick={() => setMobileDrawerOpen(true)}
                aria-label="Open navigation menu"
                className="rounded-lg border border-white/10 bg-white/5 p-2 text-white transition-all duration-300 hover:border-white/20 hover:bg-white/10 xl:hidden"
              >
                <Menu className="h-5 w-5" />
              </button>

              <Link
                to="/messages"
                aria-label="Messenger"
                title="Messenger"
                className="group relative cursor-pointer flex-shrink-0"
              >
                <div className={`rounded-lg border p-2 backdrop-blur-sm transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-cyan-500/25 ${
                  location.pathname === '/messages'
                    ? 'bg-white/15 border-white/30'
                    : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                }`}>
                  <MessageSquare className="h-4 w-4 text-white transition-colors duration-300 group-hover:text-cyan-200" />
                </div>
                {messagesUnreadCount > 0 && (
                  <div className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 px-1 text-[10px] font-bold text-white shadow-lg">
                    {messagesUnreadCount > 99 ? '99+' : messagesUnreadCount}
                  </div>
                )}
              </Link>

              <div className="relative block flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setOpenMenu((current) => (current === 'alerts' ? null : 'alerts'))}
                  aria-label="Action alerts"
                  aria-expanded={openMenu === 'alerts'}
                  className={`group relative block rounded-lg border p-2 backdrop-blur-sm transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-orange-500/25 ${
                    openMenu === 'alerts' ? 'bg-white/15 border-white/30' : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                  }`}
                >
                  <Bell className="h-4 w-4 text-white transition-colors duration-300 group-hover:text-orange-200" />
                  {alerts.length > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-gradient-to-r from-orange-500 to-red-500 px-1 text-[10px] font-bold text-white shadow-lg">
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

              <div className="relative min-w-0 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setOpenMenu((current) => (current === 'user' ? null : 'user'))}
                  aria-label="User menu"
                  aria-expanded={openMenu === 'user'}
                  className={`group flex min-w-0 max-w-[10rem] items-center gap-2 rounded-lg border p-2 backdrop-blur-sm transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/25 sm:max-w-[13rem] lg:max-w-[15rem] ${
                    openMenu === 'user'
                      ? 'from-purple-500/30 to-pink-500/30 border-white/30 bg-gradient-to-r'
                      : 'from-purple-500/20 to-pink-500/20 border-white/20 bg-gradient-to-r hover:from-purple-500/30 hover:to-pink-500/30 hover:border-white/30'
                  }`}
                >
                  <span className="relative flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-gradient-to-r from-purple-500 to-pink-500">
                    <User className="h-3 w-3 text-white" />
                    <span className="absolute -bottom-0.5 -left-0.5 h-2 w-2 rounded-full border border-slate-900 bg-gradient-to-r from-green-400 to-emerald-400 shadow-lg"></span>
                  </span>
                  <span className="hidden min-w-0 text-left sm:block">
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
                        <button
                          type="button"
                          onClick={openOwnerCockpit}
                          className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm text-gray-300 transition-colors hover:bg-white/10"
                        >
                          <Landmark className="h-4 w-4 text-amber-300" />
                          <span>Owner Cockpit</span>
                        </button>
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
        </div>
      </header>

      <MobileNavDrawer
        isOpen={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        roleCtx={roleCtx}
        messagesUnreadCount={messagesUnreadCount}
      />

      <div className="flex flex-1 w-full min-h-0">
        <AppSidebar roleCtx={roleCtx} messagesUnreadCount={messagesUnreadCount} />
        <main className="flex-1 w-full min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
