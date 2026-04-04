> **Note:** This documentation has moved to `generated-docs/docs/`.
> Please see [generated-docs/docs/technical/BACKEND_API.md](../../../generated-docs/docs/technical/BACKEND_API.md) for the latest version.

# SpOC API Integration Guide

## Overview

This document describes the API integration patterns used in the SpOC frontend, including the HTTP client configuration, React Query hooks, and data types.

## API Client Configuration

### Axios Setup

```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth token injection
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### API Endpoints

```typescript
export const api = {
  // Datasets
  getDatasets: (params?) => apiClient.get('/datasets', { params }),
  getDataset: (id) => apiClient.get(`/datasets/${id}`),
  generateDataset: (config) => apiClient.post('/datasets/generate', config),
  downloadDataset: (id) => apiClient.get(`/datasets/${id}/download`, { responseType: 'blob' }),

  // Submissions
  getSubmissions: (params?) => apiClient.get('/submissions', { params }),
  getSubmission: (id) => apiClient.get(`/submissions/${id}`),
  createSubmission: (formData) => apiClient.post('/submissions', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),

  // Results
  getResults: (submissionId) => apiClient.get(`/results/${submissionId}`),
  exportResults: (submissionId, format) => apiClient.get(`/results/${submissionId}/export`, {
    params: { format },
    responseType: 'blob',
  }),

  // Leaderboard
  getLeaderboard: (params?) => apiClient.get('/leaderboard', { params }),

  // User
  getCurrentUser: () => apiClient.get('/users/me'),
  updateProfile: (data) => apiClient.patch('/users/me', data),

  // Auth
  login: (credentials) => apiClient.post('/auth/login', credentials),
  logout: () => apiClient.post('/auth/logout'),
  refreshToken: () => apiClient.post('/auth/refresh'),
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

```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (user, token) => {
        localStorage.setItem('auth_token', token);
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('auth_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
);
```

**Usage:**

```tsx
function Header() {
  const { user, logout } = useAuthStore();

  return (
    <header>
      <span>Welcome, {user?.username}</span>
      <Button onClick={logout}>Logout</Button>
    </header>
  );
}
```

## Backend API Contract (Expected)

The frontend expects the backend to implement these endpoints:

### Datasets
- `GET /api/v1/datasets` - List datasets with optional filters
- `GET /api/v1/datasets/:id` - Get single dataset
- `POST /api/v1/datasets/generate` - Generate new dataset
- `GET /api/v1/datasets/:id/download` - Download dataset file

### Submissions
- `GET /api/v1/submissions` - List user submissions
- `GET /api/v1/submissions/:id` - Get submission details
- `POST /api/v1/submissions` - Create submission (multipart form)

### Results
- `GET /api/v1/results/:submissionId` - Get evaluation results
- `GET /api/v1/results/:submissionId/export` - Export results (PDF/CSV/JSON)

### Leaderboard
- `GET /api/v1/leaderboard` - Get rankings with optional filters

### Auth
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh JWT token

### Users
- `GET /api/v1/users/me` - Get current user profile
- `PATCH /api/v1/users/me` - Update profile
