import { Link, useNavigate } from 'react-router-dom';
import {
  Menu,
  Bell,
  User,
  LogOut,
  Settings,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/stores/authStore';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4 lg:px-8">
        {/* Menu Button */}
        <Button
          variant="ghost"
          size="icon"
          className="lg:mr-4 hover:bg-white/5"
          onClick={onMenuClick}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>

        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 mr-8 group">
          <div className="flex items-center gap-1.5 group-hover:scale-[1.02] transition-transform duration-300">
            <div className="h-9 w-9 rounded bg-white/90 p-0.5 flex items-center justify-center">
              <img src="/cfc-emblem.png" alt="Combat Forces Command" className="h-full w-full object-contain" />
            </div>
            <div className="h-9 rounded bg-white/90 px-1 py-0.5 items-center justify-center hidden sm:flex">
              <img src="/sda-tap-lab-logo.png" alt="SDA TAP Lab" className="h-full object-contain" />
            </div>
          </div>
          <div className="hidden sm:block">
            <span className="font-display font-bold text-lg tracking-tight">
              <span className="text-gradient-cosmic">UCT Benchmark</span>
            </span>
            <span className="text-muted-foreground text-xs block -mt-0.5 tracking-wide">
              Platform
            </span>
          </div>
        </Link>

        {/* Primary Navigation */}
        <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
          {[
            ...(user
              ? [
                  { to: '/datasets', label: 'Datasets' },
                  { to: '/submit', label: 'Submit' },
                  { to: '/leaderboard', label: 'Leaderboard' },
                ]
              : []),
            { to: '/docs', label: 'Docs' },
          ].map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="relative px-4 py-2 text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-white/5 group"
            >
              {link.label}
              <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue group-hover:w-1/2 transition-all duration-300" />
            </Link>
          ))}
        </nav>

        {/* Right Side Actions */}
        <div className="ml-auto flex items-center gap-2">
          {user ? (
            <>
              {/* Notifications — only when authenticated */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="relative hover:bg-white/5">
                    <Bell className="h-5 w-5" />
                    <span className="sr-only">Notifications</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80 glass border-white/10">
                  <DropdownMenuLabel className="font-display">Notifications</DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-white/10" />
                  <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                    <Bell className="h-8 w-8 text-muted-foreground/50 mb-3" />
                    <p className="text-sm font-medium text-muted-foreground">No notifications yet</p>
                    <p className="text-xs text-muted-foreground/70 mt-1">
                      We'll notify you when something important happens.
                    </p>
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* User Menu — only when authenticated */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="rounded-full hover:bg-white/5 relative group">
                    <div className="absolute inset-0 rounded-full bg-gradient-to-r from-cosmic-cyan/20 to-stellar-purple/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <User className="h-5 w-5 relative z-10" />
                    <span className="sr-only">User menu</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56 glass border-white/10">
                  <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-none font-display">{user?.username ?? 'User'}</p>
                      <p className="text-xs leading-none text-muted-foreground">{user?.email ?? ''}</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-white/10" />
                  <DropdownMenuItem asChild className="focus:bg-white/5 cursor-pointer">
                    <Link to="/profile" className="flex items-center">
                      <User className="mr-2 h-4 w-4" />
                      Profile
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="focus:bg-white/5 cursor-pointer">
                    <Link to="/settings" className="flex items-center">
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator className="bg-white/10" />
                  <DropdownMenuItem
                    onClick={() => {
                      logout();
                      navigate('/login');
                    }}
                    className="text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            /* Sign In button — shown when not authenticated */
            <Button
              variant="outline"
              size="sm"
              className="border-cosmic-cyan/30 hover:bg-cosmic-cyan/10 hover:border-cosmic-cyan/50 transition-all duration-200"
              onClick={() => navigate('/login')}
            >
              Sign In
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
