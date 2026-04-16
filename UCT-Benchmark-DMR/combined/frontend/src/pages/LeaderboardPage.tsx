import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trophy, Medal, Award, Star, TrendingUp, TrendingDown, Loader2, Crown, Sparkles, Upload, Info, ArrowDown, ArrowUp, Filter } from 'lucide-react';
import { Tooltip as RankTooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import {
  MobileDrawer,
  MobileDrawerContent,
  MobileDrawerTrigger,
} from '@/components/ui/mobile-drawer';
import { useBreakpoint } from '@/hooks/useBreakpoint';
import { Badge } from '@/components/ui/badge';
import { cn, formatDate } from '@/lib/utils';
import { getRankIcon } from '@/lib/rankUtils';
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
import { useDatasets } from '@/hooks/useDatasets';
import type { LeaderboardFilters } from '@/types';

export function LeaderboardPage() {
  const [filters, setFilters] = useState<LeaderboardFilters>({
    regime: 'all',
    tier: 'all',
    period: 'all',
    datasetId: 'all',
  });
  const [activeTab, setActiveTab] = useState('rankings');
  const [sortColumn, setSortColumn] = useState<
    'compositeScore' | 'f1Score' | 'precision' | 'recall' | 'positionRmsKm'
  >('compositeScore');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const isDesktop = useBreakpoint('md');

  // Use real API hooks
  const { data: leaderboard = [], isLoading, error } = useLeaderboard(filters);
  const { data: datasets = [] } = useDatasets();
  // On mobile, use 90-day window so the x-axis doesn't become illegibly dense.
  const { data: historyData = [] } = useLeaderboardHistory(undefined, isDesktop ? 180 : 90);

  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      const direction = sortDirection === 'desc' ? -1 : 1;
      if (sortColumn === 'positionRmsKm') {
        // Lower is better for position RMS
        return direction * (aVal - bVal);
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
        <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-stellar-purple/20 to-cosmic-blue/20 flex items-center justify-center shrink-0">
          <Trophy className="h-5 w-5 sm:h-6 sm:w-6 text-stellar-purple" />
        </div>
        <div className="min-w-0">
          <h1 className="text-2xl xs:text-3xl font-display font-bold tracking-tight">Leaderboard</h1>
          <p className="text-muted-foreground text-sm sm:text-base">
            Compare algorithm performance across submissions
          </p>
        </div>
      </div>

      {/* Top 3 Podium — source order is 2/1/3 for desktop centering; on mobile we re-order to 1/2/3 */}
      {topThree.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
          {/* Second place */}
          {topThree[1] && (
            <div className="relative order-2 md:order-1 md:mt-8">
              <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-5 text-center transition-all duration-300 hover:border-gray-400/30 group">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-gray-400 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <Medal className="h-10 w-10 text-gray-400 mx-auto mb-3" />
                <div className="text-2xl font-display font-bold text-gray-400">#2</div>
                <div className="font-semibold mt-2 truncate">{topThree[1].algorithmName}</div>
                <div className="text-xs text-muted-foreground">{topThree[1].team}</div>
                <div className="mt-3 text-xl font-mono font-bold text-gray-400">
                  {topThree[1].compositeScore.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Composite &middot; F1 {topThree[1].f1Score.toFixed(3)}
                </div>
              </div>
            </div>
          )}

          {/* First place */}
          {topThree[0] && (
            <div className="relative order-1 md:order-2">
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
                  {topThree[0].compositeScore.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Composite &middot; F1 {topThree[0].f1Score.toFixed(3)}
                </div>
              </div>
            </div>
          )}

          {/* Third place */}
          {topThree[2] && (
            <div className="relative order-3 md:order-3 md:mt-8">
              <div className="relative overflow-hidden rounded-xl border border-white/10 bg-card p-5 text-center transition-all duration-300 hover:border-amber-600/30 group">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-amber-600 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <Award className="h-10 w-10 text-amber-600 mx-auto mb-3" />
                <div className="text-2xl font-display font-bold text-amber-600">#3</div>
                <div className="font-semibold mt-2 truncate">{topThree[2].algorithmName}</div>
                <div className="text-xs text-muted-foreground">{topThree[2].team}</div>
                <div className="mt-3 text-xl font-mono font-bold text-amber-600">
                  {topThree[2].compositeScore.toFixed(4)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Composite &middot; F1 {topThree[2].f1Score.toFixed(3)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Filters — inline card on md+, drawer with chips on mobile */}
      {(() => {
        const filtersBody = (
          <div className="flex flex-col sm:flex-row flex-wrap gap-4">
            <div className="space-y-2 w-full sm:w-auto">
              <label className="text-sm font-medium text-muted-foreground">Orbital Regime</label>
              <Select
                value={filters.regime || 'all'}
                onValueChange={(v) => setFilters({ ...filters, regime: v as typeof filters.regime })}
              >
                <SelectTrigger className="w-full sm:w-[150px] bg-white/5 border-white/20">
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
            <div className="space-y-2 w-full sm:w-auto">
              <label className="text-sm font-medium text-muted-foreground">Data Tier</label>
              <Select
                value={filters.tier || 'all'}
                onValueChange={(v) => setFilters({ ...filters, tier: v as typeof filters.tier })}
              >
                <SelectTrigger className="w-full sm:w-[150px] bg-white/5 border-white/20">
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
            <div className="space-y-2 w-full sm:w-auto">
              <label className="text-sm font-medium text-muted-foreground">Time Period</label>
              <Select
                value={filters.period || 'all'}
                onValueChange={(v) => setFilters({ ...filters, period: v as typeof filters.period })}
              >
                <SelectTrigger className="w-full sm:w-[150px] bg-white/5 border-white/20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="glass border-white/10">
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="month">Last Month</SelectItem>
                  <SelectItem value="week">Last Week</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 w-full sm:w-auto">
              <label className="text-sm font-medium text-muted-foreground">Dataset</label>
              <Select
                value={filters.datasetId || 'all'}
                onValueChange={(v) => setFilters({ ...filters, datasetId: v })}
              >
                <SelectTrigger className="w-full sm:w-[220px] bg-white/5 border-white/20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="glass border-white/10 max-h-[300px]">
                  <SelectItem value="all">All Datasets</SelectItem>
                  {datasets.map((ds) => (
                    <SelectItem key={ds.id} value={String(ds.id)}>
                      {ds.name.length > 30 ? ds.name.slice(0, 27) + '...' : ds.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        );

        // Build chips for active filters
        const activeChips: { label: string; onClear: () => void }[] = [];
        if (filters.regime && filters.regime !== 'all')
          activeChips.push({ label: `Regime: ${filters.regime}`, onClear: () => setFilters({ ...filters, regime: 'all' }) });
        if (filters.tier && filters.tier !== 'all')
          activeChips.push({ label: `Tier: ${filters.tier}`, onClear: () => setFilters({ ...filters, tier: 'all' }) });
        if (filters.period && filters.period !== 'all')
          activeChips.push({ label: `Period: ${filters.period}`, onClear: () => setFilters({ ...filters, period: 'all' }) });
        if (filters.datasetId && filters.datasetId !== 'all') {
          const ds = datasets.find((d) => String(d.id) === String(filters.datasetId));
          activeChips.push({
            label: `Dataset: ${ds?.name ? (ds.name.length > 20 ? ds.name.slice(0, 17) + '…' : ds.name) : filters.datasetId}`,
            onClear: () => setFilters({ ...filters, datasetId: 'all' }),
          });
        }

        return (
          <>
            {/* Desktop inline filters */}
            <div className="hidden md:block rounded-xl border border-white/10 bg-card p-5">
              {filtersBody}
            </div>

            {/* Mobile filter trigger + active chips */}
            <div className="md:hidden flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <MobileDrawer open={filterDrawerOpen} onOpenChange={setFilterDrawerOpen}>
                  <MobileDrawerTrigger asChild>
                    <Button variant="outline" className="gap-2 flex-1 justify-start">
                      <Filter className="h-4 w-4" />
                      Filters
                      {activeChips.length > 0 && (
                        <Badge variant="secondary" className="ml-auto">
                          {activeChips.length}
                        </Badge>
                      )}
                    </Button>
                  </MobileDrawerTrigger>
                  <MobileDrawerContent title="Filters" description="Refine the leaderboard">
                    {filtersBody}
                    <div className="mt-4 flex gap-2">
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() =>
                          setFilters({ regime: 'all', tier: 'all', period: 'all', datasetId: 'all' })
                        }
                      >
                        Reset
                      </Button>
                      <Button className="flex-1" onClick={() => setFilterDrawerOpen(false)}>
                        Done
                      </Button>
                    </div>
                  </MobileDrawerContent>
                </MobileDrawer>
              </div>
              {activeChips.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {activeChips.map((chip) => (
                    <button
                      key={chip.label}
                      onClick={chip.onClear}
                      className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-white/10 transition-colors"
                    >
                      {chip.label}
                      <span aria-hidden="true">×</span>
                      <span className="sr-only">Remove filter</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        );
      })()}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-white/5 border border-white/10 grid grid-cols-2 w-full sm:w-auto sm:inline-grid">
          <TabsTrigger value="rankings" className="data-[state=active]:bg-white/10">Rankings</TabsTrigger>
          <TabsTrigger value="trends" className="data-[state=active]:bg-white/10">Trends</TabsTrigger>
        </TabsList>

        {/* Rankings Tab */}
        <TabsContent value="rankings">
          {isLoading ? (
            <div className="rounded-xl border border-white/10 bg-card flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-white/10 bg-card text-center py-12 text-muted-foreground">
              Failed to load leaderboard data
            </div>
          ) : sortedLeaderboard.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-card text-center py-12 space-y-4">
              <Sparkles className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No submissions yet. Be the first to submit!</p>
              <Link to="/submit">
                <Button className="gap-2">
                  <Upload className="h-4 w-4" />
                  Submit Algorithm
                </Button>
              </Link>
            </div>
          ) : (
            <>
              {/* Mobile: sort control + card list */}
              <div className="md:hidden space-y-3">
                <div className="flex items-center gap-2">
                  <Select value={sortColumn} onValueChange={(v) => setSortColumn(v as typeof sortColumn)}>
                    <SelectTrigger className="flex-1 bg-white/5 border-white/20">
                      <div className="flex items-center gap-2 text-muted-foreground text-xs">
                        <span>Sort by</span>
                      </div>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass border-white/10">
                      <SelectItem value="compositeScore">Composite Score</SelectItem>
                      <SelectItem value="f1Score">F1-Score</SelectItem>
                      <SelectItem value="precision">Precision</SelectItem>
                      <SelectItem value="recall">Recall</SelectItem>
                      <SelectItem value="positionRmsKm">Pos RMS (km)</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="touch"
                    onClick={() => setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))}
                    aria-label={`Sort ${sortDirection === 'desc' ? 'descending' : 'ascending'}`}
                    title={sortDirection === 'desc' ? 'Descending' : 'Ascending'}
                  >
                    {sortDirection === 'desc' ? (
                      <ArrowDown className="h-4 w-4" />
                    ) : (
                      <ArrowUp className="h-4 w-4" />
                    )}
                  </Button>
                </div>

                <ul className="space-y-3" role="list">
                  {sortedLeaderboard.map((entry, idx) => (
                    <li key={entry.submissionId}>
                      <Card
                        className={cn(
                          'p-4',
                          entry.isCurrentUser && 'border-l-2 border-l-cosmic-cyan bg-cosmic-cyan/5',
                          idx < 3 && 'bg-white/[0.02]'
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3 min-w-0 flex-1">
                            <div className="shrink-0 mt-0.5">{getRankIcon(entry.rank)}</div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="font-semibold text-base leading-tight">{entry.algorithmName}</span>
                                <span className="text-muted-foreground text-sm">{entry.version}</span>
                                {entry.isCurrentUser && (
                                  <Star className="h-4 w-4 fill-cosmic-cyan text-cosmic-cyan shrink-0" />
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground mt-0.5 truncate">{entry.team}</div>
                            </div>
                          </div>
                          <div className="shrink-0 text-right">
                            <div
                              className={cn(
                                'font-mono font-bold text-lg leading-tight',
                                idx === 0 && 'text-yellow-500',
                                idx === 1 && 'text-gray-400',
                                idx === 2 && 'text-amber-600',
                                idx > 2 && 'text-foreground'
                              )}
                            >
                              {entry.compositeScore.toFixed(4)}
                            </div>
                            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mt-0.5">
                              Score
                            </div>
                          </div>
                        </div>
                        <dl className="mt-3 grid grid-cols-3 gap-2 text-center border-t border-white/5 pt-3">
                          <div>
                            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">F1</dt>
                            <dd className="font-mono text-sm mt-0.5">{entry.f1Score.toFixed(3)}</dd>
                          </div>
                          <div>
                            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Prec.</dt>
                            <dd className="font-mono text-sm mt-0.5">
                              {(entry.precision * 100).toFixed(1)}%
                            </dd>
                          </div>
                          <div>
                            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Recall</dt>
                            <dd className="font-mono text-sm mt-0.5">
                              {(entry.recall * 100).toFixed(1)}%
                            </dd>
                          </div>
                          <div>
                            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">RMS</dt>
                            <dd className="font-mono text-sm mt-0.5">{entry.positionRmsKm.toFixed(2)} km</dd>
                          </div>
                          <div className="col-span-2 text-right sm:text-center">
                            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Submitted</dt>
                            <dd className="text-xs text-muted-foreground mt-0.5">
                              {formatDate(entry.submittedAt)}
                            </dd>
                          </div>
                        </dl>
                      </Card>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Desktop: full table */}
              <div className="hidden md:block rounded-xl border border-white/10 bg-card overflow-hidden overflow-x-auto">
                <Table>
                <TableHeader>
                  <TableRow className="border-white/10 hover:bg-transparent">
                    <TableHead scope="col" className="w-[80px]">
                      <span className="flex items-center">
                        Rank
                        <TooltipProvider>
                          <RankTooltip>
                            <TooltipTrigger><Info className="h-3 w-3 ml-1 text-muted-foreground" /></TooltipTrigger>
                            <TooltipContent>
                              Rank is based on Composite Score on the test split.
                              Test data is withheld from training so this score
                              cannot be cheated by copying the truth file.
                            </TooltipContent>
                          </RankTooltip>
                        </TooltipProvider>
                      </span>
                    </TableHead>
                    <TableHead scope="col">Algorithm</TableHead>
                    <TableHead scope="col">Team</TableHead>
                    <TableHead
                      scope="col"
                      className="cursor-pointer hover:text-foreground transition-colors"
                      tabIndex={0}
                      role="columnheader"
                      onClick={() => handleSort('compositeScore')}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('compositeScore'); } }}
                    >
                      Score <SortIndicator column="compositeScore" />
                    </TableHead>
                    <TableHead
                      scope="col"
                      className="cursor-pointer hover:text-foreground transition-colors"
                      tabIndex={0}
                      role="columnheader"
                      onClick={() => handleSort('f1Score')}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('f1Score'); } }}
                    >
                      F1-Score <SortIndicator column="f1Score" />
                    </TableHead>
                    <TableHead
                      scope="col"
                      className="cursor-pointer hover:text-foreground transition-colors"
                      tabIndex={0}
                      role="columnheader"
                      onClick={() => handleSort('precision')}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('precision'); } }}
                    >
                      Precision <SortIndicator column="precision" />
                    </TableHead>
                    <TableHead
                      scope="col"
                      className="cursor-pointer hover:text-foreground transition-colors"
                      tabIndex={0}
                      role="columnheader"
                      onClick={() => handleSort('recall')}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('recall'); } }}
                    >
                      Recall <SortIndicator column="recall" />
                    </TableHead>
                    <TableHead
                      scope="col"
                      className="hidden sm:table-cell cursor-pointer hover:text-foreground transition-colors"
                      tabIndex={0}
                      role="columnheader"
                      onClick={() => handleSort('positionRmsKm')}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSort('positionRmsKm'); } }}
                    >
                      Pos RMS (km) <SortIndicator column="positionRmsKm" />
                    </TableHead>
                    <TableHead scope="col" className="hidden sm:table-cell">Submitted</TableHead>
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
                          'font-mono font-bold',
                          idx === 0 && 'text-yellow-500',
                          idx === 1 && 'text-gray-400',
                          idx === 2 && 'text-amber-600'
                        )}>
                          {entry.compositeScore.toFixed(4)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">
                          {entry.f1Score.toFixed(4)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{(entry.precision * 100).toFixed(1)}%</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono">{(entry.recall * 100).toFixed(1)}%</span>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">
                        <span className="font-mono">{entry.positionRmsKm.toFixed(2)}</span>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
                        {formatDate(entry.submittedAt)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
            </>
          )}

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-3 sm:gap-6 text-sm text-muted-foreground mt-4">
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
                <ResponsiveContainer width="100%" height={isDesktop ? 400 : 260}>
                  <LineChart
                    data={trendData}
                    margin={isDesktop ? { top: 5, right: 20, bottom: 5, left: 0 } : { top: 5, right: 10, bottom: 30, left: -10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(222 30% 18%)" />
                    <XAxis
                      dataKey="month"
                      stroke="hsl(215 20% 55%)"
                      fontSize={isDesktop ? 12 : 10}
                      interval="preserveStartEnd"
                      angle={isDesktop ? 0 : -35}
                      textAnchor={isDesktop ? 'middle' : 'end'}
                      height={isDesktop ? 30 : 50}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      stroke="hsl(215 20% 55%)"
                      fontSize={isDesktop ? 12 : 10}
                      width={isDesktop ? 50 : 34}
                      tickFormatter={(v) => v.toFixed(2)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(222 47% 5%)',
                        borderColor: 'hsl(222 30% 18%)',
                        borderRadius: '8px',
                        fontSize: isDesktop ? 13 : 11,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: isDesktop ? 13 : 11 }} verticalAlign={isDesktop ? 'bottom' : 'top'} />
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
                          dot={{ r: isDesktop ? 4 : 2, fill: 'hsl(222 47% 5%)' }}
                          activeDot={{ r: isDesktop ? 6 : 4 }}
                        />
                      ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[260px] sm:h-[400px] text-muted-foreground">
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
