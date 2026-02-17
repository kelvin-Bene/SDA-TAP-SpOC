import { Database, GitBranch, Orbit, Target, FileOutput, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { InfoPopover } from '@/components/ui/info-popover';

/* ------------------------------------------------------------------ */
/*  Pipeline step definitions                                          */
/* ------------------------------------------------------------------ */

interface PipelineStep {
  id: string;
  label: string;
  icon: React.ElementType;
  description: string;
}

interface StepEducation {
  title: string;
  description: string;
  details?: string[];
  learnMore?: string;
  variant?: 'info' | 'tip' | 'warning' | 'concept';
}

const steps: PipelineStep[] = [
  { id: 'ingest', label: 'Ingest', icon: Database, description: 'Load observations' },
  { id: 'cluster', label: 'Cluster', icon: GitBranch, description: 'Group observations' },
  { id: 'iod', label: 'IOD', icon: Orbit, description: 'Initial orbit determination' },
  { id: 'refine', label: 'Refine', icon: Target, description: 'Orbit refinement' },
  { id: 'output', label: 'Output', icon: FileOutput, description: 'Format results' },
];

const educationContent: Record<string, StepEducation> = {
  ingest: {
    title: 'Data Ingestion',
    description:
      'Loads raw observation data (right ascension, declination, timestamps) from sensor feeds and parses the benchmark dataset.',
    details: [
      'Reads JSON observation arrays',
      'Validates measurement fields',
      'Indexes by time and sensor ID',
    ],
    variant: 'info',
  },
  cluster: {
    title: 'Track Clustering',
    description:
      'Groups observations into tracks that likely belong to the same space object using spatial-temporal algorithms.',
    details: [
      'DBSCAN for density-based grouping',
      'Multiple Hypothesis Tracking (MHT) for ambiguous cases',
      'GNN for graph-based association',
    ],
    learnMore:
      'This is the core challenge in UCTP processing. The algorithm must determine which observations come from the same satellite despite gaps, noise, and similar-looking tracks.',
    variant: 'concept',
  },
  iod: {
    title: 'Initial Orbit Determination',
    description:
      'Computes a preliminary orbital state from minimum observations in each cluster.',
    details: [
      'Gauss method for angles-only data',
      'Gooding method for range+angle',
      'Typically needs 3+ observations',
    ],
    learnMore:
      'IOD produces a rough orbit estimate that serves as the starting point for refinement. Angles-only IOD is under-determined (infinite range solutions), requiring clever algorithmic approaches.',
    variant: 'concept',
  },
  refine: {
    title: 'Orbit Refinement',
    description:
      'Improves orbit accuracy using all available observations through iterative fitting.',
    details: [
      'Batch least-squares for offline processing',
      'EKF/UKF for sequential real-time processing',
      'Produces covariance matrix for uncertainty',
    ],
    variant: 'info',
  },
  output: {
    title: 'Results Output',
    description:
      'Packages track associations, state vectors, and covariance matrices into the benchmark submission format.',
    variant: 'tip',
  },
};

/* ------------------------------------------------------------------ */
/*  Animated connecting line between stages                            */
/* ------------------------------------------------------------------ */

function ConnectingLine({ completed, active }: { completed: boolean; active: boolean }) {
  return (
    <div className="relative flex items-center mx-1 flex-shrink-0 w-8 sm:w-12 lg:w-16">
      {/* Background track */}
      <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-white/10" />

      {/* Dashed overlay */}
      <svg
        className="absolute left-0 right-0 w-full h-4 overflow-visible"
        preserveAspectRatio="none"
      >
        <line
          x1="0"
          y1="50%"
          x2="100%"
          y2="50%"
          className={cn(
            'transition-all duration-500',
            completed
              ? 'stroke-aurora-green/60'
              : active
                ? 'stroke-cosmic-cyan/40'
                : 'stroke-white/10'
          )}
          strokeWidth="2"
          strokeDasharray="6 4"
        >
          {(active || completed) && (
            <animate
              attributeName="stroke-dashoffset"
              from="20"
              to="0"
              dur={active ? '1.5s' : '3s'}
              repeatCount="indefinite"
            />
          )}
        </line>
      </svg>

      {/* Traveling dot for active connections */}
      {active && (
        <svg
          className="absolute left-0 right-0 w-full h-4 overflow-visible"
          preserveAspectRatio="none"
        >
          <circle r="2.5" className="fill-cosmic-cyan">
            <animateMotion dur="2s" repeatCount="indefinite" path="M0,8 L100,8">
              <mpath xlinkHref="#linePath" />
            </animateMotion>
            <animate
              attributeName="opacity"
              values="0;1;1;0"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
          <defs>
            <path id="linePath" d="M0,8 L100,8" />
          </defs>
        </svg>
      )}

      {/* Gradient overlay for completed */}
      {completed && (
        <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-gradient-to-r from-aurora-green/40 to-aurora-green/20" />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pipeline stage node                                                */
/* ------------------------------------------------------------------ */

function StageNode({
  step,
  index,
  isActive,
  isCompleted,
}: {
  step: PipelineStep;
  index: number;
  isActive: boolean;
  isCompleted: boolean;
}) {
  const StepIcon = step.icon;
  const edu = educationContent[step.id];

  return (
    <div className="flex flex-col items-center gap-2 flex-shrink-0">
      {/* Main node container */}
      <div className="relative group">
        {/* Outer glow ring for active state */}
        {isActive && (
          <div className="absolute -inset-1.5 rounded-2xl bg-cosmic-cyan/10 animate-pulse-slow" />
        )}

        <div
          className={cn(
            'relative flex items-center justify-center rounded-xl border-2 transition-all duration-500',
            'w-14 h-14 sm:w-16 sm:h-16',
            isActive && [
              'border-cosmic-cyan/60 bg-cosmic-cyan/10',
              'shadow-[0_0_20px_-4px_hsl(192_91%_52%/0.4)]',
              'scale-110',
            ],
            isCompleted && [
              'border-aurora-green/50 bg-aurora-green/5',
            ],
            !isActive && !isCompleted && [
              'border-white/10 bg-white/[0.03]',
              'group-hover:border-white/20 group-hover:bg-white/[0.06]',
            ],
          )}
        >
          {/* Completed check overlay */}
          {isCompleted && (
            <div className="absolute -top-1.5 -right-1.5 z-10 flex items-center justify-center w-5 h-5 rounded-full bg-aurora-green border-2 border-background shadow-sm">
              <Check className="h-3 w-3 text-background" strokeWidth={3} />
            </div>
          )}

          {/* Icon */}
          <StepIcon
            className={cn(
              'h-5 w-5 sm:h-6 sm:w-6 transition-colors duration-300',
              isActive && 'text-cosmic-cyan',
              isCompleted && 'text-aurora-green',
              !isActive && !isCompleted && 'text-muted-foreground',
            )}
          />

          {/* Active pulse ring */}
          {isActive && (
            <div className="absolute inset-0 rounded-xl border border-cosmic-cyan/30 animate-ping opacity-20" />
          )}
        </div>

        {/* Info popover positioned top-right of node */}
        {edu && (
          <div className="absolute -top-1 -right-1 z-20">
            <InfoPopover
              title={edu.title}
              description={edu.description}
              details={edu.details}
              learnMore={edu.learnMore}
              variant={edu.variant ?? 'info'}
              size="sm"
            />
          </div>
        )}
      </div>

      {/* Stage number + label */}
      <div className="flex flex-col items-center gap-0.5">
        <span
          className={cn(
            'text-[10px] font-mono font-semibold uppercase tracking-widest',
            isActive && 'text-cosmic-cyan',
            isCompleted && 'text-aurora-green',
            !isActive && !isCompleted && 'text-muted-foreground/60',
          )}
        >
          {String(index + 1).padStart(2, '0')}
        </span>
        <span
          className={cn(
            'text-xs font-medium tracking-wide',
            isActive && 'text-cosmic-cyan',
            isCompleted && 'text-aurora-green/90',
            !isActive && !isCompleted && 'text-muted-foreground',
          )}
        >
          {step.label}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  PipelineVisualizer component                                       */
/* ------------------------------------------------------------------ */

interface PipelineVisualizerProps {
  activeStep?: string;
  completedSteps?: string[];
}

export function PipelineVisualizer({
  activeStep,
  completedSteps = [],
}: PipelineVisualizerProps) {
  return (
    <div className="relative py-6 px-4 overflow-x-auto">
      {/* Stage pipeline */}
      <div className="flex items-center justify-center">
        {steps.map((step, idx) => {
          const isActive = activeStep === step.id;
          const isCompleted = completedSteps.includes(step.id);

          // Determine connecting line state: the line AFTER this step
          const nextStep = steps[idx + 1];
          const isNextActive = nextStep ? activeStep === nextStep.id : false;
          const isLineCompleted = isCompleted;
          // Line is "active" when the current step is completed and the next is active,
          // or the current step is the active one
          const isLineActive = (isCompleted && isNextActive) || isActive;

          return (
            <div key={step.id} className="flex items-start">
              <StageNode
                step={step}
                index={idx}
                isActive={isActive}
                isCompleted={isCompleted}
              />

              {idx < steps.length - 1 && (
                <div className="flex items-center pt-5 sm:pt-6">
                  <ConnectingLine
                    completed={isLineCompleted}
                    active={isLineActive}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
