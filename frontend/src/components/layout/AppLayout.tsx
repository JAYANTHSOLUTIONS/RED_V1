import * as React from 'react';
import { Outlet, useLocation } from 'react-router';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Drawer } from '../ui/Drawer';

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const location = useLocation();

  // Close sidebar on route change
  React.useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex h-screen w-full bg-[var(--color-parchment)] overflow-hidden">
      {/* Desktop Sidebar */}
      <div className="hidden lg:flex lg:w-60 lg:flex-col lg:fixed lg:inset-y-0 lg:z-50">
        <Sidebar />
      </div>

      {/* Mobile Sidebar (Drawer) */}
      <Drawer
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        className="w-64 max-w-xs p-0 sm:w-64"
      >
        <Sidebar className="w-full border-r-0" />
      </Drawer>

      {/* Main Content */}
      <div className="flex flex-1 flex-col lg:pl-60">
        <Topbar onMenuClick={() => setSidebarOpen(true)} />
        
        <main className="flex-1 overflow-y-auto outline-none" tabIndex={-1}>
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
