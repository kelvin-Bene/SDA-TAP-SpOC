import { Link } from 'react-router-dom';
import { ArrowDown, LogIn, Play } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { AnimatedCounter } from './components/AnimatedCounter';
import { OrbitalGraphic } from './components/OrbitalGraphic';
import { LandingGlobe } from './LandingGlobe';

const STATS = [
  { target: 4, label: 'Orbital Regimes' },
  { target: 5, label: 'Data Tiers' },
  { target: 4, label: 'Sensor Types' },
];

export function HeroSection() {
  const { ref: statsRef, isInView: statsVisible } = useInView({ threshold: 0.05 });

  return (
    <section
      id="mission"
      className="relative flex flex-col pt-20 sm:pt-24 pb-12 sm:pb-16 overflow-hidden"
    >
      {/* Hero content */}
      <div>
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-8 lg:gap-16 items-center">
            {/* Left column */}
            <div className="flex flex-col gap-6">
              <Badge
                variant="outline"
                className="w-fit border-white/20 bg-white/5 text-muted-foreground font-mono text-xs tracking-wider"
              >
                SDA TAP Lab // Combat Forces Command
              </Badge>

              <h1 className="font-display font-bold tracking-tight">
                <span className="block text-4xl xs:text-5xl sm:text-6xl lg:text-7xl text-gradient-cosmic">UCT Benchmark</span>
                <span className="block text-2xl xs:text-3xl sm:text-4xl lg:text-5xl mt-2">
                  Uncorrelated Track Processing
                </span>
                <span className="block text-2xl xs:text-3xl sm:text-4xl lg:text-5xl text-muted-foreground mt-1">
                  Benchmark Platform
                </span>
              </h1>

              <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
                The standardized evaluation framework for UCTP algorithms across all orbital regimes.
              </p>

              <div className="flex flex-wrap gap-3 mt-2">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white/20 hover:bg-white/5"
                  onClick={() =>
                    document.getElementById('problem')?.scrollIntoView({ behavior: 'smooth' })
                  }
                >
                  <ArrowDown className="h-4 w-4 mr-2" />
                  Mission Briefing
                </Button>
                <Button asChild size="lg" className="bg-gradient-cosmic hover:opacity-90 text-white border-0">
                  <Link to="/login">
                    <LogIn className="h-4 w-4 mr-2" />
                    Access Platform
                  </Link>
                </Button>
                <a
                  href="https://frontend-demo-1542.up.railway.app/"
                  className="inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium h-11 px-6 border border-white/20 hover:bg-white/5 transition-colors"
                >
                  <Play className="h-4 w-4" />
                  Try Demo
                </a>
              </div>
            </div>

            {/* Right column - 3D globe on desktop, mobile stays on SVG
                (kept hidden below lg: so we don't ship 1.4MB Cesium to 375px
                viewports per the recent mobile-responsive commits). */}
            <div className="hidden lg:block">
              <LandingGlobe fallback={<OrbitalGraphic />} />
            </div>
          </div>
        </div>
      </div>

      {/* Stat strip */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 mt-10 sm:mt-16">
        <div
          ref={statsRef}
          className="grid grid-cols-1 xs:grid-cols-3 gap-4 sm:gap-6 max-w-2xl mx-auto lg:mx-0 text-center lg:text-left"
        >
          {STATS.map((stat) => (
            <div key={stat.label} className="flex flex-col gap-1">
              <AnimatedCounter target={stat.target} isInView={statsVisible} />
              <span className="text-sm text-muted-foreground font-medium">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
