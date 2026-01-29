import { useState } from 'react';
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
import { InfoPopover } from '@/components/ui/info-popover';
import {
  Download,
  Satellite,
  Database,
  Calendar,
  BarChart3,
  FileJson,
  Eye,
  Orbit,
  Target,
  Copy,
  Check,
} from 'lucide-react';
import { formatFileSize, formatDate, cn } from '@/lib/utils';
import type { Dataset } from '@/types';

interface DatasetPreviewDialogProps {
  dataset: Dataset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDownload?: (dataset: Dataset) => void;
}

const regimeConfig: Record<string, { color: string; label: string }> = {
  LEO: { color: 'cosmic-blue', label: 'Low Earth Orbit' },
  MEO: { color: 'aurora-green', label: 'Medium Earth Orbit' },
  GEO: { color: 'amber-400', label: 'Geostationary' },
  HEO: { color: 'red-400', label: 'Highly Elliptical' },
};

const tierConfig: Record<string, { color: string; label: string }> = {
  T1: { color: 'aurora-green', label: 'Pristine' },
  T1H: { color: 'stellar-purple', label: 'Validated (ILRS)' },
  T2: { color: 'cosmic-blue', label: 'Downsampled' },
  T3: { color: 'nova-orange', label: 'Simulated Obs' },
  T4: { color: 'red-400', label: 'Synthetic' },
};

