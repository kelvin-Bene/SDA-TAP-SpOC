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
  RefreshCw,
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
import { ExplainResultsButton } from '@/components/llm/ExplainResultsButton';

// Phase 2 LLM features (DGX Spark local edition only).
const IS_DGX_LOCAL = import.meta.env.VITE_LOCAL_DGX_MODE === 'true';

export function ResultsPage() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const [expandedSatellites, setExpandedSatellites] = useState(false);
  const { toast } = useToast();

  // Use real API hooks
  const { data: results, isLoading: loadingResults, error: resultsError, refetch: refetchResults } = useResults(submissionId || '');
  const { data: submission, isLoading: loadingSubmission, error: submissionError } = useSubmission(submissionId || '');
  const exportMutation = useExportResults();
  const reportMutation = useDownloadReport();

  const isLoading = loadingResults || loadingSubmission;

  // ALL hooks must be above early returns to avoid React error #310
  const residualData = useMemo(() => {
    if (!results?.raResidualHistogram || !results?.decResidualHistogram) return null;
    const labels = results.raResidualHistogram.labels;
    const raBins = results.raResidualHistogram.counts;
    const decBins = results.decResidualHistogram.counts;
    return labels.map((label, i) => ({
      range: label,
      ra: raBins[i] ?? 0,
      dec: decBins[i] ?? 0,
    }));
  }, [results?.raResidualHistogram, results?.decResidualHistogram]);

  const positionErrorData = useMemo(() => {
    if (!results?.positionErrorHistogram) return null;
    const hist = results.positionErrorHistogram;
    return hist.labels.map((label, i) => ({
      range: label,
      count: hist.counts[i] ?? 0,
    }));
  }, [results?.positionErrorHistogram]);

  const handleDownloadReport = async () => {
    if (!submissionId) return;
    try {
      const blob = await reportMutation.mutateAsync({
        submissionId,
        format: 'pdf',
      });

      downloadBlob(blob, `report_${submissionId}.pdf`);
    } catch (err) {
      console.error('Report download failed:', err);
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
      console.error('Export failed:', err);
      toast({
        title: 'Export failed',
        description: 'Failed to export results. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleExportCsv = async () => {
    if (!submissionId) return;
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId,
        format: 'csv',
      });

      downloadBlob(blob, `results_${submissionId}.csv`);
    } catch (err) {
      console.error('CSV export failed:', err);
      toast({
        title: 'Export failed',
        description: 'Failed to export CSV. Please try again.',
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
    // Determine the specific error scenario for a helpful message
    const is404 = resultsError && typeof resultsError === 'object' && 'response' in resultsError
      && (resultsError as { response?: { status?: number } }).response?.status === 404;
    const isSubmission404 = submissionError && typeof submissionError === 'object' && 'response' in submissionError
      && (submissionError as { response?: { status?: number } }).response?.status === 404;
    const isNetworkError = resultsError && !is404;

    let title = 'Results Not Found';
    let description = 'The results for this submission could not be loaded.';

    if (isSubmission404 || is404) {
      title = 'Submission Not Found';
      description = `No submission exists with ID "${submissionId}". It may have been deleted, or the link may be incorrect.`;
    } else if (submission && submission.status !== 'completed') {
      title = 'Results Not Ready';
      description = `This submission is currently "${submission.status}". Results will be available once evaluation is complete.`;
    } else if (isNetworkError) {
      title = 'Failed to Load Results';
      description = 'A network error occurred while fetching the results. Please check your connection and try again.';
    }

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Link to="/submit/my-submissions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        </div>
        <Card>
          <CardContent className="pt-6 space-y-4">
            <p className="text-muted-foreground">{description}</p>
            <div className="flex gap-3">
              <Link to="/submit/my-submissions">
                <Button variant="outline">Back to Submissions</Button>
              </Link>
              {!isSubmission404 && !is404 && (
                <Button
                  onClick={() => refetchResults()}
                  className="gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Only show previous comparisons when real data exists
  const hasPreviousRank = results.previousRank !== undefined && results.previousRank !== null;
  const rankChange = hasPreviousRank ? (results.previousRank as number) - (results.rank || 0) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link to="/submit/my-submissions">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-3xl font-bold tracking-tight">
              {submission?.algorithmName || 'Submission'} {submission?.version || ''}
            </h1>
          </div>
          <p className="text-muted-foreground ml-10">
            Results for {submission?.datasetName || `Dataset ${submission?.datasetId}`}
          </p>
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
          <Button variant="outline" className="gap-2" onClick={handleExportCsv} disabled={exportMutation.isPending}>
            {exportMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            CSV
          </Button>
          <Button className="gap-2" onClick={handleExport} disabled={exportMutation.isPending}>
            {exportMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export JSON
          </Button>
          {IS_DGX_LOCAL && submissionId && (
            <ExplainResultsButton submissionId={submissionId} />
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">F1-Score</p>
                <p className="text-3xl font-bold mt-1">{results.f1Score.toFixed(4)}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {(results.f1Score * 100).toFixed(1)}% accuracy
                </p>
              </div>
              <Target className="h-8 w-8 text-primary" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Precision</p>
                <p className="text-3xl font-bold mt-1">{((results.precision ?? 0) * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives ?? 0} TP / {(results.truePositives ?? 0) + (results.falsePositives ?? 0)} predicted
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Recall</p>
                <p className="text-3xl font-bold mt-1">{((results.recall ?? 0) * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives ?? 0} TP / {(results.truePositives ?? 0) + (results.falseNegatives ?? 0)} actual
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">Rank</p>
                <p className="text-3xl font-bold mt-1">#{results.rank || '-'}</p>
                {hasPreviousRank && rankChange !== 0 && (
                  <div className={cn(
                    'flex items-center gap-1 text-sm mt-1',
                    rankChange > 0 ? 'text-green-600' : 'text-red-600'
                  )}>
                    {rankChange > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    {rankChange > 0 ? '+' : ''}{rankChange} positions
                  </div>
                )}
                {!hasPreviousRank && (
                  <p className="text-sm text-muted-foreground mt-1">on this dataset</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Results */}
      <Tabs defaultValue="binary" className="space-y-4">
        <TabsList>
          <TabsTrigger value="binary">Binary Metrics</TabsTrigger>
          <TabsTrigger value="state">State Metrics</TabsTrigger>
          <TabsTrigger value="residuals">Residual Analysis</TabsTrigger>
          <TabsTrigger value="satellites">Per-Satellite</TabsTrigger>
        </TabsList>

        {/* Binary Metrics Tab */}
        <TabsContent value="binary" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Confusion Matrix */}
            <Card>
              <CardHeader>
                <CardTitle>Confusion Matrix</CardTitle>
                <CardDescription>Classification results for track associations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div></div>
                  <div className="text-sm font-medium text-muted-foreground">Predicted Pos</div>
                  <div className="text-sm font-medium text-muted-foreground">Predicted Neg</div>

                  <div className="text-sm font-medium text-muted-foreground text-right pr-2">Actual Pos</div>
                  <div className="rounded-lg bg-green-100 dark:bg-green-900/30 p-4">
                    <p className="text-2xl font-bold text-green-600">{results.truePositives}</p>
                    <p className="text-xs text-muted-foreground">True Positive</p>
                  </div>
                  <div className="rounded-lg bg-red-100 dark:bg-red-900/30 p-4">
                    <p className="text-2xl font-bold text-red-600">{results.falseNegatives}</p>
                    <p className="text-xs text-muted-foreground">False Negative</p>
                  </div>

                  <div className="text-sm font-medium text-muted-foreground text-right pr-2">Actual Neg</div>
                  <div className="rounded-lg bg-orange-100 dark:bg-orange-900/30 p-4">
                    <p className="text-2xl font-bold text-orange-600">{results.falsePositives}</p>
                    <p className="text-xs text-muted-foreground">False Positive</p>
                  </div>
                  <div className="rounded-lg bg-blue-100 dark:bg-blue-900/30 p-4">
                    <p className="text-2xl font-bold text-blue-600">
                      {results.trueNegatives != null ? results.trueNegatives : 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground">True Negative</p>
                  </div>
                </div>
                {results.trueNegatives != null && results.trueNegatives > 0 && (
                  <p className="text-xs text-muted-foreground mt-3 text-center">
                    Total non-reference observations: {(results.trueNegatives ?? 0) + (results.falsePositives ?? 0)}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Metrics Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Classification Metrics</CardTitle>
                <CardDescription>Performance summary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Precision</span>
                    <span className="font-mono font-semibold">{((results.precision ?? 0) * 100).toFixed(2)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${(results.precision ?? 0) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Recall</span>
                    <span className="font-mono font-semibold">{((results.recall ?? 0) * 100).toFixed(2)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-stellar-cyan rounded-full"
                      style={{ width: `${(results.recall ?? 0) * 100}%` }}
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
                {results.accuracy != null && results.accuracy > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Accuracy</span>
                      <span className="font-mono font-semibold">{((results.accuracy ?? 0) * 100).toFixed(2)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full"
                        style={{ width: `${(results.accuracy ?? 0) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                {results.specificity != null && results.specificity > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Specificity</span>
                      <span className="font-mono font-semibold">{((results.specificity ?? 0) * 100).toFixed(2)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-violet-500 rounded-full"
                        style={{ width: `${(results.specificity ?? 0) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* State Metrics Tab */}
        <TabsContent value="state" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>State Vector Accuracy</CardTitle>
                <CardDescription>Position and velocity error metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Position RMS</p>
                    <p className="text-3xl font-bold">{results.positionRmsKm?.toFixed(2) ?? '-'}</p>
                    <p className="text-sm text-muted-foreground">km</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Velocity RMS</p>
                    <p className="text-3xl font-bold">{results.velocityRmsKmS?.toFixed(3) ?? '-'}</p>
                    <p className="text-sm text-muted-foreground">km/s</p>
                  </div>
                </div>
                <div className="rounded-lg border p-4">
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

            <Card>
              <CardHeader>
                <CardTitle>Position Error Distribution</CardTitle>
                <CardDescription>Histogram of position errors (km)</CardDescription>
              </CardHeader>
              <CardContent>
                {positionErrorData ? (
                  <div className="min-w-[250px]">
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={positionErrorData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="range" className="text-xs" />
                      <YAxis className="text-xs" />
                      <RechartsTooltip />
                      <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                  </div>
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
            <Card>
              <CardHeader>
                <CardTitle>RA Residuals</CardTitle>
                <CardDescription>Right Ascension residual distribution (arcsec)</CardDescription>
              </CardHeader>
              <CardContent>
                {residualData ? (
                  <>
                    <div className="min-w-[250px]">
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={residualData}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="range" className="text-xs" />
                        <YAxis className="text-xs" />
                        <RechartsTooltip />
                        <Bar dataKey="ra" fill="#06B6D4" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    </div>
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

            <Card>
              <CardHeader>
                <CardTitle>Dec Residuals</CardTitle>
                <CardDescription>Declination residual distribution (arcsec)</CardDescription>
              </CardHeader>
              <CardContent>
                {residualData ? (
                  <>
                    <div className="min-w-[250px]">
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={residualData}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="range" className="text-xs" />
                        <YAxis className="text-xs" />
                        <RechartsTooltip />
                        <Bar dataKey="dec" fill="#10B981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                    </div>
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
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Per-Satellite Breakdown</CardTitle>
                <CardDescription>Detailed results for each satellite</CardDescription>
              </div>
              {(results.satelliteResults?.length ?? 0) > 5 && (
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
              {(results.satelliteResults?.length ?? 0) > 0 ? (
                <>
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
                      {(results.satelliteResults ?? [])
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
                                  sat.positionErrorKm > 5 && 'text-red-600'
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
                                  sat.confidence < 0.5 && 'text-red-600',
                                  sat.confidence >= 0.8 && 'text-green-600'
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
                  {!expandedSatellites && (results.satelliteResults?.length ?? 0) > 5 && (
                    <p className="text-sm text-muted-foreground text-center mt-4">
                      Showing 5 of {results.satelliteResults?.length ?? 0} satellites
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
