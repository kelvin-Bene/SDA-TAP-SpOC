# SpOC API Integration Guide

## Overview

This document describes the API integration patterns used in the SpOC frontend, including the HTTP client configuration, React Query hooks, and data types.

## API Client Configuration

### Axios Setup with Supabase Auth

The frontend uses Axios with a Supabase session-based auth interceptor. Tokens are managed by the Supabase JS SDK -- there is no localStorage token management.

```typescript
// src/api/client.ts
import axios from 'axios';
import { supabase } from '@/lib/supabase';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - injects Supabase JWT from active session
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
      }
    } catch (error) {
      console.error('Failed to get auth session for request:', error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - mutex-protected token refresh on 401
// Uses a refresh subscriber queue to prevent parallel refresh attempts.
// On repeated failures (3 within 60s), signs out via authStore.logout().
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const { data, error: refreshError } = await supabase.auth.refreshSession();
      if (data.session) {
        originalRequest.headers.Authorization = `Bearer ${data.session.access_token}`;
        return apiClient(originalRequest);
      }
      // Sign out on refresh failure
      const { useAuthStore } = await import('@/stores/authStore');
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);
```

### API Helper Functions

List endpoints use a trailing slash (matching `@router.get("/")`). Detail and sub-resource endpoints do not use trailing slashes (avoids 307 redirect issues).

```typescript
export const api = {
  // Datasets
  getDatasetConfig: () => apiClient.get('/datasets/config'),
  getDatasets: (params?: Record<string, string>) => apiClient.get('/datasets/', { params }),
  getDataset: (id: string) => apiClient.get(`/datasets/${id}`),
  generateDataset: (config: unknown) => apiClient.post('/datasets/', config),
  downloadDataset: (id: string) => apiClient.get(`/datasets/${id}/download`, { responseType: 'blob' }),
  getDatasetObservations: (id: string, params?: { limit?: number; offset?: number }) =>
    apiClient.get(`/datasets/${id}/observations`, { params }),
  deleteDataset: (id: string) => apiClient.delete(`/datasets/${id}`),
  getDatasetVersions: (id: string) => apiClient.get(`/datasets/${id}/versions`),

  // Submissions
  getSubmissions: (params?: Record<string, string>) => apiClient.get('/submissions/', { params }),
  getSubmission: (id: string) => apiClient.get(`/submissions/${id}`),
  createSubmission: (formData: FormData) => apiClient.post('/submissions/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  uploadResults: (submissionId: string, formData: FormData) =>
    apiClient.post(`/submissions/${submissionId}/results`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  // Results
  getResults: (submissionId: string) => apiClient.get(`/results/${submissionId}`),
  getDetailedMetrics: (submissionId: string) => apiClient.get(`/results/${submissionId}/metrics`),
  getVisualizationData: (submissionId: string) => apiClient.get(`/results/${submissionId}/visualization`),
  exportResults: (submissionId: string, format: 'pdf' | 'csv' | 'json') =>
    apiClient.get(`/results/${submissionId}/export`, { params: { format }, responseType: 'blob' }),
  downloadReport: (submissionId: string, format: 'pdf' | 'html' | 'json' = 'pdf') =>
    apiClient.get(`/results/${submissionId}/report`, { params: { format }, responseType: 'blob' }),

  // Leaderboard
  getLeaderboard: (params?: Record<string, string>) => apiClient.get('/leaderboard/', { params }),
  getLeaderboardHistory: (params?: { dataset_id?: string; days?: number }) =>
    apiClient.get('/leaderboard/history', { params }),
  getLeaderboardStatistics: (params?: { dataset_id?: string }) =>
    apiClient.get('/leaderboard/statistics', { params }),

  // Jobs
  getJobStatus: (jobId: string) => apiClient.get(`/jobs/${jobId}`),
  listJobs: (params?: { job_type?: string; status?: string; limit?: number }) =>
    apiClient.get('/jobs/', { params }),

  // User / Auth (session verification only - login/logout handled client-side via Supabase JS SDK)
  getCurrentUser: () => apiClient.get('/auth/me'),
  updateProfile: (data: unknown) => apiClient.patch('/auth/me', data),
};
```

## React Query Hooks

### useDatasets

Fetch and filter datasets:

