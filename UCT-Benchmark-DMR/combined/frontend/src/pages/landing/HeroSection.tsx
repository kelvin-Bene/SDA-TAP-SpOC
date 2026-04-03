import { Link } from 'react-router-dom';
import { ArrowDown, LogIn } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { AnimatedCounter } from './components/AnimatedCounter';
import { OrbitalGraphic } from './components/OrbitalGraphic';

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
      className="relative min-h-screen flex flex-col justify-center pt-16 overflow-hidden"
    >
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-12 lg:py-0">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column */}
          <div className="flex flex-col gap-6">
            <Badge
              variant="outline"
              className="w-fit border-white/20 bg-white/5 text-muted-foreground font-mono text-xs tracking-wider"
            >
              SDA TAP Lab // Space Operations Command
            </Badge>

            <h1 className="font-display font-bold tracking-tight">
              <span className="block text-5xl sm:text-6xl lg:text-7xl text-gradient-cosmic">SpOC</span>
              <span className="block text-3xl sm:text-4xl lg:text-5xl mt-2">
                Uncorrelated Track Processing
              </span>
              <span className="block text-3xl sm:text-4xl lg:text-5xl text-muted-foreground mt-1">
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
            </div>
          </div>

          {/* Right column - orbital graphic */}
          <div className="hidden lg:block">
            <OrbitalGraphic />
          </div>
        </div>

        {/* Stat strip */}
        <div
          ref={statsRef}
          className="mt-16 lg:mt-20 grid grid-cols-3 gap-6 max-w-2xl mx-auto lg:mx-0 text-center lg:text-left"
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
