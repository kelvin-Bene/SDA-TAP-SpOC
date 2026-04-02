import {
  Settings, Satellite, CalendarRange, ShieldCheck, Layers,
  Download, Cpu, Upload, CheckCircle2,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { useInView } from '@/hooks/useInView';
import { SectionLabel } from './components/SectionLabel';
import { cn } from '@/lib/utils';
import { type LucideIcon } from 'lucide-react';

interface PipelineStep {
  icon: LucideIcon;
  title: string;
  desc: string;
}

const PIPELINE_A: PipelineStep[] = [
  { icon: Settings, title: 'Configure', desc: 'Set regime, tier, sensor, and epoch parameters.' },
  { icon: Satellite, title: 'Acquire', desc: 'Generate or ingest observation data.' },
  { icon: CalendarRange, title: 'Window Selection', desc: 'Define temporal bounds for the dataset.' },
  { icon: ShieldCheck, title: 'Quality Scoring', desc: 'Automated data quality assessment.' },
  { icon: Layers, title: 'Tiered Processing', desc: 'Apply tier-specific transformations.' },
];

const PIPELINE_B: PipelineStep[] = [
  { icon: Download, title: 'Download', desc: 'Retrieve benchmark dataset package.' },
  { icon: Cpu, title: 'Process', desc: 'Run UCTP algorithm against dataset.' },
  { icon: Upload, title: 'Submit', desc: 'Upload results to the platform.' },
  { icon: CheckCircle2, title: 'Evaluate', desc: 'Automated metric computation and scoring.' },
];

function PipelineCard({ title, steps, delay, isInView }: {
  title: string;
  steps: PipelineStep[];
  delay: number;
  isInView: boolean;
}) {
  return (
    <Card
      className={cn(
        'glass border-white/10 transition-all duration-700',
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      )}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <CardContent className="p-6">
        <h3 className="font-display font-semibold text-lg mb-6 text-gradient-cosmic">{title}</h3>
        <div className="flex flex-col gap-0">
          {steps.map((step, i) => (
            <div key={step.title} className="flex gap-4">
              {/* Vertical connector */}
              <div className="flex flex-col items-center">
                <div className="w-9 h-9 rounded-full border border-white/20 bg-white/5 flex items-center justify-center shrink-0">
                  <step.icon className="h-4 w-4 text-cosmic-cyan" />
                </div>
                {i < steps.length - 1 && (
                  <div className="w-px flex-1 bg-white/10 my-1" />
                )}
              </div>
              {/* Text */}
              <div className={cn('pb-6', i === steps.length - 1 && 'pb-0')}>
                <p className="font-medium text-sm">{step.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function SolutionSection() {
  const { ref, isInView } = useInView();

  return (
    <section id="solution" className="py-24 sm:py-32 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" ref={ref}>
        <div className="text-center mb-16">
          <SectionLabel>Common Task Framework</SectionLabel>
          <h2 className="font-display font-bold text-3xl sm:text-4xl mt-6 mb-4">The Solution</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Two standardized pipelines that separate data generation from algorithm evaluation.
          </p>
        </div>
        <div className="grid lg:grid-cols-2 gap-8">
          <PipelineCard title="Pipeline A: Data Generation" steps={PIPELINE_A} delay={0} isInView={isInView} />
          <PipelineCard title="Pipeline B: Evaluation" steps={PIPELINE_B} delay={200} isInView={isInView} />
        </div>
      </div>
    </section>
  );
}
