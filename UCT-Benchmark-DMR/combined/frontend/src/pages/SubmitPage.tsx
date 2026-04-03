import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Zap,
  Loader2,
  Database,
  Satellite,
  Target,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Trophy,
  Info,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores/authStore';
import { useDatasets, useJobStatus } from '@/hooks/useDatasets';
import { useDemoEvaluate } from '@/hooks/useSubmissions';

/* ─── Pipeline stage visualization ─── */

interface PipelineStage {
  name: string;
  icon: React.ElementType;
  description: string;
}

const PIPELINE_STAGES: PipelineStage[] = [
  { name: 'Ingest', icon: Database, description: 'Loading observations' },
  { name: 'Cluster', icon: Satellite, description: 'Grouping tracks' },
  { name: 'IOD', icon: Target, description: 'Initial orbit determination' },
  { name: 'Refine', icon: ArrowRight, description: 'Orbit refinement' },
  { name: 'Score', icon: Trophy, description: 'Evaluating performance' },
];

function PipelineProgress({ progress, stage }: { progress: number; stage?: string }) {
  const activeIdx = Math.min(Math.floor(progress / 20), PIPELINE_STAGES.length - 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        {PIPELINE_STAGES.map((s, i) => {
          const Icon = s.icon;
          const isActive = i === activeIdx;
          const isDone = i < activeIdx;
          return (
            <div key={s.name} className="flex flex-col items-center gap-1.5 flex-1">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-500 ${
                  isDone
                    ? 'bg-aurora-green/20 border border-aurora-green/30'
                    : isActive
                    ? 'bg-cosmic-cyan/20 border border-cosmic-cyan/30 animate-pulse'
                    : 'bg-white/[0.03] border border-white/[0.06]'
                }`}
              >
                {isDone ? (
                  <CheckCircle className="h-5 w-5 text-aurora-green" />
                ) : (
                  <Icon
                    className={`h-5 w-5 transition-colors ${
                      isActive ? 'text-cosmic-cyan' : 'text-muted-foreground/40'
                    }`}
                  />
                )}
              </div>
              <span
                className={`text-[10px] font-mono uppercase tracking-wider ${
                  isDone ? 'text-aurora-green' : isActive ? 'text-cosmic-cyan' : 'text-muted-foreground/40'
                }`}
              >
                {s.name}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-cosmic-cyan to-cosmic-blue rounded-full transition-all duration-700 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Stage description */}
      <p className="text-center text-sm text-muted-foreground">
        {stage || PIPELINE_STAGES[activeIdx]?.description || 'Initializing...'}
      </p>
    </div>
  );
}

/* ─── Main page ─── */

export function SubmitPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const user = useAuthStore((s) => s.user);
  const { data: datasets, isLoading: datasetsLoading } = useDatasets({});
  const demoEvaluate = useDemoEvaluate();

  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [algorithmName, setAlgorithmName] = useState('');
  const [version, setVersion] = useState('1.0');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeSubmissionId, setActiveSubmissionId] = useState<string | null>(null);

  const { data: jobStatus } = useJobStatus(activeJobId);
  const isProcessing = !!activeJobId;

  // Set default algorithm name from callsign
  useEffect(() => {
    if (user?.username && !algorithmName) {
      setAlgorithmName(`${user.username}'s Algorithm`);
    }
  }, [user?.username, algorithmName]);

  // Handle job completion
  useEffect(() => {
    if (jobStatus?.status === 'completed' && activeSubmissionId) {
      toast({
        title: 'Evaluation complete',
        description: 'Navigating to results...',
      });
      setActiveJobId(null);
      navigate(`/results/${activeSubmissionId}`);
      setActiveSubmissionId(null);
    } else if (jobStatus?.status === 'failed') {
      toast({
        title: 'Evaluation failed',
        description: jobStatus.error || 'The evaluation job failed. Please try again.',
        variant: 'destructive',
      });
      setActiveJobId(null);
      setActiveSubmissionId(null);
    }
  }, [jobStatus?.status, activeSubmissionId, navigate, toast, jobStatus?.error]);

  const selectedDataset = datasets?.find((d) => String(d.id) === selectedDatasetId);

  const handleRunEvaluation = async () => {
    if (!selectedDatasetId || !algorithmName.trim()) return;

    try {
      const result = await demoEvaluate.mutateAsync({
        dataset_id: Number(selectedDatasetId),
        algorithm_name: algorithmName.trim(),
        version: version.trim() || '1.0',
      });
      setActiveJobId(result.job_id);
      setActiveSubmissionId(result.submission_id);
      toast({
        title: 'Evaluation started',
        description: `Processing "${algorithmName}" against ${selectedDataset?.name || 'dataset'}...`,
      });
    } catch {
      toast({
        title: 'Failed to start evaluation',
        description: 'Could not start the evaluation. Please try again.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight font-display">Run UCTP Evaluation</h1>
        <p className="text-muted-foreground mt-1">
          Select a benchmark dataset, name your algorithm, and run the evaluation pipeline
        </p>
      </div>

      {/* Processing state */}
      {isProcessing ? (
        <Card className="bg-white/[0.02] border-white/[0.06]">
          <CardContent className="pt-8 pb-8">
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cosmic-cyan/10 border border-cosmic-cyan/20 text-cosmic-cyan text-xs font-mono tracking-wider uppercase mb-4">
                <Loader2 className="h-3 w-3 animate-spin" />
                Processing
              </div>
              <h2 className="text-xl font-bold font-display">
                Evaluating {algorithmName}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Against {selectedDataset?.name || 'dataset'}
              </p>
            </div>

            <PipelineProgress
              progress={jobStatus?.progress ?? 0}
              stage={jobStatus?.stage}
            />
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Dataset Selection */}
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6 space-y-5">
              <div className="flex items-center gap-2 mb-1">
                <Database className="h-4 w-4 text-cosmic-cyan" />
                <h2 className="font-semibold">Select Dataset</h2>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dataset">Benchmark Dataset</Label>
                <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
                  <SelectTrigger className="bg-white/5 border-white/20">
                    <SelectValue placeholder={datasetsLoading ? 'Loading datasets...' : 'Choose a dataset'} />
                  </SelectTrigger>
                  <SelectContent>
                    {datasets?.map((dataset) => (
                      <SelectItem key={dataset.id} value={String(dataset.id)}>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={dataset.regime?.toLowerCase() as 'leo' | 'meo' | 'geo' | 'heo'}
                            className="text-[10px]"
                          >
                            {dataset.regime}
                          </Badge>
                          {dataset.name}
                          <span className="text-muted-foreground text-xs">
                            ({dataset.objectCount} objects)
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Dataset info card */}
              {selectedDataset && (
                <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-sm">{selectedDataset.name}</h3>
                    <div className="flex gap-1.5">
                      <Badge variant={selectedDataset.regime?.toLowerCase() as 'leo' | 'meo' | 'geo' | 'heo'}>
                        {selectedDataset.regime}
                      </Badge>
                      <Badge variant={`tier${selectedDataset.tier?.replace('T', '')}` as 'tier1' | 'tier2' | 'tier3' | 'tier4'}>
                        {selectedDataset.tier}
                      </Badge>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-xs text-muted-foreground">
                    <div>
                      <span className="block text-foreground font-semibold">{selectedDataset.objectCount}</span>
                      Satellites
                    </div>
                    <div>
                      <span className="block text-foreground font-semibold">{selectedDataset.observationCount}</span>
                      Observations
                    </div>
                    <div>
                      <span className="block text-foreground font-semibold">{selectedDataset.coverage || '—'}%</span>
                      Coverage
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Algorithm Details */}
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardContent className="pt-6 space-y-5">
              <div className="flex items-center gap-2 mb-1">
                <Satellite className="h-4 w-4 text-stellar-purple" />
                <h2 className="font-semibold">Algorithm Details</h2>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="algorithm">Algorithm Name</Label>
                  <Input
                    id="algorithm"
                    value={algorithmName}
                    onChange={(e) => setAlgorithmName(e.target.value)}
                    placeholder="e.g. OrbTrack-Pro"
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="version">Version</Label>
                  <Input
                    id="version"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="1.0"
                    className="bg-white/5 border-white/20 focus:border-cosmic-cyan/50"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Demo notice + Run button */}
          <div className="space-y-4">
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-cosmic-cyan/5 border border-cosmic-cyan/10">
              <Info className="h-4 w-4 text-cosmic-cyan mt-0.5 flex-shrink-0" />
              <p className="text-xs text-muted-foreground leading-relaxed">
                <span className="text-cosmic-cyan font-semibold">Demo mode</span> — The evaluation
                pipeline runs with simulated scoring to demonstrate the full UCTP benchmarking workflow.
                Results are randomized but use realistic metric distributions.
              </p>
            </div>

            <Button
              onClick={handleRunEvaluation}
              disabled={!selectedDatasetId || !algorithmName.trim() || demoEvaluate.isPending}
              className="w-full h-12 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan text-base font-semibold gap-2"
            >
              {demoEvaluate.isPending ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Starting Evaluation...
                </>
              ) : (
                <>
                  <Zap className="h-5 w-5" />
                  Run UCTP Evaluation
                </>
              )}
            </Button>
          </div>
        </>
      )}

      {/* Error display */}
      {demoEvaluate.isError && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>Failed to start evaluation. Please check your selection and try again.</p>
        </div>
      )}
    </div>
  );
}
