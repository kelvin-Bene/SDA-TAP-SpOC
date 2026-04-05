import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Moon, Sun, LogIn } from 'lucide-react';
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
          <div className="flex items-center gap-2">
            <img src="/cfc-emblem.png" alt="Combat Forces Command" className="h-9 w-9 object-contain" />
            <img src="/sda-tap-lab-logo.png" alt="SDA TAP Lab" className="h-8 object-contain hidden sm:block" />
          </div>
          <span className="font-display font-bold text-lg tracking-tight text-gradient-cosmic hidden sm:block">
            UCT Benchmark
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
              Get Started
            </Link>
          </Button>
        </div>
      </div>
    </nav>
  );
}
