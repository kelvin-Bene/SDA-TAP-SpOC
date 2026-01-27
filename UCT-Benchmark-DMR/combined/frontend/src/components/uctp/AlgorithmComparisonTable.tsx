import { cn } from '@/lib/utils';
import type { UCTPRunComparison } from '@/types/uctp';

interface AlgorithmComparisonTableProps {
  comparison: UCTPRunComparison;
}

const metricLabels: Record<string, string> = {
  f1_score: 'F1 Score',
  precision: 'Precision',
  recall: 'Recall',
  position_rms_km: 'Position RMS (km)',
  velocity_rms_km_s: 'Velocity RMS (km/s)',
  clusters_found: 'Clusters Found',
  objects_resolved: 'Objects Resolved',
  elapsed_seconds: 'Elapsed Time (s)',
};

export function AlgorithmComparisonTable({ comparison }: AlgorithmComparisonTableProps) {
  const { runs, config_diffs } = comparison;
  const metrics = Object.keys(metricLabels);

  // Find best value for each metric
  const bestValues: Record<string, number> = {};
  metrics.forEach((metric) => {
    const values = runs
      .map((r) => (r.metrics as Record<string, number | null | undefined>)[metric])
      .filter((v) => v != null) as number[];
    if (values.length > 0) {
      // Lower is better for RMS metrics
      if (metric.includes('rms')) {
        bestValues[metric] = Math.min(...values);
      } else {
        bestValues[metric] = Math.max(...values);
      }
    }
  });

  return (
    <div className="rounded-xl border border-white/10 bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-3 text-xs font-medium text-muted-foreground">Metric</th>
              {runs.map((run) => (
                <th key={run.id} className="text-center p-3">
                  <p className="text-xs font-medium">{run.algorithm_name}</p>
                  <p className="text-[10px] text-muted-foreground">Run #{run.id}</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => (
              <tr key={metric} className="border-b border-white/5 hover:bg-white/5">
                <td className="p-3 text-xs text-muted-foreground">{metricLabels[metric]}</td>
                {runs.map((run) => {
                  const val = (run.metrics as Record<string, number | null | undefined>)[metric];
                  const isBest = val != null && val === bestValues[metric];
                  return (
                    <td key={run.id} className="text-center p-3">
                      <span
                        className={cn(
                          'font-mono text-xs',
                          isBest ? 'text-cosmic-cyan font-semibold' : 'text-foreground'
                        )}
                      >
                        {val != null ? (typeof val === 'number' ? val.toFixed(4) : val) : '--'}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}

            {/* Config diffs */}
            {Object.entries(config_diffs).length > 0 && (
              <>
                <tr className="border-b border-white/10">
                  <td colSpan={runs.length + 1} className="p-3 text-xs font-medium text-muted-foreground bg-white/5">
                    Configuration Differences
                  </td>
                </tr>
                {Object.entries(config_diffs).map(([key, values]) => (
                  <tr key={key} className="border-b border-white/5 hover:bg-white/5">
                    <td className="p-3 text-xs text-muted-foreground font-mono">{key}</td>
                    {(values as unknown[]).map((val, idx) => (
                      <td key={idx} className="text-center p-3 text-xs font-mono">
                        {String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
