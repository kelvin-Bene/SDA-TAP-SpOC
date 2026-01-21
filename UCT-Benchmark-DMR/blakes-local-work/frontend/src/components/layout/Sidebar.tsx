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
      <div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            'flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            hasActiveChild
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          )}
        >
          <div className="flex items-center gap-3">
            <item.icon className="h-4 w-4" />
            {item.title}
          </div>
          <ChevronDown
            className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-180')}
          />
        </button>
        {isExpanded && (
          <div className="ml-4 mt-1 space-y-1 border-l pl-4">
            {item.children.map((child) => (
              <Link
                key={child.href}
                to={child.href}
                className={cn(
                  'block rounded-lg px-3 py-2 text-sm transition-colors',
                  location.pathname === child.href
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                {child.title}
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <Link
      to={item.href!}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
      )}
    >
      <item.icon className="h-4 w-4" />
      {item.title}
    </Link>
  );
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] w-64 border-r bg-background transition-transform duration-300 ease-in-out',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Mobile close button */}
          <div className="flex items-center justify-between p-4 lg:hidden">
            <span className="font-semibold">Menu</span>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-3 py-4">
            <nav className="space-y-2">
              {navItems.map((item) => (
                <NavItemComponent key={item.title} item={item} />
              ))}
            </nav>

            {/* Quick Actions */}
            <div className="mt-8 space-y-2">
              <h4 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Quick Actions
              </h4>
              <Link to="/datasets/generate">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Plus className="h-4 w-4" />
                  Generate Dataset
                </Button>
              </Link>
              <Link to="/submit">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Upload className="h-4 w-4" />
                  Upload Submission
                </Button>
              </Link>
            </div>

            {/* Recent Activity */}
            <div className="mt-8 space-y-2">
              <h4 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Recent
              </h4>
              <div className="space-y-1">
                <Link
                  to="/results/1"
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                >
                  <FileText className="h-4 w-4" />
                  <span className="truncate">MyUCTP v2.1 Results</span>
                </Link>
                <Link
                  to="/datasets"
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                >
                  <FolderOpen className="h-4 w-4" />
                  <span className="truncate">LEO-T2-2026-01-15</span>
                </Link>
              </div>
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              All systems operational
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
