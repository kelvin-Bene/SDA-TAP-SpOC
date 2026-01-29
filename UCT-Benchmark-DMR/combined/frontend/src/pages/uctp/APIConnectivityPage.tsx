import {
  Radio,
  RefreshCw,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  Wifi,
  Shield,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InfoPopover, StepExplainer } from '@/components/ui/info-popover';
import {
  useAPIConnectivity,
  useTestConnection,
  useTestAllConnections,
} from '@/hooks/useAPIConnectivity';
import { ConnectorStatusCard } from '@/components/uctp/ConnectorStatusCard';

/** Per-service educational descriptions for InfoPopovers in the grid. */
const serviceDescriptions: Record<string, { title: string; description: string; variant: 'info' | 'tip' | 'warning' | 'concept' }> = {
  orekit: {
    title: 'Orekit JVM',
    description:
      'Java-based astrodynamics library for high-fidelity orbit propagation and coordinate transformations.',
    variant: 'concept',
  },
  orbdetpy: {
    title: 'orbdetpy',
    description:
      'Python orbit determination library providing IOD methods (Gauss, Gooding) and batch least-squares refinement.',
    variant: 'concept',
  },
  spacetrack: {
    title: 'Space-Track.org',
    description:
      'U.S. military catalog providing TLEs (Two-Line Elements) for ~30,000 tracked objects.',
    variant: 'info',
  },
  satnogs: {
    title: 'SatNOGS',
    description:
      'Open-source RF ground station network. Provides Doppler and signal strength observations.',
    variant: 'info',
  },
  celestrak: {
    title: 'CelesTrak',
    description:
      "Dr. Kelso's curated TLE distribution service. Provides supplementary orbital elements.",
    variant: 'info',
  },
  udl: {
    title: 'UDL API',
    description:
      'Unified Data Library providing optical and radar observations from the Space Surveillance Network.',
    variant: 'warning',
  },
};

