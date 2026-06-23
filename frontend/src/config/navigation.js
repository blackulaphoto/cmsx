// Centralized authenticated navigation configuration (Phase 2B).
//
// This is the single source of truth for the primary authenticated navigation
// that previously lived inline in `components/Layout.jsx`. It powers two
// surfaces:
//   1. The desktop left sidebar (`components/AppSidebar.jsx`) — grouped.
//   2. The existing mobile horizontal scroll strip (in `Layout.jsx`) — flat,
//      rendered in the original order so mobile behavior is unchanged.
//
// Account, Owner/Platform, and Super Admin links intentionally remain in the
// header user dropdown for this phase and are NOT part of this config. Routes,
// icons, gradients, and labels are preserved exactly from the prior Layout.
//
// Role metadata: an item or group may declare `roles`. `undefined` means
// "visible to everyone". The only privileged primary item today is the
// Supervisor dashboard (admin only), reproducing the prior inline filter.

import {
  Users,
  LayoutDashboard,
  MapPin,
  Hotel,
  Scale,
  FileText,
  ClipboardList,
  MessageSquare,
  Building2,
  Calendar,
  Briefcase,
  Bell,
  Heart,
  BarChart3,
  Stethoscope,
  Contact,
  BookOpen,
  Brain,
  ClipboardCheck,
} from 'lucide-react';

// --- Individual nav items (defined once, referenced by both flat + grouped) ---
// `exact: true` forces exact-path active matching (used for '/', which would
// otherwise prefix-match every route). All others support nested matching so a
// deep route (e.g. /admissions/:id/forms/:key) highlights its parent.

const DASHBOARD = { path: '/', label: 'Dashboard', icon: LayoutDashboard, gradient: 'from-blue-500 to-cyan-500', exact: true };
const CASE_MANAGEMENT = { path: '/case-management', label: 'Case Management', icon: Users, gradient: 'from-purple-500 to-indigo-500' };
const ADMISSIONS = { path: '/admissions', label: 'Admissions', icon: ClipboardCheck, gradient: 'from-cyan-500 to-blue-600' };
const DOCUMENTATION = { path: '/documentation', label: 'Documentation', icon: ClipboardList, gradient: 'from-cyan-500 to-blue-500' };
const HOUSING = { path: '/housing', label: 'Housing', icon: MapPin, gradient: 'from-blue-500 to-cyan-500' };
const SOBER_LIVING = { path: '/sober-living', label: 'Sober Living', icon: Hotel, gradient: 'from-teal-500 to-emerald-500' };
const GROUPS = { path: '/groups', label: 'Groups', icon: BookOpen, gradient: 'from-teal-400 to-cyan-500' };
const SOBER_DIRECTORY = { path: '/sober-living-directory', label: 'Sober Directory', icon: Building2, gradient: 'from-teal-500 to-cyan-500' };
const BENEFITS = { path: '/benefits', label: 'Benefits', icon: Heart, gradient: 'from-pink-500 to-rose-500' };
const MEDICAL = { path: '/medical', label: 'Medical', icon: Stethoscope, gradient: 'from-teal-500 to-cyan-500' };
const ROLODEX = { path: '/rolodex', label: 'Rolodex', icon: Contact, gradient: 'from-cyan-500 to-sky-500' };
const LEGAL = { path: '/legal', label: 'Legal', icon: Scale, gradient: 'from-indigo-500 to-purple-500' };
const FMLA = { path: '/fmla', label: 'FMLA', icon: ClipboardList, gradient: 'from-cyan-500 to-sky-500' };
const UR = { path: '/ur', label: 'UR', icon: Bell, gradient: 'from-amber-500 to-orange-500' };
const RESUME = { path: '/resume', label: 'Resume', icon: FileText, gradient: 'from-emerald-500 to-green-500' };
const JOBS = { path: '/jobs', label: 'Jobs', icon: Briefcase, gradient: 'from-emerald-500 to-green-500' };
const SUPERVISOR = { path: '/supervisor-dashboard', label: 'Supervisor', icon: BarChart3, gradient: 'from-cyan-500 to-blue-500', roles: ['admin'] };
const SERVICES = { path: '/services', label: 'Services', icon: Building2, gradient: 'from-orange-500 to-amber-500' };
// `badgeKey` markers are resolved to live counts by the rendering component.
const MESSAGES = { path: '/messages', label: 'Messages', icon: MessageSquare, gradient: 'from-cyan-500 to-blue-500', badgeKey: 'messagesUnread' };
const AI_ASSISTANT = { path: '/ai-chat', label: 'AI Assistant', icon: MessageSquare, gradient: 'from-yellow-500 to-amber-500' };
const SMART_DAILY = { path: '/smart-dashboard', label: 'Smart Daily', icon: Calendar, gradient: 'from-purple-500 to-pink-500' };
const TREATMENT_PLAN = { path: '/treatment-plan', label: 'Treatment Plan', icon: Brain, gradient: 'from-emerald-500 to-cyan-500' };

