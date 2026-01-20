import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trophy, Medal, Award, Star, TrendingUp, TrendingDown, Minus } from 'lucide-react';
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
import type { LeaderboardEntry, OrbitalRegime, DataTier } from '@/types';

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
  {
    rank: 6,
    algorithmName: 'CatalogMatch',
    team: 'JHU APL',
    version: 'v3.0',
    f1Score: 0.9089,
    precision: 0.915,
    recall: 0.903,
    positionRmsKm: 3.67,
    submissionId: 'sub-6',
    submittedAt: '2026-01-08T09:00:00Z',
    isCurrentUser: false,
  },
  {
    rank: 7,
    algorithmName: 'DeepOrbit',
    team: 'Stanford',
    version: 'v1.2',
    f1Score: 0.9045,
    precision: 0.912,
    recall: 0.897,
    positionRmsKm: 3.89,
    submissionId: 'sub-7',
    submittedAt: '2026-01-06T11:00:00Z',
    isCurrentUser: false,
  },
  {
    rank: 8,
    algorithmName: 'TrackNet',
    team: 'Raytheon',
    version: 'v2.3',
    f1Score: 0.8978,
    precision: 0.905,
    recall: 0.891,
    positionRmsKm: 4.12,
    submissionId: 'sub-8',
    submittedAt: '2026-01-04T13:00:00Z',
    isCurrentUser: false,
  },
  {
    rank: 9,
    algorithmName: 'SatTracker',
    team: 'Boeing',
    version: 'v1.8',
    f1Score: 0.8912,
    precision: 0.898,
    recall: 0.885,
    positionRmsKm: 4.45,
    submissionId: 'sub-9',
    submittedAt: '2026-01-02T10:00:00Z',
    isCurrentUser: false,
  },
  {
    rank: 10,
    algorithmName: 'OrbitGuard',
    team: 'L3Harris',
    version: 'v2.1',
    f1Score: 0.8856,
    precision: 0.892,
    recall: 0.879,
    positionRmsKm: 4.78,
    submissionId: 'sub-10',
    submittedAt: '2025-12-28T15:00:00Z',
    isCurrentUser: false,
  },
];

const trendData = [
  { month: 'Aug', OrbitalMind: 0.91, TrackFusion: 0.90, MyUCTP: 0.85, SpaceTrackAI: 0.88 },
  { month: 'Sep', OrbitalMind: 0.92, TrackFusion: 0.91, MyUCTP: 0.86, SpaceTrackAI: 0.89 },
  { month: 'Oct', OrbitalMind: 0.93, TrackFusion: 0.92, MyUCTP: 0.88, SpaceTrackAI: 0.90 },
  { month: 'Nov', OrbitalMind: 0.94, TrackFusion: 0.94, MyUCTP: 0.89, SpaceTrackAI: 0.91 },
  { month: 'Dec', OrbitalMind: 0.95, TrackFusion: 0.95, MyUCTP: 0.90, SpaceTrackAI: 0.91 },
  { month: 'Jan', OrbitalMind: 0.954, TrackFusion: 0.952, MyUCTP: 0.923, SpaceTrackAI: 0.92 },
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
      return <span className="w-5 text-center font-mono font-semibold">{rank}</span>;
  }
}

export function LeaderboardPage() {
  const [regimeFilter, setRegimeFilter] = useState<OrbitalRegime | 'all'>('all');
  const [tierFilter, setTierFilter] = useState<DataTier | 'all'>('all');
  const [periodFilter, setPeriodFilter] = useState<'all' | 'month' | 'week'>('all');
  const [sortColumn, setSortColumn] = useState<'f1Score' | 'precision' | 'recall' | 'positionRmsKm'>('f1Score');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const sortedLeaderboard = useMemo(() => {
    return [...mockLeaderboard].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      const direction = sortDirection === 'desc' ? -1 : 1;
      if (sortColumn === 'positionRmsKm') {
        // Lower is better for position RMS
        return direction * (aVal - bVal) * -1;
      }
      return direction * (aVal - bVal);
    });
  }, [sortColumn, sortDirection]);

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
              <Select value={regimeFilter} onValueChange={(v) => setRegimeFilter(v as typeof regimeFilter)}>
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
              <Select value={tierFilter} onValueChange={(v) => setTierFilter(v as typeof tierFilter)}>
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
              <Select value={periodFilter} onValueChange={(v) => setPeriodFilter(v as typeof periodFilter)}>
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
                  {sortedLeaderboard.map((entry, index) => (
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
              <CardTitle>F1-Score Trends (Top 4 Algorithms)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" className="text-xs" />
                  <YAxis domain={[0.84, 0.96]} className="text-xs" tickFormatter={(v) => v.toFixed(2)} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="OrbitalMind"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="TrackFusion"
                    stroke="#10B981"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="MyUCTP"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="SpaceTrackAI"
                    stroke="#EF4444"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
