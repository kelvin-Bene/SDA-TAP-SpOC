import { Brain, Clock, CheckCircle2, Archive } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UCTPModelSummary } from '@/types/uctp';

const statusIcons = {
  training: Clock,
  ready: CheckCircle2,
  archived: Archive,
};

const statusColors = {
  training: 'text-yellow-400',
  ready: 'text-aurora-green',
  archived: 'text-muted-foreground',
};

interface ModelCardProps {
  model: UCTPModelSummary;
  onClick?: () => void;
}

export function ModelCard({ model, onClick }: ModelCardProps) {
  const StatusIcon = statusIcons[model.status] || Clock;

  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-xl border border-white/10 bg-card p-4 transition-all duration-200',
        onClick && 'cursor-pointer hover:border-stellar-purple/30 hover:shadow-glow-purple'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-stellar-purple/10">
            <Brain className="h-5 w-5 text-stellar-purple" />
          </div>
          <div>
            <p className="text-sm font-semibold">{model.name}</p>
            <p className="text-xs text-muted-foreground">{model.version} &middot; {model.model_type.replace(/_/g, ' ')}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <StatusIcon className={cn('h-4 w-4', statusColors[model.status])} />
          <span className={cn('text-xs capitalize', statusColors[model.status])}>{model.status}</span>
        </div>
      </div>

      {model.description && (
        <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{model.description}</p>
      )}

      <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
        {model.best_f1_score != null && (
          <span>F1: <span className="text-foreground font-mono">{model.best_f1_score.toFixed(4)}</span></span>
        )}
        {model.training_epochs != null && (
          <span>Epochs: <span className="text-foreground">{model.training_epochs}</span></span>
        )}
      </div>
    </div>
  );
}
