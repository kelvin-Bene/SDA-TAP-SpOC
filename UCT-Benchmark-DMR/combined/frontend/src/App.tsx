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
const SubmitPage = lazy(() => import('@/pages/SubmitPage').then(m => ({ default: m.SubmitPage })));
const MySubmissionsPage = lazy(() => import('@/pages/MySubmissionsPage').then(m => ({ default: m.MySubmissionsPage })));
const ResultsPage = lazy(() => import('@/pages/ResultsPage').then(m => ({ default: m.ResultsPage })));
const LeaderboardPage = lazy(() => import('@/pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })));
const DocumentationPage = lazy(() => import('@/pages/DocumentationPage').then(m => ({ default: m.DocumentationPage })));
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then(m => ({ default: m.ProfilePage })));
const LoginPage = lazy(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })));

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
    <ThemeProvider defaultTheme="system" storageKey="spoc-theme">
      <ErrorBoundary>
        <FeedbackProvider>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login" element={<LazyRoute><LoginPage /></LazyRoute>} />

              {/* Public routes — no auth required */}
              <Route path="/" element={<MainLayout />}>
                <Route path="leaderboard" element={<LazyRoute><LeaderboardPage /></LazyRoute>} />
                <Route path="datasets" element={<LazyRoute><DatasetBrowserPage /></LazyRoute>} />
                <Route path="docs" element={<LazyRoute><DocumentationPage /></LazyRoute>} />
              </Route>

              {/* Authenticated routes — require login */}
              <Route
                path="/"
                element={
                  <AuthGuard>
                    <MainLayout />
                  </AuthGuard>
                }
              >
                <Route index element={<LazyRoute><DashboardPage /></LazyRoute>} />
                <Route path="datasets/generate" element={<LazyRoute><DatasetGeneratorPage /></LazyRoute>} />
                <Route path="datasets/my-datasets" element={<LazyRoute><MyDatasetsPage /></LazyRoute>} />
                <Route path="submit">
                  <Route index element={<LazyRoute><SubmitPage /></LazyRoute>} />
                  <Route path="my-submissions" element={<LazyRoute><MySubmissionsPage /></LazyRoute>} />
                </Route>
                <Route path="results/:submissionId" element={<LazyRoute><ResultsPage /></LazyRoute>} />
                <Route path="profile" element={<LazyRoute><ProfilePage /></LazyRoute>} />
              </Route>

              <Route path="*" element={<Navigate to="/leaderboard" replace />} />
            </Routes>
          </Suspense>
          <Toaster />
        </FeedbackProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
