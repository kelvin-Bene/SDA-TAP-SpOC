import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Upload,
  Eye,
  Download,
  Trash2,
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
  const pendingCount = submissions.filter((s) =>
    ['queued', 'processing', 'validating'].includes(s.status)
  ).length;

  const handleExport = async (submission: Submission) => {
    try {
      const blob = await exportMutation.mutateAsync({
        submissionId: submission.id,
        format: 'json',
      });

      downloadBlob(blob, `results_${submission.id}.json`);
    } catch (err) {
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
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cosmic-cyan/20 to-cosmic-blue/20 flex items-center justify-center">
            <Upload className="h-6 w-6 text-cosmic-cyan" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold tracking-tight">My Submissions</h1>
            <p className="text-muted-foreground mt-1">Track your algorithm submissions and view results</p>
          </div>
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
        <Card className="bg-white/[0.02] border-white/[0.06] border-t-2 border-t-stellar-purple/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Submissions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{submissions.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-white/[0.02] border-white/[0.06] border-t-2 border-t-aurora-green/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-aurora-green">{completedCount}</p>
          </CardContent>
        </Card>
        <Card className="bg-white/[0.02] border-white/[0.06] border-t-2 border-t-cosmic-cyan/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">In Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-cosmic-cyan">{pendingCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Submissions Table */}
      <Card className="bg-white/[0.02] border-white/[0.06]">
        <CardHeader>
          <CardTitle className="font-display">Submission History</CardTitle>
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
            <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-white/10 hover:bg-transparent">
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
                  <TableRow key={submission.id} className="border-white/5">
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
                            className="text-xs text-red-400 truncate max-w-[200px]"
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
                              <span className="text-xs text-aurora-green">
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
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => toast({ title: 'Coming soon', description: 'Submission deletion will be available in a future update.' })}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
