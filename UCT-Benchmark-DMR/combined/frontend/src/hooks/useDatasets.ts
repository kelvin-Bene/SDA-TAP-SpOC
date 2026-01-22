import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Dataset, DatasetFilters, DatasetGenerationConfig } from '@/types';

// Response type from backend
interface DatasetResponse {
  id: string;
  name: string;
  description?: string;
  regime: string;
  tier: string;
  status: string;
  created_at: string;
  observation_count: number;
  satellite_count: number;
  coverage: number;
  size_bytes: number;
  sensor_types: string[];
  job_id?: string;
}

// Transform backend response to frontend type
function transformDataset(data: DatasetResponse): Dataset {
  return {
    id: data.id,
    name: data.name,
    description: data.description,
    regime: data.regime as Dataset['regime'],
    tier: data.tier as Dataset['tier'],
    createdAt: data.created_at,
    objectCount: data.satellite_count,
    observationCount: data.observation_count,
    coverage: data.coverage,
    sizeBytes: data.size_bytes,
    sensorTypes: data.sensor_types as Dataset['sensorTypes'],
  };
}

export function useDatasets(filters?: DatasetFilters) {
  return useQuery({
    queryKey: ['datasets', filters],
    queryFn: async () => {
      // Build query params from filters
      const params: Record<string, string> = {};
      if (filters?.regime && filters.regime !== 'all') {
        params.regime = filters.regime;
      }
      if (filters?.tier && filters.tier !== 'all') {
        params.tier = filters.tier;
      }

      const response = await api.getDatasets(params);
      const datasets = response.data as DatasetResponse[];

      // Transform and filter
      return datasets
        .map(transformDataset)
        .filter((d) => {
          // Additional client-side filtering if needed
          if (filters?.sensor && filters.sensor !== 'all') {
            return d.sensorTypes.includes(filters.sensor);
          }
          return true;
        });
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: ['dataset', id],
    queryFn: async () => {
      const response = await api.getDataset(id);
      return transformDataset(response.data as DatasetResponse);
    },
    enabled: !!id,
  });
}

export function useGenerateDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (config: DatasetGenerationConfig) => {
      // Transform frontend config to backend format
      const backendConfig = {
        name: `${config.regime}-${config.coverage}-${new Date().toISOString().split('T')[0]}`,
        regime: config.regime,
        tier: 'T1', // Default tier, could be added to DatasetGenerationConfig
        object_count: config.objectCount,
        timeframe: Math.ceil(
          (new Date(config.endDate).getTime() - new Date(config.startDate).getTime()) /
            (1000 * 60 * 60 * 24)
        ),
        timeunit: 'days',
        sensors: config.sensors,
        coverage: config.coverage,
        include_hamr: config.includeHamr,
        start_date: config.startDate,
        end_date: config.endDate,
      };

      const response = await api.generateDataset(backendConfig);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useDownloadDataset() {
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.downloadDataset(id);
      return response.data;
    },
  });
}

// Hook for polling job status
interface JobStatus {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  result?: unknown;
  error?: string;
}

export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      if (!jobId) return null;
      const response = await api.getJobStatus(jobId);
      return response.data as JobStatus;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as JobStatus | null | undefined;
      // Poll every 2 seconds while running, stop when done
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000;
      }
      return false;
    },
  });
}

// Hook for dataset observations
interface DatasetObservation {
  id: string;
  ob_time: string;
  ra: number;
  declination: number;
  sensor_name?: string;
  track_id?: string;
}

interface ObservationsResponse {
  dataset_id: string;
  total_count: number;
  limit: number;
  offset: number;
  observations: DatasetObservation[];
}

export function useDatasetObservations(
  datasetId: string,
  options?: { limit?: number; offset?: number }
) {
  return useQuery({
    queryKey: ['dataset-observations', datasetId, options],
    queryFn: async () => {
      const response = await api.getDatasetObservations(datasetId, options);
      return response.data as ObservationsResponse;
    },
    enabled: !!datasetId,
  });
}
