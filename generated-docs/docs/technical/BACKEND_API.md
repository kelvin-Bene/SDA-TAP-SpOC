# Backend API Documentation

## Overview

The UCT Benchmark backend is built with FastAPI v2.0.0 and provides RESTful endpoints for dataset management, algorithm submissions, evaluation results, leaderboard, feedback, and authentication. Authentication is handled via Supabase JWTs (ES256 JWKS in production, HS256 fallback for development).

## API Client Configuration

### Axios Setup (Frontend)

The frontend uses Axios with a Supabase session interceptor. Tokens are obtained from `supabase.auth.getSession()` -- there is no localStorage token management.

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
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Refresh via supabase.auth.refreshSession(), queuing parallel
      // requests behind a single refresh attempt (mutex pattern).
      // On repeated failures, signs out via authStore.logout().
      // See client.ts for full implementation.
    }
    return Promise.reject(error);
  }
);
```

## API Endpoints

All endpoints are prefixed with `/api/v1`. Most require a valid Supabase JWT in the `Authorization: Bearer <token>` header.

### Auth (`/api/v1/auth`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/verify` | Required | Verify a Supabase session and return user info |
| GET | `/auth/me` | Required | Get current user profile (including encrypted API tokens) |
| PATCH | `/auth/me` | Required | Update profile (display name, UDL/ESA tokens) |

Login, logout, and signup are handled entirely client-side via the Supabase JS SDK. The backend only verifies and reads JWT claims.

### Datasets (`/api/v1/datasets`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/datasets/` | Required | List datasets with filters (status, regime, tier, search, sort) |
| POST | `/datasets/` | Required | Generate a new dataset (returns job_id for progress tracking) |
| GET | `/datasets/{id}` | Required | Get detailed dataset information |
| GET | `/datasets/{id}/config` | Required | Get dataset configuration values from backend settings |
| GET | `/datasets/{id}/observations` | Required | List observations in a dataset (paginated) |
| DELETE | `/datasets/{id}` | Required | Delete a dataset (admin or owner) |
| GET | `/datasets/{id}/download` | Required | Download dataset as JSON file |
| GET | `/datasets/{id}/versions` | Required | List version history of a dataset |
| GET | `/datasets/validate/{code}` | Required | Validate a legacy 16-character dataset code |
| GET | `/datasets/code/{code}` | Required | Look up a dataset by its legacy code |
| POST | `/datasets/legacy` | Required | Create a dataset from a legacy code |

### Submissions (`/api/v1/submissions`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/submissions/` | Required | List submissions for the current user (filterable by dataset_id, status) |
| POST | `/submissions/` | Required | Create submission with file upload (multipart form, rate-limited 10/min) |
| GET | `/submissions/{id}` | Required | Get submission details (ownership enforced) |
| POST | `/submissions/{id}/results` | Required | Upload or re-upload results file for an existing submission |

### Results (`/api/v1/results`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/results/` | Required | List submission results with filters (dataset_id, status, algorithm_name) |
| GET | `/results/{id}` | Required | Get complete results (binary, state, residual metrics, per-satellite breakdown) |
| GET | `/results/{id}/metrics` | Required | Get detailed per-satellite, per-track, and temporal metrics breakdown |
| GET | `/results/{id}/visualization` | Required | Get data formatted for orbit plots and error distributions |
| GET | `/results/{id}/export` | Required | Export results as JSON or CSV (format query param) |
| GET | `/results/{id}/report` | Required | Generate evaluation report (PDF, HTML, or JSON; rate-limited 5/min) |

### Jobs (`/api/v1/jobs`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/jobs/` | Required | List background jobs (filterable by job_type, status; ownership enforced) |
| GET | `/jobs/{id}` | Required | Get job status including progress percentage, result, or error |

### Leaderboard (`/api/v1/leaderboard`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/leaderboard/` | Required | Get rankings (ranked by F1 score DESC, filterable by regime, tier, dataset_id) |
| GET | `/leaderboard/history` | Required | Get leaderboard score history over time |
| GET | `/leaderboard/statistics` | Required | Get aggregate statistics (average, best, worst scores) |

### Feedback (`/api/v1/feedback`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/feedback` | Optional | Submit feedback or bug report (rate-limited 5/min per IP) |
| GET | `/feedback` | Admin | List all feedback entries with filters |
| GET | `/feedback/{id}` | Admin | Get detailed feedback entry |
| PATCH | `/feedback/{id}` | Admin | Update feedback status or resolution |

---

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

---

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

---

## Authentication

Authentication is handled client-side by the Supabase JS SDK (`@supabase/supabase-js`). The backend validates JWTs using ES256 JWKS public keys from Supabase's JWKS endpoint. See [Authentication](AUTHENTICATION.md) for full details.

**Key points:**

- Login/logout/signup are Supabase client-side operations (no backend endpoints)
- The backend's `POST /auth/verify` confirms a session is valid
- `GET /auth/me` and `PATCH /auth/me` manage user profiles
- Roles are extracted from `app_metadata.role` in the JWT (server-side only, not user-editable)
- Token refresh uses a mutex-protected interceptor to prevent parallel refresh races

---

## FastAPI Backend Structure

```
backend_api/
├── __init__.py
├── main.py                 # Application entry point, CORS, middleware
├── auth.py                 # ES256 JWKS JWT verification (production auth)
├── database.py             # Database dependency (get_db)
├── models/                 # Pydantic models
│   ├── dataset.py
│   ├── submission.py
│   ├── feedback.py
│   └── __init__.py
├── routers/                # API route handlers
│   ├── auth.py             # /auth/verify, /auth/me
│   ├── datasets.py         # Dataset CRUD + generation
│   ├── submissions.py      # Submission upload + validation
│   ├── results.py          # Results retrieval + export + report
│   ├── leaderboard.py      # Rankings, history, statistics
│   ├── jobs.py             # Background job status
│   └── feedback.py         # Feedback/bug reports
├── middleware/              # Middleware layer
│   ├── auth.py             # JWT auth dependencies (get_current_user)
│   ├── rate_limit.py       # slowapi rate limiting
│   └── logging.py          # Request logging with correlation IDs
├── jobs/                   # Background job processing
│   ├── __init__.py         # JobManager with in-memory state
│   └── workers.py          # ThreadPoolExecutor workers
├── utils/                  # Utility modules
│   └── token_validation.py # UDL/ESA token validation
└── tests/                  # API tests
    ├── test_jobs.py
    ├── test_leaderboard.py
    ├── test_results.py
    ├── test_crypto.py
    └── test_middleware.py
```

---

## Running the Backend

```bash
# Navigate to combined directory
cd UCT-Benchmark-DMR/combined

# Start FastAPI backend
uvicorn backend_api.main:app --reload --port 8000

# With hot reload for development
uvicorn backend_api.main:app --reload --host 0.0.0.0 --port 8000
```

Access the API documentation at http://localhost:8000/docs

---

## Related Documentation

- [Frontend Architecture](FRONTEND.md)
- [Database Schema](DATABASE.md)
- [Architecture Overview](ARCHITECTURE.md)
