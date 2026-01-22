import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowRight, Trophy, Medal, Award, Star, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useLeaderboard } from '@/hooks/useLeaderboard';

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
  const { data: leaderboard, isLoading, error } = useLeaderboard();
  const entries = leaderboard?.slice(0, 5) ?? [];

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
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>Unable to load leaderboard data</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No leaderboard entries yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) => (
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
        )}
      </CardContent>
    </Card>
  );
}
