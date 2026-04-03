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
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
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
                <p className="text-xs text-muted-foreground mt-0.5">Available after filtering</p>
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
            {/* Track Gap Distribution */}
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                Track Gap Distribution
              </h4>
              <div className="rounded-lg border bg-muted/50 p-3">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={[
                    { gap: '0-1', count: 80 },
                    { gap: '1-2', count: 60 },
                    { gap: '2-3', count: 40 },
                    { gap: '3-4', count: 25 },
                    { gap: '4-5', count: 15 },
                    { gap: '5-6', count: 8 },
                    { gap: '6-7', count: 4 },
                    { gap: '7+', count: 2 },
                  ]}>
                    <XAxis dataKey="gap" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="hsl(217, 91%, 60%)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-xs text-muted-foreground text-center mt-1">Gap duration (hours)</p>
              </div>
            </div>

            {/* Sensor Type Distribution */}
            <div>
              <h4 className="text-sm font-medium mb-2">Sensor Type Distribution</h4>
              <div className="rounded-lg border bg-muted/50 p-3 flex items-center gap-6">
                <ResponsiveContainer width={100} height={100}>
                  <PieChart>
                    <Pie
                      data={[
                        { name: 'Optical', value: 65 },
                        { name: 'Radar', value: 25 },
                        { name: 'RF', value: 10 },
                      ]}
                      cx="50%"
                      cy="50%"
                      innerRadius={20}
                      outerRadius={40}
                      dataKey="value"
                      strokeWidth={1}
                    >
                      <Cell fill="hsl(217, 91%, 60%)" />
                      <Cell fill="hsl(142, 76%, 45%)" />
                      <Cell fill="hsl(45, 93%, 47%)" />
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-col gap-1.5 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'hsl(217, 91%, 60%)' }} />
                    Optical (65%)
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'hsl(142, 76%, 45%)' }} />
                    Radar (25%)
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'hsl(45, 93%, 47%)' }} />
                    RF (10%)
                  </div>
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
