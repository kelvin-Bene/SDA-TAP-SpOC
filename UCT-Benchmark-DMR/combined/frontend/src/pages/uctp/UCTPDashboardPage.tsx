import { Link } from 'react-router-dom';
import { FlaskConical, Play, Brain, Wifi, TrendingUp, Target, BarChart3, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUCTPDashboard } from '@/hooks/useUCTPDashboard';
import { RunStatusCard } from '@/components/uctp/RunStatusCard';
import { MetricsChart } from '@/components/uctp/MetricsChart';

export function UCTPDashboardPage() {
  const { data: stats, isLoading } = useUCTPDashboard();

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-stellar-purple/5 via-transparent to-cosmic-cyan/5 p-8">
        <div className="absolute top-0 right-0 w-96 h-96 bg-stellar-purple/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-cosmic-cyan/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-stellar-purple text-sm font-medium mb-2">
            <FlaskConical className="h-4 w-4" />
            UCTP Algorithm Lab
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight mb-2">
            Algorithm <span className="text-gradient-cosmic">Workbench</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Configure, run, and compare UCT processing algorithms. Train ML models and test API connections.
          </p>

          <div className="flex flex-wrap gap-3 mt-6">
            <Link to="/uctp/workbench">
              <Button className="gap-2 bg-gradient-to-r from-stellar-purple to-cosmic-blue hover:opacity-90 transition-opacity">
                <Play className="h-4 w-4" />
                New Algorithm Run
              </Button>
            </Link>
            <Link to="/uctp/training">
              <Button variant="outline" className="gap-2 border-white/20 hover:bg-white/5">
                <Brain className="h-4 w-4" />
                Train Model
              </Button>
            </Link>
            <Link to="/uctp/connectivity">
              <Button variant="outline" className="gap-2 border-white/20 hover:bg-white/5">
                <Wifi className="h-4 w-4" />
                Test APIs
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatBox
          title="Total Runs"
          value={isLoading ? '...' : String(stats?.total_runs || 0)}
          subtitle={`${stats?.completed_runs || 0} completed`}
          icon={<BarChart3 className="h-5 w-5" />}
          color="cyan"
        />
        <StatBox
          title="Best F1 Score"
          value={isLoading ? '...' : stats?.best_f1_score?.toFixed(4) || '--'}
          subtitle={stats?.best_algorithm || 'No runs yet'}
          icon={<Target className="h-5 w-5" />}
          color="purple"
        />
        <StatBox
          title="ML Models"
          value={isLoading ? '...' : String(stats?.total_models || 0)}
          subtitle={`${stats?.ready_models || 0} ready`}
          icon={<Brain className="h-5 w-5" />}
          color="blue"
        />
        <StatBox
          title="API Health"
          value={isLoading ? '...' : `${(stats?.api_health_pct || 0).toFixed(0)}%`}
          subtitle="services connected"
          icon={<Wifi className="h-5 w-5" />}
          color="green"
        />
      </div>

      {/* Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Runs */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-display font-semibold">Recent Runs</h2>
            <Link to="/uctp/workbench" className="text-sm text-cosmic-cyan hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {stats?.recent_runs && stats.recent_runs.length > 0 ? (
            <div className="space-y-2">
              {stats.recent_runs.slice(0, 5).map((run) => (
                <Link key={run.id} to={`/uctp/workbench`}>
                  <RunStatusCard run={run} compact />
                </Link>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-8 text-center">
              <p className="text-sm text-muted-foreground">No runs yet. Start one from the Algorithm Workbench.</p>
            </div>
          )}
        </div>

        {/* F1 Score Chart */}
        <div className="space-y-4">
          <h2 className="text-lg font-display font-semibold">F1 Score Trend</h2>
          <MetricsChart runs={stats?.recent_runs || []} metric="f1_score" height={250} />
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickLink
          to="/uctp/workbench"
          title="Algorithm Workbench"
          description="Configure and run UCTP pipeline algorithms"
          icon={<Play className="h-5 w-5" />}
          color="cyan"
        />
        <QuickLink
          to="/uctp/compare"
          title="Compare Runs"
          description="Side-by-side comparison of algorithm runs"
          icon={<BarChart3 className="h-5 w-5" />}
          color="purple"
        />
        <QuickLink
          to="/uctp/training"
          title="ML Training Studio"
          description="Train and manage ML models"
          icon={<Brain className="h-5 w-5" />}
          color="blue"
        />
      </div>
    </div>
  );
}

function StatBox({ title, value, subtitle, icon, color }: {
  title: string; value: string; subtitle: string; icon: React.ReactNode; color: string;
}) {
  const colorMap: Record<string, string> = {
    cyan: 'from-cosmic-cyan/10 to-cosmic-cyan/5 border-cosmic-cyan/20',
    purple: 'from-stellar-purple/10 to-stellar-purple/5 border-stellar-purple/20',
    blue: 'from-cosmic-blue/10 to-cosmic-blue/5 border-cosmic-blue/20',
    green: 'from-aurora-green/10 to-aurora-green/5 border-aurora-green/20',
  };
  const iconColorMap: Record<string, string> = {
    cyan: 'text-cosmic-cyan', purple: 'text-stellar-purple',
    blue: 'text-cosmic-blue', green: 'text-aurora-green',
  };

  return (
    <div className={`rounded-xl border bg-gradient-to-br p-5 ${colorMap[color] || colorMap.cyan}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</span>
        <span className={iconColorMap[color] || 'text-cosmic-cyan'}>{icon}</span>
      </div>
      <p className="text-2xl font-display font-bold">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
    </div>
  );
}

function QuickLink({ to, title, description, icon, color }: {
  to: string; title: string; description: string; icon: React.ReactNode; color: string;
}) {
  const colorMap: Record<string, string> = {
    cyan: 'hover:border-cosmic-cyan/30 hover:shadow-glow-cyan',
    purple: 'hover:border-stellar-purple/30 hover:shadow-glow-purple',
    blue: 'hover:border-cosmic-blue/30',
  };
  const iconBgMap: Record<string, string> = {
    cyan: 'bg-cosmic-cyan/10', purple: 'bg-stellar-purple/10', blue: 'bg-cosmic-blue/10',
  };

  return (
    <Link to={to} className="group">
      <div className={`rounded-xl border border-white/10 bg-card p-5 transition-all duration-300 ${colorMap[color]}`}>
        <div className={`p-2.5 rounded-xl ${iconBgMap[color]} w-fit mb-3`}>
          {icon}
        </div>
        <h3 className="text-sm font-semibold mb-1">{title}</h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </Link>
  );
}
