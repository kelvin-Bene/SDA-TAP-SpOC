import { useMemo } from 'react';
import type { UCTPRunSummary } from '@/types/uctp';

interface MetricsChartProps {
  runs: UCTPRunSummary[];
  metric: 'f1_score' | 'precision' | 'recall' | 'position_rms_km';
  height?: number;
}

export function MetricsChart({ runs, metric, height = 200 }: MetricsChartProps) {
  const completedRuns = useMemo(
    () => runs.filter((r) => r.status === 'completed' && r.metrics[metric] != null),
    [runs, metric]
  );

  if (completedRuns.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-white/10 bg-white/5 text-muted-foreground text-sm"
        style={{ height }}
      >
        No completed runs with {metric.replace(/_/g, ' ')} data
      </div>
    );
  }

  const values = completedRuns.map((r) => r.metrics[metric] as number);
  const maxVal = Math.max(...values, 1);
  const barWidth = Math.max(20, Math.min(60, (100 / completedRuns.length)));

  const metricLabels: Record<string, string> = {
    f1_score: 'F1 Score',
    precision: 'Precision',
    recall: 'Recall',
    position_rms_km: 'Position RMS (km)',
  };

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4" style={{ height }}>
      <p className="text-xs text-muted-foreground mb-3 font-medium">{metricLabels[metric] || metric}</p>
      <div className="flex items-end gap-1 h-[calc(100%-40px)]">
        {completedRuns.map((run, idx) => {
          const val = run.metrics[metric] as number;
          const pct = (val / maxVal) * 100;

          return (
            <div key={run.id} className="flex flex-col items-center gap-1 flex-1 min-w-0" title={`${run.algorithm_name}: ${val.toFixed(4)}`}>
              <div className="w-full flex flex-col justify-end" style={{ height: '100%' }}>
                <div
                  className="w-full rounded-t bg-gradient-to-t from-cosmic-cyan to-cosmic-blue opacity-80 hover:opacity-100 transition-opacity min-h-[2px]"
                  style={{ height: `${Math.max(pct, 2)}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground truncate w-full text-center">
                #{run.id}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
