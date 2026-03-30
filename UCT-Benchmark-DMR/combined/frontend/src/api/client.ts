import axios from 'axios';
import { supabase } from '@/lib/supabase';
import { getMockResponse } from './mockData';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token - uses Supabase session JWT
apiClient.interceptors.request.use(
  async (config) => {
    if (!supabase) return config;
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
  (error) => {
    return Promise.reject(error);
  }
);

// U11: Token refresh mutex — prevents parallel 401 responses from triggering
// multiple concurrent refresh attempts
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Another request is already refreshing — queue this one
        return new Promise((resolve) => {
          addRefreshSubscriber((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            originalRequest._retry = true;
            resolve(apiClient(originalRequest));
          });
        });
      }

      isRefreshing = true;
      originalRequest._retry = true;

      try {
        if (!supabase) return Promise.reject(error);
        const { data, error: refreshError } = await supabase.auth.refreshSession();
        if (refreshError || !data.session) {
          await supabase.auth.signOut();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        const newToken = data.session.access_token;
        onRefreshed(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch {
        if (supabase) await supabase.auth.signOut();
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Demo-mode interceptor: when Supabase is null (no env vars) AND a request
// fails with a network error (no backend), return realistic mock data so the
// UI is fully populated for symposium demos.
// ---------------------------------------------------------------------------
const isDemoMode = !supabase;

if (isDemoMode) {
  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      // Only intercept network / connection errors (no response from server)
      const isNetworkError = !error.response;
      if (!isNetworkError) return Promise.reject(error);

      const url = error.config?.url || '';
      const method = error.config?.method || 'get';
      const mock = getMockResponse(url, method);

      if (mock) {
        console.debug(`[Demo Mode] Serving mock data for ${method.toUpperCase()} ${url}`);
        return Promise.resolve({
          data: mock.data,
          status: mock.status,
          statusText: 'OK',
          headers: {},
          config: error.config,
        });
      }

      // No mock available — let it fail normally
      return Promise.reject(error);
    }
  );
}

// API helper functions
// List endpoints use trailing slash (backend defines them as @router.get("/"))
// Detail/sub-resource endpoints do NOT use trailing slash (avoids 307 redirect → http:// → 503)
export const api = {
  // Datasets
  getDatasetConfig: () =>
    apiClient.get('/datasets/config'),

  getDatasets: (params?: Record<string, string>) =>
    apiClient.get('/datasets/', { params }),

  getDataset: (id: string) =>
    apiClient.get(`/datasets/${id}`),

  generateDataset: (config: unknown) =>
    apiClient.post('/datasets/', config),

  downloadDataset: (id: string) =>
    apiClient.get(`/datasets/${id}/download`, { responseType: 'blob' }),

  getDatasetObservations: (id: string, params?: { limit?: number; offset?: number }) =>
    apiClient.get(`/datasets/${id}/observations`, { params }),

  deleteDataset: (id: string) =>
    apiClient.delete(`/datasets/${id}`),

  getDatasetVersions: (id: string) =>
    apiClient.get(`/datasets/${id}/versions`),

  // Submissions
  getSubmissions: (params?: Record<string, string>) =>
    apiClient.get('/submissions/', { params }),

  getSubmission: (id: string) =>
    apiClient.get(`/submissions/${id}`),

  createSubmission: (formData: FormData) =>
    apiClient.post('/submissions/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  uploadResults: (submissionId: string, formData: FormData) =>
    apiClient.post(`/submissions/${submissionId}/results`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  // Results
  getResults: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}`),

  getDetailedMetrics: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}/metrics`),

  getVisualizationData: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}/visualization`),

  exportResults: (submissionId: string, format: 'pdf' | 'csv' | 'json') =>
    apiClient.get(`/results/${submissionId}/export`, {
      params: { format },
      responseType: 'blob',
    }),

  downloadReport: (submissionId: string, format: 'pdf' | 'html' | 'json' = 'pdf') =>
    apiClient.get(`/results/${submissionId}/report`, {
      params: { format },
      responseType: 'blob',
    }),

  // Leaderboard
  getLeaderboard: (params?: Record<string, string>) =>
    apiClient.get('/leaderboard/', { params }),

  getLeaderboardHistory: (params?: { dataset_id?: string; days?: number }) =>
    apiClient.get('/leaderboard/history', { params }),

  getLeaderboardStatistics: (params?: { dataset_id?: string }) =>
    apiClient.get('/leaderboard/statistics', { params }),

  // Jobs
  getJobStatus: (jobId: string) =>
    apiClient.get(`/jobs/${jobId}`),

  listJobs: (params?: { job_type?: string; status?: string; limit?: number }) =>
    apiClient.get('/jobs/', { params }),

  // User
  getCurrentUser: () =>
    apiClient.get('/auth/me'),

  updateProfile: (data: unknown) =>
    apiClient.patch('/auth/me', data),

  // Auth
  login: (credentials: { email: string; password: string }) =>
    apiClient.post('/auth/login', credentials),

  logout: () =>
    apiClient.post('/auth/logout'),

  refreshToken: () =>
    apiClient.post('/auth/refresh'),
};
