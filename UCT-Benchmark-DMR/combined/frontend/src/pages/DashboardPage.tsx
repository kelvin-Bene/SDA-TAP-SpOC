import { Link } from 'react-router-dom';
import { Trophy, FileText, Target, TrendingUp, ArrowRight, Plus, Upload, Sparkles, Rocket } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';
import { LeaderboardSnapshot } from '@/components/dashboard/LeaderboardSnapshot';
import { useDashboardStats } from '@/hooks/useDashboardStats';
import { Button } from '@/components/ui/button';

export function DashboardPage() {
  const { data: stats, isLoading } = useDashboardStats();

  // Format values for display
  const rankDisplay = stats?.topRank ? `#${stats.topRank}` : '--';
  const submissionsDisplay = stats?.totalSubmissions?.toString() || '0';
  const processingSubtitle = stats?.processingCount
    ? `${stats.processingCount} processing`
    : 'none processing';
  const f1Display = stats?.bestF1Score ? stats.bestF1Score.toFixed(4) : '--';
  const f1Subtitle = stats?.bestDatasetName || 'No submissions yet';
  const improvementDisplay = stats?.improvementVsAverage
    ? `${stats.improvementVsAverage > 0 ? '+' : ''}${stats.improvementVsAverage}%`
    : '--';

  return (
    <div className="space-y-8">
      {/* Hero Welcome Section */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-cosmic-cyan/5 via-transparent to-stellar-purple/5 p-8">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-cosmic-cyan/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-stellar-purple/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 text-cosmic-cyan text-sm font-medium mb-2">
            <Sparkles className="h-4 w-4" />
            Welcome back
          </div>
          <h1 className="text-4xl font-display font-bold tracking-tight mb-2">
            Good to see you, <span className="text-gradient-cosmic">researcher</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Track your algorithm performance, explore benchmark datasets, and climb the leaderboard.
          </p>

          {/* Quick action buttons */}
          <div className="flex flex-wrap gap-3 mt-6">
            <Link to="/datasets/generate">
              <Button className="gap-2 bg-gradient-to-r from-cosmic-cyan to-cosmic-blue hover:opacity-90 transition-opacity shadow-glow-cyan">
                <Plus className="h-4 w-4" />
                Generate Dataset
              </Button>
            </Link>
            <Link to="/submit">
              <Button variant="outline" className="gap-2 border-white/20 hover:bg-white/5 hover:border-white/30">
                <Upload className="h-4 w-4" />
                Submit Algorithm
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Top Rank"
          value={isLoading ? '...' : rankDisplay}
          subtitle={stats?.topAlgorithmName || 'Loading...'}
          icon={<Trophy className="h-5 w-5" />}
          accentColor="cyan"
        />
        <StatCard
          title="Submissions"
          value={isLoading ? '...' : submissionsDisplay}
          subtitle={processingSubtitle}
          icon={<FileText className="h-5 w-5" />}
          accentColor="blue"
        />
        <StatCard
          title="Best F1-Score"
          value={isLoading ? '...' : f1Display}
          subtitle={f1Subtitle}
          icon={<Target className="h-5 w-5" />}
          accentColor="purple"
        />
        <StatCard
          title="vs. Average"
          value={isLoading ? '...' : improvementDisplay}
          change={stats?.improvementVsAverage || 0}
          changeLabel="above average"
          icon={<TrendingUp className="h-5 w-5" />}
          accentColor="green"
        />
      </div>

      {/* Quick Actions Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link to="/datasets" className="group">
          <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-6 transition-all duration-300 hover:border-cosmic-cyan/30 hover:shadow-glow-cyan">
            <div className="absolute top-0 right-0 w-32 h-32 bg-cosmic-cyan/5 rounded-full blur-2xl group-hover:bg-cosmic-cyan/10 transition-colors" />
            <div className="relative z-10">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 flex items-center justify-center mb-4">
                <Rocket className="h-6 w-6 text-cosmic-cyan" />
              </div>
              <h3 className="font-display font-semibold text-lg mb-1">Browse Datasets</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Explore benchmark datasets across all orbital regimes
              </p>
              <div className="flex items-center text-cosmic-cyan text-sm font-medium group-hover:gap-2 transition-all">
                View datasets
                <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        </Link>

        <Link to="/leaderboard" className="group">
          <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-6 transition-all duration-300 hover:border-stellar-purple/30 hover:shadow-glow-purple">
            <div className="absolute top-0 right-0 w-32 h-32 bg-stellar-purple/5 rounded-full blur-2xl group-hover:bg-stellar-purple/10 transition-colors" />
            <div className="relative z-10">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-stellar-purple/20 to-cosmic-blue/20 flex items-center justify-center mb-4">
                <Trophy className="h-6 w-6 text-stellar-purple" />
              </div>
              <h3 className="font-display font-semibold text-lg mb-1">Leaderboard</h3>
              <p className="text-sm text-muted-foreground mb-4">
                See how your algorithms compare to others
              </p>
              <div className="flex items-center text-stellar-purple text-sm font-medium group-hover:gap-2 transition-all">
                View rankings
                <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        </Link>

        <Link to="/docs" className="group">
          <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-6 transition-all duration-300 hover:border-aurora-green/30 hover:shadow-[0_0_20px_-5px_hsl(142_76%_45%_/_0.5)]">
            <div className="absolute top-0 right-0 w-32 h-32 bg-aurora-green/5 rounded-full blur-2xl group-hover:bg-aurora-green/10 transition-colors" />
            <div className="relative z-10">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-aurora-green/20 to-cosmic-cyan/20 flex items-center justify-center mb-4">
                <FileText className="h-6 w-6 text-aurora-green" />
              </div>
              <h3 className="font-display font-semibold text-lg mb-1">Documentation</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Learn about metrics, formats, and best practices
              </p>
              <div className="flex items-center text-aurora-green text-sm font-medium group-hover:gap-2 transition-all">
                Read docs
                <ArrowRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <RecentSubmissions />
        <LeaderboardSnapshot />
      </div>

      {/* Announcements */}
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-6">
        {/* Animated gradient border effect */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cosmic-cyan/20 via-cosmic-blue/20 to-stellar-purple/20 opacity-50" style={{ padding: '1px' }}>
          <div className="absolute inset-[1px] rounded-xl bg-card" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-5 w-5 text-cosmic-cyan" />
            <h3 className="font-display font-semibold text-lg">Announcements</h3>
          </div>
          <ul className="space-y-3">
            <li className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
              <span className="shrink-0 px-2 py-0.5 rounded text-xs font-semibold bg-cosmic-cyan/20 text-cosmic-cyan border border-cosmic-cyan/30">
                NEW
              </span>
              <span className="text-sm text-muted-foreground">
                T4 synthetic object datasets are now available for testing. Generate your first T4 dataset today!
              </span>
            </li>
            <li className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5">
              <span className="shrink-0 px-2 py-0.5 rounded text-xs font-semibold bg-stellar-purple/20 text-stellar-purple border border-stellar-purple/30">
                UPDATE
              </span>
              <span className="text-sm text-muted-foreground">
                Evaluation metrics now include covariance realism checks. See the documentation for details.
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
