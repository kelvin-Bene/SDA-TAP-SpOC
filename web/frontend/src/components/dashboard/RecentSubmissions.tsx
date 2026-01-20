import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
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
    version: 'v2.0',
    status: 'processing',
    createdAt: '2026-01-18T14:00:00Z',
    queuePosition: 2,
  },
  {
    id: '3',
    datasetId: 'ds-3',
    datasetName: 'GEO-T3-2026-01-08',
    algorithmName: 'MyUCTP',
    version: 'v1.9',
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

export function RecentSubmissions() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold">Recent Submissions</CardTitle>
        <Link to="/submit/my-submissions">
          <Button variant="ghost" size="sm" className="gap-1">
            View All
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {mockSubmissions.map((submission) => (
            <Link
              key={submission.id}
              to={submission.status === 'completed' ? `/results/${submission.id}` : '#'}
              className="block"
            >
              <div className="rounded-lg border p-4 transition-colors hover:bg-accent/50">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {submission.algorithmName} {submission.version}
                      </span>
                      {getStatusBadge(submission.status)}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {submission.datasetName}
                    </p>
                  </div>
                  {submission.results && (
                    <div className="text-right">
                      <p className="font-mono text-lg font-semibold">
                        {submission.results.f1Score.toFixed(3)}
                      </p>
                      <p className="text-xs text-muted-foreground">F1-Score</p>
                    </div>
                  )}
                  {submission.queuePosition && (
                    <div className="text-right">
                      <p className="font-mono text-lg font-semibold">
                        #{submission.queuePosition}
                      </p>
                      <p className="text-xs text-muted-foreground">in queue</p>
                    </div>
                  )}
                </div>
                {submission.results && (
                  <div className="mt-3 flex gap-4 text-sm text-muted-foreground">
                    <span>Position RMS: {submission.results.positionRmsKm.toFixed(2)} km</span>
                    <span>Rank: #{submission.results.rank}</span>
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
