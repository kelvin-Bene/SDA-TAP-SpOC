import { useParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  ArrowLeft,
  Download,
  FileText,
  Target,
  TrendingUp,
  TrendingDown,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { downloadBlob } from '@/lib/downloadUtils';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useState, useMemo } from 'react';
import { useResults, useSubmission, useExportResults, useDownloadReport } from '@/hooks/useSubmissions';
import { useToast } from '@/hooks/use-toast';

export function ResultsPage() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const [expandedSatellites, setExpandedSatellites] = useState(false);
  const { toast } = useToast();

  // Use real API hooks
  const { data: results, isLoading: loadingResults, error: resultsError } = useResults(submissionId || '');
  const { data: submission, isLoading: loadingSubmission } = useSubmission(submissionId || '');
  const exportMutation = useExportResults();
  const reportMutation = useDownloadReport();

  const isLoading = loadingResults || loadingSubmission;

  const handleDownloadReport = async () => {
    if (!submissionId) return;
    try {
      const blob = await reportMutation.mutateAsync({
        submissionId,
        format: 'pdf',
      });

      downloadBlob(blob, `report_${submissionId}.pdf`);
    } catch (err) {
      toast({
        title: 'Report generation failed',
        description: 'Failed to generate evaluation report. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleExport = async () => {
    if (!submissionId) return;
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId,
        format: 'json',
      });

      downloadBlob(blob, `results_${submissionId}.json`);
    } catch (err) {
      toast({
        title: 'Export failed',
        description: 'Failed to export results. Please try again.',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (resultsError || !results) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Link to="/submit/my-submissions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Results Not Found</h1>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">
              The results for this submission are not available yet or the submission doesn't exist.
            </p>
            <Link to="/submit/my-submissions" className="mt-4 inline-block">
              <Button>Back to Submissions</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Only show previous comparisons when real data exists
  const hasPreviousRank = results.previousRank !== undefined && results.previousRank !== null;
  const rankChange = hasPreviousRank ? (results.previousRank as number) - (results.rank || 0) : 0;

  // U12: Use real histogram data only — don't mask missing backend data with synthetics
  // U10: Memoize expensive computation
  const hasRealResiduals = !!(results.raResidualHistogram && results.decResidualHistogram);

  const residualData = useMemo(() => {
    if (!hasRealResiduals) return null;
    const labels = results.raResidualHistogram!.labels;
    const raBins = results.raResidualHistogram!.counts;
    const decBins = results.decResidualHistogram!.counts;
    return labels.map((label, i) => ({
      range: label,
      ra: raBins[i] ?? 0,
      dec: decBins[i] ?? 0,
    }));
  }, [hasRealResiduals, results.raResidualHistogram, results.decResidualHistogram]);

  // U12: Position error distribution — use real data only
  const hasRealPosErrors = !!results.positionErrorHistogram;

  const positionErrorData = useMemo(() => {
    if (!hasRealPosErrors) return null;
    const hist = results.positionErrorHistogram!;
    return hist.labels.map((label, i) => ({
      range: label,
      count: hist.counts[i] ?? 0,
    }));
  }, [hasRealPosErrors, results.positionErrorHistogram]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/submit/my-submissions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 flex items-center justify-center">
            <Target className="h-6 w-6 text-cosmic-cyan" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold tracking-tight">
              {submission?.algorithmName || 'Submission'} {submission?.version || ''}
            </h1>
            <p className="text-muted-foreground">
              Results for {submission?.datasetName || `Dataset ${submission?.datasetId}`}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={handleDownloadReport} disabled={reportMutation.isPending}>
            {reportMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Download Report
          </Button>
          <Button className="gap-2" onClick={handleExport} disabled={exportMutation.isPending}>
            {exportMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export Results
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="bg-white/[0.02] border-white/[0.06]">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">F1-Score</p>
                <p className="text-3xl font-bold mt-1">{results.f1Score.toFixed(4)}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {(results.f1Score * 100).toFixed(1)}% accuracy
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-cyan/5 flex items-center justify-center">
                <Target className="h-5 w-5 text-cosmic-cyan" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white/[0.02] border-white/[0.06]">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Precision</p>
                <p className="text-3xl font-bold mt-1">{(results.precision * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives} TP / {results.truePositives + results.falsePositives} predicted
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cosmic-blue/20 to-cosmic-blue/5 flex items-center justify-center">
                <CheckCircle className="h-5 w-5 text-cosmic-blue" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white/[0.02] border-white/[0.06]">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Recall</p>
                <p className="text-3xl font-bold mt-1">{(results.recall * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives} TP / {results.truePositives + results.falseNegatives} actual
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-stellar-purple/20 to-stellar-purple/5 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-stellar-purple" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white/[0.02] border-white/[0.06]">
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Rank</p>
                <p className="text-3xl font-bold mt-1">#{results.rank || '-'}</p>
                {hasPreviousRank && rankChange !== 0 && (
                  <div className={cn(
                    'flex items-center gap-1 text-sm mt-1',
                    rankChange > 0 ? 'text-aurora-green' : 'text-red-400'
                  )}>
                    {rankChange > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    {rankChange > 0 ? '+' : ''}{rankChange} positions
                  </div>
                )}
                {!hasPreviousRank && (
                  <p className="text-sm text-muted-foreground mt-1">on this dataset</p>
                )}
              </div>
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-nova-orange/20 to-nova-orange/5 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-nova-orange" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Results */}
      <Tabs defaultValue="binary" className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1 bg-white/[0.03] border border-white/[0.06] p-1 rounded-xl overflow-x-auto">
          <TabsTrigger value="binary" className="rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">Binary Metrics</TabsTrigger>
          <TabsTrigger value="state" className="rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">State Metrics</TabsTrigger>
          <TabsTrigger value="residuals" className="rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">Residual Analysis</TabsTrigger>
          <TabsTrigger value="satellites" className="rounded-lg data-[state=active]:bg-cosmic-cyan/10 data-[state=active]:text-cosmic-cyan">Per-Satellite</TabsTrigger>
        </TabsList>

        {/* Binary Metrics Tab */}
        <TabsContent value="binary" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Confusion Matrix */}
            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">Confusion Matrix</CardTitle>
                <CardDescription>Classification results for track associations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div></div>
                  <div className="text-sm font-medium text-muted-foreground">Predicted Pos</div>
                  <div className="text-sm font-medium text-muted-foreground">Predicted Neg</div>

                  <div className="text-sm font-medium text-muted-foreground text-right pr-2">Actual Pos</div>
                  <div className="rounded-lg bg-aurora-green/10 p-4">
                    <p className="text-2xl font-bold text-aurora-green">{results.truePositives}</p>
                    <p className="text-xs text-muted-foreground">True Positive</p>
                  </div>
                  <div className="rounded-lg bg-red-500/10 p-4">
                    <p className="text-2xl font-bold text-red-400">{results.falseNegatives}</p>
                    <p className="text-xs text-muted-foreground">False Negative</p>
                  </div>

                  <div className="text-sm font-medium text-muted-foreground text-right pr-2">Actual Neg</div>
                  <div className="rounded-lg bg-nova-orange/10 p-4">
                    <p className="text-2xl font-bold text-nova-orange">{results.falsePositives}</p>
                    <p className="text-xs text-muted-foreground">False Positive</p>
                  </div>
                  <div className="rounded-lg bg-white/[0.05] p-4">
                    <p className="text-2xl font-bold text-muted-foreground">—</p>
                    <p className="text-xs text-muted-foreground">True Negative</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Metrics Summary */}
            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">Classification Metrics</CardTitle>
                <CardDescription>Performance summary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Precision</span>
                    <span className="font-mono font-semibold">{(results.precision * 100).toFixed(2)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${results.precision * 100}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Recall</span>
                    <span className="font-mono font-semibold">{(results.recall * 100).toFixed(2)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-cosmic-cyan rounded-full"
                      style={{ width: `${results.recall * 100}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">F1-Score</span>
                    <span className="font-mono font-semibold">{(results.f1Score * 100).toFixed(2)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-cosmic-blue rounded-full"
                      style={{ width: `${results.f1Score * 100}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* State Metrics Tab */}
        <TabsContent value="state" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">State Vector Accuracy</CardTitle>
                <CardDescription>Position and velocity error metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                    <p className="text-sm text-muted-foreground">Position RMS</p>
                    <p className="text-3xl font-bold">{results.positionRmsKm.toFixed(2)}</p>
                    <p className="text-sm text-muted-foreground">km</p>
                  </div>
                  <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                    <p className="text-sm text-muted-foreground">Velocity RMS</p>
                    <p className="text-3xl font-bold">{results.velocityRmsKmS.toFixed(3)}</p>
                    <p className="text-sm text-muted-foreground">km/s</p>
                  </div>
                </div>
                <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                  <p className="text-sm text-muted-foreground">Mahalanobis Distance</p>
                  <p className="text-3xl font-bold">{results.mahalanobisDistance?.toFixed(2) || '-'}</p>
                  <p className="text-sm text-muted-foreground">
                    {results.mahalanobisDistance && results.mahalanobisDistance < 2
                      ? 'Good covariance realism'
                      : 'Check covariance scaling'}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">Position Error Distribution</CardTitle>
                <CardDescription>Histogram of position errors (km)</CardDescription>
              </CardHeader>
              <CardContent>
                {positionErrorData ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={positionErrorData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="range" className="text-xs" />
                      <YAxis className="text-xs" />
                      <RechartsTooltip />
                      <Bar dataKey="count" fill="hsl(217, 91%, 60%)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                    No position error histogram data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Residual Analysis Tab */}
        <TabsContent value="residuals" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">RA Residuals</CardTitle>
                <CardDescription>Right Ascension residual distribution (arcsec)</CardDescription>
              </CardHeader>
              <CardContent>
                {residualData ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={residualData}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="range" className="text-xs" />
                        <YAxis className="text-xs" />
                        <RechartsTooltip />
                        <Bar dataKey="ra" fill="hsl(192, 91%, 52%)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-muted-foreground mt-2 text-center">
                      RMS: {results.raResidualRmsArcsec?.toFixed(2) || '-'} arcsec
                    </p>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                    No RA residual histogram data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/[0.02] border-white/[0.06]">
              <CardHeader>
                <CardTitle className="font-display">Dec Residuals</CardTitle>
                <CardDescription>Declination residual distribution (arcsec)</CardDescription>
              </CardHeader>
              <CardContent>
                {residualData ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={residualData}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="range" className="text-xs" />
                        <YAxis className="text-xs" />
                        <RechartsTooltip />
                        <Bar dataKey="dec" fill="hsl(142, 76%, 45%)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-sm text-muted-foreground mt-2 text-center">
                      RMS: {results.decResidualRmsArcsec?.toFixed(2) || '-'} arcsec
                    </p>
                  </>
                ) : (
                  <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                    No Dec residual histogram data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Per-Satellite Tab */}
        <TabsContent value="satellites">
          <Card className="bg-white/[0.02] border-white/[0.06]">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-display">Per-Satellite Breakdown</CardTitle>
                <CardDescription>Detailed results for each satellite</CardDescription>
              </div>
              {results.satelliteResults.length > 5 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setExpandedSatellites(!expandedSatellites)}
                  className="gap-1"
                >
                  {expandedSatellites ? (
                    <>
                      <ChevronUp className="h-4 w-4" />
                      Collapse
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-4 w-4" />
                      Expand All
                    </>
                  )}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {results.satelliteResults.length > 0 ? (
                <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead scope="col">Satellite ID</TableHead>
                        <TableHead scope="col">Status</TableHead>
                        <TableHead scope="col">Obs Used</TableHead>
                        <TableHead scope="col">Pos Error (km)</TableHead>
                        <TableHead scope="col">Vel Error (km/s)</TableHead>
                        <TableHead scope="col">Confidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.satelliteResults
                        .slice(0, expandedSatellites ? undefined : 5)
                        .map((sat) => (
                          <TableRow key={sat.satelliteId}>
                            <TableCell className="font-mono">{sat.satelliteId}</TableCell>
                            <TableCell>
                              {sat.status === 'TP' && (
                                <Badge variant="success" className="gap-1">
                                  <CheckCircle className="h-3 w-3" />
                                  TP
                                </Badge>
                              )}
                              {sat.status === 'FP' && (
                                <Badge variant="warning" className="gap-1">
                                  <AlertTriangle className="h-3 w-3" />
                                  FP
                                </Badge>
                              )}
                              {sat.status === 'FN' && (
                                <Badge variant="destructive" className="gap-1">
                                  <XCircle className="h-3 w-3" />
                                  FN
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell>
                              {sat.observationsUsed > 0 ? (
                                <span>
                                  {sat.observationsUsed}/{sat.totalObservations}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {sat.positionErrorKm !== undefined ? (
                                <span className={cn(
                                  'font-mono',
                                  sat.positionErrorKm > 5 && 'text-red-400'
                                )}>
                                  {sat.positionErrorKm.toFixed(2)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {sat.velocityErrorKmS !== undefined ? (
                                <span className="font-mono">{sat.velocityErrorKmS.toFixed(3)}</span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              {sat.confidence !== undefined ? (
                                <span className={cn(
                                  'font-mono',
                                  sat.confidence < 0.5 && 'text-red-400',
                                  sat.confidence >= 0.8 && 'text-aurora-green'
                                )}>
                                  {sat.confidence.toFixed(2)}
                                </span>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </div>
                {!expandedSatellites && results.satelliteResults.length > 5 && (
                  <p className="text-sm text-muted-foreground text-center mt-4">
                    Showing 5 of {results.satelliteResults.length} satellites
                  </p>
                )}
                </>
              ) : (
                <p className="text-center py-8 text-muted-foreground">
                  No per-satellite data available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
