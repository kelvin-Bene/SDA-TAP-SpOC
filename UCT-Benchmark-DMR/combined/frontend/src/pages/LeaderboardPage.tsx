import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trophy, Medal, Award, Star, TrendingUp, TrendingDown, Loader2, Crown, Sparkles } from 'lucide-react';
import { cn, formatDate } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useLeaderboard, useLeaderboardHistory } from '@/hooks/useLeaderboard';
import type { LeaderboardFilters } from '@/types';

function getRankIcon(rank: number) {
  switch (rank) {
    case 1:
      return <Trophy className="h-5 w-5 text-yellow-500" />;
    case 2:
      return <Medal className="h-5 w-5 text-gray-400" />;
    case 3:
      return <Award className="h-5 w-5 text-amber-600" />;
    default:
      return <span className="w-5 text-center font-mono font-semibold text-muted-foreground">{rank}</span>;
  }
}

export function LeaderboardPage() {
  const [filters, setFilters] = useState<LeaderboardFilters>({
    regime: 'all',
    tier: 'all',
    period: 'all',
  });
  const [sortColumn, setSortColumn] = useState<'f1Score' | 'precision' | 'recall' | 'positionRmsKm'>('f1Score');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Use real API hooks
  const { data: leaderboard = [], isLoading, error } = useLeaderboard(filters);
  const { data: historyData = [] } = useLeaderboardHistory(undefined, 180);

  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      const direction = sortDirection === 'desc' ? -1 : 1;
      if (sortColumn === 'positionRmsKm') {
        // Lower is better for position RMS
        return direction * (aVal - bVal) * -1;
      }
      return direction * (aVal - bVal);
    });
  }, [leaderboard, sortColumn, sortDirection]);

  // Get top 3 for podium
  const topThree = sortedLeaderboard.slice(0, 3);

  // Transform history data for chart
  const trendData = useMemo(() => {
    const byMonth: Record<string, Record<string, number>> = {};

    historyData.forEach((entry) => {
      const month = entry.date.substring(0, 7); // YYYY-MM
      if (!byMonth[month]) {
        byMonth[month] = {};
      }
      const algKey = entry.algorithmName.replace(/\s+/g, '');
      if (!byMonth[month][algKey] || entry.bestF1 > byMonth[month][algKey]) {
        byMonth[month][algKey] = entry.bestF1;
      }
    });

    return Object.entries(byMonth)
      .map(([month, scores]) => ({
        month: month.substring(5), // MM only
        ...scores,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [historyData]);

  const handleSort = (column: typeof sortColumn) => {
    if (column === sortColumn) {
      setSortDirection((prev) => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortColumn(column);
      setSortDirection(column === 'positionRmsKm' ? 'asc' : 'desc');
    }
  };

  const SortIndicator = ({ column }: { column: typeof sortColumn }) => {
    if (column !== sortColumn) return null;
    return sortDirection === 'desc' ? (
      <TrendingDown className="h-3 w-3 inline ml-1" />
    ) : (
      <TrendingUp className="h-3 w-3 inline ml-1" />
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-stellar-purple/20 to-cosmic-blue/20 flex items-center justify-center">
          <Trophy className="h-6 w-6 text-stellar-purple" />
        </div>
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Leaderboard</h1>
          <p className="text-muted-foreground">
            Compare algorithm performance across submissions
          </p>
        </div>
      </div>

      {/* Top 3 Podium */}
      {topThree.length > 0 && (
        <div className="grid grid-cols-3 gap-4 max-w-3xl mx-auto">
          {/* Second place */}
          {topThree[1] && (
            <div className="relative mt-8">
              <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-5 text-center transition-all duration-300 hover:border-gray-400/30 group">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-gray-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <Medal className="h-10 w-10 text-gray-400 mx-auto mb-3" />
                <div className="text-2xl font-display font-bold text-gray-400">#2</div>
                <div className="font-semibold mt-2 truncate">{topThree[1].algorithmName}</div>
                <div className="text-xs text-muted-foreground">{topThree[1].team}</div>
                <div className="mt-3 text-xl font-mono font-bold text-gray-400">
                  {topThree[1].f1Score.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">F1-Score</div>
              </div>
            </div>
          )}

          {/* First place */}
          {topThree[0] && (
            <div className="relative">
              <div className="relative overflow-hidden rounded-xl border border-yellow-500/30 bg-gradient-to-b from-yellow-500/10 to-card p-6 text-center transition-all duration-300 hover:border-yellow-500/50 hover:shadow-[0_0_30px_-5px_hsl(45_93%_47%_/_0.3)] group">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-yellow-500 to-transparent" />
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Crown className="h-6 w-6 text-yellow-500 animate-float" />
                </div>
                <Trophy className="h-12 w-12 text-yellow-500 mx-auto mb-3 mt-2" />
                <div className="text-3xl font-display font-bold text-yellow-500">#1</div>
                <div className="font-semibold mt-2 truncate text-lg">{topThree[0].algorithmName}</div>
                <div className="text-sm text-muted-foreground">{topThree[0].team}</div>
                <div className="mt-4 text-2xl font-mono font-bold text-gradient-cosmic">
                  {topThree[0].f1Score.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">F1-Score</div>
              </div>
            </div>
          )}

          {/* Third place */}
          {topThree[2] && (
            <div className="relative mt-8">
              <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-5 text-center transition-all duration-300 hover:border-amber-600/30 group">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-amber-600 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <Award className="h-10 w-10 text-amber-600 mx-auto mb-3" />
                <div className="text-2xl font-display font-bold text-amber-600">#3</div>
                <div className="font-semibold mt-2 truncate">{topThree[2].algorithmName}</div>
                <div className="text-xs text-muted-foreground">{topThree[2].team}</div>
                <div className="mt-3 text-xl font-mono font-bold text-amber-600">
                  {topThree[2].f1Score.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">F1-Score</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="rounded-xl border border-white/10 bg-card p-5">
        <div className="flex flex-wrap gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Orbital Regime</label>
            <Select
              value={filters.regime || 'all'}
              onValueChange={(v) => setFilters({ ...filters, regime: v as typeof filters.regime })}
            >
              <SelectTrigger className="w-[150px] bg-white/5 border-white/20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="glass border-white/10">
                <SelectItem value="all">All Regimes</SelectItem>
                <SelectItem value="LEO">LEO</SelectItem>
                <SelectItem value="MEO">MEO</SelectItem>
                <SelectItem value="GEO">GEO</SelectItem>
                <SelectItem value="HEO">HEO</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Data Tier</label>
            <Select
              value={filters.tier || 'all'}
              onValueChange={(v) => setFilters({ ...filters, tier: v as typeof filters.tier })}
            >
              <SelectTrigger className="w-[150px] bg-white/5 border-white/20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="glass border-white/10">
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="T1">T1 - Pristine</SelectItem>
                <SelectItem value="T2">T2 - Downsampled</SelectItem>
                <SelectItem value="T3">T3 - Simulated</SelectItem>
                <SelectItem value="T4">T4 - Synthetic</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Time Period</label>
            <Select
              value={filters.period || 'all'}
              onValueChange={(v) => setFilters({ ...filters, period: v as typeof filters.period })}
            >
              <SelectTrigger className="w-[150px] bg-white/5 border-white/20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="glass border-white/10">
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="month">Last Month</SelectItem>
                <SelectItem value="week">Last Week</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <Tabs defaultValue="rankings" className="space-y-4">
        <TabsList className="bg-white/5 border border-white/10">
          <TabsTrigger value="rankings" className="data-[state=active]:bg-white/10">Rankings</TabsTrigger>
          <TabsTrigger value="trends" className="data-[state=active]:bg-white/10">Performance Trends</TabsTrigger>
        </TabsList>

        {/* Rankings Tab */}
        <TabsContent value="rankings">
          <div className="rounded-xl border border-white/10 bg-card overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="text-center py-12 text-muted-foreground">
                Failed to load leaderboard data
              </div>
            ) : sortedLeaderboard.length === 0 ? (
              <div className="text-center py-12">
                <Sparkles className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No submissions yet. Be the first to submit!</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-transparent">
                    <TableHead className="w-[80px]">Rank</TableHead>
                    <TableHead>Algorithm</TableHead>
                    <TableHead>Team</TableHead>
                    <TableHead
                      className="cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => handleSort('f1Score')}
                    >
                      F1-Score <SortIndicator column="f1Score" />
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => handleSort('precision')}
                    >
                      Precision <SortIndicator column="precision" />
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => handleSort('recall')}
                    >
                      Recall <SortIndicator column="recall" />
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:text-foreground transition-colors"
                      onClick={() => handleSort('positionRmsKm')}
                    >
                      Pos RMS (km) <SortIndicator column="positionRmsKm" />
                    </TableHead>
                    <TableHead>Submitted</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedLeaderboard.map((entry, idx) => (
                    <TableRow
                      key={entry.submissionId}
                      className={cn(
                        'border-white/5 transition-colors',
                        entry.isCurrentUser && 'bg-cosmic-cyan/5 border-l-2 border-l-cosmic-cyan',
                        idx < 3 && 'bg-white/[0.02]'
                      )}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getRankIcon(entry.rank)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{entry.algorithmName}</span>
                          <span className="text-muted-foreground text-sm">{entry.version}</span>
                          {entry.isCurrentUser && (
                            <Star className="h-4 w-4 fill-cosmic-cyan text-cosmic-cyan" />
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{entry.team}</TableCell>
                      <TableCell>
                        <span className={cn(
                          'font-mono font-semibold',
                          idx === 0 && 'text-yellow-500',
                          idx === 1 && 'text-gray-400',
                          idx === 2 && 'text-amber-600'
                        )}>
                          {entry.f1Score.toFixed(4)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{(entry.precision * 100).toFixed(1)}%</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{(entry.recall * 100).toFixed(1)}%</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{entry.positionRmsKm.toFixed(2)}</span>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatDate(entry.submittedAt)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-6 text-sm text-muted-foreground mt-4">
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 fill-cosmic-cyan text-cosmic-cyan" />
              Your best submission
            </div>
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-yellow-500" />
              Gold
            </div>
            <div className="flex items-center gap-2">
              <Medal className="h-4 w-4 text-gray-400" />
              Silver
            </div>
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-amber-600" />
              Bronze
            </div>
          </div>
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends">
          <Card className="border-white/10 bg-card">
            <CardHeader>
              <CardTitle className="font-display">F1-Score Trends (Top Algorithms)</CardTitle>
            </CardHeader>
            <CardContent>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 30% 18%)" />
                    <XAxis dataKey="month" stroke="hsl(215 20% 55%)" fontSize={12} />
                    <YAxis domain={['auto', 'auto']} stroke="hsl(215 20% 55%)" fontSize={12} tickFormatter={(v) => v.toFixed(2)} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(222 47% 5%)',
                        borderColor: 'hsl(222 30% 18%)',
                        borderRadius: '8px',
                      }}
                    />
                    <Legend />
                    {/* Dynamic lines based on data */}
                    {Object.keys(trendData[0] || {})
                      .filter((key) => key !== 'month')
                      .slice(0, 4)
                      .map((alg, idx) => (
                        <Line
                          key={alg}
                          type="monotone"
                          dataKey={alg}
                          stroke={[
                            'hsl(192 91% 52%)',  // cosmic-cyan
                            'hsl(265 89% 66%)',  // stellar-purple
                            'hsl(142 76% 45%)',  // aurora-green
                            'hsl(217 91% 60%)',  // cosmic-blue
                          ][idx]}
                          strokeWidth={2}
                          dot={{ r: 4, fill: 'hsl(222 47% 5%)' }}
                          activeDot={{ r: 6 }}
                        />
                      ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[400px] text-muted-foreground">
                  No trend data available yet
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
