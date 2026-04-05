import { Link } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useInView } from '@/hooks/useInView';
import { cn } from '@/lib/utils';

export function CTASection() {
  const { ref, isInView } = useInView();

  return (
    <>
      {/* CTA */}
      <section id="access" className="py-24 sm:py-32 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
          <div
            className={cn(
              'glass border-white/10 rounded-2xl p-12 sm:p-16 text-center transition-all duration-700',
              isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            )}
          >
            <h2 className="font-display font-bold text-3xl sm:text-4xl mb-4">
              Access the Platform
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto mb-8">
              Authenticate to browse datasets, submit algorithm results, and view evaluation metrics.
            </p>
            <Button asChild size="lg" className="bg-gradient-cosmic hover:opacity-90 text-white border-0 px-8">
              <Link to="/login">
                <LogIn className="h-4 w-4 mr-2" />
                Sign In to UCT Benchmark
              </Link>
            </Button>
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
