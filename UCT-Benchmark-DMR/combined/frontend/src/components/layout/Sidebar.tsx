import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Plus,
  Upload,
  FileText,
  Trophy,
  BookOpen,
  Settings,
  X,
  ChevronDown,
  Sparkles,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useRef, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useSubmissions } from '@/hooks/useSubmissions';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  title: string;
  href?: string;
  icon: React.ElementType;
  children?: { title: string; href: string }[];
}

// Public nav items — always visible (only non-data pages)
const publicNavItems: NavItem[] = [
  {
    title: 'Documentation',
    href: '/docs',
    icon: BookOpen,
  },
];

// Authenticated-only nav items
const authNavItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Datasets',
    icon: Database,
    children: [
      { title: 'Browse Datasets', href: '/datasets' },
      { title: 'Generate Dataset', href: '/datasets/generate' },
      { title: 'My Datasets', href: '/datasets/my-datasets' },
    ],
  },
  {
    title: 'Submit',
    icon: Upload,
    children: [
      { title: 'New Submission', href: '/submit' },
      { title: 'My Submissions', href: '/submit/my-submissions' },
    ],
  },
  {
    title: 'Leaderboard',
    href: '/leaderboard',
    icon: Trophy,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

function NavItemComponent({ item }: { item: NavItem }) {
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(
    item.children?.some((child) => location.pathname === child.href) ?? false
  );

  const isActive = item.href ? location.pathname === item.href : false;
  const hasActiveChild = item.children?.some((child) => location.pathname === child.href);

  if (item.children) {
    return (
      <div className="space-y-1">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            'flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200',
            hasActiveChild
              ? 'bg-gradient-to-r from-cosmic-cyan/10 to-cosmic-blue/10 text-foreground border border-cosmic-cyan/20'
              : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
          )}
        >
          <div className="flex items-center gap-3">
            <item.icon className={cn(
              'h-5 w-5',
              hasActiveChild ? 'text-cosmic-cyan' : ''
            )} />
            {item.title}
          </div>
          <ChevronDown
            className={cn('h-4 w-4 transition-transform duration-200', isExpanded && 'rotate-180')}
          />
        </button>
        <div
          className={cn(
            'overflow-hidden transition-all duration-200',
            isExpanded ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'
          )}
        >
          <div className="ml-4 mt-1 space-y-1 border-l border-white/10 pl-4">
            {item.children.map((child) => (
              <Link
                key={child.href}
                to={child.href}
                className={cn(
                  'block rounded-lg px-3 py-2 text-sm transition-all duration-200',
                  location.pathname === child.href
                    ? 'bg-cosmic-cyan/10 text-cosmic-cyan font-medium'
                    : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
                )}
              >
                {child.title}
              </Link>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <Link
      to={item.href!}
      className={cn(
        'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 group',
        isActive
          ? 'bg-gradient-to-r from-cosmic-cyan/10 to-cosmic-blue/10 text-foreground border border-cosmic-cyan/20'
          : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
      )}
    >
      <item.icon className={cn(
        'h-5 w-5 transition-colors',
        isActive ? 'text-cosmic-cyan' : 'group-hover:text-cosmic-cyan'
      )} />
      {item.title}
      {isActive && (
        <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cosmic-cyan shadow-glow-cyan" />
      )}
    </Link>
  );
}

function RecentActivitySection() {
  const { data: submissions } = useSubmissions();
  const recentCompleted = (submissions ?? [])
    .filter((s) => s.status === 'completed')
    .slice(0, 3);

  if (recentCompleted.length === 0) return null;

  return (
    <div className="mt-8 space-y-3">
      <h4 className="px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
        <Sparkles className="h-3 w-3" />
        Recent Results
      </h4>
      <div className="space-y-1">
        {recentCompleted.map((sub) => (
          <Link
            key={sub.id}
            to={`/results/${sub.id}`}
            className="flex items-center gap-3 rounded-lg px-4 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground transition-all duration-200 group"
          >
            <FileText className="h-4 w-4 group-hover:text-cosmic-cyan transition-colors" />
            <span className="truncate">{sub.algorithmName} {sub.version}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { isAuthenticated } = useAuthStore();
  const navItems = isAuthenticated ? authNavItems : publicNavItems;
  const asideRef = useRef<HTMLElement>(null);

  // Apply `inert` imperatively so the off-canvas drawer doesn't trap focus or
  // leak into the a11y tree while closed. (React 18 types lack `inert`; DOM
  // attribute set/remove is universally supported.)
  useEffect(() => {
    const el = asideRef.current;
    if (!el) return;
    if (isOpen) el.removeAttribute('inert');
    else el.setAttribute('inert', '');
  }, [isOpen]);

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        ref={asideRef}
        aria-hidden={!isOpen}
        className={cn(
          'fixed left-0 top-14 sm:top-16 z-40 h-[calc(100dvh-3.5rem)] sm:h-[calc(100dvh-4rem)] w-[min(18rem,calc(100vw-3rem))] sm:w-72 transition-transform duration-300 ease-in-out pb-safe',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Glass background */}
        <div className="absolute inset-0 bg-background/80 backdrop-blur-xl border-r border-white/10" />

        <div className="relative h-full flex flex-col">
          {/* Mobile close button */}
          <div className="flex items-center justify-between p-4 lg:hidden border-b border-white/10">
            <span className="font-display font-semibold">Menu</span>
            <Button variant="ghost" size="icon" onClick={onClose} className="hover:bg-white/5">
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-4 py-6 scrollbar-thin">
            <nav className="space-y-2">
              {navItems.map((item) => (
                <NavItemComponent key={item.title} item={item} />
              ))}
            </nav>

            {/* Quick Actions — only when authenticated */}
            {isAuthenticated && (
            <div className="mt-8 space-y-3">
              <h4 className="px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Zap className="h-3 w-3" />
                Quick Actions
              </h4>
              <Link to="/datasets/generate">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-3 border-dashed border-white/20 bg-white/5 hover:bg-white/10 hover:border-cosmic-cyan/50 transition-all duration-200"
                >
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 flex items-center justify-center">
                    <Plus className="h-4 w-4 text-cosmic-cyan" />
                  </div>
                  Generate Dataset
                </Button>
              </Link>
              <Link to="/submit">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-3 border-dashed border-white/20 bg-white/5 hover:bg-white/10 hover:border-stellar-purple/50 transition-all duration-200"
                >
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-stellar-purple/20 to-cosmic-blue/20 flex items-center justify-center">
                    <Upload className="h-4 w-4 text-stellar-purple" />
                  </div>
                  Upload Submission
                </Button>
              </Link>
            </div>
            )}

            {/* Recent Activity — only when authenticated, populated from real data */}
            {isAuthenticated && <RecentActivitySection />}
          </ScrollArea>

          {/* Footer */}
          <div className="border-t border-white/10 p-4">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="relative">
                <div className="w-2 h-2 rounded-full bg-aurora-green" />
                <div className="absolute inset-0 w-2 h-2 rounded-full bg-aurora-green animate-ping opacity-75" />
              </div>
              <span>All systems operational</span>
              <span className="ml-auto text-muted-foreground/50">v{__APP_VERSION__}</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
