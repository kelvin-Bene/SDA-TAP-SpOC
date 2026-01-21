import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Dataset, DatasetFilters, DatasetGenerationConfig } from '@/types';

export function useDatasets(filters?: DatasetFilters) {
  return useQuery({
    queryKey: ['datasets', filters],
    queryFn: async () => {
      // Mock data for now - replace with API call when backend is ready
      // const response = await api.getDatasets(filters);
      // return response.data;

      // Mock data
      const mockDatasets: Dataset[] = [
        {
          id: '1',
          name: 'LEO-T1-2026-01-15',
          regime: 'LEO',
          tier: 'T1',
          createdAt: '2026-01-15T08:00:00Z',
          objectCount: 42,
          observationCount: 12456,
          coverage: 0.78,
          sizeBytes: 2.3 * 1024 * 1024,
          sensorTypes: ['optical', 'radar'],
        },
        {
          id: '2',
          name: 'MEO-T2-2026-01-14',
          regime: 'MEO',
          tier: 'T2',
          createdAt: '2026-01-14T10:00:00Z',
          objectCount: 38,
          observationCount: 8234,
          coverage: 0.45,
          sizeBytes: 1.8 * 1024 * 1024,
          sensorTypes: ['optical'],
        },
      ];

      // Apply filters
      return mockDatasets.filter((d) => {
        if (filters?.regime && filters.regime !== 'all' && d.regime !== filters.regime) return false;
        if (filters?.tier && filters.tier !== 'all' && d.tier !== filters.tier) return false;
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

export function useDownloadDataset() {
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await api.downloadDataset(id);
      return response.data;
    },
  });
}
