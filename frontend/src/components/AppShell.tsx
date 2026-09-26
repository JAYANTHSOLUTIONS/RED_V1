import { useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router';
import {
  LayoutDashboard, Building2, Users, TrendingUp, ClipboardList,
  MapPin, Bell, FileText, ScrollText, LogOut, ChevronDown,
  Search, Menu, X, CheckSquare, AlertCircle
} from 'lucide-react';
import { notifications as allNotifications } from '../data/mock';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties', icon: Building2, label: 'Properties' },
  { to: '/clients', icon: Users, label: 'Clients' },
  { to: '/leads', icon: TrendingUp, label: 'Leads' },
  { to: '/requirements', icon: ClipboardList, label: 'Requirements' },
  { to: '/site-visits', icon: MapPin, label: 'Site Visits' },
  { to: '/follow-ups', icon: CheckSquare, label: 'Follow-ups' },
];

const SECONDARY_NAV = [
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/notifications', icon: Bell, label: 'Notifications', badge: true },
  { to: '/audit-logs', icon: ScrollText, label: 'Audit Logs' },
];

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const unreadCount = allNotifications.filter(n => !n.read).length;

  const pageTitle = (() => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return 'Dashboard';
    if (path.startsWith('/properties/new')) return 'New Property';
    if (path.match(/\/properties\/[^/]+$/)) return 'Property Detail';
    if (path.startsWith('/properties')) return 'Properties';
    if (path.match(/\/clients\/[^/]+$/)) return 'Client Detail';
    if (path.startsWith('/clients')) return 'Clients';
    if (path.match(/\/leads\/[^/]+$/)) return 'Lead Detail';
    if (path.startsWith('/leads')) return 'Leads';
    if (path.match(/\/requirements\/[^/]+\/matches/)) return 'Matching Results';
    if (path.match(/\/requirements\/[^/]+$/)) return 'Requirement Detail';
    if (path.startsWith('/requirements')) return 'Requirements';
    if (path.match(/\/site-visits\/[^/]+$/)) return 'Site Visit Detail';
    if (path.startsWith('/site-visits')) return 'Site Visits';
    if (path.startsWith('/follow-ups')) return 'Follow-ups';
    if (path.startsWith('/documents')) return 'Documents';
    if (path.startsWith('/notifications')) return 'Notifications';
    if (path.startsWith('/audit-logs')) return 'Audit Logs';
    return 'RED V1';
  })();

  const handleLogout = () => navigate('/login');

  return (
    <div className="h-full flex bg-[#F7F7F5]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-60 flex flex-col bg-white border-r border-[#E4E5E2] transition-transform duration-200 lg:relative lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-5 border-b border-[#E4E5E2] flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-[#1F3A37] rounded flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold tracking-wider">R</span>
            </div>
            <div>
              <span className="text-[#1C2422] font-semibold text-sm tracking-wide">RED</span>
              <span className="text-[#8A928F] text-xs ml-1">V1</span>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-[#68716E] hover:text-[#1C2422] p-1"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-3">
          <div className="space-y-0.5">
            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-[6px] text-sm transition-colors ${
                    isActive
                      ? 'bg-[#1F3A37]/8 text-[#1F3A37] font-medium border-l-2 border-[#1F3A37] -ml-px pl-[13px]'
                      : 'text-[#68716E] hover:bg-[#F7F7F5] hover:text-[#1C2422]'
                  }`
                }
              >
                <Icon size={16} strokeWidth={1.75} />
                {label}
              </NavLink>
            ))}
          </div>

          <div className="mt-5 pt-4 border-t border-[#E4E5E2] space-y-0.5">
            <p className="px-3 mb-2 text-[10px] font-semibold text-[#8A928F] uppercase tracking-widest">Admin</p>
            {SECONDARY_NAV.map(({ to, icon: Icon, label, badge }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-[6px] text-sm transition-colors ${
                    isActive
                      ? 'bg-[#1F3A37]/8 text-[#1F3A37] font-medium border-l-2 border-[#1F3A37] -ml-px pl-[13px]'
                      : 'text-[#68716E] hover:bg-[#F7F7F5] hover:text-[#1C2422]'
                  }`
                }
              >
                <Icon size={16} strokeWidth={1.75} />
                {label}
                {badge && unreadCount > 0 && (
                  <span className="ml-auto bg-[#1F3A37] text-white text-[10px] font-semibold rounded-full w-4 h-4 flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Profile */}
        <div className="border-t border-[#E4E5E2] p-3 flex-shrink-0">
          <div className="flex items-center gap-3 px-2 py-2 rounded-[6px] hover:bg-[#F7F7F5] cursor-pointer group">
            <div className="w-7 h-7 rounded-full bg-[#1F3A37] flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-semibold">RC</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[#1C2422] truncate">Ravi Chandran</p>
              <p className="text-[10px] text-[#8A928F] truncate">ravi@red.co.in</p>
            </div>
            <button
              onClick={handleLogout}
              className="opacity-0 group-hover:opacity-100 text-[#8A928F] hover:text-[#A33A3A] transition-all"
              title="Logout"
            >
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-[#E4E5E2] flex items-center px-4 lg:px-6 gap-4 flex-shrink-0 z-10">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden text-[#68716E] hover:text-[#1C2422] p-1 -ml-1"
          >
            <Menu size={20} />
          </button>

          <div className="hidden sm:flex items-center gap-1.5 flex-1 max-w-xs">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8A928F]" />
              <input
                type="text"
                placeholder="Search properties, clients…"
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-[#E4E5E2] rounded-[6px] bg-[#F7F7F5] text-[#1C2422] placeholder-[#8A928F] focus:outline-none focus:ring-1 focus:ring-[#1F3A37] focus:border-[#1F3A37] focus:bg-white transition-colors"
              />
            </div>
          </div>

          <div className="hidden sm:block h-4 w-px bg-[#E4E5E2]" />
          <p className="hidden sm:block text-sm font-medium text-[#1C2422] flex-1">{pageTitle}</p>

          <div className="ml-auto flex items-center gap-2">
            <button
              className="relative p-2 text-[#68716E] hover:text-[#1C2422] hover:bg-[#F7F7F5] rounded-[6px] transition-colors"
              onClick={() => navigate('/notifications')}
            >
              <Bell size={17} />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-[#A33A3A] rounded-full" />
              )}
            </button>

            <div className="relative">
              <button
                onClick={() => setProfileOpen(p => !p)}
                className="flex items-center gap-2 px-2 py-1.5 rounded-[6px] hover:bg-[#F7F7F5] transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-[#1F3A37] flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-semibold">RC</span>
                </div>
                <span className="hidden md:block text-sm font-medium text-[#1C2422]">Ravi Chandran</span>
                <ChevronDown size={13} className="text-[#8A928F]" />
              </button>
              {profileOpen && (
                <div className="absolute right-0 top-full mt-1 w-52 bg-white border border-[#E4E5E2] rounded-[8px] shadow-md py-1 z-50">
                  <div className="px-3 py-2 border-b border-[#E4E5E2]">
                    <p className="text-xs font-medium text-[#1C2422]">Ravi Chandran</p>
                    <p className="text-[10px] text-[#8A928F]">ravi@red.co.in</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#A33A3A] hover:bg-[#FAECEC] transition-colors"
                  >
                    <LogOut size={14} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
