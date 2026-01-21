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
import { Download, Satellite, Database, Calendar } from 'lucide-react';
import { formatFileSize, formatDate } from '@/lib/utils';
import type { Dataset } from '@/types';

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
  if (!dataset) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
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

        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="sample">Sample Data</TabsTrigger>
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
            <div className="flex items-center gap-2 text-sm text-muted-foreground pt-4 border-t">
              <Calendar className="h-4 w-4" />
              Created {formatDate(dataset.createdAt)}
            </div>
            {dataset.description && (
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="mt-1">{dataset.description}</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="statistics" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground mb-2">Observation Density</p>
                <div className="h-24 flex items-end gap-1">
                  {[35, 45, 60, 75, 85, 70, 55, 40].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-primary/20 rounded-t"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">Avg: 50 obs/satellite/3-days</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground mb-2">Track Gap Distribution</p>
                <div className="h-24 flex items-end gap-1">
                  {[80, 60, 40, 25, 15, 8, 4, 2].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-stellar-cyan/20 rounded-t"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">Median gap: 2.3 orbital periods</p>
              </div>
            </div>
            <div className="rounded-lg border p-4">
              <p className="text-sm text-muted-foreground mb-2">Sensor Type Distribution</p>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orbital-leo" />
                  <span className="text-sm">Optical: 65%</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orbital-meo" />
                  <span className="text-sm">Radar: 25%</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orbital-geo" />
                  <span className="text-sm">RF: 10%</span>
                </div>
              </div>
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
        </Tabs>

        <DialogFooter className="mt-6">
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
