import * as React from 'react';
import { NavLink, useNavigate } from 'react-router';
import { cn } from '../../utils/cn';
import {
  LayoutDashboard,
  Building,
  Compass,
  Users,
  Target,
  FileCheck,
  Calendar,
  Clock,
  FolderOpen,
  Bell,
  Activity,
  LogOut,
  Globe,
} from 'lucide-react';
import { Avatar } from '../ui/Avatar';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

const primaryNav = [
  { name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { name: 'Properties', to: '/properties', icon: Building },
  { name: 'Boundary Sketches', to: '/sketches', icon: Compass },
  { name: 'Clients', to: '/clients', icon: Users },
  { name: 'Leads', to: '/leads', icon: Target },
  { name: 'Requirements', to: '/requirements', icon: FileCheck },
  { name: 'Site Visits', to: '/site-visits', icon: Calendar },
  { name: 'Follow-ups', to: '/follow-ups', icon: Clock },
  { name: 'Documents', to: '/documents', icon: FolderOpen },
];

const secondaryNav = [
  { name: 'Notifications', to: '/notifications', icon: Bell, badgeKey: 'notifications' },
  { name: 'Audit Logs', to: '/audit-logs', icon: Activity },
  { name: 'Public Directory', to: '/public/properties', icon: Globe },
];

export function Sidebar({ className }: { className?: string }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { unreadCount } = useNotifications();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : 'VK';

  return (
    <div className={cn("flex h-full w-60 flex-col border-r border-[var(--color-border-ui)] bg-white", className)}>
      <div className="flex h-16 shrink-0 items-center px-6 border-b border-[var(--color-border-ui)]">
        <span className="font-serif text-2xl font-bold tracking-tight text-[var(--color-forest)]">RED</span>
        <span className="ml-2 mt-0.5 rounded-[4px] bg-[var(--color-parchment)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-ink-secondary)]">
          TN V1
        </span>
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto px-3 py-4">
        <nav className="flex-1 space-y-1">
          {primaryNav.map((item) => (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'group flex items-center justify-between rounded-[6px] px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-[var(--color-parchment)] text-[var(--color-forest)]'
                    : 'text-[var(--color-ink-secondary)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-ink)]'
                )
              }
            >
              {({ isActive }) => (
                <div className="flex items-center">
                  <item.icon
                    className={cn(
                      'mr-3 h-4 w-4 shrink-0',
                      isActive ? 'text-[var(--color-gold)]' : 'text-[var(--color-ink-muted)] group-hover:text-[var(--color-ink-secondary)]'
                    )}
                    aria-hidden="true"
                  />
                  <span>{item.name}</span>
                </div>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6 border-t border-[var(--color-border-ui)] pt-4">
          <h3 className="px-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]" id="secondary-nav-heading">
            Operations & Compliance
          </h3>
          <nav className="mt-2 space-y-1" aria-labelledby="secondary-nav-heading">
            {secondaryNav.map((item) => (
              <NavLink
                key={item.name}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center justify-between rounded-[6px] px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-[var(--color-parchment)] text-[var(--color-forest)]'
                      : 'text-[var(--color-ink-secondary)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-ink)]'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center">
                      <item.icon
                        className={cn(
                          'mr-3 h-4 w-4 shrink-0',
                          isActive ? 'text-[var(--color-gold)]' : 'text-[var(--color-ink-muted)] group-hover:text-[var(--color-ink-secondary)]'
                        )}
                        aria-hidden="true"
                      />
                      <span>{item.name}</span>
                    </div>
                    {item.badgeKey === 'notifications' && unreadCount > 0 && (
                      <span className="rounded-full bg-[var(--color-gold)] px-2 py-0.5 text-[10px] font-bold text-white">
                        {unreadCount}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      <div className="border-t border-[var(--color-border-ui)] p-3">
        <div className="flex w-full items-center justify-between rounded-[6px] px-2 py-1.5 hover:bg-[var(--color-parchment)] transition-colors">
          <div className="flex items-center flex-1 min-w-0">
            <Avatar fallback={initials} className="h-8 w-8 text-xs font-semibold" />
            <div className="ml-2.5 min-w-0">
              <p className="truncate text-xs font-semibold text-[var(--color-ink)]">
                {user?.full_name || 'Consultant'}
              </p>
              <p className="truncate text-[10px] text-[var(--color-ink-muted)]">
                {user?.role || 'CONSULTANT'}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="text-[var(--color-ink-muted)] hover:text-red-700 transition-colors p-1.5 rounded hover:bg-white"
            title="Log Out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
