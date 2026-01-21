import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { DatasetCard } from '@/components/datasets/DatasetCard';
import { DatasetFilters } from '@/components/datasets/DatasetFilters';
import { DatasetPreviewDialog } from '@/components/datasets/DatasetPreviewDialog';
import { Plus, LayoutGrid, List } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Dataset, DatasetFilters as FilterType } from '@/types';

// Mock data
const mockDatasets: Dataset[] = [
  {
    id: '1',
    name: 'LEO-T1-2026-01-15',
    regime: 'LEO',
    tier: 'T1',
    createdAt: '2026-01-15T08:00:00Z',
    objectCount: 42,
    observationCount: 12456,
    coverage: 0.78,
    sizeBytes: 2.3 * 1024 * 1024,
    sensorTypes: ['optical', 'radar'],
  },
  {
    id: '2',
    name: 'MEO-T2-2026-01-14',
    regime: 'MEO',
    tier: 'T2',
    createdAt: '2026-01-14T10:00:00Z',
    objectCount: 38,
    observationCount: 8234,
    coverage: 0.45,
    sizeBytes: 1.8 * 1024 * 1024,
    sensorTypes: ['optical'],
  },
  {
    id: '3',
    name: 'GEO-T3-2026-01-13',
    regime: 'GEO',
    tier: 'T3',
    createdAt: '2026-01-13T14:00:00Z',
    objectCount: 28,
    observationCount: 6123,
    coverage: 0.82,
    sizeBytes: 1.2 * 1024 * 1024,
    sensorTypes: ['optical', 'rf'],
  },
  {
    id: '4',
    name: 'HEO-T4-2026-01-12',
    regime: 'HEO',
    tier: 'T4',
    createdAt: '2026-01-12T09:00:00Z',
    objectCount: 15,
    observationCount: 4567,
    coverage: 0.55,
    sizeBytes: 0.9 * 1024 * 1024,
    sensorTypes: ['radar'],
  },
  {
    id: '5',
    name: 'LEO-T2-2026-01-11',
    regime: 'LEO',
    tier: 'T2',
    createdAt: '2026-01-11T16:00:00Z',
    objectCount: 56,
    observationCount: 15234,
    coverage: 0.62,
    sizeBytes: 3.1 * 1024 * 1024,
    sensorTypes: ['optical', 'radar'],
  },
  {
    id: '6',
    name: 'MEO-T1-2026-01-10',
    regime: 'MEO',
    tier: 'T1',
    createdAt: '2026-01-10T11:00:00Z',
    objectCount: 45,
    observationCount: 9876,
    coverage: 0.71,
    sizeBytes: 2.5 * 1024 * 1024,
    sensorTypes: ['optical'],
  },
  {
    id: '7',
    name: 'GEO-T2-2026-01-09',
    regime: 'GEO',
    tier: 'T2',
    createdAt: '2026-01-09T13:00:00Z',
    objectCount: 22,
    observationCount: 5432,
    coverage: 0.88,
    sizeBytes: 1.1 * 1024 * 1024,
    sensorTypes: ['optical', 'rf'],
  },
  {
    id: '8',
    name: 'LEO-T3-2026-01-08',
    regime: 'LEO',
    tier: 'T3',
    createdAt: '2026-01-08T08:00:00Z',
    objectCount: 68,
    observationCount: 18234,
    coverage: 0.42,
    sizeBytes: 3.8 * 1024 * 1024,
    sensorTypes: ['optical', 'radar', 'rf'],
  },
];

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

  const filteredDatasets = useMemo(() => {
    return mockDatasets.filter((dataset) => {
      if (filters.regime && filters.regime !== 'all' && dataset.regime !== filters.regime) {
        return false;
      }
      if (filters.tier && filters.tier !== 'all' && dataset.tier !== filters.tier) {
        return false;
      }
      if (filters.sensor && filters.sensor !== 'all' && !dataset.sensorTypes.includes(filters.sensor)) {
        return false;
      }
      if (filters.objectCountRange) {
        if (
          dataset.objectCount < filters.objectCountRange.min ||
          dataset.objectCount > filters.objectCountRange.max
        ) {
          return false;
        }
      }
      return true;
    });
  }, [filters]);

  const handlePreview = (dataset: Dataset) => {
    setPreviewDataset(dataset);
    setPreviewOpen(true);
  };

  const handleDownload = (dataset: Dataset) => {
    // In a real app, this would trigger an API call
    console.log('Downloading dataset:', dataset.name);
    alert(`Downloading ${dataset.name}...`);
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
          Showing <span className="font-medium text-foreground">{filteredDatasets.length}</span> datasets
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

      {/* Dataset Grid/List */}
      {filteredDatasets.length > 0 ? (
        <div
          className={cn(
            'grid gap-4',
            viewMode === 'grid'
              ? 'sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
              : 'grid-cols-1'
          )}
        >
          {filteredDatasets.map((dataset) => (
            <DatasetCard
              key={dataset.id}
              dataset={dataset}
              onPreview={handlePreview}
              onDownload={handleDownload}
            />
          ))}
        </div>
      ) : (
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
