import { useState } from 'react';
import { BarChart3, Plus, X } from 'lucide-react';
import { useUCTPRuns, useUCTPRunComparison } from '@/hooks/useUCTPRuns';
import { AlgorithmComparisonTable } from '@/components/uctp/AlgorithmComparisonTable';
import { MetricsChart } from '@/components/uctp/MetricsChart';

export function ComparisonPage() {
  const [selectedRunIds, setSelectedRunIds] = useState<number[]>([]);
  const { data: runs } = useUCTPRuns({ status: 'completed', limit: 50 });
  const { data: comparison, isLoading: isComparing } = useUCTPRunComparison(selectedRunIds);

  const toggleRun = (id: number) => {
    setSelectedRunIds((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-1">
          <BarChart3 className="h-4 w-4" />
          Algorithm Comparison
        </div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Compare Runs</h1>
        <p className="text-muted-foreground mt-1">Select 2-4 completed runs to compare side-by-side.</p>
      </div>

      {/* Run Selector */}
      <div className="rounded-xl border border-white/10 bg-card p-5">
        <h2 className="text-sm font-semibold mb-3">Select Runs to Compare</h2>

        {/* Selected runs */}
        {selectedRunIds.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {selectedRunIds.map((id) => {
              const run = runs?.find((r) => r.id === id);
              return (
                <div
                  key={id}
                  className="flex items-center gap-2 rounded-lg border border-stellar-purple/30 bg-stellar-purple/10 px-3 py-1.5 text-xs"
                >
                  <span className="text-stellar-purple font-medium">
                    #{id} {run?.algorithm_name || ''}
                  </span>
                  <button onClick={() => toggleRun(id)} className="text-stellar-purple/60 hover:text-stellar-purple">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Available runs list */}
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {runs && runs.length > 0 ? (
            runs.map((run) => {
              const isSelected = selectedRunIds.includes(run.id);
              return (
                <button
                  key={run.id}
                  onClick={() => toggleRun(run.id)}
                  disabled={!isSelected && selectedRunIds.length >= 4}
                  className={`w-full flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-all ${
                    isSelected
                      ? 'bg-stellar-purple/10 border border-stellar-purple/30'
                      : 'hover:bg-white/5 border border-transparent'
                  } ${!isSelected && selectedRunIds.length >= 4 ? 'opacity-40 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-5 h-5 rounded border flex items-center justify-center ${
                        isSelected
                          ? 'border-stellar-purple bg-stellar-purple/20'
                          : 'border-white/20 bg-white/5'
                      }`}
                    >
                      {isSelected && <Plus className="h-3 w-3 text-stellar-purple rotate-45" />}
                    </div>
                    <div className="text-left">
                      <span className="font-medium">{run.algorithm_name}</span>
                      <span className="text-muted-foreground ml-2">Run #{run.id}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    {run.metrics.f1_score != null && (
                      <span>F1: {run.metrics.f1_score.toFixed(4)}</span>
                    )}
                    <span>{new Date(run.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              );
            })
          ) : (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No completed runs available for comparison.
            </p>
          )}
        </div>
      </div>

      {/* Comparison Results */}
      {selectedRunIds.length < 2 && (
        <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
          <BarChart3 className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Select at least 2 runs to see comparison.</p>
        </div>
      )}

      {isComparing && selectedRunIds.length >= 2 && (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-stellar-purple" />
        </div>
      )}

      {comparison && (
        <div className="space-y-6">
          <h2 className="text-lg font-display font-semibold">Metrics Comparison</h2>
          <AlgorithmComparisonTable comparison={comparison} />

          {/* Charts */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-card p-5">
              <h3 className="text-sm font-semibold mb-3">F1 Score</h3>
              <MetricsChart runs={comparison.runs} metric="f1_score" height={200} />
            </div>
            <div className="rounded-xl border border-white/10 bg-card p-5">
              <h3 className="text-sm font-semibold mb-3">Position RMS (km)</h3>
              <MetricsChart runs={comparison.runs} metric="position_rms_km" height={200} />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-card p-5">
              <h3 className="text-sm font-semibold mb-3">Precision</h3>
              <MetricsChart runs={comparison.runs} metric="precision" height={200} />
            </div>
            <div className="rounded-xl border border-white/10 bg-card p-5">
              <h3 className="text-sm font-semibold mb-3">Recall</h3>
              <MetricsChart runs={comparison.runs} metric="recall" height={200} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