// --- Flat list, ORIGINAL order ---
// Preserves the exact ordering of the previous `navigationItems` array so the
// mobile scroll strip renders identically to before Phase 2B.
export const NAV_ITEMS = [
  DASHBOARD,
  CASE_MANAGEMENT,
  ADMISSIONS,
  DOCUMENTATION,
  HOUSING,
  SOBER_LIVING,
  GROUPS,
  SOBER_DIRECTORY,
  BENEFITS,
  MEDICAL,
  ROLODEX,
  LEGAL,
  FMLA,
  UR,
  RESUME,
  JOBS,
  SUPERVISOR,
  SERVICES,
  MESSAGES,
  AI_ASSISTANT,
  SMART_DAILY,
  TREATMENT_PLAN,
];

// --- Grouped structure for the desktop sidebar ---
// Order and grouping follow the Phase 2A audit (§3). Every item points at its
// existing route — no routes change.
export const NAV_GROUPS = [
  {
    id: 'home',
    label: 'Home',
    items: [DASHBOARD],
  },
  {
    id: 'daily',
    label: 'Daily Work',
    items: [SMART_DAILY, MESSAGES, AI_ASSISTANT],
  },
  {
    id: 'clients',
    label: 'Clients & Care',
    items: [CASE_MANAGEMENT, ADMISSIONS, BENEFITS, LEGAL],
  },
  {
    id: 'clinical',
    label: 'Clinical & Documentation',
    items: [DOCUMENTATION, TREATMENT_PLAN, GROUPS, MEDICAL, FMLA, UR],
  },
  {
    id: 'housing',
    label: 'Housing & Resources',
    items: [HOUSING, SOBER_LIVING, SOBER_DIRECTORY, SERVICES, ROLODEX],
  },
  {
    id: 'workforce',
    label: 'Workforce & Reentry',
    items: [RESUME, JOBS],
  },
  {
    id: 'admin',
    label: 'Team & Admin',
    roles: ['admin'],
    items: [SUPERVISOR],
  },
];

// Returns true if an item/group with the given `roles` is visible to the
// current user. `undefined` roles → visible to everyone. Mirrors the prior
// inline gating (only the Supervisor dashboard was admin-gated).
export function canSeeNav(roles, { isAdmin = false, isSuperAdmin = false } = {}) {
  if (!roles || roles.length === 0) return true;
  if (roles.includes('admin') && isAdmin) return true;
  if (roles.includes('superAdmin') && isSuperAdmin) return true;
  return false;
}

// Returns the groups (and their items) visible to the current user. Groups
// whose items are all filtered out are dropped entirely so no empty group
// label renders.
export function getVisibleNavGroups(roleCtx) {
  return NAV_GROUPS
    .filter((group) => canSeeNav(group.roles, roleCtx))
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => canSeeNav(item.roles, roleCtx)),
    }))
    .filter((group) => group.items.length > 0);
}

// Active-state matcher. Exact-only for items flagged `exact` (e.g. '/'),
// otherwise exact OR nested (`/parent/child` highlights `/parent`).
export function isNavItemActive(pathname, item) {
  if (item.exact) return pathname === item.path;
  return pathname === item.path || pathname.startsWith(`${item.path}/`);
}
