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
import type { Submission, SubmissionStatus } from '@/types';

const mockSubmissions: Submission[] = [
  {
    id: '1',
    datasetId: 'ds-1',
    datasetName: 'LEO-T2-2026-01-15',
    algorithmName: 'MyUCTP',
    version: 'v2.1',
    status: 'completed',
    createdAt: '2026-01-18T10:30:00Z',
    completedAt: '2026-01-18T11:15:00Z',
    results: {
      truePositives: 38,
      falsePositives: 2,
      falseNegatives: 4,
      precision: 0.95,
      recall: 0.905,
      f1Score: 0.923,
      positionRmsKm: 2.34,
      velocityRmsKmS: 0.12,
      mahalanobisDistance: 1.89,
      raResidualRmsArcsec: 0.87,
      decResidualRmsArcsec: 0.92,
      satelliteResults: [],
      rank: 3,
      previousRank: 5,
    },
  },
  {
    id: '2',
    datasetId: 'ds-2',
    datasetName: 'MEO-T1-2026-01-10',
    algorithmName: 'MyUCTP',
    version: 'v2.1',
    status: 'processing',
    createdAt: '2026-01-18T14:00:00Z',
    queuePosition: 2,
  },
  {
    id: '3',
    datasetId: 'ds-3',
    datasetName: 'GEO-T3-2026-01-08',
    algorithmName: 'MyUCTP',
    version: 'v2.0',
    status: 'completed',
    createdAt: '2026-01-17T09:00:00Z',
    completedAt: '2026-01-17T09:45:00Z',
    results: {
      truePositives: 32,
      falsePositives: 3,
      falseNegatives: 6,
      precision: 0.914,
      recall: 0.842,
      f1Score: 0.876,
      positionRmsKm: 3.12,
      velocityRmsKmS: 0.18,
      mahalanobisDistance: 2.14,
      raResidualRmsArcsec: 1.12,
      decResidualRmsArcsec: 1.08,
      satelliteResults: [],
      rank: 7,
      previousRank: 6,
    },
  },
  {
    id: '4',
    datasetId: 'ds-4',
    datasetName: 'LEO-T1-2026-01-05',
    algorithmName: 'MyUCTP',
    version: 'v1.9',
    status: 'queued',
    createdAt: '2026-01-18T15:30:00Z',
    queuePosition: 5,
  },
  {
    id: '5',
    datasetId: 'ds-5',
    datasetName: 'HEO-T2-2026-01-03',
    algorithmName: 'MyUCTP',
    version: 'v1.8',
    status: 'failed',
    createdAt: '2026-01-15T11:00:00Z',
    errorMessage: 'Invalid covariance matrix detected in observation #1234',
  },
];

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
  const completedCount = mockSubmissions.filter((s) => s.status === 'completed').length;
  const pendingCount = mockSubmissions.filter((s) => ['queued', 'processing', 'validating'].includes(s.status)).length;

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
          <Button variant="outline" className="gap-2">
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
            <p className="text-2xl font-bold">{mockSubmissions.length}</p>
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
              {mockSubmissions.map((submission) => (
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
                        <p className="text-xs text-red-600 truncate max-w-[200px]" title={submission.errorMessage}>
                          {submission.errorMessage}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {submission.results ? (
                      <span className="font-mono font-semibold">
                        {submission.results.f1Score.toFixed(4)}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {submission.results ? (
                      <div className="flex items-center gap-1">
                        <span className="font-semibold">#{submission.results.rank}</span>
                        {submission.results.previousRank && submission.results.previousRank > submission.results.rank && (
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
                      <Button variant="ghost" size="icon" disabled={submission.status !== 'completed'}>
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
        </CardContent>
      </Card>
    </div>
  );
}
