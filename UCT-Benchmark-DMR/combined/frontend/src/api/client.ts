import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
// Prefers Supabase session token when available, falls back to localStorage
apiClient.interceptors.request.use(
  async (config) => {
    let token: string | null = null;

    // Try to get token from Supabase session first
    try {
      const { supabase } = await import('@/lib/supabase');
      if (supabase) {
        const { data: { session } } = await supabase.auth.getSession();
        token = session?.access_token ?? null;
      }
    } catch {
      // Supabase not configured; fall through to localStorage
    }

    // Fallback to localStorage (non-Supabase auth or persisted token)
    if (!token) {
      token = localStorage.getItem('auth_token');
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
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

// API helper functions
// Note: Using trailing slashes to match FastAPI's redirect behavior and avoid CORS issues
export const api = {
  // Datasets
  getDatasets: (params?: Record<string, string>) =>
    apiClient.get('/datasets/', { params }),

  getDataset: (id: string) =>
    apiClient.get(`/datasets/${id}/`),

  // Create dataset (POST to /datasets/, not /datasets/generate)
  generateDataset: (config: unknown) =>
    apiClient.post('/datasets/', config),

  downloadDataset: (id: string) =>
    apiClient.get(`/datasets/${id}/download/`, { responseType: 'blob' }),

  getDatasetObservations: (id: string, params?: { limit?: number; offset?: number }) =>
    apiClient.get(`/datasets/${id}/observations/`, { params }),

  deleteDataset: (id: string) =>
    apiClient.delete(`/datasets/${id}`),

  // Submissions
  getSubmissions: (params?: Record<string, string>) =>
    apiClient.get('/submissions/', { params }),

  getSubmission: (id: string) =>
    apiClient.get(`/submissions/${id}/`),

  createSubmission: (formData: FormData) =>
    apiClient.post('/submissions/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  uploadResults: (submissionId: string, formData: FormData) =>
    apiClient.post(`/submissions/${submissionId}/results/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  // Results
  getResults: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}/`),

  getDetailedMetrics: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}/metrics/`),

  getVisualizationData: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}/visualization/`),

  exportResults: (submissionId: string, format: 'pdf' | 'csv' | 'json') =>
    apiClient.get(`/results/${submissionId}/export/`, {
      params: { format },
      responseType: 'blob',
    }),

  // Leaderboard
  getLeaderboard: (params?: Record<string, string>) =>
    apiClient.get('/leaderboard/', { params }),

  getLeaderboardHistory: (params?: { dataset_id?: string; days?: number }) =>
    apiClient.get('/leaderboard/history/', { params }),

  getLeaderboardStatistics: (params?: { dataset_id?: string }) =>
    apiClient.get('/leaderboard/statistics/', { params }),

  // Jobs
  getJobStatus: (jobId: string) =>
    apiClient.get(`/jobs/${jobId}/`),

  listJobs: (params?: { job_type?: string; status?: string; limit?: number }) =>
    apiClient.get('/jobs/', { params }),

  // User
  getCurrentUser: () =>
    apiClient.get('/users/me/'),

  updateProfile: (data: unknown) =>
    apiClient.patch('/users/me/', data),

  // Auth
  login: (credentials: { email: string; password: string }) =>
    apiClient.post('/auth/login/', credentials),

  logout: () =>
    apiClient.post('/auth/logout/'),

  refreshToken: () =>
    apiClient.post('/auth/refresh/'),

  // ============================================================
  // UCTP Lab
  // ============================================================

  // Dashboard
  getUCTPDashboardStats: () =>
    apiClient.get('/uctp/dashboard/stats'),

  // Runs
  getUCTPRuns: (params?: { status?: string; dataset_id?: number; limit?: number; offset?: number }) =>
    apiClient.get('/uctp/runs/', { params }),

  createUCTPRun: (data: unknown) =>
    apiClient.post('/uctp/runs/', data),

  getUCTPRun: (runId: number) =>
    apiClient.get(`/uctp/runs/${runId}`),

  deleteUCTPRun: (runId: number) =>
    apiClient.delete(`/uctp/runs/${runId}`),

  getUCTPRunLogs: (runId: number) =>
    apiClient.get(`/uctp/runs/${runId}/logs`),

  compareUCTPRuns: (runIds: number[]) =>
    apiClient.get('/uctp/runs/compare/', { params: { run_ids: runIds.join(',') } }),

  // Models
  getUCTPModels: (params?: { status?: string; limit?: number }) =>
    apiClient.get('/uctp/models/', { params }),

  trainUCTPModel: (data: unknown) =>
    apiClient.post('/uctp/models/train', data),

  getUCTPModel: (modelId: number) =>
    apiClient.get(`/uctp/models/${modelId}`),

  deleteUCTPModel: (modelId: number) =>
    apiClient.delete(`/uctp/models/${modelId}`),

  evaluateUCTPModel: (modelId: number, datasetId: number) =>
    apiClient.post(`/uctp/models/${modelId}/evaluate`, null, { params: { dataset_id: datasetId } }),

  // Connectivity
  getConnectivity: () =>
    apiClient.get('/uctp/connectivity/'),

  testConnection: (serviceName: string) =>
    apiClient.post('/uctp/connectivity/test', { service_name: serviceName }),

  testAllConnections: () =>
    apiClient.post('/uctp/connectivity/test-all'),

  // Algorithm options
  getAlgorithmOptions: () =>
    apiClient.get('/uctp/algorithms/options'),

  // ============================================================
  // Credentials
  // ============================================================

  getCredentials: () =>
    apiClient.get('/credentials/'),

  getCredential: (serviceName: string) =>
    apiClient.get(`/credentials/${serviceName}`),

  saveCredential: (serviceName: string, data: { primary: string; secondary?: string }) =>
    apiClient.put(`/credentials/${serviceName}`, data),

  deleteCredential: (serviceName: string) =>
    apiClient.delete(`/credentials/${serviceName}`),

  testCredential: (serviceName: string) =>
    apiClient.post(`/credentials/${serviceName}/test`),

  generateEncryptionKey: () =>
    apiClient.post('/credentials/generate-key'),
};
