import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { DatasetFilters } from '@/components/datasets/DatasetFilters';
import { DatasetPreviewDialog } from '@/components/datasets/DatasetPreviewDialog';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  Plus,
  LayoutGrid,
  List,
  Loader2,
  Database,
  FolderSearch,
  RefreshCw,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDatasets, useDownloadDataset } from '@/hooks/useDatasets';
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

  const { data: datasets = [], isLoading, error, refetch } = useDatasets(filters);
  const downloadMutation = useDownloadDataset();

  const handlePreview = (dataset: Dataset) => {
    setPreviewDataset(dataset);
    setPreviewOpen(true);
  };

  const handleDownload = async (dataset: Dataset) => {
    try {
      const blob = await downloadMutation.mutateAsync(dataset.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${dataset.name}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to download dataset. Please try again.');
    }
  };

  const clearFilters = () => {
    setFilters(defaultFilters);
  };

  return (
    <div className="space-y-6">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-cosmic-blue/5 via-transparent to-cosmic-cyan/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-cosmic-blue/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-cosmic-cyan/8 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-cosmic-blue text-sm font-medium mb-2">
              <Database className="h-4 w-4" />
              Dataset Library
            </div>
            <h1 className="text-3xl sm:text-4xl font-display font-bold tracking-tight">
              Browse <span className="text-gradient-cosmic">Datasets</span>
            </h1>
            <p className="text-muted-foreground mt-2 max-w-xl flex items-center gap-2">
              Explore and download benchmark datasets for UCTP algorithm evaluation
              <InfoPopover
                title="What are Benchmark Datasets?"
                description="Each dataset contains real-world satellite observations, a truth catalog of known orbits, and ground-truth track associations for scoring."
                details={[
                  'Observations: angles-only measurements (RA, Dec) from ground sensors',
                  'Truth Catalog: known orbital states for each satellite',
                  'Associations: ground truth mapping of tracks to satellites',
                  'Filter by orbital regime, data tier, and sensor type',
                ]}
                learnMore="Datasets are generated from real space surveillance data sources. The combination of orbital regime, data tier, and sensor type determines the difficulty of the benchmark. Start with LEO T2 datasets for standard benchmarking."
                variant="concept"
              />
            </p>
          </div>
          <Link to="/datasets/generate" className="flex-shrink-0">
            <Button className="gap-2 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity">
              <Plus className="h-4 w-4" />
              Generate New
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Filters ──────────────────────────────────────────────── */}
      <DatasetFilters
        filters={filters}
        onFiltersChange={setFilters}
        onClear={clearFilters}
      />

      {/* ── Results Header ───────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {isLoading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-cosmic-cyan" />
              Loading datasets...
            </span>
          ) : (
            <>
              Showing <span className="font-medium text-foreground">{datasets.length}</span> dataset{datasets.length !== 1 ? 's' : ''}
            </>
          )}
        </p>
        <div className="flex items-center gap-1.5">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="icon"
            className={cn(
              'h-8 w-8 transition-all duration-200',
              viewMode === 'grid' && 'bg-cosmic-cyan/10 text-cosmic-cyan border border-cosmic-cyan/20',
            )}
            onClick={() => setViewMode('grid')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon"
            className={cn(
              'h-8 w-8 transition-all duration-200',
              viewMode === 'list' && 'bg-cosmic-cyan/10 text-cosmic-cyan border border-cosmic-cyan/20',
            )}
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* ── Error State ──────────────────────────────────────────── */}
      {error && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto">
            <Database className="h-7 w-7 text-destructive" />
          </div>
          <div>
            <p className="font-semibold text-destructive">Failed to load datasets</p>
            <p className="text-sm text-muted-foreground mt-1">
              There was an error connecting to the dataset service. Please try again.
            </p>
          </div>
          <Button variant="outline" onClick={() => refetch()} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </div>
      )}

      {/* ── Loading State ────────────────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <div className="w-14 h-14 rounded-2xl border-2 border-cosmic-cyan/20 flex items-center justify-center">
                <Loader2 className="h-7 w-7 animate-spin text-cosmic-cyan" />
              </div>
              <div className="absolute inset-0 rounded-2xl border-2 border-cosmic-cyan/10 animate-ping" />
            </div>
            <p className="text-sm text-muted-foreground">Loading datasets...</p>
          </div>
        </div>
      )}

      {/* ── Dataset Grid/List ────────────────────────────────────── */}
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
            />
          ))}
        </div>
      )}

      {/* ── Empty State ──────────────────────────────────────────── */}
      {!isLoading && !error && datasets.length === 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-12 text-center space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-cosmic-cyan/10 border border-cosmic-cyan/20 flex items-center justify-center mx-auto">
            <FolderSearch className="h-8 w-8 text-cosmic-cyan" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-display font-semibold">No datasets found</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {filters.regime !== 'all' || filters.tier !== 'all' || filters.sensor !== 'all'
                ? 'No datasets match your current filters. Try adjusting the filters or generate a new dataset.'
                : 'No datasets have been generated yet. Create your first benchmark dataset to get started.'}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3">
            {(filters.regime !== 'all' || filters.tier !== 'all' || filters.sensor !== 'all') && (
              <Button variant="outline" onClick={clearFilters} className="gap-2 border-white/10">
                Clear Filters
              </Button>
            )}
            <Link to="/datasets/generate">
              <Button className="gap-2 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity">
                <Sparkles className="h-4 w-4" />
                Generate Dataset
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* ── Preview Dialog ───────────────────────────────────────── */}
      <DatasetPreviewDialog
        dataset={previewDataset}
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        onDownload={handleDownload}
      />
    </div>
  );
}
