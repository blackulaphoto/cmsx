import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getVisibleNavGroups, isNavItemActive } from '../config/navigation';

// Phase 2B desktop left sidebar.
//
// Desktop-only chrome (hidden below `xl`, where the existing mobile scroll
// strip in Layout takes over). Renders the grouped navigation config with
// Ember styling (dark slate/purple glass panel, gradient icon chips, a flame
// accent on the active item). Role visibility is delegated to the config
// helper so it exactly mirrors the prior inline gating.
//
// Props:
//   roleCtx           — { isAdmin, isSuperAdmin } used for group/item filtering.
//   messagesUnreadCount — live unread count, injected into badge-keyed items.
const AppSidebar = ({ roleCtx, messagesUnreadCount = 0 }) => {
  const location = useLocation();
  const groups = getVisibleNavGroups(roleCtx);

  const resolveBadge = (item) => {
    if (item.badgeKey === 'messagesUnread') return messagesUnreadCount;
    return 0;
  };

  return (
    <aside
      aria-label="Primary"
      className="hidden xl:block w-64 flex-shrink-0 border-r border-white/10 bg-slate-900/40 backdrop-blur-xl"
    >
      <nav className="sticky top-16 max-h-[calc(100vh-4rem)] overflow-y-auto px-3 py-4 scrollbar-none">
        {groups.map((group) => (
          <div key={group.id} className="mb-5 last:mb-1">
            <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {group.label}
            </p>
            <div className="grid gap-0.5">
              {group.items.map((item) => {
                const IconComponent = item.icon;
                const isActive = isNavItemActive(location.pathname, item);
                const badge = resolveBadge(item);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    aria-current={isActive ? 'page' : undefined}
                    className={`group relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-all duration-200 hover:bg-white/10 ${
                      isActive ? 'bg-white/10 text-white border border-white/20' : 'text-gray-300 border border-transparent'
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-ember-flame-start via-ember-flame-mid to-ember-flame-end" />
                    )}
                    <span className={`p-1 bg-gradient-to-r ${item.gradient} rounded-md flex-shrink-0`}>
                      <IconComponent className="h-3.5 w-3.5 text-white" />
                    </span>
                    <span className="truncate">{item.label}</span>
                    {badge > 0 && (
                      <span className="ml-auto rounded-full bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                        {badge > 99 ? '99+' : badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
};

export default AppSidebar;
