import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import { ErrorBoundary, RouteErrorBoundary } from '@/components/ErrorBoundary';
import { MainLayout } from '@/components/layout/MainLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { DatasetBrowserPage } from '@/pages/DatasetBrowserPage';
import { DatasetGeneratorPage } from '@/pages/DatasetGeneratorPage';
import { MyDatasetsPage } from '@/pages/MyDatasetsPage';
import { SubmitPage } from '@/pages/SubmitPage';
import { MySubmissionsPage } from '@/pages/MySubmissionsPage';
import { ResultsPage } from '@/pages/ResultsPage';
import { LeaderboardPage } from '@/pages/LeaderboardPage';
import { DocumentationPage } from '@/pages/DocumentationPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { LoginPage } from '@/pages/LoginPage';

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="spoc-theme">
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<MainLayout />}>
            <Route index element={<RouteErrorBoundary><DashboardPage /></RouteErrorBoundary>} />
            <Route path="datasets">
              <Route index element={<RouteErrorBoundary><DatasetBrowserPage /></RouteErrorBoundary>} />
              <Route path="generate" element={<RouteErrorBoundary><DatasetGeneratorPage /></RouteErrorBoundary>} />
              <Route path="my-datasets" element={<RouteErrorBoundary><MyDatasetsPage /></RouteErrorBoundary>} />
            </Route>
            <Route path="submit">
              <Route index element={<RouteErrorBoundary><SubmitPage /></RouteErrorBoundary>} />
              <Route path="my-submissions" element={<RouteErrorBoundary><MySubmissionsPage /></RouteErrorBoundary>} />
            </Route>
            <Route path="results/:submissionId" element={<RouteErrorBoundary><ResultsPage /></RouteErrorBoundary>} />
            <Route path="leaderboard" element={<RouteErrorBoundary><LeaderboardPage /></RouteErrorBoundary>} />
            <Route path="docs" element={<RouteErrorBoundary><DocumentationPage /></RouteErrorBoundary>} />
            <Route path="profile" element={<RouteErrorBoundary><ProfilePage /></RouteErrorBoundary>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
        <Toaster />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
