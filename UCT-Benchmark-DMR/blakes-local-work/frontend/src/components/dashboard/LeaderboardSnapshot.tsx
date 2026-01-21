import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, Trophy, Medal, Award, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LeaderboardEntry } from '@/types';

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
  {
    rank: 4,
    algorithmName: 'SpaceTrack AI',
    team: 'NGC',
    version: 'v2.0',
    f1Score: 0.9198,
    precision: 0.932,
    recall: 0.908,
    positionRmsKm: 3.12,
    submissionId: 'sub-4',
    submittedAt: '2026-01-12T14:00:00Z',
    isCurrentUser: false,
  },
  {
    rank: 5,
    algorithmName: 'OrbitNet',
    team: 'MIT',
    version: 'v1.5',
    f1Score: 0.9156,
    precision: 0.921,
    recall: 0.910,
    positionRmsKm: 3.45,
    submissionId: 'sub-5',
    submittedAt: '2026-01-10T16:00:00Z',
    isCurrentUser: false,
  },
];

function getRankIcon(rank: number) {
  switch (rank) {
    case 1:
      return <Trophy className="h-5 w-5 text-yellow-500" />;
    case 2:
      return <Medal className="h-5 w-5 text-gray-400" />;
    case 3:
      return <Award className="h-5 w-5 text-amber-600" />;
    default:
      return <span className="w-5 text-center font-mono">{rank}</span>;
  }
}

export function LeaderboardSnapshot() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold">Leaderboard</CardTitle>
        <Link to="/leaderboard">
          <Button variant="ghost" size="sm" className="gap-1">
            View Full
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {mockLeaderboard.map((entry) => (
            <div
              key={entry.submissionId}
              className={cn(
                'flex items-center justify-between rounded-lg p-3 transition-colors',
                entry.isCurrentUser
                  ? 'bg-primary/10 border border-primary/20'
                  : 'hover:bg-accent/50'
              )}
            >
              <div className="flex items-center gap-3">
                {getRankIcon(entry.rank)}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{entry.algorithmName}</span>
                    {entry.isCurrentUser && (
                      <Star className="h-3 w-3 fill-primary text-primary" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{entry.team}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-mono font-semibold">{entry.f1Score.toFixed(4)}</p>
                <p className="text-xs text-muted-foreground">F1-Score</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
