import { Link } from 'react-router-dom';
import {
  FlaskConical,
  Play,
  Brain,
  Wifi,
  Target,
  BarChart3,
  ArrowRight,
  GitCompareArrows,
  Activity,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUCTPPDashboard } from '@/hooks/useUCTPPDashboard';
import { RunStatusCard } from '@/components/uctp/RunStatusCard';
import { MetricsChart } from '@/components/uctp/MetricsChart';
import { InfoPopover, StepExplainer } from '@/components/ui/info-popover';

export function UCTPPDashboardPage() {
  const { data: stats, isLoading } = useUCTPPDashboard();

  return (
    <div className="space-y-8">
      {/* ============================================================
          Hero Header
          ============================================================ */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-stellar-purple/5 via-transparent to-cosmic-cyan/5 p-6 sm:p-8">
        <div className="absolute top-0 right-0 w-72 h-72 bg-stellar-purple/8 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-cosmic-cyan/8 rounded-full blur-3xl translate-y-1/3 -translate-x-1/4" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-2">
            <FlaskConical className="h-4 w-4" />
            UCTPP Algorithm Lab
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-bold tracking-tight">
            Algorithm <span className="text-gradient-cosmic">Testing Hub</span>
          </h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">
            Configure, run, and compare UCTP processing algorithms. Train ML
            models and test API connectivity.
          </p>

          {/* Quick action buttons */}
          <div className="flex flex-wrap gap-3 mt-6">
            <Link to="/uctp/workbench">
              <Button className="gap-2 bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90 transition-opacity">
                <Play className="h-4 w-4" />
                New Algorithm Run
              </Button>
            </Link>
            <Link to="/uctp/training">
              <Button
                variant="outline"
                className="gap-2 border-white/20 hover:bg-white/5"
              >
                <Brain className="h-4 w-4" />
                Train Model
              </Button>
            </Link>
            <Link to="/uctp/connectivity">
              <Button
                variant="outline"
                className="gap-2 border-white/20 hover:bg-white/5"
              >
                <Wifi className="h-4 w-4" />
                Test APIs
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* ============================================================
          Stat Cards with InfoPopovers
          ============================================================ */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatBox
          title="Total Runs"
          value={isLoading ? '...' : String(stats?.total_runs || 0)}
          subtitle={`${stats?.completed_runs || 0} completed`}
          icon={<BarChart3 className="h-5 w-5" />}
          color="cyan"
          popover={
            <InfoPopover
              title="Total Runs"
              description="Each run executes the full UCTPP pipeline on a dataset, including clustering, initial orbit determination, and optional refinement."
              details={[
                'A run processes raw UCTP observations through the entire pipeline',
                'Completed runs produce metrics like F1-Score and position RMS',
                'Failed runs include diagnostic logs for troubleshooting',
              ]}
              learnMore="/docs#uctp-pipeline"
              variant="info"
              size="sm"
            />
          }
        />
        <StatBox
          title="Best F1 Score"
          value={
            isLoading ? '...' : stats?.best_f1_score?.toFixed(4) || '--'
          }
          subtitle={stats?.best_algorithm || 'No runs yet'}
          icon={<Target className="h-5 w-5" />}
          color="purple"
          popover={
            <InfoPopover
              title="F1-Score Metric"
              description="The F1-Score is the harmonic mean of precision and recall, providing a single balanced measure of algorithm accuracy."
              details={[
                'Precision measures how many predicted objects are correct',
                'Recall measures how many true objects were found',
                'F1 = 2 * (Precision * Recall) / (Precision + Recall)',
                'A perfect score is 1.0; higher is better',
              ]}
              learnMore="/docs#metrics"
              variant="concept"
              size="sm"
            />
          }
        />
        <StatBox
          title="ML Models"
          value={isLoading ? '...' : String(stats?.total_models || 0)}
          subtitle={`${stats?.ready_models || 0} ready`}
          icon={<Brain className="h-5 w-5" />}
          color="blue"
          popover={
            <InfoPopover
              title="ML Models"
              description="Machine learning models can enhance UCTP processing by improving clustering accuracy and orbit propagation predictions."
              details={[
                'Clustering NN models learn optimal grouping from training data',
                'Propagation ML models predict orbital trajectories more accurately',
                'Hybrid models combine both approaches for end-to-end improvement',
                'Models in "ready" status can be used in algorithm runs',
              ]}
              learnMore="/docs#ml-models"
              variant="info"
              size="sm"
            />
          }
        />
        <StatBox
          title="API Health"
          value={
            isLoading
              ? '...'
              : `${(stats?.api_health_pct || 0).toFixed(0)}%`
          }
          subtitle="services connected"
          icon={<Wifi className="h-5 w-5" />}
          color="green"
          popover={
            <InfoPopover
              title="API Health"
              description="Indicates the availability of external services that the UCTPP pipeline depends on for orbit determination and propagation."
              details={[
                'OrbDetPy provides high-fidelity IOD solvers',
                'Orekit supplies numerical propagation and coordinate transforms',
                'Stone Soup offers multi-hypothesis tracking algorithms',
                '100% means all configured services are responding',
              ]}
              learnMore="/uctp/connectivity"
              variant="info"
              size="sm"
            />
          }
        />
      </div>

      {/* ============================================================
          Content Grid: Recent Runs + F1 Trend
          ============================================================ */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Runs */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-cosmic-cyan" />
              <h2 className="text-lg font-display font-semibold">
                Recent Runs
              </h2>
            </div>
            <Link
              to="/uctp/workbench"
              className="text-sm text-cosmic-cyan hover:underline flex items-center gap-1"
            >
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {stats?.recent_runs && stats.recent_runs.length > 0 ? (
            <div className="space-y-2">
              {stats.recent_runs.slice(0, 5).map((run) => (
                <Link key={run.id} to="/uctp/workbench">
                  <RunStatusCard run={run} compact />
                </Link>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-8 text-center">
              <FlaskConical className="h-8 w-8 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-sm font-medium text-muted-foreground">
                No runs yet
              </p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Head to the Algorithm Workbench to start your first pipeline
                run.
              </p>
            </div>
          )}
        </div>

        {/* F1 Score Chart */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-stellar-purple" />
            <h2 className="text-lg font-display font-semibold">
              F1 Score Trend
            </h2>
          </div>
          <MetricsChart
            runs={stats?.recent_runs || []}
            metric="f1_score"
            height={250}
          />
        </div>
      </div>

      {/* ============================================================
          Quick Actions
          ============================================================ */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-4 w-4 text-nova-orange" />
          <h2 className="text-lg font-display font-semibold">Quick Actions</h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QuickActionCard
            to="/uctp/workbench"
            title="Algorithm Workbench"
            description="Configure clustering, IOD, and refinement parameters then execute the full UCTPP pipeline against any dataset."
            icon={<Play className="h-6 w-6 text-cosmic-cyan" />}
            color="cyan"
            cta="Launch workbench"
          />
          <QuickActionCard
            to="/uctp/compare"
            title="Compare Runs"
            description="Place algorithm runs side-by-side to identify parameter differences and performance improvements across configurations."
            icon={<GitCompareArrows className="h-6 w-6 text-stellar-purple" />}
            color="purple"
            cta="Compare results"
          />
          <QuickActionCard
            to="/uctp/training"
            title="ML Training Studio"
            description="Train neural network and ML models on completed run data to boost clustering accuracy and propagation fidelity."
            icon={<Brain className="h-6 w-6 text-cosmic-blue" />}
            color="blue"
            cta="Train models"
          />
        </div>
      </div>

      {/* ============================================================
          Workflow Explainer
          ============================================================ */}
      <StepExplainer
        title="UCTPP Lab Workflow"
        description="The typical workflow for testing and improving your UCTP processing algorithm."
        tips={[
          'Start in the Algorithm Workbench to configure and run the UCTPP pipeline',
          'Compare results across different runs and parameter settings',
          'Train ML models to improve clustering and propagation accuracy',
          'Test API connectivity to ensure all external services are available',
        ]}
        variant="tip"
        defaultOpen={false}
      />
    </div>
  );
}

/* ================================================================
   StatBox - individual stat card with optional InfoPopover
   ================================================================ */

function StatBox({
  title,
  value,
  subtitle,
  icon,
  color,
  popover,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  color: string;
  popover?: React.ReactNode;
}) {
  const colorMap: Record<string, string> = {
    cyan: 'from-cosmic-cyan/10 to-cosmic-cyan/5 border-cosmic-cyan/20',
    purple: 'from-stellar-purple/10 to-stellar-purple/5 border-stellar-purple/20',
    blue: 'from-cosmic-blue/10 to-cosmic-blue/5 border-cosmic-blue/20',
    green: 'from-aurora-green/10 to-aurora-green/5 border-aurora-green/20',
  };
  const iconColorMap: Record<string, string> = {
    cyan: 'text-cosmic-cyan',
    purple: 'text-stellar-purple',
    blue: 'text-cosmic-blue',
    green: 'text-aurora-green',
  };

  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-5 transition-all duration-200 hover:scale-[1.02] ${colorMap[color] || colorMap.cyan}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {title}
          </span>
          {popover}
        </div>
        <span className={iconColorMap[color] || 'text-cosmic-cyan'}>
          {icon}
        </span>
      </div>
      <p className="text-2xl font-display font-bold">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
    </div>
  );
}

/* ================================================================
   QuickActionCard - enhanced navigation cards
   ================================================================ */

function QuickActionCard({
  to,
  title,
  description,
  icon,
  color,
  cta,
}: {
  to: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  cta: string;
}) {
  const hoverMap: Record<string, string> = {
    cyan: 'hover:border-cosmic-cyan/30 hover:shadow-glow-cyan',
    purple: 'hover:border-stellar-purple/30 hover:shadow-glow-purple',
    blue: 'hover:border-cosmic-blue/30',
  };
  const iconBgMap: Record<string, string> = {
    cyan: 'from-cosmic-cyan/20 to-cosmic-blue/20',
    purple: 'from-stellar-purple/20 to-cosmic-blue/20',
    blue: 'from-cosmic-blue/20 to-stellar-purple/20',
  };
  const ctaColorMap: Record<string, string> = {
    cyan: 'text-cosmic-cyan',
    purple: 'text-stellar-purple',
    blue: 'text-cosmic-blue',
  };
  const glowBgMap: Record<string, string> = {
    cyan: 'bg-cosmic-cyan/5 group-hover:bg-cosmic-cyan/10',
    purple: 'bg-stellar-purple/5 group-hover:bg-stellar-purple/10',
    blue: 'bg-cosmic-blue/5 group-hover:bg-cosmic-blue/10',
  };

  return (
    <Link to={to} className="group">
      <div
        className={`relative overflow-hidden rounded-xl border border-white/10 bg-card p-6 transition-all duration-300 ${hoverMap[color] || ''}`}
      >
        {/* Decorative glow */}
        <div
          className={`absolute top-0 right-0 w-32 h-32 rounded-full blur-2xl transition-colors ${glowBgMap[color] || ''}`}
        />

        <div className="relative z-10">
          <div
            className={`w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center mb-4 ${iconBgMap[color] || ''}`}
          >
            {icon}
          </div>
          <h3 className="font-display font-semibold text-lg mb-1">{title}</h3>
          <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
            {description}
          </p>
          <div
            className={`flex items-center text-sm font-medium group-hover:gap-2 transition-all ${ctaColorMap[color] || 'text-cosmic-cyan'}`}
          >
            {cta}
            <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>
    </Link>
  );
}
