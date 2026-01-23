import { Link } from 'react-router-dom';
import {
  Menu,
  Bell,
  User,
  LogOut,
  Settings,
  Moon,
  Sun,
  Monitor,
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
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/theme-provider';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { theme, setTheme } = useTheme();

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
              UCT Benchmark
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
                <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs bg-gradient-to-r from-cosmic-cyan to-cosmic-blue border-0 animate-pulse-glow">
                  2
                </Badge>
                <span className="sr-only">Notifications</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 glass border-white/10">
              <DropdownMenuLabel className="font-display">Notifications</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem className="flex flex-col items-start gap-1 p-3 focus:bg-white/5 cursor-pointer">
                <div className="font-medium flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-aurora-green" />
                  Submission Complete
                </div>
                <div className="text-sm text-muted-foreground">
                  MyUCTP v2.1 evaluation finished. F1-Score: 0.923
                </div>
                <div className="text-xs text-muted-foreground">2 hours ago</div>
              </DropdownMenuItem>
              <DropdownMenuItem className="flex flex-col items-start gap-1 p-3 focus:bg-white/5 cursor-pointer">
                <div className="font-medium flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cosmic-cyan" />
                  New Dataset Available
                </div>
                <div className="text-sm text-muted-foreground">
                  LEO-T2-2026-01-15 is ready for download
                </div>
                <div className="text-xs text-muted-foreground">5 hours ago</div>
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem className="text-center text-sm text-cosmic-cyan hover:text-cosmic-cyan focus:text-cosmic-cyan focus:bg-white/5 cursor-pointer justify-center">
                View all notifications
              </DropdownMenuItem>
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
                  <p className="text-sm font-medium leading-none font-display">researcher</p>
                  <p className="text-xs leading-none text-muted-foreground">researcher@aerospace.org</p>
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
              <DropdownMenuItem className="text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer">
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
