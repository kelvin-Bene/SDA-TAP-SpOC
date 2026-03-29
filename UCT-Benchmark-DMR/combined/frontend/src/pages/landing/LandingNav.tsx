import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Orbit, Moon, Sun, LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme-provider';

const NAV_LINKS = [
  { href: '#mission', label: 'Mission' },
  { href: '#problem', label: 'Problem' },
  { href: '#solution', label: 'Solution' },
  { href: '#capabilities', label: 'Capabilities' },
  { href: '#access', label: 'Access' },
];

export function LandingNav() {
  const { theme, setTheme } = useTheme();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 40);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-background/80 backdrop-blur-xl border-b border-white/10 shadow-lg'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <a href="#mission" className="flex items-center gap-3 group">
          <div className="relative w-10 h-10 flex items-center justify-center">
            <div className="absolute inset-0 border border-cosmic-cyan/30 rounded-full animate-orbit-slow" />
            <div className="absolute inset-1 border border-stellar-purple/20 rounded-full animate-orbit-reverse" />
            <div className="relative z-10 w-6 h-6 rounded-full bg-gradient-to-br from-cosmic-cyan to-cosmic-blue flex items-center justify-center shadow-glow-cyan group-hover:shadow-glow-lg transition-shadow duration-300">
              <Orbit className="h-3.5 w-3.5 text-white" />
            </div>
          </div>
          <span className="font-display font-bold text-lg tracking-tight text-gradient-cosmic hidden sm:block">
            SpOC
          </span>
        </a>

        {/* Center links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-white/5"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="hover:bg-white/5"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Button asChild size="sm" className="bg-gradient-cosmic hover:opacity-90 text-white border-0">
            <Link to="/login">
              <LogIn className="h-4 w-4 mr-2" />
              Sign In
            </Link>
          </Button>
        </div>
      </div>
    </nav>
  );
}
