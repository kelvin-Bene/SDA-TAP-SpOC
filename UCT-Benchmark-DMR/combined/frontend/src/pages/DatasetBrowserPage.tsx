import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { DatasetFilters } from '@/components/datasets/DatasetFilters';
import { DatasetPreviewDialog } from '@/components/datasets/DatasetPreviewDialog';
import { Plus, LayoutGrid, List, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { downloadBlob } from '@/lib/downloadUtils';
import { useDatasets, useDownloadDataset } from '@/hooks/useDatasets';
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
      console.error('Download failed:', err);
      // U6: Differentiate network vs server errors for better user guidance
      const isNetworkError = err instanceof Error && ('code' in err || err.message === 'Network Error');
      // Extract server error detail from axios error response (may be a Blob)
      let serverDetail = '';
      const axiosErr = err as { response?: { status?: number; data?: unknown } };
      if (axiosErr?.response?.data instanceof Blob) {
        try {
          const text = await axiosErr.response.data.text();
          const parsed = JSON.parse(text);
          serverDetail = parsed.detail || '';
        } catch { /* ignore parse errors */ }
      } else if (axiosErr?.response?.data && typeof axiosErr.response.data === 'object') {
        serverDetail = (axiosErr.response.data as { detail?: string }).detail || '';
      }

      const status = axiosErr?.response?.status;
      toast({
        title: 'Download failed',
        description: isNetworkError
          ? 'Network error — check your connection and try again.'
          : status === 404 && serverDetail
            ? serverDetail
            : status === 400
              ? serverDetail || 'This dataset is not available for download.'
              : 'Failed to download dataset. The server may be unavailable.',
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
            Browse and download benchmark datasets for UCT algorithm evaluation
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
      {error && (() => {
        const axiosErr = error as { response?: { status?: number } };
        const status = axiosErr?.response?.status;
        let errorMessage = 'Failed to load datasets. Please check your connection and try again.';
        if (status === 401 || status === 403) {
          errorMessage = 'You are not authorized to view datasets. Please log in again.';
        } else if (status && status >= 500) {
          errorMessage = 'The server encountered an error. Please try again later.';
        }
        return (
          <div className="text-center py-12">
            <p className="text-destructive mb-2">{errorMessage}</p>
            <Button variant="outline" onClick={() => refetch()}>
              Try Again
            </Button>
          </div>
        );
      })()}

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-lg border p-4 space-y-3 animate-pulse">
              <div className="h-5 bg-muted rounded w-3/4" />
              <div className="h-4 bg-muted rounded w-1/2" />
              <div className="flex gap-2">
                <div className="h-6 bg-muted rounded w-16" />
                <div className="h-6 bg-muted rounded w-16" />
              </div>
              <div className="h-4 bg-muted rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {/* Dataset Grid/List */}
      {!isLoading && !error && datasets.length > 0 && (
        <div
          className={cn(
            'grid gap-4',
            viewMode === 'grid'
              ? 'sm:grid-cols-2 lg:grid-cols-3'
              : 'grid-cols-1'
          )}
        >
          {datasets.map((dataset) => (
            <DatasetCard
              key={dataset.id}
              dataset={dataset}
              onPreview={handlePreview}
              onDownload={handleDownload}
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
    </div>
  );
}
