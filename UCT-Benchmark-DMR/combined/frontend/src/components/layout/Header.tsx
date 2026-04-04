import { Link, useNavigate } from 'react-router-dom';
import {
  Menu,
  Bell,
  User,
  LogOut,
  Settings,
  Moon,
  Sun,
  Orbit,
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
import { useTheme } from '@/components/theme-provider';
import { useAuthStore } from '@/stores/authStore';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/welcome');
  };

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
        <Link to="/" className="flex items-center gap-3 mr-3 lg:mr-8 group">
          {/* Animated orbital logo */}
          <div className="relative w-10 h-10 flex items-center justify-center">
            {/* Outer orbit ring */}
            <div className="absolute inset-0 border border-cosmic-cyan/30 rounded-full animate-orbit-slow" />
            {/* Inner orbit ring */}
            <div className="absolute inset-1 border border-stellar-purple/20 rounded-full animate-orbit-reverse" />
            {/* Center icon */}
            <div className="relative z-10 w-6 h-6 rounded-full bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center shadow-glow-cyan group-hover:shadow-glow-lg transition-shadow duration-300">
              <Orbit className="h-3.5 w-3.5 text-white" />
            </div>
            {/* Orbiting dot */}
            <div className="absolute w-2 h-2 rounded-full bg-cosmic-cyan shadow-glow-cyan animate-orbit" style={{ top: '0', left: '50%', marginLeft: '-4px' }} />
          </div>
          <div className="hidden sm:block">
            <span className="font-display font-bold text-lg tracking-tight">
              <span className="text-gradient-cosmic">SpOC</span>
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
              <div className="p-4 text-center text-sm text-muted-foreground">
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
                  <p className="text-sm font-medium leading-none font-display">{user?.username || 'User'}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.email || ''}</p>
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
                <Link to="/profile" className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="focus:bg-white/5 cursor-pointer"
              >
                {theme === 'dark' ? (
                  <Sun className="mr-2 h-4 w-4" />
                ) : (
                  <Moon className="mr-2 h-4 w-4" />
                )}
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem onClick={handleLogout} className="text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer">
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
