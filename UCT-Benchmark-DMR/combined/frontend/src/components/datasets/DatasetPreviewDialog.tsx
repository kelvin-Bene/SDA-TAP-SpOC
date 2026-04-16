import { useMemo } from 'react';
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
import { useDatasetVersions, useDatasetObservations } from '@/hooks/useDatasets';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

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

  const { data: obsData, isLoading: obsLoading } = useDatasetObservations(
    open && dataset ? dataset.id : null,
    { limit: 500 }
  );

  const chartData = useMemo(() => {
    const obs = obsData?.observations ?? [];
    if (!obs.length) return null;

    // Observations per satellite
    const perSat: Record<string, number> = {};
    obs.forEach((o: any) => {
      const key = o.sat_no ? `SAT-${o.sat_no}` : 'Unknown';
      perSat[key] = (perSat[key] || 0) + 1;
    });
    const perSatData = Object.entries(perSat)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Sensor breakdown
    const perSensor: Record<string, number> = {};
    obs.forEach((o: any) => {
      const key = o.sensor_name || o.sensor_id || 'Unknown';
      perSensor[key] = (perSensor[key] || 0) + 1;
    });
    const sensorData = Object.entries(perSensor)
      .map(([name, value]) => ({ name: name.length > 15 ? name.slice(0, 15) + '...' : name, value }))
      .sort((a, b) => b.value - a.value);

    return { perSatData, sensorData };
  }, [obsData]);

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
            {obsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !chartData ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <BarChart3 className="h-12 w-12 text-muted-foreground/30 mb-4" />
                <p className="text-sm text-muted-foreground">No observation data available</p>
              </div>
            ) : (
              <>
                {/* Summary stats */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="rounded-lg border bg-muted/30 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Objects</p>
                    <p className="text-lg font-bold">{dataset.objectCount}</p>
                  </div>
                  <div className="rounded-lg border bg-muted/30 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Observations</p>
                    <p className="text-lg font-bold">{dataset.observationCount.toLocaleString()}</p>
                  </div>
                  <div className="rounded-lg border bg-muted/30 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Coverage</p>
                    <p className="text-lg font-bold">{(dataset.coverage * 100).toFixed(1)}%</p>
                  </div>
                  <div className="rounded-lg border bg-muted/30 p-3 text-center">
                    <p className="text-xs text-muted-foreground">Avg Obs/Object</p>
                    <p className="text-lg font-bold">
                      {dataset.objectCount > 0 ? Math.round(dataset.observationCount / dataset.objectCount) : 0}
                    </p>
                  </div>
                </div>

                {/* Observations per satellite chart */}
                {chartData.perSatData.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Observations per Object</p>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={chartData.perSatData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 30% 18%)" />
                        <XAxis dataKey="name" fontSize={10} stroke="hsl(222 20% 50%)" />
                        <YAxis fontSize={10} stroke="hsl(222 20% 50%)" />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'hsl(222 47% 5%)', borderColor: 'hsl(222 30% 18%)', fontSize: 12 }}
                        />
                        <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Sensor breakdown */}
                {chartData.sensorData.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Sensor Breakdown</p>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={chartData.sensorData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 30% 18%)" />
                        <XAxis type="number" fontSize={10} stroke="hsl(222 20% 50%)" />
                        <YAxis dataKey="name" type="category" fontSize={10} stroke="hsl(222 20% 50%)" width={100} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'hsl(222 47% 5%)', borderColor: 'hsl(222 30% 18%)', fontSize: 12 }}
                        />
                        <Bar dataKey="value" fill="#06B6D4" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          <TabsContent value="sample" className="mt-4">
            <div className="rounded-lg border bg-muted/50 p-4 font-mono text-xs overflow-x-auto">
              <pre>{`{
  "dataset": {
    "id": 155,
    "name": "example-leo-t1",
    "regime": "LEO",
    "tier": "T1",
    "observation_count": 1200,
    "satellite_count": 3,
    "calibration_quality": "GOOD",
    "maneuver_during_gap": false,
    "created_at": "2026-04-14T12:34:56Z"
  },
  "observations": [
    {
      "obTime": "2026-04-14T08:30:45.123Z",
      "ra": 145.234,
      "declination": -23.456,
      "azimuth": 92.11,
      "elevation": 47.80,
      "senlat": 34.744,
      "senlon": -120.573,
      "senalt": 0.123,
      "idSensor": "SENSOR_01",
      "trackId": "TRK_001",
      "split": "train"
    },
    ...
  ]
}`}</pre>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Sample format — state vectors and satellite IDs are not included in downloads (answer-key separation, Apr 9 2026).
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
