import { Wifi, WifiOff, Clock, ShieldAlert, PackageX, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { ConnectorStatus } from '@/types/uctp';

const statusConfig = {
  connected: { icon: Wifi, color: 'text-aurora-green', bg: 'bg-aurora-green/10', label: 'Connected' },
  failed: { icon: WifiOff, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Failed' },
  timeout: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: 'Timeout' },
  unauthorized: { icon: ShieldAlert, color: 'text-orange-400', bg: 'bg-orange-400/10', label: 'Unauthorized' },
  not_installed: { icon: PackageX, color: 'text-muted-foreground', bg: 'bg-white/5', label: 'Not Installed' },
};

const serviceLabels: Record<string, string> = {
  orekit: 'Orekit JVM',
  orbdetpy: 'orbdetpy',
  spacetrack: 'Space-Track.org',
  satnogs: 'SatNOGS',
  celestrak: 'CelesTrak',
  udl: 'UDL API',
};

interface ConnectorStatusCardProps {
  connector: ConnectorStatus;
  onTest?: () => void;
  isTesting?: boolean;
}

export function ConnectorStatusCard({ connector, onTest, isTesting = false }: ConnectorStatusCardProps) {
  const cfg = statusConfig[connector.status] || statusConfig.failed;
  const StatusIcon = cfg.icon;

  return (
    <div className="rounded-xl border border-white/10 bg-card p-4 transition-all duration-200 hover:border-white/20">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', cfg.bg)}>
            <StatusIcon className={cn('h-4 w-4', cfg.color)} />
          </div>
          <div>
            <p className="text-sm font-medium">{serviceLabels[connector.service_name] || connector.service_name}</p>
            <p className={cn('text-xs', cfg.color)}>{cfg.label}</p>
          </div>
        </div>

        {onTest && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onTest}
            disabled={isTesting}
            className="h-8 w-8 p-0 hover:bg-white/10"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isTesting && 'animate-spin')} />
          </Button>
        )}
      </div>

      <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
        {connector.response_time_ms != null && (
          <span>{connector.response_time_ms.toFixed(0)}ms</span>
        )}
        {connector.last_checked && (
          <span>{new Date(connector.last_checked).toLocaleTimeString()}</span>
        )}
      </div>

      {connector.error_message && (
        <p className="mt-2 text-xs text-red-400/80 truncate">{connector.error_message}</p>
      )}
    </div>
  );
}
