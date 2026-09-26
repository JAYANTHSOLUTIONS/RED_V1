import * as React from 'react';
import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { cn } from '../../utils/cn';
import { Search, Bell, Menu, LogOut, Check, ExternalLink, ShieldCheck } from 'lucide-react';
import { Avatar } from '../ui/Avatar';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

interface TopbarProps {
  onMenuClick?: () => void;
  className?: string;
}

export function Topbar({ onMenuClick, className }: TopbarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { unreadCount, notifications, markAsRead, markAllAsRead } = useNotifications();

  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setIsNotifOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/properties?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

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
    <header
      className={cn(
        'sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-[var(--color-border-ui)] bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8',
        className
      )}
    >
      <button
        type="button"
        className="-m-2.5 p-2.5 text-[var(--color-ink-muted)] lg:hidden hover:text-[var(--color-ink)]"
        onClick={onMenuClick}
      >
        <span className="sr-only">Open sidebar</span>
        <Menu className="h-6 w-6" aria-hidden="true" />
      </button>

      {/* Separator for mobile */}
      <div className="h-6 w-px bg-[var(--color-border-ui)] lg:hidden" aria-hidden="true" />

      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        <form className="relative flex flex-1" onSubmit={handleSearch}>
          <label htmlFor="search-field" className="sr-only">
            Search
          </label>
          <Search
            className="pointer-events-none absolute inset-y-0 left-0 h-full w-5 text-[var(--color-ink-muted)]"
            aria-hidden="true"
          />
          <input
            id="search-field"
            className="block h-full w-full border-0 py-0 pl-8 pr-0 text-[var(--color-ink)] placeholder:text-[var(--color-ink-muted)] focus:ring-0 sm:text-sm bg-transparent outline-none"
            placeholder="Search properties, clients, leads... (Press Enter)"
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </form>

        <div className="flex items-center gap-x-4 lg:gap-x-6">
          {/* Notifications Dropdown */}
          <div className="relative" ref={notifRef}>
            <button
              type="button"
              className="-m-2.5 p-2.5 text-[var(--color-ink-muted)] hover:text-[var(--color-ink)] relative transition-colors"
              onClick={() => setIsNotifOpen((prev) => !prev)}
            >
              <span className="sr-only">View notifications</span>
              <Bell className="h-5 w-5" aria-hidden="true" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[var(--color-gold)] px-1 text-[10px] font-bold text-white ring-2 ring-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {isNotifOpen && (
              <div className="absolute right-0 mt-3 w-80 sm:w-96 rounded-md bg-white p-2 shadow-lg ring-1 ring-black/5 z-50 border border-[var(--color-border-ui)]">
                <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border-ui)]">
                  <div className="font-semibold text-xs text-[var(--color-ink)] uppercase tracking-wider">
                    Notifications {unreadCount > 0 && `(${unreadCount} unread)`}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="text-[11px] text-[var(--color-gold)] hover:underline flex items-center gap-1 font-medium"
                    >
                      <Check className="h-3 w-3" /> Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-72 overflow-y-auto divide-y divide-gray-100 py-1">
                  {notifications.length === 0 ? (
                    <div className="px-4 py-6 text-center text-xs text-[var(--color-ink-muted)]">
                      No notifications yet.
                    </div>
                  ) : (
                    notifications.slice(0, 5).map((n) => (
                      <div
                        key={n.id}
                        className={cn(
                          'p-3 hover:bg-[var(--color-parchment-warm)] transition-colors cursor-pointer text-xs',
                          !n.is_read ? 'bg-amber-50/50' : ''
                        )}
                        onClick={() => {
                          if (!n.is_read) markAsRead(n.id);
                          setIsNotifOpen(false);
                          navigate('/notifications');
                        }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-[var(--color-ink)] line-clamp-1">{n.title}</span>
                          {!n.is_read && (
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-gold)] mt-1"></span>
                          )}
                        </div>
                        <p className="text-[var(--color-ink-muted)] line-clamp-2 mt-0.5">{n.message}</p>
                        <span className="text-[10px] text-gray-400 mt-1 block">
                          {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    ))
                  )}
                </div>

                <div className="border-t border-[var(--color-border-ui)] pt-1 px-1">
                  <Link
                    to="/notifications"
                    onClick={() => setIsNotifOpen(false)}
                    className="block text-center py-2 text-xs font-medium text-[var(--color-primary)] hover:bg-[var(--color-parchment-warm)] rounded"
                  >
                    View all notifications &rarr;
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Separator */}
          <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-[var(--color-border-ui)]" aria-hidden="true" />

          {/* Profile dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              className="-m-1.5 flex items-center p-1.5 focus:outline-none gap-2"
              onClick={() => setIsProfileOpen((prev) => !prev)}
            >
              <span className="sr-only">Open user menu</span>
              <Avatar fallback={initials} className="h-8 w-8 text-xs font-semibold" />
              <div className="hidden md:flex flex-col text-left">
                <span className="text-xs font-medium text-[var(--color-ink)] leading-tight">
                  {user?.full_name || 'Consultant'}
                </span>
                <span className="text-[10px] text-[var(--color-ink-muted)] leading-tight">
                  {user?.role || 'CONSULTANT'}
                </span>
              </div>
            </button>

            {isProfileOpen && (
              <div className="absolute right-0 mt-3 w-56 rounded-md bg-white p-1 shadow-lg ring-1 ring-black/5 z-50 border border-[var(--color-border-ui)]">
                <div className="px-3 py-2 border-b border-[var(--color-border-ui)]">
                  <p className="text-xs font-semibold text-[var(--color-ink)]">{user?.full_name || 'Consultant'}</p>
                  <p className="text-[11px] text-[var(--color-ink-muted)] truncate">{user?.email || 'consultant@red.tn'}</p>
                  <div className="mt-1 flex items-center gap-1 text-[10px] text-[var(--color-primary)]">
                    <ShieldCheck className="h-3 w-3" /> TN Real Estate Verified
                  </div>
                </div>

                <div className="py-1">
                  <Link
                    to="/audit-logs"
                    onClick={() => setIsProfileOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-xs text-[var(--color-ink)] hover:bg-[var(--color-parchment-warm)] rounded"
                  >
                    Audit Trail
                  </Link>
                  <Link
                    to="/public/properties"
                    target="_blank"
                    onClick={() => setIsProfileOpen(false)}
                    className="flex items-center justify-between px-3 py-2 text-xs text-[var(--color-ink)] hover:bg-[var(--color-parchment-warm)] rounded"
                  >
                    <span>Public Directory</span>
                    <ExternalLink className="h-3 w-3 text-gray-400" />
                  </Link>
                </div>

                <div className="border-t border-[var(--color-border-ui)] pt-1">
                  <button
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 px-3 py-2 text-xs text-red-700 hover:bg-red-50 rounded"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
