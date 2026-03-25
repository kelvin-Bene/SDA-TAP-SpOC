import { Component, ErrorInfo, ReactNode } from 'react';
import * as Sentry from '@sentry/react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, Home, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    // Log error to console for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    // Report to Sentry if initialized
    Sentry.captureException(error, {
      contexts: {
        react: {
          componentStack: errorInfo.componentStack ?? undefined,
        },
      },
    });
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = (): void => {
    this.handleReset();
    window.location.href = '/';
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback UI if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background">
          <Card className="max-w-lg w-full">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 rounded-full bg-destructive/10 p-3 w-fit">
                <AlertTriangle className="h-8 w-8 text-destructive" />
              </div>
              <CardTitle className="text-2xl">Something went wrong</CardTitle>
              <CardDescription>
                An unexpected error occurred. We apologize for the inconvenience.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {this.state.error && (
                <div className="rounded-lg bg-muted p-4">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Error details:</p>
                  <p className="text-sm font-mono text-destructive break-all">
                    {this.state.error.message}
                  </p>
                </div>
              )}
              <div className="flex flex-col sm:flex-row gap-2">
                <Button
                  variant="outline"
                  className="flex-1 gap-2"
                  onClick={this.handleGoHome}
                >
                  <Home className="h-4 w-4" />
                  Go to Dashboard
                </Button>
                <Button
                  className="flex-1 gap-2"
                  onClick={this.handleReload}
                >
                  <RefreshCw className="h-4 w-4" />
                  Reload Page
                </Button>
              </div>
              <p className="text-xs text-center text-muted-foreground">
                If this problem persists, please contact support or check the console for more details.
              </p>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * ErrorBoundary wrapper for specific routes/sections
 * with a more compact inline fallback
 */
interface RouteErrorBoundaryProps {
  children: ReactNode;
}

export function RouteErrorBoundary({ children }: RouteErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="rounded-full bg-destructive/10 p-3">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <div className="text-center">
            <h3 className="text-lg font-semibold">Failed to load this section</h3>
            <p className="text-sm text-muted-foreground mt-1">
              An error occurred while loading this content.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => window.location.reload()}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
