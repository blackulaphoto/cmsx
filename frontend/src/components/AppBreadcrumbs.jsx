import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';
import { buildBreadcrumbs, isPublicPath } from '../config/breadcrumbs';

// App-shell breadcrumbs (Phase 2D). Renders a subtle trail below the header and
// above the page content so users can orient themselves on deep routes. Reads
// the current pathname only — no data fetching, no route changes.
const AppBreadcrumbs = () => {
  const location = useLocation();

  // Defensive: public (unauthenticated) pages must never show app breadcrumbs.
  if (isPublicPath(location.pathname)) return null;

  const crumbs = buildBreadcrumbs(location.pathname);
  if (!crumbs.length) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className="border-b border-white/5 bg-slate-900/30 px-4 py-2 sm:px-6 lg:px-8"
    >
      <ol className="mx-auto flex w-full max-w-[96rem] items-center gap-1 overflow-hidden text-xs sm:text-sm">
        {crumbs.map((crumb, idx) => {
          const isLast = idx === crumbs.length - 1;
          const linkable = Boolean(crumb.to) && !isLast;

          return (
            <li key={`${crumb.label}-${idx}`} className="flex min-w-0 items-center gap-1">
              {idx > 0 && (
                <ChevronRight
                  className="h-3.5 w-3.5 flex-shrink-0 text-slate-500"
                  aria-hidden="true"
                />
              )}
              {linkable ? (
                <Link
                  to={crumb.to}
                  className="flex min-w-0 items-center gap-1 truncate text-slate-400 transition-colors hover:text-white"
                >
                  {idx === 0 && <Home className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />}
                  <span className="truncate">{crumb.label}</span>
                </Link>
              ) : (
                <span
                  aria-current={isLast ? 'page' : undefined}
                  className={`flex min-w-0 items-center gap-1 truncate ${
                    isLast ? 'font-medium text-slate-100' : 'text-slate-400'
                  }`}
                >
                  {idx === 0 && <Home className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />}
                  {crumb.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default AppBreadcrumbs;
