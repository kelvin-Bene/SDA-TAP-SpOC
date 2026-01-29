import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import type { SubmissionStatus } from '@/types';
import { useSubmissions } from '@/hooks/useSubmissions';

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
  const { data: submissions, isLoading, error } = useSubmissions();
  const recentSubmissions = submissions?.slice(0, 3) ?? [];

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
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>Unable to load submissions</p>
          </div>
        ) : recentSubmissions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No submissions yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            {recentSubmissions.map((submission) => (
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
                    {submission.results && submission.results.f1Score != null && (
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
                  {submission.results && (submission.results.positionRmsKm != null || submission.results.rank != null) && (
                    <div className="mt-3 flex gap-4 text-sm text-muted-foreground">
                      {submission.results.positionRmsKm != null && (
                        <span>Position RMS: {submission.results.positionRmsKm.toFixed(2)} km</span>
                      )}
                      {submission.results.rank != null && (
                        <span>Rank: #{submission.results.rank}</span>
                      )}
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
