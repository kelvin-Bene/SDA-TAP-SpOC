import { Trophy, FileText, Target, TrendingUp } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';
import { LeaderboardSnapshot } from '@/components/dashboard/LeaderboardSnapshot';
import { QuickActions } from '@/components/dashboard/QuickActions';
import { useDashboardStats } from '@/hooks/useDashboardStats';

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
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome back, researcher</h1>
        <p className="text-muted-foreground mt-1">
          Here's an overview of your algorithm benchmarking progress.
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Top Rank"
          value={isLoading ? '...' : rankDisplay}
          subtitle={stats?.topAlgorithmName || 'Loading...'}
          icon={<Trophy className="h-5 w-5" />}
        />
        <StatCard
          title="Submissions"
          value={isLoading ? '...' : submissionsDisplay}
          subtitle={processingSubtitle}
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          title="Best F1-Score"
          value={isLoading ? '...' : f1Display}
          subtitle={f1Subtitle}
          icon={<Target className="h-5 w-5" />}
        />
        <StatCard
          title="vs. Average"
          value={isLoading ? '...' : improvementDisplay}
          change={stats?.improvementVsAverage || 0}
          changeLabel="above average"
          icon={<TrendingUp className="h-5 w-5" />}
        />
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* 3D Orbit Visualization - temporarily disabled for debugging */}
      {/* <OrbitViewer /> */}

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <RecentSubmissions />
        <LeaderboardSnapshot />
      </div>

      {/* Announcements */}
      <div className="rounded-lg border bg-gradient-to-r from-cosmic-blue/10 to-stellar-cyan/10 p-6">
        <h3 className="font-semibold text-lg mb-2">Announcements</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="text-cosmic-blue font-bold">NEW:</span>
            <span>T4 synthetic object datasets are now available for testing. Generate your first T4 dataset today!</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-stellar-cyan font-bold">UPDATE:</span>
            <span>Evaluation metrics now include covariance realism checks. See the documentation for details.</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
