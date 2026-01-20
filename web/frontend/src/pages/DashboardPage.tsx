import { Trophy, FileText, Target, TrendingUp } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { RecentSubmissions } from '@/components/dashboard/RecentSubmissions';
import { LeaderboardSnapshot } from '@/components/dashboard/LeaderboardSnapshot';
import { QuickActions } from '@/components/dashboard/QuickActions';

export function DashboardPage() {
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
          title="Your Rank"
          value="#3"
          change={2}
          changeLabel="this week"
          icon={<Trophy className="h-5 w-5" />}
        />
        <StatCard
          title="Submissions"
          value="7"
          subtitle="2 processing"
          icon={<FileText className="h-5 w-5" />}
        />
        <StatCard
          title="Best F1-Score"
          value="0.9234"
          subtitle="LEO-T2 dataset"
          icon={<Target className="h-5 w-5" />}
        />
        <StatCard
          title="Improvement"
          value="+4.2%"
          change={4.2}
          changeLabel="vs. previous"
          icon={<TrendingUp className="h-5 w-5" />}
        />
      </div>

      {/* Quick Actions */}
      <QuickActions />

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
