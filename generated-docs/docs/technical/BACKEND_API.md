# Backend API Documentation

## Overview

The UCT Benchmark backend is built with FastAPI and provides RESTful endpoints for dataset management, algorithm submissions, and evaluation results.

## API Client Configuration

### Axios Setup (Frontend)

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

## API Endpoints

All routers are registered in `main.py` with their respective prefixes under `/api/v1/`.
Authentication is enforced via Supabase JWT middleware unless noted otherwise.

---

### 1. Root Endpoints

Registered directly on the FastAPI app (no prefix).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | None | API root health check -- returns `{"status": "ok"}` |
| GET | `/health` | None | Detailed health check with component status (database, disk, Orekit) |

---

### 2. Auth (`/api/v1/auth`)

User identity verification and profile management. Uses its own auth dependency (ES256 JWKS in production).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/verify` | Verify JWT and return authenticated user profile (creates profile on first login) |
| GET | `/api/v1/auth/me` | Get the current authenticated user's profile |
| PATCH | `/api/v1/auth/me` | Update profile fields (`display_name`, `organization`, `udl_token`, `esa_token`) |

---

### 3. Datasets (`/api/v1/datasets`)

Dataset generation, browsing, download, and legacy-code operations. Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/datasets/config` | Return backend dataset configuration values (coverage thresholds, track gap multiplier, observation count thresholds) |
| GET | `/api/v1/datasets/` | List datasets with optional filters (`status`, `regime`, `tier`, `sensor`, `legacy_code`, `search`) |
| GET | `/api/v1/datasets/{dataset_id}` | Get full details of a single dataset |
| GET | `/api/v1/datasets/{dataset_id}/versions` | List all version variants of a dataset |
| POST | `/api/v1/datasets/` | Create/generate a new dataset (rate-limited: 5/min) |
| GET | `/api/v1/datasets/{dataset_id}/observations` | List observations linked to a dataset (with pagination) |
| POST | `/api/v1/datasets/{dataset_id}/link-observations` | Manually link observations to a dataset (repair endpoint) |
| PATCH | `/api/v1/datasets/{dataset_id}/coverage` | Update a dataset's coverage value |
| DELETE | `/api/v1/datasets/{dataset_id}` | Delete a dataset (admin only) |
| GET | `/api/v1/datasets/{dataset_id}/download` | Download the dataset file as JSON (rate-limited: 10/min; answer-key fields stripped) |
| POST | `/api/v1/datasets/legacy` | Create a dataset from a legacy code string |
| GET | `/api/v1/datasets/code/{legacy_code}` | Look up a dataset by its legacy code |
| GET | `/api/v1/datasets/validate/{code}` | Validate a dataset code (legacy or enhanced format) |

---

### 4. Submissions (`/api/v1/submissions`)

Upload and manage algorithm submission files. Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/submissions/` | List submissions for the current user (filterable by `dataset_id`, `status`) |
| GET | `/api/v1/submissions/{submission_id}` | Get detailed info for a specific submission |
| POST | `/api/v1/submissions/` | Create a new submission with file upload (multipart form; rate-limited: 10/min) |
| POST | `/api/v1/submissions/{submission_id}/results` | Upload or re-upload a results file for an existing submission |

---

### 5. Results (`/api/v1/results`)

Retrieve evaluation results, metrics, visualizations, and reports. Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/results/` | List all submission results with optional filtering (`dataset_id`, `status`, `algorithm_name`) |
| GET | `/api/v1/results/{submission_id}` | Get complete results for a submission (binary metrics, state metrics, per-satellite breakdown) |
| GET | `/api/v1/results/{submission_id}/metrics` | Get detailed per-satellite and per-track metrics breakdown |
| GET | `/api/v1/results/{submission_id}/visualization` | Get data formatted for orbit plots, error distributions, and temporal analysis |
| GET | `/api/v1/results/{submission_id}/export` | Export results as JSON or CSV download |
| GET | `/api/v1/results/{submission_id}/report` | Generate a comprehensive evaluation report (PDF, HTML, or JSON; rate-limited: 5/min) |

---

### 6. Leaderboard (`/api/v1/leaderboard`)

Rankings, history, and aggregate statistics. Requires JWT. Leaderboard data is intentionally visible to all authenticated users to support the benchmark competition.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/leaderboard/` | Get ranked leaderboard entries (filterable by `dataset_id`, `regime`, `tier`, `period`) |
| GET | `/api/v1/leaderboard/history` | Get leaderboard score history over time (for trend visualization) |
| GET | `/api/v1/leaderboard/statistics` | Get aggregate statistics (total submissions, unique algorithms, averages, trend) |

---

### 7. Jobs (`/api/v1/jobs`)

Background job status tracking (dataset generation, evaluation). Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs/` | List background jobs with optional filtering (`job_type`, `status`). Users see own jobs; admins see all. |
| GET | `/api/v1/jobs/{job_id}` | Get status of a specific background job (progress, result, or error) |

