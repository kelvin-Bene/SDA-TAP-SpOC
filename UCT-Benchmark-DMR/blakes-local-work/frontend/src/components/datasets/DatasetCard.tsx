import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Eye, Download, Database, Satellite, Calendar } from 'lucide-react';
import { formatFileSize, formatDate } from '@/lib/utils';
import type { Dataset, OrbitalRegime, DataTier } from '@/types';

interface DatasetCardProps {
  dataset: Dataset;
  onPreview?: (dataset: Dataset) => void;
  onDownload?: (dataset: Dataset) => void;
}

function getRegimeBadgeVariant(regime: OrbitalRegime) {
  switch (regime) {
    case 'LEO':
      return 'leo';
    case 'MEO':
      return 'meo';
    case 'GEO':
      return 'geo';
    case 'HEO':
      return 'heo';
  }
}

function getTierBadgeVariant(tier: DataTier) {
  switch (tier) {
    case 'T1':
      return 'tier1';
    case 'T2':
      return 'tier2';
    case 'T3':
      return 'tier3';
    case 'T4':
      return 'tier4';
  }
}

function getTierDescription(tier: DataTier) {
  switch (tier) {
    case 'T1':
      return 'Pristine';
    case 'T2':
      return 'Downsampled';
    case 'T3':
      return 'Simulated Obs';
    case 'T4':
      return 'Synthetic';
  }
}

export function DatasetCard({ dataset, onPreview, onDownload }: DatasetCardProps) {
  return (
    <Card className="overflow-hidden transition-all hover:shadow-lg hover:-translate-y-0.5">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <h3 className="font-semibold truncate">{dataset.name}</h3>
        </div>
        <div className="flex gap-2 mt-2">
          <Badge variant={getRegimeBadgeVariant(dataset.regime)}>
            {dataset.regime}
          </Badge>
          <Badge variant={getTierBadgeVariant(dataset.tier)}>
            {dataset.tier} - {getTierDescription(dataset.tier)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Satellite className="h-4 w-4 text-muted-foreground" />
            <span>
              <span className="font-medium">{dataset.objectCount}</span>{' '}
              <span className="text-muted-foreground">objects</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <span>
              <span className="font-medium">{dataset.observationCount.toLocaleString()}</span>{' '}
              <span className="text-muted-foreground">obs</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Coverage:</span>
            <span className="font-medium">{(dataset.coverage * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Size:</span>
            <span className="font-medium">{formatFileSize(dataset.sizeBytes)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {formatDate(dataset.createdAt)}
        </div>
      </CardContent>
      <CardFooter className="border-t pt-3 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 gap-1"
          onClick={() => onPreview?.(dataset)}
        >
          <Eye className="h-4 w-4" />
          Preview
        </Button>
        <Button
          size="sm"
          className="flex-1 gap-1"
          onClick={() => onDownload?.(dataset)}
        >
          <Download className="h-4 w-4" />
          Download
        </Button>
      </CardFooter>
    </Card>
  );
}
