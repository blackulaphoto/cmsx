import React from 'react';
import { Link } from 'react-router-dom';
import { Flame, ArrowLeft, AlertTriangle } from 'lucide-react';

// Public-facing shell for the legal / compliance pages. Intentionally
// self-contained and unauthenticated — it does NOT use the authenticated app
// shell (components/Layout.jsx) and does not re-introduce the marketing footer
// that was removed in Phase 1A. The minimal footer here only cross-links the
// legal pages and the sign-in screen.

export const LEGAL_LINKS = [
  { path: '/privacy', label: 'Privacy Policy' },
  { path: '/terms', label: 'Terms of Service' },
  { path: '/data-security', label: 'Data Security' },
  { path: '/compliance', label: 'Compliance' },
  { path: '/hipaa-baa', label: 'HIPAA / BAA' },
];

export const LEGAL_LAST_UPDATED = 'June 2026';

export function LegalSection({ title, children }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
      <h2 className="mb-3 text-lg font-semibold text-white">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-gray-300">{children}</div>
    </section>
  );
}

export function LegalDisclaimer({ children }) {
  return (
    <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-5">
      <p className="flex items-start gap-2 text-sm leading-relaxed text-amber-100">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-300" />
        <span>{children}</span>
      </p>
    </div>
  );
}

const LegalPageLayout = ({ icon: Icon, title, subtitle, lastUpdated = LEGAL_LAST_UPDATED, children }) => {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 px-3 sm:px-6 py-8 text-white">
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Brand bar */}
        <div className="flex items-center justify-between gap-3">
          <Link to="/login" className="group flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-r from-ember-flame-start via-ember-flame-mid to-ember-flame-end shadow-lg">
              <Flame className="h-5 w-5 text-white" />
            </span>
            <span className="text-lg font-bold bg-gradient-to-r from-white via-orange-200 to-pink-200 bg-clip-text text-transparent">
              Ember
            </span>
          </Link>
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 px-3 py-1.5 text-sm text-gray-200 transition-colors hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to sign in
          </Link>
        </div>

        {/* Page header */}
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600">
            {Icon ? <Icon className="h-6 w-6" /> : null}
          </span>
          <div>
            <h1 className="text-3xl font-bold">{title}</h1>
            {subtitle ? <p className="text-gray-300">{subtitle}</p> : null}
          </div>
        </div>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last updated: {lastUpdated}</p>

        {/* Page content */}
        {children}

        {/* Minimal legal nav + sign-in link */}
        <footer className="border-t border-white/10 pt-6">
          <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-400">
            {LEGAL_LINKS.map((link) => (
              <Link key={link.path} to={link.path} className="transition-colors hover:text-white">
                {link.label}
              </Link>
            ))}
            <Link to="/login" className="transition-colors hover:text-white">
              Sign in
            </Link>
          </nav>
          <p className="mt-4 text-xs text-slate-500">
            © 2026 Ember Case Management Suite. This page is provided for informational purposes only and
            does not constitute legal advice.
          </p>
        </footer>
      </div>
    </div>
  );
};

export default LegalPageLayout;
