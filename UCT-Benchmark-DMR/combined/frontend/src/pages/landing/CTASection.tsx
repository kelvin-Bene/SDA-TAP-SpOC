import { useNavigate } from 'react-router-dom';
import { Rocket, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';

const MAIN_URL = 'https://frontend-production-6d80.up.railway.app';

export function CTASection() {
  const { ref, isInView } = useInView();
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
    <>
      {/* CTA */}
      <section id="access" className="py-16 sm:py-24 lg:py-32 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
          <div
            className={cn(
              'glass border-white/10 rounded-2xl p-6 sm:p-12 lg:p-16 text-center transition-all duration-700',
              isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            )}
          >
            <h2 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl mb-4">
              Choose Your Environment
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto mb-8">
              Explore the platform instantly with the interactive demo, or sign in to the main environment with your credentials.
            </p>
            <div className="flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3">
              <Button
                size="lg"
                className="bg-gradient-cosmic hover:opacity-90 text-white border-0 w-full sm:w-auto sm:px-8"
                onClick={tryDemo}
              >
                <Rocket className="h-4 w-4 mr-2" />
                Try Demo
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="border-white/20 hover:bg-white/5 w-full sm:w-auto sm:px-8"
                onClick={goToMain}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Go to Main
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex flex-wrap items-center gap-2 justify-center sm:justify-start">
            <span className="font-display font-semibold text-foreground">UCT Benchmark</span>
            <span className="text-white/20">|</span>
            <span>SDA TAP Lab</span>
            <span className="text-white/20">|</span>
            <span>Combat Forces Command</span>
          </div>
          <span className="font-mono text-xs">v1.0.0</span>
        </div>
      </footer>
    </>
  );
}
