import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
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
          <div className="flex items-center gap-1.5">
            <div className="h-9 w-9 rounded bg-white/90 p-0.5 flex items-center justify-center">
              <img src="/cfc-emblem.png" alt="Combat Forces Command" className="h-full w-full object-contain" />
            </div>
            <div className="h-9 rounded bg-white/90 px-1 py-0.5 items-center justify-center hidden sm:flex">
              <img src="/sda-tap-lab-logo.png" alt="SDA TAP Lab" className="h-full object-contain" />
            </div>
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
            size="sm"
            className="bg-gradient-cosmic hover:opacity-90 text-white border-0"
            onClick={() =>
              document.getElementById('access')?.scrollIntoView({ behavior: 'smooth' })
            }
          >
            Get Started
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
