import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogIn, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const NAV_LINKS = [
  { href: '#mission', label: 'Mission' },
  { href: '#problem', label: 'Problem' },
  { href: '#solution', label: 'Solution' },
  { href: '#capabilities', label: 'Capabilities' },
  { href: '#access', label: 'Access' },
];

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 40);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close the mobile menu whenever the route or hash changes
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname, location.hash]);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 pt-safe ${
        scrolled || mobileOpen
          ? 'bg-background/90 backdrop-blur-xl border-b border-white/10 shadow-lg'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between h-14 sm:h-16 gap-2 px-3 sm:px-6 lg:px-8">
        {/* Logo */}
        <a href="#mission" className="flex items-center gap-3 group min-w-0">
          <div className="flex items-center gap-1.5">
            <div className="h-9 w-9 rounded bg-white/90 p-0.5 flex items-center justify-center shrink-0">
              <img src="/cfc-emblem.png" alt="Combat Forces Command" className="h-full w-full object-contain" />
            </div>
            <div className="h-9 rounded bg-white/90 px-1 py-0.5 items-center justify-center hidden md:flex">
              <img src="/sda-tap-lab-logo.png" alt="SDA TAP Lab" className="h-full object-contain" />
            </div>
          </div>
          <span className="font-display font-bold text-lg tracking-tight text-gradient-cosmic hidden xs:block truncate">
            UCT Benchmark
          </span>
        </a>

        {/* Center links — desktop */}
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
          <a
            href="https://frontend-demo-1542.up.railway.app/"
            className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground transition-colors px-3 py-2"
          >
            Try Demo
          </a>
          <Button asChild size="sm" className="bg-gradient-cosmic hover:opacity-90 text-white border-0">
            <Link to="/login">
              <LogIn className="h-4 w-4 sm:mr-2" />
              <span className="hidden xs:inline">Get Started</span>
            </Link>
          </Button>
          {/* Mobile menu button */}
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            aria-expanded={mobileOpen}
            aria-controls="landing-mobile-menu"
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            className="md:hidden inline-flex items-center justify-center h-11 w-11 rounded-md text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu panel */}
      <div
        id="landing-mobile-menu"
        className={`md:hidden overflow-hidden border-t border-white/10 bg-background/95 backdrop-blur-xl transition-[max-height,opacity] duration-300 ease-in-out ${
          mobileOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="flex flex-col p-2">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="px-4 py-3 rounded-lg text-base text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
            >
              {link.label}
            </a>
          ))}
          <a
            href="https://frontend-demo-1542.up.railway.app/"
            onClick={() => setMobileOpen(false)}
            className="px-4 py-3 rounded-lg text-base text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors sm:hidden"
          >
            Try Demo
          </a>
        </div>
      </div>
    </nav>
  );
}
