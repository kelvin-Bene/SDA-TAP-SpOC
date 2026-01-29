import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Download, Database, Satellite, Calendar, Orbit } from 'lucide-react';
import { formatFileSize, formatDate, cn } from '@/lib/utils';
import type { Dataset, OrbitalRegime, DataTier } from '@/types';

interface DatasetCardProps {
  dataset: Dataset;
  onPreview?: (dataset: Dataset) => void;
  onDownload?: (dataset: Dataset) => void;
}

const regimeStyles: Record<OrbitalRegime, { color: string; bgColor: string; borderColor: string; glowColor: string; dotColor: string; gradient: string }> = {
  LEO: {
    color: 'text-cosmic-blue',
    bgColor: 'bg-cosmic-blue/10',
    borderColor: 'border-cosmic-blue/30',
    glowColor: 'group-hover:shadow-[0_0_24px_-6px_hsl(217_91%_60%/0.35)]',
    dotColor: 'bg-cosmic-blue',
    gradient: 'hsl(217, 91%, 60%)',
  },
  MEO: {
    color: 'text-aurora-green',
    bgColor: 'bg-aurora-green/10',
    borderColor: 'border-aurora-green/30',
    glowColor: 'group-hover:shadow-[0_0_24px_-6px_hsl(142_76%_45%/0.35)]',
    dotColor: 'bg-aurora-green',
    gradient: 'hsl(142, 76%, 45%)',
  },
  GEO: {
    color: 'text-amber-400',
    bgColor: 'bg-amber-400/10',
    borderColor: 'border-amber-400/30',
    glowColor: 'group-hover:shadow-[0_0_24px_-6px_hsl(45_93%_47%/0.35)]',
    dotColor: 'bg-amber-400',
    gradient: 'hsl(45, 93%, 47%)',
  },
  HEO: {
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
    borderColor: 'border-red-400/30',
    glowColor: 'group-hover:shadow-[0_0_24px_-6px_hsl(0_72%_51%/0.35)]',
    dotColor: 'bg-red-400',
    gradient: 'hsl(0, 72%, 51%)',
  },
};

const tierStyles: Record<DataTier, { color: string; bgColor: string; borderColor: string; label: string }> = {
  T1: { color: 'text-aurora-green', bgColor: 'bg-aurora-green/10', borderColor: 'border-aurora-green/30', label: 'Pristine' },
  T1H: { color: 'text-stellar-purple', bgColor: 'bg-stellar-purple/10', borderColor: 'border-stellar-purple/30', label: 'Validated' },
  T2: { color: 'text-cosmic-blue', bgColor: 'bg-cosmic-blue/10', borderColor: 'border-cosmic-blue/30', label: 'Downsampled' },
  T3: { color: 'text-nova-orange', bgColor: 'bg-nova-orange/10', borderColor: 'border-nova-orange/30', label: 'Simulated' },
  T4: { color: 'text-red-400', bgColor: 'bg-red-400/10', borderColor: 'border-red-400/30', label: 'Synthetic' },
};

export function DatasetCard({ dataset, onPreview, onDownload }: DatasetCardProps) {
  const regime = regimeStyles[dataset.regime];
  const tier = tierStyles[dataset.tier];

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border border-white/10 bg-card transition-all duration-300 group',
        'hover:border-white/20',
        regime.glowColor,
      )}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{
          background: `linear-gradient(90deg, transparent, ${regime.gradient}, transparent)`,
        }}
      />

      {/* Header */}
      <div className="p-5 pb-3">
        <div className="flex items-start justify-between gap-2 mb-3">
          <h3 className="font-display font-semibold truncate text-foreground group-hover:text-cosmic-cyan transition-colors">
            {dataset.name}
          </h3>
        </div>

        {/* Badges */}
        <div className="flex gap-2 flex-wrap">
          <Badge
            variant="outline"
            className={cn('font-medium border text-[10px]', regime.color, regime.bgColor, regime.borderColor)}
          >
            <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5', regime.dotColor)} />
            {dataset.regime}
          </Badge>
          <Badge
            variant="outline"
            className={cn('font-medium border text-[10px]', tier.color, tier.bgColor, tier.borderColor)}
          >
            {dataset.tier} - {tier.label}
          </Badge>
        </div>
      </div>

      {/* Stats */}
      <div className="px-5 pb-4 space-y-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          <div className="flex items-center gap-2">
            <Satellite className={cn('h-3.5 w-3.5', regime.color)} />
            <span className="text-xs">
              <span className="font-semibold text-foreground">{dataset.objectCount}</span>{' '}
              <span className="text-muted-foreground">objects</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-3.5 w-3.5 text-cosmic-cyan" />
            <span className="text-xs">
              <span className="font-semibold text-foreground">{dataset.observationCount.toLocaleString()}</span>{' '}
              <span className="text-muted-foreground">obs</span>
            </span>
          </div>
        </div>

        {/* Coverage bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground flex items-center gap-1">
              <Orbit className="h-3 w-3" />
              Coverage
            </span>
            <span className="font-semibold font-mono">{(dataset.coverage * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${dataset.coverage * 100}%`, background: regime.gradient }}
            />
          </div>
        </div>

        {/* Date & Size */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Calendar className="h-3 w-3" />
            {formatDate(dataset.createdAt)}
          </span>
          <span className="font-mono">{formatFileSize(dataset.sizeBytes)}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="border-t border-white/10 p-3 flex gap-2 bg-white/[0.02]">
        <Button
          variant="ghost"
          size="sm"
          className="flex-1 gap-1.5 h-8 text-xs text-muted-foreground hover:text-foreground hover:bg-white/5"
          onClick={() => onPreview?.(dataset)}
        >
          <Eye className="h-3.5 w-3.5" />
          Preview
        </Button>
        <Button
          size="sm"
          className="flex-1 gap-1.5 h-8 text-xs bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity"
          onClick={() => onDownload?.(dataset)}
        >
          <Download className="h-3.5 w-3.5" />
          Download
        </Button>
      </div>
    </div>
  );
}
