import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
import { AuthProvider } from '@/components/auth/AuthProvider';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
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
import { SettingsPage } from '@/pages/SettingsPage';
import { LoginPage } from '@/pages/LoginPage';
import { UCTPDashboardPage } from '@/pages/uctp/UCTPDashboardPage';
import { AlgorithmWorkbenchPage } from '@/pages/uctp/AlgorithmWorkbenchPage';
import { RunResultsPage } from '@/pages/uctp/RunResultsPage';
import { MLTrainingPage } from '@/pages/uctp/MLTrainingPage';
import { APIConnectivityPage } from '@/pages/uctp/APIConnectivityPage';
import { ComparisonPage } from '@/pages/uctp/ComparisonPage';

function App() {
  return (
    <AuthProvider>
      <ThemeProvider defaultTheme="system" storageKey="spoc-theme">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="datasets">
              <Route index element={<DatasetBrowserPage />} />
              <Route path="generate" element={<DatasetGeneratorPage />} />
              <Route path="my-datasets" element={<MyDatasetsPage />} />
            </Route>
            <Route path="submit">
              <Route index element={<SubmitPage />} />
              <Route path="my-submissions" element={<MySubmissionsPage />} />
            </Route>
            <Route path="results/:submissionId" element={<ResultsPage />} />
            <Route path="leaderboard" element={<LeaderboardPage />} />
            <Route path="uctp">
              <Route index element={<UCTPDashboardPage />} />
              <Route path="workbench" element={<AlgorithmWorkbenchPage />} />
              <Route path="runs/:runId" element={<RunResultsPage />} />
              <Route path="training" element={<MLTrainingPage />} />
              <Route path="connectivity" element={<APIConnectivityPage />} />
              <Route path="compare" element={<ComparisonPage />} />
            </Route>
            <Route path="docs" element={<DocumentationPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
        <Toaster />
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;
