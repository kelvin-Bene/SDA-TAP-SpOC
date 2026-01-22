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
import { Trophy, Medal, Award, Star, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
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
      return <span className="w-5 text-center font-mono font-semibold">{rank}</span>;
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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
        <p className="text-muted-foreground mt-1">
          Compare algorithm performance across submissions
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Orbital Regime</label>
              <Select
                value={filters.regime || 'all'}
                onValueChange={(v) => setFilters({ ...filters, regime: v as typeof filters.regime })}
              >
                <SelectTrigger className="w-[150px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Regimes</SelectItem>
                  <SelectItem value="LEO">LEO</SelectItem>
                  <SelectItem value="MEO">MEO</SelectItem>
                  <SelectItem value="GEO">GEO</SelectItem>
                  <SelectItem value="HEO">HEO</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Data Tier</label>
              <Select
                value={filters.tier || 'all'}
                onValueChange={(v) => setFilters({ ...filters, tier: v as typeof filters.tier })}
              >
                <SelectTrigger className="w-[150px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="T1">T1 - Pristine</SelectItem>
                  <SelectItem value="T2">T2 - Downsampled</SelectItem>
                  <SelectItem value="T3">T3 - Simulated</SelectItem>
                  <SelectItem value="T4">T4 - Synthetic</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Time Period</label>
              <Select
                value={filters.period || 'all'}
                onValueChange={(v) => setFilters({ ...filters, period: v as typeof filters.period })}
              >
                <SelectTrigger className="w-[150px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="month">Last Month</SelectItem>
                  <SelectItem value="week">Last Week</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="rankings" className="space-y-4">
        <TabsList>
          <TabsTrigger value="rankings">Rankings</TabsTrigger>
          <TabsTrigger value="trends">Performance Trends</TabsTrigger>
        </TabsList>

        {/* Rankings Tab */}
        <TabsContent value="rankings">
          <Card>
            <CardContent className="pt-6">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : error ? (
                <div className="text-center py-12 text-muted-foreground">
                  Failed to load leaderboard data
                </div>
              ) : sortedLeaderboard.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  No submissions yet. Be the first to submit!
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[80px]">Rank</TableHead>
                      <TableHead>Algorithm</TableHead>
                      <TableHead>Team</TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-foreground"
                        onClick={() => handleSort('f1Score')}
                      >
                        F1-Score <SortIndicator column="f1Score" />
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-foreground"
                        onClick={() => handleSort('precision')}
                      >
                        Precision <SortIndicator column="precision" />
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-foreground"
                        onClick={() => handleSort('recall')}
                      >
                        Recall <SortIndicator column="recall" />
                      </TableHead>
                      <TableHead
                        className="cursor-pointer hover:text-foreground"
                        onClick={() => handleSort('positionRmsKm')}
                      >
                        Pos RMS (km) <SortIndicator column="positionRmsKm" />
                      </TableHead>
                      <TableHead>Submitted</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedLeaderboard.map((entry) => (
                      <TableRow
                        key={entry.submissionId}
                        className={cn(
                          entry.isCurrentUser && 'bg-primary/5 border-l-2 border-l-primary'
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
                            <span className="text-muted-foreground">{entry.version}</span>
                            {entry.isCurrentUser && (
                              <Star className="h-4 w-4 fill-primary text-primary" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{entry.team}</TableCell>
                        <TableCell>
                          <span className="font-mono font-semibold">{entry.f1Score.toFixed(4)}</span>
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
                        <TableCell className="text-muted-foreground">
                          {formatDate(entry.submittedAt)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Legend */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-primary text-primary" />
              Your best submission
            </div>
            <div className="flex items-center gap-1">
              <Trophy className="h-4 w-4 text-yellow-500" />
              Gold
            </div>
            <div className="flex items-center gap-1">
              <Medal className="h-4 w-4 text-gray-400" />
              Silver
            </div>
            <div className="flex items-center gap-1">
              <Award className="h-4 w-4 text-amber-600" />
              Bronze
            </div>
          </div>
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends">
          <Card>
            <CardHeader>
              <CardTitle>F1-Score Trends (Top Algorithms)</CardTitle>
            </CardHeader>
            <CardContent>
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="month" className="text-xs" />
                    <YAxis domain={['auto', 'auto']} className="text-xs" tickFormatter={(v) => v.toFixed(2)} />
                    <Tooltip />
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
                          stroke={['#3B82F6', '#10B981', '#F59E0B', '#EF4444'][idx]}
                          strokeWidth={2}
                          dot={{ r: 4 }}
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
