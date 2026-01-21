import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Upload, Trophy, BookOpen } from 'lucide-react';

export function QuickActions() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3">
          <Link to="/datasets/generate">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Generate Dataset
            </Button>
          </Link>
          <Link to="/submit">
            <Button variant="outline" className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Submission
            </Button>
          </Link>
          <Link to="/leaderboard">
            <Button variant="outline" className="gap-2">
              <Trophy className="h-4 w-4" />
              View Leaderboard
            </Button>
          </Link>
          <Link to="/docs">
            <Button variant="ghost" className="gap-2">
              <BookOpen className="h-4 w-4" />
              Documentation
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
