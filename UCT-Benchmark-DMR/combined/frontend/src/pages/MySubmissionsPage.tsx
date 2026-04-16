import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Upload,
  Eye,
  Download,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { getStatusBadge } from '@/lib/statusUtils';
import { downloadBlob } from '@/lib/downloadUtils';
import { useSubmissions, useExportResults } from '@/hooks/useSubmissions';
import { useToast } from '@/hooks/use-toast';
import type { Submission } from '@/types';

export function MySubmissionsPage() {
  const { toast } = useToast();
  // Use real API hook
  const { data: submissions = [], isLoading, error, refetch } = useSubmissions();
  const exportMutation = useExportResults();

  const completedCount = submissions.filter((s) => s.status === 'completed').length;
  const queuedCount = submissions.filter((s) =>
    ['queued', 'processing', 'validating'].includes(s.status)
  ).length;
  const failedCount = submissions.filter((s) => s.status === 'failed').length;

  const handleExport = async (submission: Submission) => {
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId: submission.id,
        format: 'json',
      });

      downloadBlob(blob, `results_${submission.id}.json`);
    } catch (err) {
      console.error('Export failed:', err);
      toast({
        title: 'Export failed',
        description: 'Failed to export results. Please try again.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl xs:text-3xl font-bold tracking-tight">My Submissions</h1>
          <p className="text-muted-foreground mt-1">
            Track your algorithm submissions and view results
          </p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" className="gap-2 flex-1 sm:flex-initial" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Link to="/submit" className="flex-1 sm:flex-initial">
            <Button className="gap-2 w-full">
              <Upload className="h-4 w-4" />
              <span className="hidden xs:inline">New Submission</span>
              <span className="xs:hidden">New</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Submissions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{submissions.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{completedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Queued</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{queuedCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Failed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">{failedCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Submissions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Submission History</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-destructive mb-2">Failed to load submissions.</p>
              <Button variant="outline" onClick={() => refetch()}>
                Try Again
              </Button>
            </div>
          ) : submissions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">No submissions yet.</p>
              <Link to="/submit">
                <Button>Create Your First Submission</Button>
              </Link>
            </div>
          ) : (
            <>
              {/* Desktop: full table */}
              <div className="hidden md:block overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Algorithm</TableHead>
                      <TableHead scope="col">Dataset</TableHead>
                      <TableHead scope="col">Status</TableHead>
                      <TableHead scope="col">F1-Score</TableHead>
                      <TableHead scope="col">Rank</TableHead>
                      <TableHead scope="col">Submitted</TableHead>
                      <TableHead scope="col" className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {submissions.map((submission) => (
                      <TableRow key={submission.id}>
                        <TableCell>
                          <div>
                            <span className="font-medium">{submission.algorithmName}</span>
                            <span className="text-muted-foreground ml-1">{submission.version}</span>
                          </div>
                        </TableCell>
                        <TableCell>{submission.datasetName}</TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            {getStatusBadge(submission.status)}
                            {submission.queuePosition && (
                              <p className="text-xs text-muted-foreground">
                                Position: #{submission.queuePosition}
                              </p>
                            )}
                            {submission.errorMessage && (
                              <p
                                className="text-xs text-red-600 truncate max-w-[200px]"
                                title={submission.errorMessage}
                              >
                                {submission.errorMessage}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {submission.results && submission.results.f1Score != null ? (
                            <span className="font-mono font-semibold">
                              {submission.results.f1Score.toFixed(4)}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {submission.results && submission.results.rank != null ? (
                            <div className="flex items-center gap-1">
                              <span className="font-semibold">#{submission.results.rank}</span>
                              {submission.results.previousRank != null &&
                                submission.results.previousRank > submission.results.rank && (
                                  <span className="text-xs text-green-600">
                                    (+{submission.results.previousRank - submission.results.rank})
                                  </span>
                                )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDateTime(submission.createdAt)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            {submission.status === 'completed' && (
                              <Link to={`/results/${submission.id}`}>
                                <Button variant="ghost" size="icon">
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </Link>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              disabled={submission.status !== 'completed'}
                              onClick={() => handleExport(submission)}
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            {submission.status === 'failed' && (
                              <Link to={`/submit?dataset=${encodeURIComponent(submission.datasetId)}&algorithm=${encodeURIComponent(submission.algorithmName)}&version=${encodeURIComponent(submission.version)}`}>
                                <Button variant="ghost" size="icon" title="Re-submit with same parameters">
                                  <RefreshCw className="h-4 w-4" />
                                </Button>
                              </Link>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile: card list */}
              <ul className="md:hidden space-y-3" role="list">
                {submissions.map((submission) => (
                  <li key={submission.id}>
                    <div className="rounded-lg border bg-card p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="font-medium text-base truncate">
                            {submission.algorithmName}{' '}
                            <span className="text-muted-foreground font-normal">{submission.version}</span>
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5 truncate">
                            {submission.datasetName}
                          </div>
                        </div>
                        <div className="shrink-0 flex flex-col items-end gap-1">
                          {getStatusBadge(submission.status)}
                        </div>
                      </div>

                      {submission.queuePosition && (
                        <p className="text-xs text-muted-foreground mt-2">
                          Queue position: #{submission.queuePosition}
                        </p>
                      )}
                      {submission.errorMessage && (
                        <details className="mt-2">
                          <summary className="text-xs text-red-500 cursor-pointer select-none">
                            Show error
                          </summary>
                          <p className="text-xs text-red-500 mt-1 break-words whitespace-pre-wrap">
                            {submission.errorMessage}
                          </p>
                        </details>
                      )}

                      <dl className="mt-3 grid grid-cols-3 gap-2 text-center border-t pt-3">
                        <div>
                          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">F1</dt>
                          <dd className="font-mono text-sm mt-0.5">
                            {submission.results?.f1Score != null
                              ? submission.results.f1Score.toFixed(4)
                              : '—'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Rank</dt>
                          <dd className="font-mono text-sm mt-0.5">
                            {submission.results?.rank != null ? `#${submission.results.rank}` : '—'}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">Submitted</dt>
                          <dd className="text-xs text-muted-foreground mt-0.5 truncate">
                            {formatDateTime(submission.createdAt)}
                          </dd>
                        </div>
                      </dl>

                      <div className="mt-3 flex gap-2 border-t pt-3">
                        {submission.status === 'completed' && (
                          <Link to={`/results/${submission.id}`} className="flex-1">
                            <Button variant="outline" size="sm" className="w-full gap-2">
                              <Eye className="h-4 w-4" />
                              View
                            </Button>
                          </Link>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 gap-2"
                          disabled={submission.status !== 'completed'}
                          onClick={() => handleExport(submission)}
                        >
                          <Download className="h-4 w-4" />
                          Export
                        </Button>
                        {submission.status === 'failed' && (
                          <Link
                            to={`/submit?dataset=${encodeURIComponent(submission.datasetId)}&algorithm=${encodeURIComponent(submission.algorithmName)}&version=${encodeURIComponent(submission.version)}`}
                            className="flex-1"
                          >
                            <Button variant="outline" size="sm" className="w-full gap-2">
                              <RefreshCw className="h-4 w-4" />
                              Retry
                            </Button>
                          </Link>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
