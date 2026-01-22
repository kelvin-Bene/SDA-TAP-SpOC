import { useParams, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  ArrowLeft,
  Download,
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
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useState } from 'react';
import { useResults, useSubmission, useExportResults } from '@/hooks/useSubmissions';

export function ResultsPage() {
  const { submissionId } = useParams<{ submissionId: string }>();
  const [expandedSatellites, setExpandedSatellites] = useState(false);

  // Use real API hooks
  const { data: results, isLoading: loadingResults, error: resultsError } = useResults(submissionId || '');
  const { data: submission, isLoading: loadingSubmission } = useSubmission(submissionId || '');
  const exportMutation = useExportResults();

  const isLoading = loadingResults || loadingSubmission;

  const handleExport = async () => {
    if (!submissionId) return;
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId,
        format: 'json',
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `results_${submissionId}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
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

  // Calculate changes (mock previous values for now)
  const previousF1Score = results.f1Score > 0 ? results.f1Score * 0.95 : 0;
  const f1Change = results.f1Score - previousF1Score;
  const previousRank = results.previousRank || results.rank + 2;
  const rankChange = previousRank - (results.rank || 0);

  // Mock chart data based on actual results
  const residualData = [
    { range: '-3', ra: 2, dec: 1 },
    { range: '-2', ra: 8, dec: 5 },
    { range: '-1', ra: 25, dec: 22 },
    { range: '0', ra: 45, dec: 48 },
    { range: '1', ra: 28, dec: 30 },
    { range: '2', ra: 10, dec: 8 },
    { range: '3', ra: 3, dec: 2 },
  ];

  const positionErrorData = [
    { range: '0-1', count: Math.round(results.truePositives * 0.3) },
    { range: '1-2', count: Math.round(results.truePositives * 0.4) },
    { range: '2-3', count: Math.round(results.truePositives * 0.15) },
    { range: '3-4', count: Math.round(results.truePositives * 0.1) },
    { range: '4-5', count: Math.round(results.truePositives * 0.04) },
    { range: '5+', count: Math.round(results.truePositives * 0.01) },
  ];

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
        <Button className="gap-2" onClick={handleExport} disabled={exportMutation.isPending}>
          {exportMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export Results
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground uppercase tracking-wide">F1-Score</p>
                <p className="text-3xl font-bold mt-1">{results.f1Score.toFixed(4)}</p>
                {f1Change !== 0 && (
                  <div className={cn(
                    'flex items-center gap-1 text-sm mt-1',
                    f1Change > 0 ? 'text-green-600' : 'text-red-600'
                  )}>
                    {f1Change > 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    {f1Change > 0 ? '+' : ''}{(f1Change * 100).toFixed(1)}% vs previous
                  </div>
                )}
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
                <p className="text-3xl font-bold mt-1">{(results.precision * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives} TP / {results.truePositives + results.falsePositives} predicted
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
                <p className="text-3xl font-bold mt-1">{(results.recall * 100).toFixed(1)}%</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {results.truePositives} TP / {results.truePositives + results.falseNegatives} actual
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
                {rankChange > 0 && (
                  <div className="flex items-center gap-1 text-sm mt-1 text-green-600">
                    <TrendingUp className="h-4 w-4" />
                    +{rankChange} positions
                  </div>
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
                  <div className="rounded-lg bg-gray-100 dark:bg-gray-800 p-4">
                    <p className="text-2xl font-bold text-muted-foreground">—</p>
                    <p className="text-xs text-muted-foreground">True Negative</p>
                  </div>
                </div>
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
                      className="h-full bg-stellar-cyan rounded-full"
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
            <Card>
              <CardHeader>
                <CardTitle>State Vector Accuracy</CardTitle>
                <CardDescription>Position and velocity error metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Position RMS</p>
                    <p className="text-3xl font-bold">{results.positionRmsKm.toFixed(2)}</p>
                    <p className="text-sm text-muted-foreground">km</p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground">Velocity RMS</p>
                    <p className="text-3xl font-bold">{results.velocityRmsKmS.toFixed(3)}</p>
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
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={positionErrorData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="range" className="text-xs" />
                    <YAxis className="text-xs" />
                    <RechartsTooltip />
                    <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
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
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={residualData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="range" className="text-xs" />
                    <YAxis className="text-xs" />
                    <RechartsTooltip />
                    <Bar dataKey="ra" fill="#06B6D4" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-sm text-muted-foreground mt-2 text-center">
                  RMS: {results.raResidualRmsArcsec?.toFixed(2) || '-'} arcsec
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Dec Residuals</CardTitle>
                <CardDescription>Declination residual distribution (arcsec)</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={residualData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="range" className="text-xs" />
                    <YAxis className="text-xs" />
                    <RechartsTooltip />
                    <Bar dataKey="dec" fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-sm text-muted-foreground mt-2 text-center">
                  RMS: {results.decResidualRmsArcsec?.toFixed(2) || '-'} arcsec
                </p>
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
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Satellite ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Obs Used</TableHead>
                        <TableHead>Pos Error (km)</TableHead>
                        <TableHead>Vel Error (km/s)</TableHead>
                        <TableHead>Confidence</TableHead>
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
