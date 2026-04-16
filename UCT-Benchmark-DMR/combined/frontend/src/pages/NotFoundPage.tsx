import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Home } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-5xl xs:text-6xl font-display font-bold tracking-tight mb-4">
        <span className="text-gradient-cosmic">404</span>
      </h1>
      <h2 className="text-xl xs:text-2xl font-semibold mb-2">Page Not Found</h2>
      <p className="text-muted-foreground max-w-md mb-8">
        The page you are looking for does not exist or may have been moved.
      </p>
      <Link to="/dashboard">
        <Button className="gap-2">
          <Home className="h-4 w-4" />
          Go Home
        </Button>
      </Link>
    </div>
  );
}
