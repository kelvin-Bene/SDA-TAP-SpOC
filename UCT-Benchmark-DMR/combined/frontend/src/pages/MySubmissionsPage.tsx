import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Upload,
  Eye,
  Download,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { useSubmissions, useExportResults } from '@/hooks/useSubmissions';
import type { Submission, SubmissionStatus } from '@/types';

function getStatusBadge(status: SubmissionStatus) {
  switch (status) {
    case 'completed':
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle className="h-3 w-3" />
          Complete
        </Badge>
      );
    case 'processing':
      return (
        <Badge variant="processing" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      );
    case 'queued':
      return (
        <Badge variant="secondary" className="gap-1">
          <Clock className="h-3 w-3" />
          Queued
        </Badge>
      );
    case 'validating':
      return (
        <Badge variant="secondary" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Validating
        </Badge>
      );
    case 'failed':
      return (
        <Badge variant="destructive" className="gap-1">
          <AlertCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
  }
}

export function MySubmissionsPage() {
  // Use real API hook
  const { data: submissions = [], isLoading, error, refetch } = useSubmissions();
  const exportMutation = useExportResults();

  const completedCount = submissions.filter((s) => s.status === 'completed').length;
  const pendingCount = submissions.filter((s) =>
    ['queued', 'processing', 'validating'].includes(s.status)
  ).length;

  const handleExport = async (submission: Submission) => {
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId: submission.id,
        format: 'json',
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `results_${submission.id}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Submissions</h1>
          <p className="text-muted-foreground mt-1">
            Track your algorithm submissions and view results
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
          <Link to="/submit">
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              New Submission
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
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
            <CardTitle className="text-sm font-medium text-muted-foreground">In Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{pendingCount}</p>
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Algorithm</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>F1-Score</TableHead>
                  <TableHead>Rank</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
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
                        <Button variant="ghost" size="icon" className="text-destructive">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
