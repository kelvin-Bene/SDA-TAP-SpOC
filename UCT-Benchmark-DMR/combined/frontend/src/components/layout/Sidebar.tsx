import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Plus,
  FolderOpen,
  Upload,
  FileText,
  Trophy,
  BookOpen,
  X,
  ChevronDown,
  Sparkles,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useState } from 'react';

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

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
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
    title: 'Documentation',
    href: '/docs',
    icon: BookOpen,
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

export function Sidebar({ isOpen, onClose }: SidebarProps) {
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
        className={cn(
          'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-72 transition-transform duration-300 ease-in-out',
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

            {/* Quick Actions */}
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

            {/* Recent Activity */}
            <div className="mt-8 space-y-3">
              <h4 className="px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Sparkles className="h-3 w-3" />
                Recent
              </h4>
              <div className="space-y-1">
                <Link
                  to="/results/1"
                  className="flex items-center gap-3 rounded-lg px-4 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground transition-all duration-200 group"
                >
                  <FileText className="h-4 w-4 group-hover:text-cosmic-cyan transition-colors" />
                  <span className="truncate">MyUCTP v2.1 Results</span>
                </Link>
                <Link
                  to="/datasets"
                  className="flex items-center gap-3 rounded-lg px-4 py-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground transition-all duration-200 group"
                >
                  <FolderOpen className="h-4 w-4 group-hover:text-cosmic-cyan transition-colors" />
                  <span className="truncate">LEO-T2-2026-01-15</span>
                </Link>
              </div>
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t border-white/10 p-4">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="relative">
                <div className="w-2 h-2 rounded-full bg-aurora-green" />
                <div className="absolute inset-0 w-2 h-2 rounded-full bg-aurora-green animate-ping opacity-75" />
              </div>
              <span>All systems operational</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
