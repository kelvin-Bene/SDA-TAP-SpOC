import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { LeaderboardEntry, LeaderboardFilters } from '@/types';

// Response types from backend
interface LeaderboardEntryResponse {
  rank: number;
  algorithm_name: string;
  team?: string;
  version: string;
  // Headline composite — sourced from test_composite_score on the backend
  // (with COALESCE fallback to legacy composite_score and then f1_score).
  composite_score?: number | null;
  // CTF per-split breakdown. Test is the rank-defining split.
  train_composite_score?: number | null;
  val_composite_score?: number | null;
  test_composite_score?: number | null;
  f1_score: number;
  precision: number;
  recall: number;
  position_rms_km: number;
  submission_id: string;
  submitted_at: string;
  is_current_user: boolean;
}

interface LeaderboardResponse {
  dataset_id?: string;
  dataset_name?: string;
  last_updated: string;
  total_entries: number;
  entries: LeaderboardEntryResponse[];
}

// Transform backend response to frontend type
function transformLeaderboardEntry(data: LeaderboardEntryResponse): LeaderboardEntry {
  return {
    rank: data.rank,
    algorithmName: data.algorithm_name,
    team: data.team || 'Independent',
    version: data.version,
    // Fall back to f1_score when composite_score is null so legacy submissions
    // still render a sensible headline number in the UI.
    compositeScore: data.composite_score ?? data.f1_score,
    // CTF per-split breakdown. Backend nullables map to undefined in TS.
    trainCompositeScore: data.train_composite_score ?? undefined,
    valCompositeScore: data.val_composite_score ?? undefined,
    testCompositeScore: data.test_composite_score ?? undefined,
    f1Score: data.f1_score,
    precision: data.precision,
    recall: data.recall,
    positionRmsKm: data.position_rms_km,
    submissionId: data.submission_id,
    submittedAt: data.submitted_at,
    isCurrentUser: data.is_current_user,
  };
}

export function useLeaderboard(filters?: LeaderboardFilters) {
  return useQuery({
    queryKey: ['leaderboard', filters],
    queryFn: async () => {
      // Build query params from filters
      const params: Record<string, string> = {};
      if (filters?.regime && filters.regime !== 'all') {
        params.regime = filters.regime;
      }
      if (filters?.tier && filters.tier !== 'all') {
        params.tier = filters.tier;
      }
      if (filters?.period && filters.period !== 'all') {
        params.period = filters.period;
      }
      if (filters?.datasetId && filters.datasetId !== 'all') {
        params.dataset_id = filters.datasetId;
      }

      const response = await api.getLeaderboard(params);
      const data = response.data as LeaderboardResponse;

      return data.entries.map(transformLeaderboardEntry);
    },
    staleTime: 1000 * 60, // 1 minute
  });
}

// Hook for leaderboard history (for charts)
interface LeaderboardHistoryEntry {
  date: string;
  algorithmName: string;
  bestF1: number;
}

export function useLeaderboardHistory(datasetId?: string, days: number = 30) {
  return useQuery({
    queryKey: ['leaderboard-history', datasetId, days],
    queryFn: async () => {
      const response = await api.getLeaderboardHistory({ dataset_id: datasetId, days });
      const data = response.data as {
        dataset_id?: string;
        history: Array<{ date: string; algorithm_name: string; best_f1: number }>;
        period_days: number;
      };

      return data.history.map((entry) => ({
        date: entry.date,
        algorithmName: entry.algorithm_name,
        bestF1: entry.best_f1,
      })) as LeaderboardHistoryEntry[];
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Hook for leaderboard statistics
interface LeaderboardStatistics {
  datasetId?: string;
  totalSubmissions: number;
  uniqueAlgorithms: number;
  averageScore: number;
  bestScore: number;
  worstScore: number;
  submissionTrend: 'increasing' | 'decreasing' | 'stable';
}

export function useLeaderboardStatistics(datasetId?: string) {
  return useQuery({
    queryKey: ['leaderboard-statistics', datasetId],
    queryFn: async () => {
      const response = await api.getLeaderboardStatistics({ dataset_id: datasetId });
      const data = response.data as {
        dataset_id?: string;
        total_submissions: number;
        unique_algorithms: number;
        average_score: number;
        best_score: number;
        worst_score: number;
        submission_trend: string;
      };

      return {
        datasetId: data.dataset_id,
        totalSubmissions: data.total_submissions,
        uniqueAlgorithms: data.unique_algorithms,
        averageScore: data.average_score,
        bestScore: data.best_score,
        worstScore: data.worst_score,
        submissionTrend: data.submission_trend as 'increasing' | 'decreasing' | 'stable',
      } as LeaderboardStatistics;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
