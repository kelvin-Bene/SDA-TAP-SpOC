import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { DatasetFilters } from '@/components/datasets/DatasetFilters';
import { DatasetPreviewDialog } from '@/components/datasets/DatasetPreviewDialog';
import { Plus, LayoutGrid, List, Loader2, Zap, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { downloadBlob } from '@/lib/downloadUtils';
import { useDatasets, useDownloadDataset, useJobStatus } from '@/hooks/useDatasets';
import { useDemoEvaluate } from '@/hooks/useSubmissions';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/hooks/use-toast';
import type { Dataset, DatasetFilters as FilterType } from '@/types';

const defaultFilters: FilterType = {
  regime: 'all',
  tier: 'all',
  sensor: 'all',
};

export function DatasetBrowserPage() {
  const [filters, setFilters] = useState<FilterType>(defaultFilters);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [previewDataset, setPreviewDataset] = useState<Dataset | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  // UCTP evaluation state
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [showRunDialog, setShowRunDialog] = useState(false);
  const user = useAuthStore((s) => s.user);
  const [algorithmName, setAlgorithmName] = useState('');
  const [version, setVersion] = useState('1.0');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeSubmissionId, setActiveSubmissionId] = useState<string | null>(null);

  const demoEvaluate = useDemoEvaluate();
  const { data: jobStatus } = useJobStatus(activeJobId);

  // Navigate to results when job completes
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

  // Use real API hook instead of mock data
  const { data: datasets = [], isLoading, error, refetch } = useDatasets(filters);
  const downloadMutation = useDownloadDataset();

  const handlePreview = (dataset: Dataset) => {
    setPreviewDataset(dataset);
    setPreviewOpen(true);
  };

  const handleDownload = async (dataset: Dataset) => {
    try {
      const blob = await downloadMutation.mutateAsync(dataset.id);

      downloadBlob(blob, `${dataset.name}.json`);
    } catch (err: unknown) {
      // U6: Differentiate network vs server errors for better user guidance
      const isNetworkError = err instanceof Error && ('code' in err || err.message === 'Network Error');
      toast({
        title: 'Download failed',
        description: isNetworkError
          ? 'Network error — check your connection and try again.'
          : 'Failed to download dataset. The server may be unavailable.',
        variant: 'destructive',
      });
    }
  };

  const handleRunUCTP = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setAlgorithmName(`${user?.username || 'Operator'}'s Algorithm`);
    setVersion('1.0');
    setShowRunDialog(true);
  };

  const handleSubmitEvaluation = async () => {
    if (!selectedDataset) return;
    try {
      const result = await demoEvaluate.mutateAsync({
        dataset_id: Number(selectedDataset.id),
        algorithm_name: algorithmName,
        version,
      });
      setShowRunDialog(false);
      setActiveJobId(result.job_id);
      setActiveSubmissionId(result.submission_id);
      toast({
        title: 'Evaluation started',
        description: `Processing "${algorithmName}" against ${selectedDataset.name}...`,
      });
    } catch {
      toast({
        title: 'Failed to start evaluation',
        description: 'Could not start the demo evaluation. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const clearFilters = () => {
    setFilters(defaultFilters);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Datasets</h1>
          <p className="text-muted-foreground mt-1">
            Browse and download benchmark datasets for UCTP algorithm evaluation
          </p>
        </div>
        <Link to="/datasets/generate">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Generate New
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <DatasetFilters
        filters={filters}
        onFiltersChange={setFilters}
        onClear={clearFilters}
      />

      {/* Results Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {isLoading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading datasets...
            </span>
          ) : (
            <>
              Showing <span className="font-medium text-foreground">{datasets.length}</span> datasets
            </>
          )}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="icon"
            onClick={() => setViewMode('grid')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="text-center py-12">
          <p className="text-destructive mb-2">Failed to load datasets.</p>
          <Button variant="outline" onClick={() => refetch()}>
            Try Again
          </Button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Dataset Grid/List */}
      {!isLoading && !error && datasets.length > 0 && (
        <div
          className={cn(
            'grid gap-4',
            viewMode === 'grid'
              ? 'sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
              : 'grid-cols-1'
          )}
        >
          {datasets.map((dataset) => (
            <DatasetCard
              key={dataset.id}
              dataset={dataset}
              onPreview={handlePreview}
              onDownload={handleDownload}
              onRunUCTP={handleRunUCTP}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && datasets.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No datasets match your filters.</p>
          <Button variant="link" onClick={clearFilters}>
            Clear filters
          </Button>
        </div>
      )}

      {/* Preview Dialog */}
      <DatasetPreviewDialog
        dataset={previewDataset}
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        onDownload={handleDownload}
      />

      {/* Processing Indicator */}
      {activeJobId && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg border border-white/10 bg-card px-4 py-3 shadow-lg">
          <Loader2 className="h-5 w-5 animate-spin text-amber-400" />
          <div className="text-sm">
            <p className="font-medium">Evaluating...</p>
            <p className="text-muted-foreground">
              {jobStatus?.stage || 'Processing submission'}
            </p>
          </div>
        </div>
      )}

      {/* Run UCTP Dialog */}
      <Dialog open={showRunDialog} onOpenChange={setShowRunDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-400" />
              Run UCTP Evaluation
            </DialogTitle>
            <DialogDescription>
              Run a UCTP evaluation against{' '}
              <span className="font-medium text-foreground">{selectedDataset?.name}</span>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="algorithm-name">Algorithm Name</Label>
              <Input
                id="algorithm-name"
                value={algorithmName}
                onChange={(e) => setAlgorithmName(e.target.value)}
                placeholder="My Algorithm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0"
              />
            </div>

            <div className="flex items-start gap-2 rounded-md border border-white/10 bg-white/[0.02] p-3">
              <Info className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <p className="text-xs text-muted-foreground">
                Demo mode -- scores are simulated to demonstrate the evaluation pipeline
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowRunDialog(false)}>
              Cancel
            </Button>
            <Button
              className="gap-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:opacity-90 text-white"
              onClick={handleSubmitEvaluation}
              disabled={!algorithmName.trim() || !version.trim() || demoEvaluate.isPending}
            >
              {demoEvaluate.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              Run Evaluation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
