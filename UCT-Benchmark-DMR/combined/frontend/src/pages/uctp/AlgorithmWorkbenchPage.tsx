import { useState } from 'react';
import { Play, History } from 'lucide-react';
import { useUCTPRuns, useCreateUCTPRun } from '@/hooks/useUCTPRuns';
import { AlgorithmConfigPanel } from '@/components/uctp/AlgorithmConfigPanel';
import { PipelineVisualizer } from '@/components/uctp/PipelineVisualizer';
import { RunStatusCard } from '@/components/uctp/RunStatusCard';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPRunCreate } from '@/types/uctp';

export function AlgorithmWorkbenchPage() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<number>(0);
  const { data: runs } = useUCTPRuns({ limit: 20 });
  const createRun = useCreateUCTPRun();

  // Fetch available datasets
  const { data: datasets } = useQuery({
    queryKey: ['datasets-for-uctp'],
    queryFn: async () => {
      const res = await api.getDatasets({ status: 'available' });
      return res.data as { id: string; name: string; observation_count: number }[];
    },
    staleTime: 1000 * 60,
  });

  const handleSubmit = (config: UCTPRunCreate) => {
    createRun.mutate(config);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-cosmic-cyan text-sm font-medium mb-1">
          <Play className="h-4 w-4" />
          Algorithm Workbench
        </div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Configure & Run Pipeline</h1>
        <p className="text-muted-foreground mt-1">Select a dataset, configure the pipeline, and run.</p>
      </div>

      {/* Pipeline Visualizer */}
      <div className="rounded-xl border border-white/10 bg-card p-4">
        <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wider">Pipeline Steps</p>
        <PipelineVisualizer />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Config Panel */}
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-xl border border-white/10 bg-card p-5">
            <h2 className="text-sm font-semibold mb-4">Pipeline Configuration</h2>

            {/* Dataset Selector */}
            <div className="mb-4">
              <label className="text-sm font-medium text-muted-foreground mb-1.5 block">Dataset</label>
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(parseInt(e.target.value) || 0)}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm focus:border-cosmic-cyan/50 focus:outline-none"
              >
                <option value={0}>Select a dataset...</option>
                {datasets?.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.observation_count} obs)
                  </option>
                ))}
              </select>
            </div>

            <AlgorithmConfigPanel
              datasetId={selectedDatasetId}
              onSubmit={handleSubmit}
              isSubmitting={createRun.isPending}
            />
          </div>
        </div>

        {/* Run History */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Run History</h2>
          </div>

          {createRun.isSuccess && (
            <div className="rounded-xl border border-aurora-green/30 bg-aurora-green/5 p-4 text-sm">
              Pipeline run started. Tracking run #{createRun.data?.id}.
            </div>
          )}

          {runs && runs.length > 0 ? (
            <div className="space-y-2">
              {runs.map((run) => (
                <RunStatusCard key={run.id} run={run} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
              <Play className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No pipeline runs yet.</p>
              <p className="text-xs text-muted-foreground mt-1">Configure the pipeline on the left and click "Run Pipeline".</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
