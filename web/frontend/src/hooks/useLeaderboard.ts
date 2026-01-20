import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { LeaderboardEntry, LeaderboardFilters } from '@/types';

export function useLeaderboard(filters?: LeaderboardFilters) {
  return useQuery({
    queryKey: ['leaderboard', filters],
    queryFn: async () => {
      // Mock data for now
      const mockLeaderboard: LeaderboardEntry[] = [
        {
          rank: 1,
          algorithmName: 'OrbitalMind',
          team: 'AeroCorp',
          version: 'v3.2',
          f1Score: 0.9543,
          precision: 0.961,
          recall: 0.948,
          positionRmsKm: 2.12,
          submissionId: 'sub-1',
          submittedAt: '2026-01-15T08:00:00Z',
          isCurrentUser: false,
        },
        {
          rank: 2,
          algorithmName: 'TrackFusion Pro',
          team: 'LockheedM',
          version: 'v4.1',
          f1Score: 0.9521,
          precision: 0.958,
          recall: 0.946,
          positionRmsKm: 2.34,
          submissionId: 'sub-2',
          submittedAt: '2026-01-14T12:00:00Z',
          isCurrentUser: false,
        },
        {
          rank: 3,
          algorithmName: 'MyUCTP',
          team: 'You',
          version: 'v2.1',
          f1Score: 0.9234,
          precision: 0.941,
          recall: 0.906,
          positionRmsKm: 2.89,
          submissionId: 'sub-3',
          submittedAt: '2026-01-18T10:30:00Z',
          isCurrentUser: true,
        },
      ];

      return mockLeaderboard;
    },
    staleTime: 1000 * 60, // 1 minute
  });
}
