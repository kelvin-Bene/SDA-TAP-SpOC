import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDatasets } from '@/hooks/useDatasets';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import { useSubmissions } from '@/hooks/useSubmissions';

// Mock supabase (required by api/client)
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
      refreshSession: vi.fn(),
      signOut: vi.fn(),
    },
  },
}));

// Mock the API client
vi.mock('@/api/client', () => ({
  api: {
    getDatasets: vi.fn(),
    getLeaderboard: vi.fn(),
    getSubmissions: vi.fn(),
  },
  apiClient: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

// Import mock after vi.mock so we can control return values
import { api } from '@/api/client';

const mockApi = api as {
  getDatasets: ReturnType<typeof vi.fn>;
  getLeaderboard: ReturnType<typeof vi.fn>;
  getSubmissions: ReturnType<typeof vi.fn>;
};

// Create a wrapper with QueryClientProvider for renderHook
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('useDatasets', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns loading state initially', () => {
    // Make the API hang so we observe the loading state
    mockApi.getDatasets.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useDatasets(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('transforms API response correctly', async () => {
    const apiResponse = [
      {
        id: '42',
        name: 'LEO Test Dataset',
        description: 'A test dataset',
        regime: 'LEO',
        tier: 'T1',
        status: 'available',
        created_at: '2026-01-15T00:00:00Z',
        observation_count: 5000,
        satellite_count: 25,
        coverage: 0.85,
        size_bytes: 1048576,
        sensor_types: ['optical', 'radar'],
        version: 1,
        parent_id: null,
        error_message: null,
      },
    ];

    mockApi.getDatasets.mockResolvedValue({ data: apiResponse });

    const { result } = renderHook(() => useDatasets(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(1);
    const dataset = result.current.data![0];
    // Verify snake_case -> camelCase transform
    expect(dataset.id).toBe('42');
    expect(dataset.name).toBe('LEO Test Dataset');
    expect(dataset.regime).toBe('LEO');
    expect(dataset.tier).toBe('T1');
    expect(dataset.status).toBe('available');
    expect(dataset.createdAt).toBe('2026-01-15T00:00:00Z');
    expect(dataset.observationCount).toBe(5000);
    expect(dataset.objectCount).toBe(25);
    expect(dataset.coverage).toBe(0.85);
    expect(dataset.sizeBytes).toBe(1048576);
    expect(dataset.sensorTypes).toEqual(['optical', 'radar']);
  });
});

describe('useLeaderboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('transforms entries with team fallback to Independent', async () => {
    const apiResponse = {
      dataset_id: 'ds-1',
      dataset_name: 'LEO T1',
      last_updated: '2026-03-01T00:00:00Z',
      total_entries: 2,
      entries: [
        {
          rank: 1,
          algorithm_name: 'AlphaOD',
          team: 'MIT Lab',
          version: '2.0',
          f1_score: 0.95,
          precision: 0.96,
          recall: 0.94,
          position_rms_km: 5.2,
          submission_id: 'sub-1',
          submitted_at: '2026-02-15T00:00:00Z',
          is_current_user: false,
        },
        {
          rank: 2,
          algorithm_name: 'SoloTracker',
          // team is missing -- should fall back to 'Independent'
          version: '1.0',
          f1_score: 0.88,
          precision: 0.90,
          recall: 0.86,
          position_rms_km: 8.1,
          submission_id: 'sub-2',
          submitted_at: '2026-02-20T00:00:00Z',
          is_current_user: true,
        },
      ],
    };

    mockApi.getLeaderboard.mockResolvedValue({ data: apiResponse });

    const { result } = renderHook(() => useLeaderboard(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);

    // Entry with explicit team
    expect(result.current.data![0].algorithmName).toBe('AlphaOD');
    expect(result.current.data![0].team).toBe('MIT Lab');
    expect(result.current.data![0].f1Score).toBe(0.95);
    expect(result.current.data![0].positionRmsKm).toBe(5.2);

    // Entry without team -- should default to 'Independent'
    expect(result.current.data![1].algorithmName).toBe('SoloTracker');
    expect(result.current.data![1].team).toBe('Independent');
    expect(result.current.data![1].isCurrentUser).toBe(true);
  });
});

describe('useSubmissions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('transforms submission data from snake_case to camelCase', async () => {
    const apiResponse = [
      {
        id: 'sub-100',
        dataset_id: 'ds-5',
        dataset_name: 'GEO T2 Full',
        algorithm_name: 'MyAlgo',
        version: '3.1',
        status: 'completed',
        created_at: '2026-03-10T12:00:00Z',
        completed_at: '2026-03-10T12:05:00Z',
        score: 0.92,
        rank: 3,
        queue_position: undefined,
      },
      {
        id: 'sub-101',
        dataset_id: 'ds-5',
        // dataset_name is missing -- should fallback
        algorithm_name: 'AnotherAlgo',
        version: '1.0',
        status: 'queued',
        created_at: '2026-03-11T08:00:00Z',
        completed_at: undefined,
        score: undefined,
        queue_position: 2,
      },
    ];

    mockApi.getSubmissions.mockResolvedValue({ data: apiResponse });

    const { result } = renderHook(() => useSubmissions(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toHaveLength(2);

    // Completed submission
    const completed = result.current.data![0];
    expect(completed.id).toBe('sub-100');
    expect(completed.datasetId).toBe('ds-5');
    expect(completed.datasetName).toBe('GEO T2 Full');
    expect(completed.algorithmName).toBe('MyAlgo');
    expect(completed.version).toBe('3.1');
    expect(completed.status).toBe('completed');
    expect(completed.createdAt).toBe('2026-03-10T12:00:00Z');
    expect(completed.completedAt).toBe('2026-03-10T12:05:00Z');
    expect(completed.results).toBeDefined();
    expect(completed.results!.f1Score).toBe(0.92);

    // Queued submission without dataset_name
    const queued = result.current.data![1];
    expect(queued.datasetName).toBe('Dataset ds-5');
    expect(queued.status).toBe('queued');
    expect(queued.queuePosition).toBe(2);
    expect(queued.results).toBeUndefined();
  });
});
