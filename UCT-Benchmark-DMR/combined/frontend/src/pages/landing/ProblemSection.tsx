import { AlertTriangle, BarChart3, Lock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { useInView } from '@/hooks/useInView';
import { SectionLabel } from './components/SectionLabel';
import { cn } from '@/lib/utils';
import { type LucideIcon } from 'lucide-react';

interface ProblemCardProps {
  icon: LucideIcon;
  title: string;
  line1: string;
  line2: string;
  delay: number;
  isInView: boolean;
}

function ProblemCard({ icon: Icon, title, line1, line2, delay, isInView }: ProblemCardProps) {
  return (
    <Card
      className={cn(
        'glass border-white/10 card-hover transition-all duration-700',
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      )}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <CardContent className="p-6 flex flex-col gap-4">
        <div className="w-12 h-12 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center">
          <Icon className="h-6 w-6 text-red-400" />
        </div>
        <h3 className="font-display font-semibold text-lg">{title}</h3>
        <div className="text-sm text-muted-foreground leading-relaxed space-y-1">
          <p>{line1}</p>
          <p>{line2}</p>
        </div>
      </CardContent>
    </Card>
  );
}

const PROBLEMS = [
  {
    icon: AlertTriangle,
    title: 'Inconsistent Data',
    line1: 'No common datasets across evaluation efforts.',
    line2: 'No controlled variables. No reproducible baselines.',
  },
  {
    icon: BarChart3,
    title: 'No Objective Metrics',
    line1: 'Evaluation criteria vary between organizations.',
    line2: 'No standardized performance measures.',
  },
  {
    icon: Lock,
    title: 'Closed Evaluation',
    line1: 'No third-party verification of algorithm claims.',
    line2: 'No reproducible benchmarks.',
  },
];

export function ProblemSection() {
  const { ref, isInView } = useInView();

  return (
    <section id="problem" className="py-16 sm:py-24 md:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
        <div className="text-center mb-10 sm:mb-16">
          <SectionLabel>Current State Assessment</SectionLabel>
          <h2 className="font-display font-bold text-3xl sm:text-4xl mt-6 mb-4">The Problem</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            UCTP algorithm evaluation lacks standardization, objectivity, and reproducibility.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {PROBLEMS.map((p, i) => (
            <ProblemCard key={p.title} {...p} delay={i * 150} isInView={isInView} />
          ))}
        </div>
      </div>
    </section>
  );
}
