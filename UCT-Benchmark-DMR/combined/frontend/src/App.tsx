import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import { ErrorBoundary, RouteErrorBoundary } from '@/components/ErrorBoundary';
import { FeedbackProvider } from '@/components/feedback/FeedbackProvider';
import { AuthGuard } from '@/components/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';

// U2/P1: Lazy-load all page components for code splitting
// Heavy deps (Cesium ~1.4MB, Recharts ~260KB) only load when needed
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const DatasetBrowserPage = lazy(() => import('@/pages/DatasetBrowserPage').then(m => ({ default: m.DatasetBrowserPage })));
const DatasetGeneratorPage = lazy(() => import('@/pages/DatasetGeneratorPage').then(m => ({ default: m.DatasetGeneratorPage })));
const MyDatasetsPage = lazy(() => import('@/pages/MyDatasetsPage').then(m => ({ default: m.MyDatasetsPage })));
const DatasetDetailPage = lazy(() => import('@/pages/DatasetDetailPage').then(m => ({ default: m.DatasetDetailPage })));
const SubmitPage = lazy(() => import('@/pages/SubmitPage').then(m => ({ default: m.SubmitPage })));
const MySubmissionsPage = lazy(() => import('@/pages/MySubmissionsPage').then(m => ({ default: m.MySubmissionsPage })));
const ResultsPage = lazy(() => import('@/pages/ResultsPage').then(m => ({ default: m.ResultsPage })));
const LeaderboardPage = lazy(() => import('@/pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })));
const DocumentationPage = lazy(() => import('@/pages/DocumentationPage').then(m => ({ default: m.DocumentationPage })));
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then(m => ({ default: m.ProfilePage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        {children}
      </Suspense>
    </RouteErrorBoundary>
  );
}

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="uct-benchmark-theme">
      <ErrorBoundary>
        <FeedbackProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Demo mode: redirect root and legacy routes to dashboard */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/welcome" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<Navigate to="/dashboard" replace />} />

              {/* Single layout route — auth enforced per-route */}
              <Route element={<MainLayout />}>
                {/* Public routes — no auth required */}
                <Route path="docs" element={<LazyRoute><DocumentationPage /></LazyRoute>} />

                {/* Authenticated routes — each individually guarded */}
                <Route path="dashboard" element={<AuthGuard><LazyRoute><DashboardPage /></LazyRoute></AuthGuard>} />
                <Route path="leaderboard" element={<AuthGuard><LazyRoute><LeaderboardPage /></LazyRoute></AuthGuard>} />
                <Route path="datasets" element={<AuthGuard><LazyRoute><DatasetBrowserPage /></LazyRoute></AuthGuard>} />
                <Route path="datasets/:id" element={<AuthGuard><LazyRoute><DatasetDetailPage /></LazyRoute></AuthGuard>} />
                <Route path="datasets/generate" element={<AuthGuard><LazyRoute><DatasetGeneratorPage /></LazyRoute></AuthGuard>} />
                <Route path="datasets/my-datasets" element={<AuthGuard><LazyRoute><MyDatasetsPage /></LazyRoute></AuthGuard>} />
                <Route path="submit" element={<AuthGuard><LazyRoute><SubmitPage /></LazyRoute></AuthGuard>} />
                <Route path="submit/my-submissions" element={<AuthGuard><LazyRoute><MySubmissionsPage /></LazyRoute></AuthGuard>} />
                <Route path="results/:submissionId" element={<AuthGuard><LazyRoute><ResultsPage /></LazyRoute></AuthGuard>} />
                <Route path="profile" element={<AuthGuard><LazyRoute><ProfilePage /></LazyRoute></AuthGuard>} />
                <Route path="settings" element={<AuthGuard><LazyRoute><SettingsPage /></LazyRoute></AuthGuard>} />

                {/* Catch-all */}
                <Route path="*" element={<LazyRoute><NotFoundPage /></LazyRoute>} />
              </Route>
            </Routes>
          </Suspense>
          <Toaster />
        </FeedbackProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
