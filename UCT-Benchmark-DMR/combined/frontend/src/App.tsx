import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ThemeProvider } from '@/components/theme-provider';
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
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<MainLayout />}>
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
          <Route path="docs" element={<DocumentationPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      <Toaster />
    </ThemeProvider>
  );
}

export default App;
