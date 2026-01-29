import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Download, Target, GitBranch, Orbit, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUCTPRun } from '@/hooks/useUCTPRuns';
import { PipelineVisualizer } from '@/components/uctp/PipelineVisualizer';

export function RunResultsPage() {
  const { runId } = useParams<{ runId: string }>();
  const { data: run, isLoading } = useUCTPRun(runId ? parseInt(runId) : null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cosmic-cyan" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Run not found.</p>
        <Link to="/uctp/workbench" className="text-cosmic-cyan hover:underline text-sm mt-2 inline-block">
          Back to Workbench
        </Link>
      </div>
    );
  }

  const completedSteps = run.status === 'completed'
    ? ['ingest', 'cluster', 'iod', 'refine', 'output']
    : run.status === 'running'
      ? ['ingest']
      : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to="/uctp/workbench" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mb-2">
            <ArrowLeft className="h-3 w-3" /> Back to Workbench
          </Link>
          <h1 className="text-3xl font-display font-bold tracking-tight">{run.algorithm_name}</h1>
          <p className="text-muted-foreground mt-1">
            Run #{run.id} &middot; Dataset #{run.dataset_id} &middot;
            <span className={run.status === 'completed' ? 'text-aurora-green' : run.status === 'failed' ? 'text-red-400' : 'text-yellow-400'}>
              {' '}{run.status}
            </span>
          </p>
        </div>

        {run.output_path && (
          <Button variant="outline" className="gap-2 border-white/20">
            <Download className="h-4 w-4" />
            Download Output
          </Button>
        )}
      </div>

      {/* Pipeline Progress */}
      <div className="rounded-xl border border-white/10 bg-card p-4">
        <PipelineVisualizer activeStep={run.status === 'running' ? 'iod' : undefined} completedSteps={completedSteps} />
      </div>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard icon={<Target className="h-4 w-4" />} label="F1 Score" value={run.metrics.f1_score?.toFixed(4)} color="cyan" />
        <MetricCard icon={<Target className="h-4 w-4" />} label="Precision" value={run.metrics.precision?.toFixed(4)} color="purple" />
        <MetricCard icon={<Target className="h-4 w-4" />} label="Recall" value={run.metrics.recall?.toFixed(4)} color="blue" />
        <MetricCard icon={<Orbit className="h-4 w-4" />} label="Position RMS" value={run.metrics.position_rms_km != null ? `${run.metrics.position_rms_km.toFixed(2)} km` : undefined} color="green" />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard icon={<GitBranch className="h-4 w-4" />} label="Clusters Found" value={run.metrics.clusters_found?.toString()} color="cyan" />
        <MetricCard icon={<Orbit className="h-4 w-4" />} label="Objects Resolved" value={run.metrics.objects_resolved?.toString()} color="purple" />
        <MetricCard icon={<Clock className="h-4 w-4" />} label="Elapsed Time" value={run.metrics.elapsed_seconds != null ? `${run.metrics.elapsed_seconds.toFixed(1)}s` : undefined} color="blue" />
      </div>

      {/* Logs */}
      {run.log_output && (
        <div className="rounded-xl border border-white/10 bg-card p-5">
          <h2 className="text-sm font-semibold mb-3">Pipeline Logs</h2>
          <pre className="text-xs text-muted-foreground bg-black/30 rounded-lg p-4 overflow-x-auto max-h-64 font-mono">
            {run.log_output}
          </pre>
        </div>
      )}

      {/* Error */}
      {run.error_message && (
        <div className="rounded-xl border border-red-400/30 bg-red-400/5 p-5">
          <h2 className="text-sm font-semibold text-red-400 mb-2">Error</h2>
          <pre className="text-xs text-red-300 bg-black/30 rounded-lg p-4 overflow-x-auto font-mono">
            {run.error_message}
          </pre>
        </div>
      )}

      {/* Config */}
      <div className="rounded-xl border border-white/10 bg-card p-5">
        <h2 className="text-sm font-semibold mb-3">Configuration</h2>
        <pre className="text-xs text-muted-foreground bg-black/30 rounded-lg p-4 overflow-x-auto font-mono">
          {JSON.stringify(run.config, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value?: string; color: string }) {
  const bgMap: Record<string, string> = {
    cyan: 'bg-cosmic-cyan/10', purple: 'bg-stellar-purple/10', blue: 'bg-cosmic-blue/10', green: 'bg-aurora-green/10',
  };

  return (
    <div className="rounded-xl border border-white/10 bg-card p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${bgMap[color] || bgMap.cyan}`}>{icon}</div>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className="text-xl font-display font-bold">{value || '--'}</p>
    </div>
  );
}
