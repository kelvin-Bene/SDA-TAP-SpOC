import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
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
export const api = {
  // Datasets
  getDatasets: (params?: Record<string, string>) =>
    apiClient.get('/datasets', { params }),

  getDataset: (id: string) =>
    apiClient.get(`/datasets/${id}`),

  generateDataset: (config: unknown) =>
    apiClient.post('/datasets/generate', config),

  downloadDataset: (id: string) =>
    apiClient.get(`/datasets/${id}/download`, { responseType: 'blob' }),

  // Submissions
  getSubmissions: (params?: Record<string, string>) =>
    apiClient.get('/submissions', { params }),

  getSubmission: (id: string) =>
    apiClient.get(`/submissions/${id}`),

  createSubmission: (formData: FormData) =>
    apiClient.post('/submissions', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  // Results
  getResults: (submissionId: string) =>
    apiClient.get(`/results/${submissionId}`),

  exportResults: (submissionId: string, format: 'pdf' | 'csv' | 'json') =>
    apiClient.get(`/results/${submissionId}/export`, {
      params: { format },
      responseType: 'blob',
    }),

  // Leaderboard
  getLeaderboard: (params?: Record<string, string>) =>
    apiClient.get('/leaderboard', { params }),

  // User
  getCurrentUser: () =>
    apiClient.get('/users/me'),

  updateProfile: (data: unknown) =>
    apiClient.patch('/users/me', data),

  // Auth
  login: (credentials: { email: string; password: string }) =>
    apiClient.post('/auth/login', credentials),

  logout: () =>
    apiClient.post('/auth/logout'),

  refreshToken: () =>
    apiClient.post('/auth/refresh'),
};