---

### 8. Events (`/api/v1/events`)

Event labelling and detection for observation data. Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/events/types` | List all available event types |
| GET | `/api/v1/events/` | List events with optional filters (`event_type`, `sat_no`, `start_time`, `end_time`, `dataset_id`) |
| GET | `/api/v1/events/{event_id}` | Get event detail with linked observations |
| POST | `/api/v1/events/detect` | Trigger event detection as a background job (specify `sat_nos`, time window, detector types) |
| DELETE | `/api/v1/events/{event_id}` | Delete an event (admin only) |

---

### 9. Credentials (`/api/v1/credentials`)

Encrypted credential storage and connectivity testing for external data services. Requires JWT.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/credentials/` | List all credential services and their configuration status |
| GET | `/api/v1/credentials/{service_name}` | Get metadata for a single credential service (never returns secret values) |
| PUT | `/api/v1/credentials/{service_name}` | Save encrypted credentials for a service |
| DELETE | `/api/v1/credentials/{service_name}` | Delete stored credentials for a service |
| POST | `/api/v1/credentials/{service_name}/test` | Resolve credentials and test connectivity against the service API |

#### Response: CredentialServiceInfo

```json
{
  "service_name": "udl",
  "label": "Unified Data Library",
  "description": "...",
  "is_configured": true,
  "source": "database",
  "validation_status": "valid",
  "last_tested_at": "2026-01-27T15:30:00Z"
}
```

**Validation Status Values:**
- `untested` -- Credentials saved but not validated
- `valid` -- Connection test passed
- `invalid` -- Connection test failed (wrong credentials)
- `error` -- Connection test errored (network/service issue)
- `not_configured` -- No credentials saved

---

### 10. Feedback (`/api/v1/feedback`)

Bug reports and user feedback. Registered under `/api/v1` prefix (not `/api/v1/feedback`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/feedback` | Optional | Submit a feedback or bug report (anonymous allowed; rate-limited: 5/min) |
| GET | `/api/v1/feedback` | Admin | List all feedback entries with optional filters (`status_filter`, `severity`, `date_from`, `date_to`) |
| GET | `/api/v1/feedback/{feedback_id}` | Admin | Get detailed information about a single feedback entry |
| PATCH | `/api/v1/feedback/{feedback_id}` | Admin | Update feedback status/resolution (currently returns 501 -- pending cross-project schema sync) |

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

---

## FastAPI Backend Structure

```
backend_api/
├── __init__.py
├── main.py              # Application entry point, router registration, middleware stack
├── auth.py              # JWT verification (ES256 JWKS), CurrentUser model
├── config.py            # Application configuration
├── database.py          # Database connection management (DuckDB / PostgreSQL)
├── models/              # Pydantic request/response models
│   ├── __init__.py
│   ├── dataset.py
│   ├── submission.py
│   ├── feedback.py
│   └── ...
├── routers/             # API route handlers
│   ├── auth.py          # /api/v1/auth — verify, profile (me)
│   ├── datasets.py      # /api/v1/datasets — CRUD, generation, download, legacy codes
│   ├── submissions.py   # /api/v1/submissions — upload, list, detail
│   ├── results.py       # /api/v1/results — metrics, visualization, export, report
│   ├── leaderboard.py   # /api/v1/leaderboard — rankings, history, statistics
│   ├── jobs.py          # /api/v1/jobs — background job status
│   ├── events.py        # /api/v1/events — event labelling and detection
│   ├── credentials.py   # /api/v1/credentials — encrypted credential CRUD and testing
│   └── feedback.py      # /api/v1/feedback — bug reports and user feedback
├── middleware/           # Custom middleware
│   ├── auth.py          # get_current_user dependency, require_admin
│   ├── audit.py         # Audit logging
│   ├── logging.py       # Request logging with correlation IDs
│   └── rate_limit.py    # Rate limiting (slowapi)
├── services/            # Business logic services
│   └── credential_service.py  # Credential encryption, resolution, connectivity testing
├── jobs/                # Background job management
│   ├── __init__.py      # JobManager, JobStatus, JobType
│   └── workers.py       # Worker threads for evaluation, generation, event detection
├── utils/               # Shared utilities
│   ├── crypto.py        # Token encryption/decryption
│   └── token_validation.py  # UDL/ESA token validation
└── tests/               # API tests
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
