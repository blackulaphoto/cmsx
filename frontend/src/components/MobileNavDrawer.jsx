import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Flame, X } from 'lucide-react';
import { getVisibleNavGroups, isNavItemActive } from '../config/navigation';

const MobileNavDrawer = ({ isOpen, onClose, roleCtx, messagesUnreadCount = 0 }) => {
  const location = useLocation();
  const groups = getVisibleNavGroups(roleCtx);

  const resolveBadge = (item) => {
    if (item.badgeKey === 'messagesUnread') return messagesUnreadCount;
    return 0;
  };

  if (!isOpen) return null;

  return (
    <div className="xl:hidden">
      <button
        type="button"
        aria-hidden="true"
        tabIndex={-1}
        className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        className="fixed inset-y-0 left-0 z-50 w-[min(22rem,calc(100vw-2.5rem))] max-w-full"
      >
        <div className="flex h-full flex-col border-r border-white/15 bg-slate-950/96 shadow-2xl shadow-purple-950/60 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
            <div className="flex min-w-0 items-center gap-3">
              <div className="rounded-xl bg-gradient-to-r from-ember-flame-start via-ember-flame-mid to-ember-flame-end p-2 shadow-lg shadow-orange-500/30">
                <Flame className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">Ember</p>
                <p className="truncate text-xs text-slate-400">Case Management Suite</p>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close navigation menu"
              className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-200 transition-colors hover:bg-white/10"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <nav aria-label="Mobile primary" className="flex-1 overflow-y-auto px-3 py-4 scrollbar-none">
            {groups.map((group) => (
              <div key={group.id} className="mb-5 last:mb-1">
                <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  {group.label}
                </p>
                <div className="grid gap-1">
                  {group.items.map((item) => {
                    const IconComponent = item.icon;
                    const isActive = isNavItemActive(location.pathname, item);
                    const badge = resolveBadge(item);
                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={onClose}
                        aria-current={isActive ? 'page' : undefined}
                        className={`group relative flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-all duration-200 hover:bg-white/10 ${
                          isActive ? 'border border-white/20 bg-white/10 text-white' : 'border border-transparent text-slate-200'
                        }`}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-ember-flame-start via-ember-flame-mid to-ember-flame-end" />
                        )}
                        <span className={`flex-shrink-0 rounded-md bg-gradient-to-r ${item.gradient} p-1.5`}>
                          <IconComponent className="h-4 w-4 text-white" />
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
        </div>
      </div>
    </div>
  );
};

export default MobileNavDrawer;
