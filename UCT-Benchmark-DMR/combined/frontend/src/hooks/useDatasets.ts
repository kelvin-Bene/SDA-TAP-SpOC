import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Dataset, DatasetFilters, DatasetGenerationConfig } from '@/types';

// Maximum timeframe allowed by the backend (in days)
// This should match the backend's Pydantic validation in DatasetCreate model
export const MAX_TIMEFRAME_DAYS = 90;

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
      console.log('=== useGenerateDataset mutationFn called ===');
      console.log('Input config:', config);
      console.log('config.startDate:', config.startDate, 'type:', typeof config.startDate);
      console.log('config.endDate:', config.endDate, 'type:', typeof config.endDate);

      // Transform frontend config to backend format
      const startDate = new Date(config.startDate);
      const endDate = new Date(config.endDate);

      console.log('Parsed startDate:', startDate, 'ISO:', startDate.toISOString());
      console.log('Parsed endDate:', endDate, 'ISO:', endDate.toISOString());

      // Validate dates
      if (isNaN(startDate.getTime())) {
        console.error('Invalid start date!');
        throw new Error(`Invalid start date: ${config.startDate}`);
      }
      if (isNaN(endDate.getTime())) {
        console.error('Invalid end date!');
        throw new Error(`Invalid end date: ${config.endDate}`);
      }

      const timeframeDays = Math.ceil(
        (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
      );

      // Validate timeframe is within allowed range
      if (timeframeDays < 1) {
        throw new Error('End date must be after start date (timeframe must be at least 1 day)');
      }
      if (timeframeDays > MAX_TIMEFRAME_DAYS) {
        throw new Error(
          `Date range exceeds maximum of ${MAX_TIMEFRAME_DAYS} days (currently ${timeframeDays} days). ` +
          `Please select a shorter date range.`
        );
      }

      // Timeframe is valid
      const validTimeframe = timeframeDays;

      // Determine tier based on downsampling/simulation settings
      let tier = 'T1';
      if (config.downsampling?.enabled) {
        tier = 'T2';
      }
      if (config.simulation?.enabled) {
        tier = 'T3';
      }

      const backendConfig: Record<string, unknown> = {
        name: `${config.regime}-${config.coverage}-${new Date().toISOString().split('T')[0]}`,
        regime: config.regime,
        tier: tier,
        object_count: config.objectCount,
        timeframe: validTimeframe,
        timeunit: 'days',
        sensors: config.sensors,
        coverage: config.coverage,
        include_hamr: config.includeHamr,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        // Search strategy
        search_strategy: config.searchStrategy || 'hybrid',
      };

      // Add window size if using windowed strategy
      if (config.searchStrategy === 'windowed') {
        backendConfig.window_size_minutes = config.windowSizeMinutes || 10;
      }

      // Add downsampling options if enabled
      if (config.downsampling?.enabled) {
        backendConfig.downsampling = {
          enabled: true,
          target_coverage: config.downsampling.targetCoverage,
          target_gap: config.downsampling.targetGap,
          max_obs_per_sat: config.downsampling.maxObsPerSat,
          preserve_tracks: config.downsampling.preserveTracks,
          seed: config.downsampling.seed,
        };
      }

      // Add simulation options if enabled
      if (config.simulation?.enabled) {
        backendConfig.simulation = {
          enabled: true,
          fill_gaps: config.simulation.fillGaps,
          sensor_model: config.simulation.sensorModel,
          apply_noise: config.simulation.applyNoise,
          max_synthetic_ratio: config.simulation.maxSyntheticRatio,
          seed: config.simulation.seed,
        };
      }

      console.log('Frontend config:', config);
      console.log('Sending to backend:', JSON.stringify(backendConfig, null, 2));
      console.log('Raw JSON:', JSON.stringify(backendConfig));

      try {
        const response = await api.generateDataset(backendConfig);
        console.log('Success! Response:', response);
        return response.data;
      } catch (err: any) {
        console.error('API Error:', err);
        console.error('Error response data:', JSON.stringify(err?.response?.data, null, 2));
        console.error('Error response status:', err?.response?.status);
        throw err;
      }
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

export function useDeleteDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.deleteDataset(id);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch datasets list
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

// Hook for polling job status
interface JobStatus {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  stage?: string;  // Current stage description from backend
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
