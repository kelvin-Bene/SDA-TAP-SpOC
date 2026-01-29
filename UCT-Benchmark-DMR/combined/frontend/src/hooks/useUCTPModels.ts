import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPModelSummary, UCTPModelDetail, UCTPModelTrainRequest } from '@/types/uctp';

export function useUCTPModels(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: ['uctp-models', params],
    queryFn: async () => {
      const res = await api.getUCTPModels(params);
      return res.data as UCTPModelSummary[];
    },
    staleTime: 1000 * 30,
  });
}

export function useUCTPModel(modelId: number | null) {
  return useQuery({
    queryKey: ['uctp-model', modelId],
    queryFn: async () => {
      if (!modelId) return null;
      const res = await api.getUCTPModel(modelId);
      return res.data as UCTPModelDetail;
    },
    enabled: modelId !== null,
    staleTime: 1000 * 15,
  });
}

export function useTrainUCTPModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UCTPModelTrainRequest) => {
      const res = await api.trainUCTPModel(data);
      return res.data as UCTPModelSummary;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-models'] });
      queryClient.invalidateQueries({ queryKey: ['uctp-dashboard-stats'] });
    },
  });
}

export function useDeleteUCTPModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: number) => {
      await api.deleteUCTPModel(modelId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-models'] });
    },
  });
}
