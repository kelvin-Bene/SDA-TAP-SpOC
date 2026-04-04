import { useNavigate } from 'react-router-dom';
import { useDataSourceStatus } from '@/hooks/useDataSourceStatus';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, Settings2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DataSourceStatusIndicatorProps {
  selectedPreset: string | null;
}

/**
 * Displays the current credential configuration status for the dataset generator.
 * Shows warnings when required credentials are missing for the selected preset.
 */
export function DataSourceStatusIndicator({ selectedPreset }: DataSourceStatusIndicatorProps) {
  const navigate = useNavigate();
  const {
    getMissingForPreset,
    configuredCount,
    totalCount,
    isLoading,
  } = useDataSourceStatus();

  if (isLoading) {
    return (
      <Card className="p-4 mb-4 border-white/10">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Checking data source configuration...</span>
        </div>
      </Card>
    );
  }

  const missing = selectedPreset ? getMissingForPreset(selectedPreset) : [];
  const hasWarning = missing.length > 0;

  // Don't show anything if no credentials are configured yet (first-time users)
  if (totalCount === 0) {
    return null;
  }

  return (
    <Card
      className={cn(
        'p-4 mb-4 transition-colors duration-200',
        hasWarning
          ? 'border-nova-orange/40 bg-nova-orange/5'
          : configuredCount > 0
          ? 'border-aurora-green/40 bg-aurora-green/5'
          : 'border-white/10'
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {hasWarning ? (
            <div className="p-2 rounded-lg bg-nova-orange/15">
              <AlertTriangle className="h-5 w-5 text-nova-orange" />
            </div>
          ) : configuredCount > 0 ? (
            <div className="p-2 rounded-lg bg-aurora-green/15">
              <CheckCircle className="h-5 w-5 text-aurora-green" />
            </div>
          ) : (
            <div className="p-2 rounded-lg bg-white/5">
              <Settings2 className="h-5 w-5 text-muted-foreground" />
            </div>
          )}
          <div>
            <p className="font-medium text-sm">
              {configuredCount}/{totalCount} data sources configured
            </p>
            <p className="text-xs text-muted-foreground">
              {hasWarning
                ? 'Some required credentials are missing'
                : configuredCount === totalCount
                ? 'All data sources ready'
                : 'Configure credentials to access more data sources'}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="border-white/10 hover:border-white/20"
          onClick={() => navigate('/settings')}
        >
          <Settings2 className="h-4 w-4 mr-2" />
          Configure
        </Button>
      </div>

      {hasWarning && selectedPreset && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-nova-orange/30 bg-nova-orange/5 p-3">
          <AlertTriangle className="h-4 w-4 text-nova-orange flex-shrink-0 mt-0.5" />
          <p className="text-sm text-muted-foreground">
            This preset requires:{' '}
            <strong className="text-nova-orange">
              {missing.map((svc) => svc.toUpperCase()).join(', ')}
            </strong>
            . Configure credentials in Settings to use this preset.
          </p>
        </div>
      )}
    </Card>
  );
}
