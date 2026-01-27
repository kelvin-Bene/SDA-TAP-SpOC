import { Wifi, RefreshCw, Activity, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAPIConnectivity, useTestConnection, useTestAllConnections } from '@/hooks/useAPIConnectivity';
import { ConnectorStatusCard } from '@/components/uctp/ConnectorStatusCard';

export function APIConnectivityPage() {
  const { data: connectors, isLoading } = useAPIConnectivity();
  const testOne = useTestConnection();
  const testAll = useTestAllConnections();

  const connected = connectors?.filter((c) => c.status === 'connected').length ?? 0;
  const total = connectors?.length ?? 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-aurora-green text-sm font-medium mb-1">
            <Wifi className="h-4 w-4" />
            API Connectivity
          </div>
          <h1 className="text-3xl font-display font-bold tracking-tight">External Service Status</h1>
          <p className="text-muted-foreground mt-1">Test and monitor connections to external APIs and libraries.</p>
        </div>
        <Button
          onClick={() => testAll.mutate()}
          disabled={testAll.isPending}
          className="gap-2 bg-gradient-to-r from-aurora-green to-cosmic-cyan hover:opacity-90"
        >
          <RefreshCw className={`h-4 w-4 ${testAll.isPending ? 'animate-spin' : ''}`} />
          {testAll.isPending ? 'Testing...' : 'Test All Connections'}
        </Button>
      </div>

      {/* Summary Bar */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-aurora-green/20 bg-gradient-to-br from-aurora-green/10 to-aurora-green/5 p-5">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-aurora-green" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Connected</span>
          </div>
          <p className="text-2xl font-display font-bold">{isLoading ? '...' : connected}</p>
        </div>
        <div className="rounded-xl border border-red-400/20 bg-gradient-to-br from-red-400/10 to-red-400/5 p-5">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="h-4 w-4 text-red-400" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Failed</span>
          </div>
          <p className="text-2xl font-display font-bold">{isLoading ? '...' : total - connected}</p>
        </div>
        <div className="rounded-xl border border-cosmic-cyan/20 bg-gradient-to-br from-cosmic-cyan/10 to-cosmic-cyan/5 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="h-4 w-4 text-cosmic-cyan" />
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Health</span>
          </div>
          <p className="text-2xl font-display font-bold">
            {isLoading ? '...' : total > 0 ? `${Math.round((connected / total) * 100)}%` : '--'}
          </p>
        </div>
      </div>

      {/* Test All Results */}
      {testAll.data && (
        <div className="rounded-xl border border-aurora-green/30 bg-aurora-green/5 p-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-aurora-green" />
            <span>
              Test completed at {new Date(testAll.data.tested_at).toLocaleTimeString()} &middot;{' '}
              <span className="text-aurora-green font-medium">{testAll.data.total_connected} connected</span>,{' '}
              <span className="text-red-400 font-medium">{testAll.data.total_failed} failed</span>
            </span>
          </div>
        </div>
      )}

      {/* Service Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cosmic-cyan" />
        </div>
      ) : connectors && connectors.length > 0 ? (
        <div>
          <h2 className="text-sm font-semibold mb-4">Services</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connectors.map((connector) => (
              <ConnectorStatusCard
                key={connector.service_name}
                connector={connector}
                onTest={() => testOne.mutate(connector.service_name)}
                isTesting={testOne.isPending}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-white/10 p-12 text-center">
          <Wifi className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No connectivity data yet.</p>
          <p className="text-xs text-muted-foreground mt-1">Click "Test All Connections" to check service availability.</p>
        </div>
      )}

      {/* Info */}
      <div className="rounded-xl border border-white/10 bg-card p-5">
        <h2 className="text-sm font-semibold mb-3">About Services</h2>
        <div className="grid gap-3 sm:grid-cols-2 text-xs text-muted-foreground">
          <div>
            <p className="font-medium text-foreground">Orekit JVM</p>
            <p>Java-based orbit determination library. Provides Gooding IOD and advanced propagation.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">orbdetpy</p>
            <p>Python orbit determination library from UT Austin. Supports Laplace IOD, batch LS, and EKF/UKF.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">Space-Track.org</p>
            <p>US Space Command public catalog. Provides TLE data for active objects.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">SatNOGS</p>
            <p>Open satellite observation network. Provides RF observation data from ground stations.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">CelesTrak</p>
            <p>Satellite catalog and TLE distribution service by Dr. T.S. Kelso.</p>
          </div>
          <div>
            <p className="font-medium text-foreground">UDL API</p>
            <p>Unified Data Library for space domain awareness observation data.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
