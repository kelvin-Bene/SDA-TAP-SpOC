import { useNavigate } from 'react-router-dom';
import { ArrowDown, Rocket, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { AnimatedCounter } from './components/AnimatedCounter';
import { OrbitalGraphic } from './components/OrbitalGraphic';
import { useAuthStore } from '@/stores/authStore';

const MAIN_URL = 'https://frontend-production-6d80.up.railway.app';

const STATS = [
  { target: 4, label: 'Orbital Regimes' },
  { target: 5, label: 'Data Tiers' },
  { target: 4, label: 'Sensor Types' },
];

export function HeroSection() {
  const { ref: statsRef, isInView: statsVisible } = useInView({ threshold: 0.05 });
  const navigate = useNavigate();
  const initialize = useAuthStore((s) => s.initialize);

  const tryDemo = async () => {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem('demo_logged_out');
    }
    await initialize();
    navigate('/dashboard');
  };

  const goToMain = () => {
    window.location.href = MAIN_URL;
  };

  return (
    <section
      id="mission"
      className="relative flex flex-col pt-24 pb-16 overflow-hidden"
    >
      {/* Hero content */}
      <div>
        <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
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

              <div className="flex flex-col sm:flex-row flex-wrap gap-3 mt-2">
                <Button
                  size="lg"
                  className="bg-gradient-cosmic hover:opacity-90 text-white border-0 w-full sm:w-auto"
                  onClick={tryDemo}
                >
                  <Rocket className="h-4 w-4 mr-2" />
                  Try Demo
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="border-white/20 hover:bg-white/5 w-full sm:w-auto"
                  onClick={goToMain}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Go to Main
                </Button>
                <Button
                  variant="ghost"
                  size="lg"
                  className="w-full sm:w-auto"
                  onClick={() =>
                    document.getElementById('problem')?.scrollIntoView({ behavior: 'smooth' })
                  }
                >
                  <ArrowDown className="h-4 w-4 mr-2" />
                  Mission Briefing
                </Button>
              </div>
            </div>

            {/* Right column - orbital graphic */}
            <div className="hidden lg:block">
              <OrbitalGraphic />
            </div>
          </div>
        </div>
      </div>

      {/* Stat strip */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 mt-16">
        <div
          ref={statsRef}
          className="grid grid-cols-3 gap-3 xs:gap-6 max-w-2xl mx-auto lg:mx-0 text-center lg:text-left"
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
