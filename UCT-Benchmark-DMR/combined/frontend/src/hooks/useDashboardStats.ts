import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

interface DashboardStats {
  // Leader/Top algorithm info (since no user auth yet)
  topRank: number;
  topAlgorithmName: string;
  topF1Score: number;

  // Aggregate stats
  totalSubmissions: number;
  processingCount: number;
  bestF1Score: number;
  bestDatasetName: string | null;

  // Trend info
  submissionTrend: 'increasing' | 'decreasing' | 'stable';
  trendPercentage: number;

  // For "improvement" - compare best to average
  improvementVsAverage: number;
}

interface LeaderboardEntry {
  rank: number;
  algorithm_name: string;
  f1_score: number;
  submission_id: string;
  submitted_at: string;
}

interface LeaderboardResponse {
  dataset_id?: string;
  dataset_name?: string;
  entries: LeaderboardEntry[];
}

interface StatisticsResponse {
  total_submissions: number;
  unique_algorithms: number;
  average_score: number;
  best_score: number;
  worst_score: number;
  submission_trend: string;
}

interface SubmissionResponse {
  id: string;
  status: string;
  score?: number;
  dataset_name?: string;
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // Fetch all required data in parallel
      const [leaderboardRes, statsRes, submissionsRes] = await Promise.all([
        api.getLeaderboard({ limit: '10' }),
        api.getLeaderboardStatistics({}),
        api.getSubmissions({ limit: '100' }),
      ]);

      const leaderboard = leaderboardRes.data as LeaderboardResponse;
      const stats = statsRes.data as StatisticsResponse;
      const submissions = submissionsRes.data as SubmissionResponse[];

      // Get top entry from leaderboard
      const topEntry = leaderboard.entries?.[0];

      // Count processing submissions
      const processingCount = submissions.filter(
        (s) => s.status === 'queued' || s.status === 'validating' || s.status === 'processing'
      ).length;

      // Find the submission with best score and its dataset
      const completedWithScores = submissions.filter((s) => s.score !== undefined && s.score !== null);
      const bestSubmission = completedWithScores.reduce<SubmissionResponse | null>(
        (best, curr) => (!best || (curr.score || 0) > (best.score || 0) ? curr : best),
        null
      );

      // Calculate improvement vs average
      const improvementVsAverage = stats.average_score > 0
        ? ((stats.best_score - stats.average_score) / stats.average_score) * 100
        : 0;

      // Map trend to percentage (rough estimate based on trend)
      let trendPercentage = 0;
      if (stats.submission_trend === 'increasing') {
        trendPercentage = 15; // Placeholder positive trend
      } else if (stats.submission_trend === 'decreasing') {
        trendPercentage = -10; // Placeholder negative trend
      }

      const dashboardStats: DashboardStats = {
        topRank: topEntry?.rank || 0,
        topAlgorithmName: topEntry?.algorithm_name || 'No submissions yet',
        topF1Score: topEntry?.f1_score || 0,

        totalSubmissions: stats.total_submissions || 0,
        processingCount,
        bestF1Score: stats.best_score || 0,
        bestDatasetName: bestSubmission?.dataset_name || null,

        submissionTrend: stats.submission_trend as 'increasing' | 'decreasing' | 'stable',
        trendPercentage,

        improvementVsAverage: Math.round(improvementVsAverage * 10) / 10,
      };

      return dashboardStats;
    },
    staleTime: 1000 * 30, // 30 seconds
  });
}
