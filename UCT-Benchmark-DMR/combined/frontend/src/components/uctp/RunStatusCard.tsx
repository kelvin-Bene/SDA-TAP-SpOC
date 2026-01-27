import { Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UCTPRunSummary } from '@/types/uctp';

const statusConfig = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: 'Pending' },
  running: { icon: Loader2, color: 'text-cosmic-cyan', bg: 'bg-cosmic-cyan/10', label: 'Running' },
  completed: { icon: CheckCircle2, color: 'text-aurora-green', bg: 'bg-aurora-green/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Failed' },
};

interface RunStatusCardProps {
  run: UCTPRunSummary;
  onClick?: () => void;
  compact?: boolean;
}

export function RunStatusCard({ run, onClick, compact = false }: RunStatusCardProps) {
  const cfg = statusConfig[run.status];
  const StatusIcon = cfg.icon;

  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-xl border border-white/10 bg-card transition-all duration-200',
        onClick && 'cursor-pointer hover:border-cosmic-cyan/30 hover:shadow-glow-cyan',
        compact ? 'p-3' : 'p-4'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className={cn('p-2 rounded-lg', cfg.bg)}>
            <StatusIcon className={cn('h-4 w-4', cfg.color, run.status === 'running' && 'animate-spin')} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{run.algorithm_name}</p>
            <p className="text-xs text-muted-foreground">
              Dataset #{run.dataset_id} &middot; {cfg.label}
            </p>
          </div>
        </div>

        {run.metrics.f1_score !== null && run.metrics.f1_score !== undefined && (
          <div className="text-right">
            <p className="text-sm font-mono font-semibold">{run.metrics.f1_score.toFixed(4)}</p>
            <p className="text-xs text-muted-foreground">F1</p>
          </div>
        )}
      </div>

      {!compact && run.metrics.objects_resolved !== undefined && (
        <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
          <span>{run.metrics.clusters_found ?? '--'} clusters</span>
          <span>{run.metrics.objects_resolved ?? '--'} objects</span>
          {run.metrics.elapsed_seconds && <span>{run.metrics.elapsed_seconds.toFixed(1)}s</span>}
        </div>
      )}
    </div>
  );
}
