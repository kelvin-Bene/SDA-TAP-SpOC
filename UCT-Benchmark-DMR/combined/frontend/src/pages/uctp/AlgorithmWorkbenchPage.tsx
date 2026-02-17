import { useState } from 'react';
import { FlaskConical, Play, History, Database, Rocket, Clock, BarChart3 } from 'lucide-react';
import { useUCTPRuns, useCreateUCTPRun } from '@/hooks/useUCTPRuns';
import { AlgorithmConfigPanel } from '@/components/uctp/AlgorithmConfigPanel';
import { PipelineVisualizer } from '@/components/uctp/PipelineVisualizer';
import { RunStatusCard } from '@/components/uctp/RunStatusCard';
import { InfoPopover, StepExplainer } from '@/components/ui/info-popover';
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

  const completedRuns = runs?.filter((r) => r.status === 'completed') ?? [];
  const activeRuns = runs?.filter((r) => r.status === 'running' || r.status === 'pending') ?? [];
  const pastRuns = runs?.filter((r) => r.status === 'completed' || r.status === 'failed') ?? [];

  return (
    <div className="space-y-8">
      {/* ---------------------------------------------------------------- */}
      {/*  Gradient Hero Header                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-cosmic-cyan/5 via-transparent to-stellar-purple/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-cosmic-cyan/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-stellar-purple/8 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-cosmic-cyan text-sm font-medium mb-2">
            <FlaskConical className="h-4 w-4" />
            Algorithm Workbench
            <InfoPopover
              title="Algorithm Workbench"
              description="The workbench is your central hub for configuring and executing the full UCTP pipeline. Select a dataset, tune algorithm parameters, and launch processing runs."
              details={[
                'Supports multiple clustering, IOD, and refinement strategies',
                'Results are scored against ground-truth using F1, precision, and recall',
                'Every run is saved so you can compare configurations over time',
              ]}
              learnMore="The UCTP pipeline processes uncorrelated tracks (UCTs) through a multi-stage pipeline: clustering groups raw observations, Initial Orbit Determination (IOD) fits preliminary orbits, and refinement improves those solutions. The workbench lets you swap each stage independently."
              variant="info"
              size="sm"
            />
          </div>
          <h1 className="text-3xl font-display font-bold tracking-tight">
            Configure & <span className="text-gradient-cosmic">Run Pipeline</span>
          </h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Select a dataset, configure algorithm parameters, and execute the full UCTP pipeline.
          </p>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Pipeline Visualizer                                             */}
      {/* ---------------------------------------------------------------- */}
      <div className="rounded-xl border border-white/10 bg-card/50 backdrop-blur-sm p-4">
        <div className="flex items-center gap-2 mb-2">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
            Pipeline Steps
          </p>
          <InfoPopover
            title="Pipeline Stages"
            description="The UCTP pipeline processes observations through a sequence of stages. Each stage transforms the data toward final orbit solutions."
            details={[
              'Ingest: Load and validate raw observation data',
              'Cluster: Group observations that likely belong to the same object',
              'IOD: Compute an initial orbit from each cluster',
              'Refine: Improve orbit accuracy with filtering techniques',
              'Output: Format and score the final catalog',
            ]}
            variant="concept"
            size="sm"
          />
        </div>
        <PipelineVisualizer />
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Main Content Grid                                               */}
      {/* ---------------------------------------------------------------- */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* ---------- Left Column: Configuration ---------- */}
        <div className="lg:col-span-1 space-y-4">
          {/* Dataset Selection Card */}
          <div className="rounded-xl border border-white/10 bg-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-stellar-purple/10">
                  <Database className="h-3.5 w-3.5 text-stellar-purple" />
                </div>
                <h2 className="text-sm font-semibold">Dataset</h2>
              </div>
              <InfoPopover
                title="Dataset Selection"
                description="Choose which benchmark dataset to process. The dataset determines the orbital regime, object count, and difficulty."
                details={[
                  'Smaller datasets run faster and are great for quick iteration',
                  'Each dataset has a fixed set of ground-truth orbits for scoring',
                  'Observation count directly impacts processing time',
                ]}
                learnMore="Datasets are pre-built collections of simulated or real observations. They include ground-truth information so the pipeline can compute accuracy metrics like F1-Score after processing."
                variant="info"
                size="sm"
              />
            </div>

            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(parseInt(e.target.value) || 0)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm focus:border-cosmic-cyan/50 focus:outline-none transition-colors"
            >
              <option value={0}>Select a dataset...</option>
              {datasets?.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.observation_count} obs)
                </option>
              ))}
            </select>

            {selectedDatasetId > 0 && (
              <div className="mt-3 flex items-center gap-2 text-xs text-aurora-green">
                <div className="h-1.5 w-1.5 rounded-full bg-aurora-green animate-pulse" />
                Dataset selected and ready
              </div>
            )}
          </div>

          {/* Algorithm Configuration Card */}
          <div className="rounded-xl border border-white/10 bg-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-cosmic-cyan/10">
                  <Rocket className="h-3.5 w-3.5 text-cosmic-cyan" />
                </div>
                <h2 className="text-sm font-semibold">Pipeline Configuration</h2>
              </div>
              <InfoPopover
                title="Algorithm Configuration"
                description="Configure how each pipeline stage operates: clustering method, IOD approach, refinement strategy."
                details={[
                  'Clustering: Choose DBSCAN or Stone Soup tracker-based grouping',
                  'IOD: Select from Gauss, Laplace, or Gooding methods',
                  'Refinement: Optional orbit improvement via least-squares or Kalman filters',
                  'DBSCAN epsilon and min_samples control cluster sensitivity',
                ]}
                learnMore="Start with Angular DBSCAN for clustering and Gauss IOD as a baseline. Then experiment with different refinement methods to improve orbit accuracy. Each configuration is saved so you can compare results."
                variant="tip"
                size="sm"
              />
            </div>

            <AlgorithmConfigPanel
              datasetId={selectedDatasetId}
              onSubmit={handleSubmit}
              isSubmitting={createRun.isPending}
            />
          </div>
        </div>

        {/* ---------- Right Column: Run History ---------- */}
        <div className="lg:col-span-2 space-y-4">
          {/* Run History Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-white/10">
                <History className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
              <h2 className="text-sm font-semibold">Run History</h2>
              {runs && runs.length > 0 && (
                <span className="text-xs text-muted-foreground bg-white/5 rounded-full px-2 py-0.5">
                  {runs.length} runs
                </span>
              )}
            </div>
            <InfoPopover
              title="Run History"
              description="Previous runs with their metrics. Compare F1-Score across different configurations."
              details={[
                'Each card shows the algorithm name, status, and key metrics',
                'F1-Score combines precision and recall into a single quality metric',
                'Click a run to view full details including position RMS',
                'Active runs update automatically until they complete or fail',
              ]}
              variant="info"
              size="sm"
            />
          </div>

          {/* Success Banner */}
          {createRun.isSuccess && (
            <div className="rounded-xl border border-aurora-green/30 bg-aurora-green/5 p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-aurora-green/10">
                <Rocket className="h-4 w-4 text-aurora-green" />
              </div>
              <div>
                <p className="text-sm font-medium text-aurora-green">Pipeline run started</p>
                <p className="text-xs text-muted-foreground">
                  Tracking run #{createRun.data?.id}. Results will appear below when complete.
                </p>
              </div>
            </div>
          )}

          {/* Active Runs Section */}
          {activeRuns.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-cosmic-cyan animate-pulse" />
                Active
              </p>
              <div className="space-y-2">
                {activeRuns.map((run) => (
                  <RunStatusCard key={run.id} run={run} />
                ))}
              </div>
            </div>
          )}

          {/* Completed / Failed Runs */}
          {pastRuns.length > 0 && (
            <div className="space-y-2">
              {activeRuns.length > 0 && (
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mt-2">
                  Completed
                </p>
              )}
              <div className="space-y-2">
                {pastRuns.map((run) => (
                  <RunStatusCard key={run.id} run={run} />
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {(!runs || runs.length === 0) && (
            <div className="rounded-xl border border-dashed border-white/10 bg-card/30 p-12 text-center">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-cosmic-cyan/10 to-stellar-purple/10 border border-white/10 flex items-center justify-center mb-4">
                <Play className="h-7 w-7 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold mb-1">No pipeline runs yet</h3>
              <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                Configure the pipeline on the left, select a dataset, and click
                "Run Pipeline" to execute your first algorithm run.
              </p>
              <div className="flex items-center justify-center gap-6 mt-6 text-xs text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Database className="h-3.5 w-3.5 text-stellar-purple" />
                  Pick a dataset
                </div>
                <div className="flex items-center gap-1.5">
                  <Rocket className="h-3.5 w-3.5 text-cosmic-cyan" />
                  Configure params
                </div>
                <div className="flex items-center gap-1.5">
                  <Play className="h-3.5 w-3.5 text-aurora-green" />
                  Run pipeline
                </div>
              </div>
            </div>
          )}

          {/* Quick Stats Bar (only when runs exist) */}
          {completedRuns.length > 0 && (
            <div className="rounded-xl border border-white/10 bg-card/50 p-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1.5 text-muted-foreground mb-1">
                    <BarChart3 className="h-3 w-3" />
                    <span className="text-xs font-medium uppercase tracking-wider">Best F1</span>
                  </div>
                  <p className="text-lg font-mono font-bold text-aurora-green">
                    {Math.max(
                      ...completedRuns
                        .map((r) => r.metrics.f1_score ?? 0)
                        .filter((v) => v > 0),
                      0
                    ).toFixed(4) || '--'}
                  </p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1.5 text-muted-foreground mb-1">
                    <Play className="h-3 w-3" />
                    <span className="text-xs font-medium uppercase tracking-wider">Runs</span>
                  </div>
                  <p className="text-lg font-mono font-bold">
                    {completedRuns.length}
                  </p>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1.5 text-muted-foreground mb-1">
                    <Clock className="h-3 w-3" />
                    <span className="text-xs font-medium uppercase tracking-wider">Avg Time</span>
                  </div>
                  <p className="text-lg font-mono font-bold">
                    {completedRuns.length > 0
                      ? (
                          completedRuns.reduce(
                            (sum, r) => sum + (r.metrics.elapsed_seconds ?? 0),
                            0
                          ) / completedRuns.length
                        ).toFixed(1) + 's'
                      : '--'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Step Explainer (educational footer)                              */}
      {/* ---------------------------------------------------------------- */}
      <StepExplainer
        title="Workbench Workflow"
        description="Follow these steps to run and evaluate your algorithm configuration."
        tips={[
          'Select a dataset from the dropdown - start with a small one for quick iteration',
          'Configure algorithm parameters or use defaults for a baseline run',
          'Click Run to execute the full pipeline - watch progress in the Pipeline Visualizer',
          'Review results: F1-Score, precision, recall, and position RMS',
        ]}
        variant="tip"
        defaultOpen={false}
      />
    </div>
  );
}