export function DatasetPreviewDialog({
  dataset,
  open,
  onOpenChange,
  onDownload,
}: DatasetPreviewDialogProps) {
  const [copied, setCopied] = useState(false);

  if (!dataset) return null;

  const regime = regimeConfig[dataset.regime] || { color: 'muted-foreground', label: dataset.regime };
  const tier = tierConfig[dataset.tier] || { color: 'muted-foreground', label: dataset.tier };

  const handleCopy = () => {
    navigator.clipboard.writeText(sampleJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sampleJson = `{
  "observations": [
    {
      "obsId": "obs_001",
      "time": "2026-01-15T08:30:45.123Z",
      "ra": 145.234,
      "dec": -23.456,
      "raRate": 0.0012,
      "decRate": -0.0008,
      "raSigma": 2.5,
      "decSigma": 2.5,
      "sensorId": "GEODSS_1",
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
}`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl border-white/10 bg-card/95 backdrop-blur-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 flex-wrap">
            <span className="font-display">{dataset.name}</span>
            <Badge
              variant="outline"
              className={cn(
                'font-medium border',
                `text-${regime.color} bg-${regime.color}/10 border-${regime.color}/30`,
              )}
            >
              {dataset.regime}
            </Badge>
            <Badge
              variant="outline"
              className={cn(
                'font-medium border',
                `text-${tier.color} bg-${tier.color}/10 border-${tier.color}/30`,
              )}
            >
              {dataset.tier} - {tier.label}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Dataset details, statistics, and sample data format
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="mt-4">
          <TabsList className="grid w-full grid-cols-3 bg-white/5 border border-white/10 rounded-xl">
            <TabsTrigger value="overview" className="gap-2 rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">
              <Eye className="h-3.5 w-3.5" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="statistics" className="gap-2 rounded-lg data-[state=active]:bg-stellar-purple/10 data-[state=active]:text-stellar-purple">
              <BarChart3 className="h-3.5 w-3.5" />
              Statistics
            </TabsTrigger>
            <TabsTrigger value="sample" className="gap-2 rounded-lg data-[state=active]:bg-aurora-green/10 data-[state=active]:text-aurora-green">
              <FileJson className="h-3.5 w-3.5" />
              Sample Data
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02] space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Satellite className={`h-3.5 w-3.5 text-${regime.color}`} />
                  Objects
                </p>
                <p className="text-2xl font-display font-bold">{dataset.objectCount}</p>
              </div>
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02] space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Database className="h-3.5 w-3.5 text-cosmic-cyan" />
                  Observations
                </p>
                <p className="text-2xl font-display font-bold">{dataset.observationCount.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02] space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Orbit className="h-3.5 w-3.5 text-stellar-purple" />
                  Coverage
                </p>
                <div className="flex items-center gap-3">
                  <p className="text-2xl font-display font-bold">{(dataset.coverage * 100).toFixed(1)}%</p>
                  <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className={`h-full rounded-full bg-${regime.color}`}
                      style={{ width: `${dataset.coverage * 100}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02] space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Target className="h-3.5 w-3.5 text-aurora-green" />
                  File Size
                </p>
                <p className="text-2xl font-display font-bold">{formatFileSize(dataset.sizeBytes)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground pt-3 border-t border-white/5">
              <Calendar className="h-4 w-4 text-cosmic-cyan" />
              Created {formatDate(dataset.createdAt)}
            </div>
            {dataset.description && (
              <div className="pt-3 border-t border-white/5">
                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">Description</p>
                <p className="text-sm leading-relaxed">{dataset.description}</p>
              </div>
            )}
          </TabsContent>

          {/* Statistics Tab */}
          <TabsContent value="statistics" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02]">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground font-medium">Observation Density</p>
                  <InfoPopover
                    title="Observation Density"
                    description="Distribution of observation counts per satellite. Higher density enables more accurate orbit determination."
                    variant="info"
                  />
                </div>
                <div className="h-24 flex items-end gap-1">
                  {[35, 45, 60, 75, 85, 70, 55, 40].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-cosmic-cyan/20 hover:bg-cosmic-cyan/30 transition-colors rounded-t"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">Avg: 50 obs/satellite/3-days</p>
              </div>
              <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02]">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground font-medium">Track Gap Distribution</p>
                  <InfoPopover
                    title="Track Gap Distribution"
                    description="Time gaps between consecutive observation tracks, measured in orbital periods. Larger gaps make track association harder."
                    variant="info"
                  />
                </div>
                <div className="h-24 flex items-end gap-1">
                  {[80, 60, 40, 25, 15, 8, 4, 2].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-stellar-purple/20 hover:bg-stellar-purple/30 transition-colors rounded-t"
                      style={{ height: `${h}%` }}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">Median gap: 2.3 orbital periods</p>
              </div>
            </div>
            <div className="rounded-xl border border-white/10 p-4 bg-white/[0.02]">
              <p className="text-xs text-muted-foreground font-medium mb-3">Sensor Type Distribution</p>
              <div className="flex gap-6">
                {[
                  { label: 'Optical', pct: 65, color: 'cosmic-cyan' },
                  { label: 'Radar', pct: 25, color: 'aurora-green' },
                  { label: 'RF', pct: 10, color: 'stellar-purple' },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full bg-${s.color}`} />
                    <span className="text-sm">{s.label}: <span className="font-semibold">{s.pct}%</span></span>
                  </div>
                ))}
              </div>
              <div className="flex mt-3 h-2 rounded-full overflow-hidden bg-white/5">
                <div className="bg-cosmic-cyan h-full" style={{ width: '65%' }} />
                <div className="bg-aurora-green h-full" style={{ width: '25%' }} />
                <div className="bg-stellar-purple h-full" style={{ width: '10%' }} />
              </div>
            </div>
          </TabsContent>

          {/* Sample Data Tab */}
          <TabsContent value="sample" className="mt-4">
            <div className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/[0.02]">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">JSON</span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  {copied ? <Check className="h-3 w-3 text-aurora-green" /> : <Copy className="h-3 w-3" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="p-4 overflow-x-auto text-xs font-mono text-muted-foreground leading-relaxed max-h-72">
                {sampleJson}
              </pre>
            </div>
            <div className="flex items-start gap-2 mt-3 rounded-lg bg-cosmic-cyan/5 border border-cosmic-cyan/20 p-3">
              <FileJson className="h-3.5 w-3.5 text-cosmic-cyan mt-0.5 flex-shrink-0" />
              <p className="text-xs text-muted-foreground">
                The actual dataset includes full observation arrays, truth catalog with state vectors, and track-to-satellite association mappings.
                See <a href="/docs" className="text-cosmic-cyan hover:underline font-medium">Documentation</a> for the complete schema.
              </p>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-6 gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="border-white/10">
            Close
          </Button>
          <Button
            onClick={() => dataset && onDownload?.(dataset)}
            className="gap-2 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity"
          >
            <Download className="h-4 w-4" />
            Download Dataset
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
