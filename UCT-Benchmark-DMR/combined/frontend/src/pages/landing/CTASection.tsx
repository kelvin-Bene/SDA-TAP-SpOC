import { Link } from 'react-router-dom';
import { LogIn, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { cn } from '@/lib/utils';

export function CTASection() {
  const { ref, isInView } = useInView();

  return (
    <>
      {/* CTA */}
      <section id="access" className="py-16 sm:py-24 md:py-32 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
          <div
            className={cn(
              'glass border-white/10 rounded-2xl p-8 sm:p-12 md:p-16 text-center transition-all duration-700',
              isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            )}
          >
            <h2 className="font-display font-bold text-3xl sm:text-4xl mb-4">
              Access the Platform
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto mb-8">
              Authenticate to browse datasets, submit algorithm results, and view evaluation metrics.
            </p>
            <div className="flex flex-col xs:flex-row items-center justify-center gap-3">
              <Button asChild size="lg" className="w-full xs:w-auto bg-gradient-cosmic hover:opacity-90 text-white border-0 px-8">
                <Link to="/login">
                  <LogIn className="h-4 w-4 mr-2" />
                  Sign In to UCT Benchmark
                </Link>
              </Button>
              <a
                href="https://frontend-demo-1542.up.railway.app/"
                className="w-full xs:w-auto inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium h-11 px-8 border border-white/20 hover:bg-white/5 transition-colors"
              >
                <Play className="h-4 w-4" />
                Try Demo
              </a>
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
