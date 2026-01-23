import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Download, Database, Satellite, Calendar } from 'lucide-react';
import { formatFileSize, formatDate, cn } from '@/lib/utils';
import type { Dataset, OrbitalRegime, DataTier } from '@/types';

interface DatasetCardProps {
  dataset: Dataset;
  onPreview?: (dataset: Dataset) => void;
  onDownload?: (dataset: Dataset) => void;
}

const regimeStyles: Record<OrbitalRegime, { color: string; bgColor: string; borderColor: string; glowColor: string }> = {
  LEO: {
    color: 'text-cosmic-blue',
    bgColor: 'bg-cosmic-blue/10',
    borderColor: 'border-cosmic-blue/30',
    glowColor: 'group-hover:shadow-glow-blue',
  },
  MEO: {
    color: 'text-aurora-green',
    bgColor: 'bg-aurora-green/10',
    borderColor: 'border-aurora-green/30',
    glowColor: 'group-hover:shadow-[0_0_20px_-5px_hsl(142_76%_45%_/_0.5)]',
  },
  GEO: {
    color: 'text-amber-400',
    bgColor: 'bg-amber-400/10',
    borderColor: 'border-amber-400/30',
    glowColor: 'group-hover:shadow-[0_0_20px_-5px_hsl(45_93%_47%_/_0.5)]',
  },
  HEO: {
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
    borderColor: 'border-red-400/30',
    glowColor: 'group-hover:shadow-[0_0_20px_-5px_hsl(0_72%_51%_/_0.5)]',
  },
};

const tierStyles: Record<DataTier, { color: string; bgColor: string; borderColor: string; label: string }> = {
  T1: {
    color: 'text-aurora-green',
    bgColor: 'bg-aurora-green/10',
    borderColor: 'border-aurora-green/30',
    label: 'Pristine',
  },
  T2: {
    color: 'text-cosmic-blue',
    bgColor: 'bg-cosmic-blue/10',
    borderColor: 'border-cosmic-blue/30',
    label: 'Downsampled',
  },
  T3: {
    color: 'text-amber-400',
    bgColor: 'bg-amber-400/10',
    borderColor: 'border-amber-400/30',
    label: 'Simulated',
  },
  T4: {
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
    borderColor: 'border-red-400/30',
    label: 'Synthetic',
  },
};

export function DatasetCard({ dataset, onPreview, onDownload }: DatasetCardProps) {
  const regime = regimeStyles[dataset.regime];
  const tier = tierStyles[dataset.tier];

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border border-white/10 bg-card transition-all duration-300 group',
        'hover:border-white/20',
        regime.glowColor
      )}
    >
      {/* Top accent line based on regime */}
      <div
        className={cn(
          'absolute top-0 left-0 right-0 h-0.5 opacity-0 group-hover:opacity-100 transition-opacity',
          regime.bgColor.replace('/10', '')
        )}
        style={{
          background: `linear-gradient(90deg, transparent, ${
            dataset.regime === 'LEO' ? 'hsl(217, 91%, 60%)' :
            dataset.regime === 'MEO' ? 'hsl(142, 76%, 45%)' :
            dataset.regime === 'GEO' ? 'hsl(45, 93%, 47%)' :
            'hsl(0, 72%, 51%)'
          }, transparent)`,
        }}
      />

      {/* Header */}
      <div className="p-5 pb-3">
        <div className="flex items-start justify-between gap-2 mb-3">
          <h3 className="font-display font-semibold truncate text-foreground group-hover:text-gradient-cosmic transition-colors">
            {dataset.name}
          </h3>
        </div>

        {/* Badges */}
        <div className="flex gap-2">
          <Badge
            variant="outline"
            className={cn(
              'font-medium border',
              regime.color,
              regime.bgColor,
              regime.borderColor
            )}
          >
            {dataset.regime}
          </Badge>
          <Badge
            variant="outline"
            className={cn(
              'font-medium border',
              tier.color,
              tier.bgColor,
              tier.borderColor
            )}
          >
            {dataset.tier} - {tier.label}
          </Badge>
        </div>
      </div>

      {/* Stats */}
      <div className="px-5 pb-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Satellite className={cn('h-4 w-4', regime.color)} />
            <span>
              <span className="font-semibold">{dataset.objectCount}</span>{' '}
              <span className="text-muted-foreground">objects</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span>
              <span className="font-semibold">{dataset.observationCount.toLocaleString()}</span>{' '}
              <span className="text-muted-foreground">obs</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs">Coverage:</span>
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className={cn('h-full rounded-full', regime.bgColor.replace('/10', ''))}
                  style={{
                    width: `${dataset.coverage * 100}%`,
                    background: dataset.regime === 'LEO' ? 'hsl(217, 91%, 60%)' :
                               dataset.regime === 'MEO' ? 'hsl(142, 76%, 45%)' :
                               dataset.regime === 'GEO' ? 'hsl(45, 93%, 47%)' :
                               'hsl(0, 72%, 51%)',
                  }}
                />
              </div>
              <span className="font-semibold text-xs">{(dataset.coverage * 100).toFixed(0)}%</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs">Size:</span>
            <span className="font-semibold text-xs">{formatFileSize(dataset.sizeBytes)}</span>
          </div>
        </div>

        {/* Date */}
        <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {formatDate(dataset.createdAt)}
        </div>
      </div>

      {/* Actions */}
      <div className="border-t border-white/10 p-3 flex gap-2 bg-white/[0.02]">
        <Button
          variant="ghost"
          size="sm"
          className="flex-1 gap-1.5 text-muted-foreground hover:text-foreground hover:bg-white/5"
          onClick={() => onPreview?.(dataset)}
        >
          <Eye className="h-4 w-4" />
          Preview
        </Button>
        <Button
          size="sm"
          className={cn(
            'flex-1 gap-1.5 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity'
          )}
          onClick={() => onDownload?.(dataset)}
        >
          <Download className="h-4 w-4" />
          Download
        </Button>
      </div>
    </div>
  );
}
