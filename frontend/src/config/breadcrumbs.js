// Breadcrumb route-label config + builder (Phase 2D).
//
// Pure, dependency-free helper that maps a pathname to an ordered crumb list.
// Each crumb is `{ label, to }` where `to` is a clickable route string or
// `null` (null = not navigable / current page). This file performs NO data
// fetching and changes NO route paths — it only describes how existing routes
// are labelled for the breadcrumb trail rendered by `AppBreadcrumbs.jsx`.

const DASHBOARD_CRUMB = { label: 'Dashboard', to: '/' };

// Public routes that render OUTSIDE the authenticated app shell. Breadcrumbs
// must never appear on these even if the builder is somehow invoked.
export const PUBLIC_PATHS = new Set([
  '/login',
  '/privacy',
  '/terms',
  '/data-security',
  '/compliance',
  '/hipaa-baa',
  '/onboarding',
]);

export function isPublicPath(pathname) {
  const clean = (pathname || '').replace(/\/+$/, '');
  return PUBLIC_PATHS.has(clean || '/');
}

// Human-friendly labels for top-level (single-segment) authenticated routes.
// Keys are the first path segment; values are the displayed crumb label.
const TOP_LABELS = {
  'case-management': 'Case Management',
  admissions: 'Admissions',
  documentation: 'Documentation',
  'treatment-plan': 'Treatment Plan',
  groups: 'Groups',
  ur: 'Utilization Review',
  housing: 'Housing',
  'sober-living': 'Sober Living',
  'sober-living-directory': 'Sober Living Directory',
  benefits: 'Benefits',
  medical: 'Medical',
  rolodex: 'Rolodex',
  legal: 'Legal',
  fmla: 'FMLA',
  resume: 'Resume Builder',
  jobs: 'Jobs',
  services: 'Services',
  messages: 'Messages',
  'ai-chat': 'AI Assistant',
  'smart-dashboard': 'Smart Daily',
  team: 'Team Management',
  'supervisor-dashboard': 'Supervisor Dashboard',
  owner: 'Owner Cockpit',
  'super-admin': 'Super Admin',
  profile: 'Profile',
  settings: 'Settings',
  support: 'Support',
  billing: 'Billing',
  'system-integrity': 'System Integrity',
  'integration-audit': 'Integration Audit',
  'enhanced-dashboard': 'Dashboard',
  'legacy-dashboard': 'Dashboard',
};

// Multi-segment / dynamic patterns. First match wins. Each `crumbs()` returns
// the trail AFTER the leading Dashboard crumb (which the builder prepends).
// Parent `to` values point ONLY at routes that actually exist (see App.jsx);
// dynamic / index-less segments stay non-clickable (`to: null`).
const PATTERNS = [
  {
    // /client/:clientId  →  Dashboard > Case Management > Client Profile
    test: /^\/client\/[^/]+$/,
    crumbs: () => [
      { label: 'Case Management', to: '/case-management' },
      { label: 'Client Profile', to: null },
    ],
  },
  {
    // /admissions/:client_id/forms/:form_key
    test: /^\/admissions\/[^/]+\/forms\/[^/]+$/,
    crumbs: (path) => {
      const clientId = path.split('/')[2];
      return [
        { label: 'Admissions', to: '/admissions' },
        { label: 'Client Detail', to: `/admissions/${clientId}` },
        { label: 'Form', to: null },
      ];
    },
  },
  {
    // /admissions/new
    test: /^\/admissions\/new$/,
    crumbs: () => [
      { label: 'Admissions', to: '/admissions' },
      { label: 'New Intake', to: null },
    ],
  },
  {
    // /admissions/:client_id
    test: /^\/admissions\/[^/]+$/,
    crumbs: () => [
      { label: 'Admissions', to: '/admissions' },
      { label: 'Client Detail', to: null },
    ],
  },
  {
    // /housing/case-manager
    test: /^\/housing\/case-manager$/,
    crumbs: () => [
      { label: 'Housing', to: '/housing' },
      { label: 'Case Manager Tools', to: null },
    ],
  },
  {
    // /housing/test
    test: /^\/housing\/test$/,
    crumbs: () => [
      { label: 'Housing', to: '/housing' },
      { label: 'Housing Test', to: null },
    ],
  },
  {
    // /sober-living-directory/discovery | /review
    test: /^\/sober-living-directory\/(discovery|review)$/,
    crumbs: (path) => [
      { label: 'Sober Living Directory', to: '/sober-living-directory' },
      { label: path.endsWith('discovery') ? 'Discovery' : 'Review', to: null },
    ],
  },
  {
    // /sober-living-directory/:listingId
    test: /^\/sober-living-directory\/[^/]+$/,
    crumbs: () => [
      { label: 'Sober Living Directory', to: '/sober-living-directory' },
      { label: 'Listing', to: null },
    ],
  },
  {
    // /sober-living/:houseId
    test: /^\/sober-living\/[^/]+$/,
    crumbs: () => [
      { label: 'Sober Living', to: '/sober-living' },
      { label: 'Detail', to: null },
    ],
  },
  {
    // /groups/sessions/:sessionId
    test: /^\/groups\/sessions\/[^/]+$/,
    crumbs: () => [
      { label: 'Groups', to: '/groups' },
      { label: 'Group Notes', to: null },
    ],
  },
];

// Fallback formatter for unknown segments: "some-segment" → "Some Segment".
function titleCase(segment) {
  return segment
    .split('-')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Builds the ordered crumb trail for a pathname. The final crumb is always the
// current page and is rendered non-clickable (`to: null`).
export function buildBreadcrumbs(pathname) {
  const clean = (pathname || '/').split('?')[0].split('#')[0].replace(/\/+$/, '');
  const path = clean || '/';

  // Root / dashboard → a single, non-clickable crumb (avoids a duplicate
  // "Dashboard > Dashboard" trail).
  if (path === '/') {
    return [{ label: 'Dashboard', to: null }];
  }

  // Known multi-segment / dynamic patterns.
  for (const pattern of PATTERNS) {
    if (pattern.test.test(path)) {
      const tail = pattern.crumbs(path).map((crumb) => ({ ...crumb }));
      if (tail.length) tail[tail.length - 1].to = null; // current page
      return [DASHBOARD_CRUMB, ...tail];
    }
  }

  const segments = path.slice(1).split('/');

  // Single top-level segment with a known label.
  if (segments.length === 1 && TOP_LABELS[segments[0]]) {
    return [DASHBOARD_CRUMB, { label: TOP_LABELS[segments[0]], to: null }];
  }

  // Generic fallback: build from segments using known labels where available.
  // Intermediate crumbs stay non-clickable so we never invent a parent route
  // that may not exist.
  const crumbs = [DASHBOARD_CRUMB];
  segments.forEach((segment, idx) => {
    const isLast = idx === segments.length - 1;
    const label = TOP_LABELS[segment] || titleCase(segment) || 'Detail';
    crumbs.push({ label, to: null });
    void isLast;
  });
  return crumbs;
}
