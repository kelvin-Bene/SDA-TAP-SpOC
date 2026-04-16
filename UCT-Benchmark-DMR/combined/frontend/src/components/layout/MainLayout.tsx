import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Close sidebar on route change (especially important on mobile)
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen sm:min-h-dvh bg-background space-bg">
      {/* Animated starfield background */}
      <div className="starfield" aria-hidden="true" />

      {/* Subtle grid overlay */}
      <div className="fixed inset-0 grid-pattern opacity-30 pointer-events-none" aria-hidden="true" />

      {/* Main content */}
      <div className="relative z-10">
        <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        <div className="flex">
          <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <main
            className={cn(
              'flex-1 transition-all duration-300 ease-in-out',
              sidebarOpen ? 'lg:ml-72' : 'lg:ml-0'
            )}
          >
            <div className="container mx-auto px-4 py-8 lg:px-8">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