```typescript
// src/hooks/useDatasets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useDatasets(filters?: DatasetFilters) {
  return useQuery({
    queryKey: ['datasets', filters],
    queryFn: async () => {
      const response = await api.getDatasets(filters);
      return response.data as Dataset[];
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: ['dataset', id],
    queryFn: async () => {
      const response = await api.getDataset(id);
      return response.data as Dataset;
    },
    enabled: !!id,
  });
}

export function useGenerateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (config: DatasetGenerationConfig) => {
      const response = await api.generateDataset(config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}
```

**Usage:**

```tsx
function DatasetBrowserPage() {
  const [filters, setFilters] = useState<DatasetFilters>({});
  const { data: datasets, isLoading, error } = useDatasets(filters);

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <DatasetGrid>
      {datasets?.map(d => <DatasetCard key={d.id} dataset={d} />)}
    </DatasetGrid>
  );
}
```

### useSubmissions

Manage algorithm submissions:

```typescript
// src/hooks/useSubmissions.ts
export function useSubmissions() {
  return useQuery({
    queryKey: ['submissions'],
    queryFn: async () => {
      const response = await api.getSubmissions();
      return response.data as Submission[];
    },
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useCreateSubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SubmissionForm) => {
      const formData = new FormData();
      formData.append('file', data.file);
      formData.append('datasetId', data.datasetId);
      formData.append('algorithmName', data.algorithmName);
      formData.append('version', data.version);
      if (data.description) {
        formData.append('description', data.description);
      }
      const response = await api.createSubmission(formData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
    },
  });
}

export function useResults(submissionId: string) {
  return useQuery({
    queryKey: ['results', submissionId],
    queryFn: async () => {
      const response = await api.getResults(submissionId);
      return response.data as SubmissionResults;
    },
    enabled: !!submissionId,
  });
}
```

**Usage:**

```tsx
function SubmitPage() {
  const { mutate: createSubmission, isPending } = useCreateSubmission();

  const handleSubmit = (data: SubmissionForm) => {
    createSubmission(data, {
      onSuccess: () => {
        navigate('/submit/my-submissions');
      },
      onError: (error) => {
        toast({ variant: 'destructive', title: 'Submission failed' });
      },
    });
  };

  return <SubmissionForm onSubmit={handleSubmit} isLoading={isPending} />;
}
```

### useLeaderboard

Fetch leaderboard rankings:

```typescript
// src/hooks/useLeaderboard.ts
export function useLeaderboard(filters?: LeaderboardFilters) {
  return useQuery({
    queryKey: ['leaderboard', filters],
    queryFn: async () => {
      const response = await api.getLeaderboard(filters);
      return response.data as LeaderboardEntry[];
    },
    staleTime: 1000 * 60, // 1 minute
  });
}
```

## Type Definitions

### Dataset Types

```typescript
// src/types/index.ts
export type OrbitalRegime = 'LEO' | 'MEO' | 'GEO' | 'HEO';
export type DataTier = 'T1' | 'T2' | 'T3' | 'T4';
export type SensorType = 'optical' | 'radar' | 'rf';

export interface Dataset {
  id: string;
  name: string;
  regime: OrbitalRegime;
  tier: DataTier;
  createdAt: string;
  objectCount: number;
  observationCount: number;
  coverage: number;
  sizeBytes: number;
  sensorTypes: SensorType[];
  description?: string;
  downloadUrl?: string;
}

export interface DatasetFilters {
  regime?: OrbitalRegime | 'all';
  tier?: DataTier | 'all';
  sensor?: SensorType | 'all';
  dateRange?: { start: Date; end: Date };
  objectCountRange?: { min: number; max: number };
}

export interface DatasetGenerationConfig {
  regime: OrbitalRegime;
  coverage: 'high' | 'standard' | 'low' | 'mixed';
  observationDensity: number;
  trackGapTarget: number;
  objectCount: number;
  includeHamr: boolean;
  startDate: string;
  endDate: string;
  sensors: SensorType[];
}
```

### Submission Types

