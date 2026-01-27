import { ArrowRight, Database, GitBranch, Orbit, Settings2, FileOutput } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PipelineStep {
  id: string;
  label: string;
  icon: React.ElementType;
  description: string;
}

const steps: PipelineStep[] = [
  { id: 'ingest', label: 'Ingest', icon: Database, description: 'Load observations' },
  { id: 'cluster', label: 'Cluster', icon: GitBranch, description: 'Group observations' },
  { id: 'iod', label: 'IOD', icon: Orbit, description: 'Initial orbit determination' },
  { id: 'refine', label: 'Refine', icon: Settings2, description: 'Orbit refinement' },
  { id: 'output', label: 'Output', icon: FileOutput, description: 'Format results' },
];

interface PipelineVisualizerProps {
  activeStep?: string;
  completedSteps?: string[];
}

export function PipelineVisualizer({ activeStep, completedSteps = [] }: PipelineVisualizerProps) {
  return (
    <div className="flex items-center justify-between gap-1 py-4 px-2 overflow-x-auto">
      {steps.map((step, idx) => {
        const isActive = activeStep === step.id;
        const isCompleted = completedSteps.includes(step.id);
        const StepIcon = step.icon;

        return (
          <div key={step.id} className="flex items-center gap-1 flex-shrink-0">
            <div
              className={cn(
                'flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all duration-300 min-w-[80px]',
                isActive
                  ? 'border-cosmic-cyan/50 bg-cosmic-cyan/10 shadow-glow-cyan'
                  : isCompleted
                    ? 'border-aurora-green/30 bg-aurora-green/5'
                    : 'border-white/10 bg-white/5'
              )}
            >
              <div
                className={cn(
                  'p-2 rounded-lg',
                  isActive ? 'bg-cosmic-cyan/20' : isCompleted ? 'bg-aurora-green/20' : 'bg-white/10'
                )}
              >
                <StepIcon
                  className={cn(
                    'h-4 w-4',
                    isActive
                      ? 'text-cosmic-cyan'
                      : isCompleted
                        ? 'text-aurora-green'
                        : 'text-muted-foreground'
                  )}
                />
              </div>
              <span
                className={cn(
                  'text-xs font-medium',
                  isActive ? 'text-cosmic-cyan' : isCompleted ? 'text-aurora-green' : 'text-muted-foreground'
                )}
              >
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <ArrowRight className="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}