export function APIConnectivityPage() {
  const { data: connectors, isLoading } = useAPIConnectivity();
  const testOne = useTestConnection();
  const testAll = useTestAllConnections();

  const connected =
    connectors?.filter((c) => c.status === 'connected').length ?? 0;
  const total = connectors?.length ?? 0;
  const failed = total - connected;
  const healthPct = total > 0 ? Math.round((connected / total) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* ---------------------------------------------------------------- */}
      {/*  Gradient Hero Header                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-aurora-green/5 via-transparent to-cosmic-cyan/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-aurora-green/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />

        <div className="relative z-10">
          <div className="flex items-center justify-between flex-wrap gap-4">
            {/* Left: Title block */}
            <div>
              <div className="flex items-center gap-2 text-aurora-green text-sm font-medium mb-2">
                <Radio className="h-4 w-4" />
                API Connectivity
              </div>
              <h1 className="text-3xl font-display font-bold tracking-tight">
                Service{' '}
                <span className="text-gradient-cosmic">Health Monitor</span>
              </h1>
              <p className="text-muted-foreground mt-2 max-w-2xl">
                Monitor and test connections to external computation services
                and data providers required for UCT processing.
              </p>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-3">
              <InfoPopover
                title="External Service Dependencies"
                description="The UCTP pipeline depends on several external services for orbit computation, data access, and validation."
                details={[
                  'Orekit/orbdetpy: Physics engines for orbit propagation and determination',
                  'Space-Track/CelesTrak: TLE catalogs for reference orbits',
                  'SatNOGS: RF observation data from ground stations',
                  'UDL: Primary observation data from the U.S. sensor network',
                ]}
                variant="info"
                size="md"
              />
              <Button
                onClick={() => testAll.mutate()}
                disabled={testAll.isPending}
                className="gap-2 bg-gradient-to-r from-aurora-green to-cosmic-cyan hover:opacity-90 transition-opacity"
              >
                <RefreshCw
                  className={`h-4 w-4 ${testAll.isPending ? 'animate-spin' : ''}`}
                />
                {testAll.isPending ? 'Testing...' : 'Test All'}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Summary Cards                                                    */}
      {/* ---------------------------------------------------------------- */}
      <div className="grid gap-4 sm:grid-cols-3">
        {/* Connected */}
        <div className="group relative overflow-hidden rounded-xl border border-aurora-green/20 bg-gradient-to-br from-aurora-green/10 to-aurora-green/5 p-5 transition-all duration-300 hover:border-aurora-green/40 hover:shadow-lg hover:shadow-aurora-green/5">
          <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-aurora-green/10 blur-2xl transition-all duration-300 group-hover:bg-aurora-green/20" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-1.5 rounded-lg bg-aurora-green/15">
                <CheckCircle2 className="h-4 w-4 text-aurora-green" />
              </div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Connected
              </span>
            </div>
            <p className="text-3xl font-display font-bold tabular-nums">
              {isLoading ? (
                <span className="inline-block h-8 w-8 animate-pulse rounded bg-aurora-green/10" />
              ) : (
                connected
              )}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {isLoading ? 'Loading...' : `of ${total} services online`}
            </p>
          </div>
        </div>

        {/* Failed */}
        <div className="group relative overflow-hidden rounded-xl border border-red-400/20 bg-gradient-to-br from-red-400/10 to-red-400/5 p-5 transition-all duration-300 hover:border-red-400/40 hover:shadow-lg hover:shadow-red-400/5">
          <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-red-400/10 blur-2xl transition-all duration-300 group-hover:bg-red-400/20" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-1.5 rounded-lg bg-red-400/15">
                <XCircle className="h-4 w-4 text-red-400" />
              </div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Failed
              </span>
            </div>
            <p className="text-3xl font-display font-bold tabular-nums">
              {isLoading ? (
                <span className="inline-block h-8 w-8 animate-pulse rounded bg-red-400/10" />
              ) : (
                failed
              )}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {isLoading
                ? 'Loading...'
                : failed === 0
                  ? 'All services healthy'
                  : `${failed} service${failed > 1 ? 's' : ''} need attention`}
            </p>
          </div>
        </div>

        {/* Overall Health */}
        <div className="group relative overflow-hidden rounded-xl border border-cosmic-cyan/20 bg-gradient-to-br from-cosmic-cyan/10 to-cosmic-cyan/5 p-5 transition-all duration-300 hover:border-cosmic-cyan/40 hover:shadow-lg hover:shadow-cosmic-cyan/5">
          <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-cosmic-cyan/10 blur-2xl transition-all duration-300 group-hover:bg-cosmic-cyan/20" />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <div className="p-1.5 rounded-lg bg-cosmic-cyan/15">
                <Activity className="h-4 w-4 text-cosmic-cyan" />
              </div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Health
              </span>
            </div>
            <p className="text-3xl font-display font-bold tabular-nums">
              {isLoading ? (
                <span className="inline-block h-8 w-8 animate-pulse rounded bg-cosmic-cyan/10" />
              ) : total > 0 ? (
                <span className={healthPct === 100 ? 'text-aurora-green' : healthPct >= 50 ? 'text-cosmic-cyan' : 'text-red-400'}>
                  {healthPct}%
                </span>
              ) : (
                '--'
              )}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {isLoading
                ? 'Loading...'
                : healthPct === 100
                  ? 'All systems operational'
                  : 'System availability'}
            </p>
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/*  Test-All Results Banner                                          */}
      {/* ---------------------------------------------------------------- */}
      {testAll.data && (
        <div className="flex items-center gap-3 rounded-xl border border-aurora-green/30 bg-aurora-green/5 px-5 py-3">
          <div className="p-1.5 rounded-lg bg-aurora-green/15">
            <Clock className="h-4 w-4 text-aurora-green" />
          </div>
          <span className="text-sm text-muted-foreground">
            Sweep completed at{' '}
            <span className="font-medium text-foreground">
              {new Date(testAll.data.tested_at).toLocaleTimeString()}
            </span>{' '}
            &mdash;{' '}
            <span className="text-aurora-green font-medium">
              {testAll.data.total_connected} connected
            </span>
            ,{' '}
            <span className="text-red-400 font-medium">
              {testAll.data.total_failed} failed
            </span>
          </span>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/*  Service Grid                                                     */}
      {/* ---------------------------------------------------------------- */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-48 gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-cosmic-cyan border-t-transparent" />
          <p className="text-sm text-muted-foreground animate-pulse">
            Loading service status...
          </p>
        </div>
      ) : connectors && connectors.length > 0 ? (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">External Services</h2>
            <span className="text-xs text-muted-foreground">
              ({connected}/{total} online)
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connectors.map((connector) => {
              const svcInfo = serviceDescriptions[connector.service_name];
              return (
                <div key={connector.service_name} className="relative">
                  <ConnectorStatusCard
                    connector={connector}
                    onTest={() => testOne.mutate(connector.service_name)}
                    isTesting={testOne.isPending}
                  />
                  {/* Educational InfoPopover overlay in the bottom-right corner */}
                  {svcInfo && (
                    <div className="absolute bottom-3 right-3">
                      <InfoPopover
                        title={svcInfo.title}
                        description={svcInfo.description}
                        variant={svcInfo.variant}
                        size="sm"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-white/10 p-16 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-cosmic-cyan/10 to-aurora-green/10">
            <Wifi className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium text-muted-foreground">
            No connectivity data available
          </p>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            Click &quot;Test All&quot; above to probe service availability and
            populate the dashboard.
          </p>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/*  Troubleshooting Guide                                            */}
      {/* ---------------------------------------------------------------- */}
      <StepExplainer
        title="Connectivity Troubleshooting"
        description="If services show as failed, here are common fixes."
        tips={[
          'Orekit requires a running JVM service - check that the Java backend is started',
          'Space-Track requires credentials - configure them in Settings',
          'UDL API requires a DoD CAC or authorized credentials',
          'SatNOGS is public but rate-limited - allow time between requests',
        ]}
        variant="warning"
        defaultOpen={false}
      />

      {/* ---------------------------------------------------------------- */}
      {/*  Quick-Reference Service Info                                     */}
      {/* ---------------------------------------------------------------- */}
      <div className="rounded-xl border border-white/10 bg-card/50 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-4 w-4 text-cosmic-cyan" />
          <h2 className="text-sm font-semibold">Service Quick Reference</h2>
          <InfoPopover
            title="About This Panel"
            description="A compact reference for the six external services the UCTP pipeline relies on. Hover over any service name above for a deeper explanation."
            variant="tip"
            size="sm"
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">Orekit JVM</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Java astrodynamics library. High-fidelity orbit propagation and
              coordinate transforms.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">orbdetpy</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Python OD library. Gauss/Gooding IOD, batch least-squares, and
              EKF/UKF filters.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">
              Space-Track.org
            </p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              U.S. military TLE catalog. ~30,000 tracked objects. Requires
              credentials.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">SatNOGS</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Open-source RF ground station network. Doppler and signal
              observations.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">CelesTrak</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Dr. Kelso's curated TLE distribution. Supplementary orbital
              elements.
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-foreground">UDL API</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Unified Data Library. Optical and radar observations from the
              Space Surveillance Network.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