```typescript
export type SubmissionStatus = 'queued' | 'validating' | 'processing' | 'completed' | 'failed';

export interface Submission {
  id: string;
  datasetId: string;
  datasetName: string;
  algorithmName: string;
  version: string;
  status: SubmissionStatus;
  createdAt: string;
  completedAt?: string;
  queuePosition?: number;
  results?: SubmissionResults;
  errorMessage?: string;
}

export interface SubmissionResults {
  // Binary Metrics
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  precision: number;
  recall: number;
  f1Score: number;

  // State Metrics
  positionRmsKm: number;
  velocityRmsKmS: number;
  mahalanobisDistance: number;

  // Residual Analysis
  raResidualRmsArcsec: number;
  decResidualRmsArcsec: number;

  // Per-satellite breakdown
  satelliteResults: SatelliteResult[];

  // Rank info
  rank: number;
  previousRank?: number;
}

export interface SatelliteResult {
  satelliteId: string;
  status: 'TP' | 'FP' | 'FN';
  observationsUsed: number;
  totalObservations: number;
  positionErrorKm?: number;
  velocityErrorKmS?: number;
  confidence?: number;
}
```

### Leaderboard Types

```typescript
export interface LeaderboardEntry {
  rank: number;
  algorithmName: string;
  team: string;
  version: string;
  f1Score: number;
  precision: number;
  recall: number;
  positionRmsKm: number;
  submissionId: string;
  submittedAt: string;
  isCurrentUser: boolean;
}

export interface LeaderboardFilters {
  regime?: OrbitalRegime | 'all';
  tier?: DataTier | 'all';
  period?: 'all' | 'month' | 'week';
}
```

## Auth Store (Zustand)

Authentication state is managed via Zustand, backed by the Supabase JS SDK. Login/logout are handled client-side through Supabase -- the store tracks session state but does not manage tokens directly.

```typescript
// src/stores/authStore.ts - conceptual overview
// The actual store uses supabase.auth.signInWithPassword() for login,
// supabase.auth.signOut() for logout, and listens to onAuthStateChange
// to keep the Zustand state in sync with the Supabase session.
```

## Backend API Contract

The frontend expects the backend to implement these endpoints (all implemented as of v2.0.0):

### Auth (session verification only -- login/logout handled client-side via Supabase JS SDK)
- `POST /api/v1/auth/verify` - Verify a Supabase session
- `GET /api/v1/auth/me` - Get current user profile
- `PATCH /api/v1/auth/me` - Update profile (including UDL/ESA tokens)

### Datasets
- `GET /api/v1/datasets/` - List datasets with filters (status, regime, tier, search)
- `POST /api/v1/datasets/` - Generate new dataset (returns job_id)
- `GET /api/v1/datasets/:id` - Get single dataset
- `GET /api/v1/datasets/:id/observations` - List observations (paginated)
- `GET /api/v1/datasets/:id/download` - Download dataset file
- `GET /api/v1/datasets/:id/versions` - List version history
- `DELETE /api/v1/datasets/:id` - Delete dataset
- `GET /api/v1/datasets/validate/:code` - Validate legacy code
- `GET /api/v1/datasets/code/:code` - Look up dataset by code
- `POST /api/v1/datasets/legacy` - Create from legacy code

### Submissions
- `GET /api/v1/submissions/` - List user submissions
- `POST /api/v1/submissions/` - Create submission (multipart form)
- `GET /api/v1/submissions/:id` - Get submission details
- `POST /api/v1/submissions/:id/results` - Upload/re-upload results file

### Results
- `GET /api/v1/results/` - List results with filters
- `GET /api/v1/results/:id` - Get complete evaluation results
- `GET /api/v1/results/:id/metrics` - Detailed per-satellite/per-track metrics
- `GET /api/v1/results/:id/visualization` - Visualization data (orbit plots, error distributions)
- `GET /api/v1/results/:id/export` - Export results (JSON/CSV)
- `GET /api/v1/results/:id/report` - Generate evaluation report (PDF/HTML/JSON)

### Leaderboard
- `GET /api/v1/leaderboard/` - Rankings (filterable by regime, tier, dataset_id)
- `GET /api/v1/leaderboard/history` - Score history over time
- `GET /api/v1/leaderboard/statistics` - Aggregate statistics

### Jobs
- `GET /api/v1/jobs/` - List background jobs
- `GET /api/v1/jobs/:id` - Get job status (progress, result, error)

### Feedback
- `POST /api/v1/feedback` - Submit feedback (auth optional)
- `GET /api/v1/feedback` - List feedback (admin only)
- `GET /api/v1/feedback/:id` - Get feedback detail (admin only)
- `PATCH /api/v1/feedback/:id` - Update feedback status (admin only)
