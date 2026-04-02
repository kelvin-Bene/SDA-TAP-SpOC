import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Download, Satellite, Database, Calendar, History, Loader2, BarChart3 } from 'lucide-react';
import { formatFileSize, formatDate } from '@/lib/utils';
import type { Dataset } from '@/types';
import { useDatasetVersions } from '@/hooks/useDatasets';

interface DatasetPreviewDialogProps {
  dataset: Dataset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDownload?: (dataset: Dataset) => void;
}

export function DatasetPreviewDialog({
  dataset,
  open,
  onOpenChange,
  onDownload,
}: DatasetPreviewDialogProps) {
  const { data: versions = [], isLoading: versionsLoading } = useDatasetVersions(
    open && dataset ? dataset.id : null
  );

  if (!dataset) return null;

  const hasVersionHistory = versions.length > 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {dataset.name}
            <Badge variant={dataset.regime === 'LEO' ? 'leo' : dataset.regime === 'MEO' ? 'meo' : dataset.regime === 'GEO' ? 'geo' : 'heo'}>
              {dataset.regime}
            </Badge>
            <Badge variant={dataset.tier === 'T1' ? 'tier1' : dataset.tier === 'T2' ? 'tier2' : dataset.tier === 'T3' ? 'tier3' : 'tier4'}>
              {dataset.tier}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Preview dataset metadata and quality metrics
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="mt-4 min-h-0 flex-1 overflow-y-auto">
          <TabsList className={`grid w-full ${hasVersionHistory ? 'grid-cols-4' : 'grid-cols-3'}`}>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="sample">Sample Data</TabsTrigger>
            {hasVersionHistory && (
              <TabsTrigger value="versions" className="gap-1">
                <History className="h-3 w-3" />
                Versions
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Objects</p>
                <p className="text-2xl font-semibold flex items-center gap-2">
                  <Satellite className="h-5 w-5 text-primary" />
                  {dataset.objectCount}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Observations</p>
                <p className="text-2xl font-semibold flex items-center gap-2">
                  <Database className="h-5 w-5 text-primary" />
                  {dataset.observationCount.toLocaleString()}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Coverage</p>
                <p className="text-2xl font-semibold">{(dataset.coverage * 100).toFixed(1)}%</p>
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">File Size</p>
                <p className="text-2xl font-semibold">{formatFileSize(dataset.sizeBytes)}</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground pt-4 border-t">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Created {formatDate(dataset.createdAt)}
              </div>
              {dataset.version && dataset.version > 1 && (
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4" />
                  Version {dataset.version}
                </div>
              )}
            </div>
            {dataset.description && (
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="mt-1">{dataset.description}</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="statistics" className="space-y-4 mt-4">
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <BarChart3 className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm font-medium text-muted-foreground">Dataset Statistics Coming Soon</p>
              <p className="text-xs text-muted-foreground/70 mt-1 max-w-sm">
                Real-time observation density, track gap distribution, and sensor type
                breakdowns will be available in a future release.
              </p>
            </div>
          </TabsContent>

          <TabsContent value="sample" className="mt-4">
            <div className="rounded-lg border bg-muted/50 p-4 font-mono text-xs overflow-x-auto">
              <pre>{`{
  "observations": [
    {
      "obsId": "obs_001",
      "time": "2026-01-15T08:30:45.123Z",
      "ra": 145.234,
      "dec": -23.456,
      "raRate": 0.0012,
      "decRate": -0.0008,
      "sensorId": "SENSOR_01",
      "trackId": "TRK_001"
    },
    ...
  ],
  "truthCatalog": [
    {
      "satId": "25544",
      "epoch": "2026-01-15T00:00:00Z",
      "state": [6800.0, 0.0, 0.0, 0.0, 7.5, 0.0]
    },
    ...
  ]
}`}</pre>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Sample format showing observation and truth catalog structure
            </p>
          </TabsContent>

          {hasVersionHistory && (
            <TabsContent value="versions" className="mt-4">
              {versionsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    {versions.length} version{versions.length !== 1 ? 's' : ''} of this dataset configuration
                  </p>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {versions.map((v) => (
                      <div
                        key={v.id}
                        className={`rounded-lg border p-3 ${v.id === dataset.id ? 'border-primary bg-primary/5' : ''}`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm">v{v.version || 1}</span>
                            {v.id === dataset.id && (
                              <Badge variant="outline" className="text-xs">Current</Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(v.createdAt)}
                          </span>
                        </div>
                        <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
                          <span>{v.objectCount} objects</span>
                          <span>{v.observationCount.toLocaleString()} obs</span>
                          <span>{(v.coverage * 100).toFixed(0)}% coverage</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>
          )}
        </Tabs>

        <DialogFooter className="mt-6 flex-shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={() => dataset && onDownload?.(dataset)} className="gap-2">
            <Download className="h-4 w-4" />
            Download Dataset
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
