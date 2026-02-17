import { Link, useNavigate } from 'react-router-dom';
import {
  Menu,
  Bell,
  User,
  LogOut,
  Settings,
  Moon,
  Sun,
  Monitor,
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { useTheme } from '@/components/theme-provider';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const user = useAuthStore((s) => s.user);

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
          {/* Orbital globe logo */}
          <div className="relative w-10 h-10 flex items-center justify-center group-hover:scale-105 transition-transform duration-300">
            <svg
              viewBox="0 0 100 100"
              className="w-10 h-10 drop-shadow-[0_0_8px_hsl(220,82%,58%,0.4)] group-hover:drop-shadow-[0_0_14px_hsl(220,82%,58%,0.6)] transition-all duration-300"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Orbit ring 1 - tilted left */}
              <ellipse
                cx="50" cy="50" rx="45" ry="18"
                transform="rotate(-30 50 50)"
                stroke="hsl(220, 82%, 58%)"
                strokeWidth="2.5"
                strokeLinecap="round"
                opacity="0.8"
              />
              {/* Orbit ring 2 - tilted right */}
              <ellipse
                cx="50" cy="50" rx="45" ry="18"
                transform="rotate(30 50 50)"
                stroke="hsl(265, 72%, 58%)"
                strokeWidth="2.5"
                strokeLinecap="round"
                opacity="0.7"
              />
              {/* Orbit ring 3 - horizontal */}
              <ellipse
                cx="50" cy="50" rx="45" ry="18"
                transform="rotate(90 50 50)"
                stroke="hsl(210, 85%, 58%)"
                strokeWidth="2"
                strokeLinecap="round"
                opacity="0.5"
              />
              {/* Central globe */}
              <circle
                cx="50" cy="50" r="12"
                fill="url(#globeGradient)"
              />
              {/* Globe highlight */}
              <circle
                cx="46" cy="46" r="5"
                fill="white"
                opacity="0.15"
              />
              <defs>
                <radialGradient id="globeGradient" cx="40%" cy="40%">
                  <stop offset="0%" stopColor="hsl(210, 85%, 65%)" />
                  <stop offset="100%" stopColor="hsl(230, 80%, 45%)" />
                </radialGradient>
              </defs>
            </svg>
          </div>
          <div className="hidden sm:block">
            <span className="font-display font-bold text-lg tracking-tight">
              <span className="text-gradient-cosmic">UI</span>
            </span>
            <span className="text-muted-foreground text-xs block -mt-0.5 tracking-wide">
              UCTP Benchmark
            </span>
          </div>
        </Link>

        {/* Primary Navigation */}
        <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
          {[
            { to: '/datasets', label: 'Datasets' },
            { to: '/submit', label: 'Submit' },
            { to: '/leaderboard', label: 'Leaderboard' },
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
          {/* Notifications */}
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
              <div className="p-4 text-center text-muted-foreground text-sm">
                No new notifications
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Menu */}
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
                  <p className="text-sm font-medium leading-none font-display">
                    {user?.username || user?.email?.split('@')[0] || 'User'}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email || ''}
                  </p>
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
              <DropdownMenuSub>
                <DropdownMenuSubTrigger className="focus:bg-white/5">
                  {theme === 'dark' ? (
                    <Moon className="mr-2 h-4 w-4" />
                  ) : theme === 'light' ? (
                    <Sun className="mr-2 h-4 w-4" />
                  ) : (
                    <Monitor className="mr-2 h-4 w-4" />
                  )}
                  Theme
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent className="glass border-white/10">
                  <DropdownMenuRadioGroup value={theme} onValueChange={(value) => setTheme(value as 'light' | 'dark' | 'system')}>
                    <DropdownMenuRadioItem value="light" className="focus:bg-white/5 cursor-pointer">
                      <Sun className="mr-2 h-4 w-4" />
                      Light
                    </DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="dark" className="focus:bg-white/5 cursor-pointer">
                      <Moon className="mr-2 h-4 w-4" />
                      Dark
                    </DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="system" className="focus:bg-white/5 cursor-pointer">
                      <Monitor className="mr-2 h-4 w-4" />
                      System
                    </DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem
                className="text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer"
                onClick={async () => {
                  await logout();
                  navigate('/login');
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
