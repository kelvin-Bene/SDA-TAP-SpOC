import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPRunSummary, UCTPRunDetail, UCTPRunCreate, UCTPRunComparison } from '@/types/uctp';

export function useUCTPRuns(params?: { status?: string; dataset_id?: number; limit?: number }) {
  return useQuery({
    queryKey: ['uctp-runs', params],
    queryFn: async () => {
      const res = await api.getUCTPRuns(params);
      return res.data as UCTPRunSummary[];
    },
    staleTime: 1000 * 10,
  });
}

export function useUCTPRun(runId: number | null) {
  return useQuery({
    queryKey: ['uctp-run', runId],
    queryFn: async () => {
      if (!runId) return null;
      const res = await api.getUCTPRun(runId);
      return res.data as UCTPRunDetail;
    },
    enabled: runId !== null,
    staleTime: 1000 * 5,
  });
}

export function useUCTPRunComparison(runIds: number[]) {
  return useQuery({
    queryKey: ['uctp-run-comparison', runIds],
    queryFn: async () => {
      const res = await api.compareUCTPRuns(runIds);
      return res.data as UCTPRunComparison;
    },
    enabled: runIds.length >= 2,
    staleTime: 1000 * 30,
  });
}

export function useCreateUCTPRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UCTPRunCreate) => {
      const res = await api.createUCTPRun(data);
      return res.data as UCTPRunSummary;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-runs'] });
      queryClient.invalidateQueries({ queryKey: ['uctp-dashboard-stats'] });
    },
  });
}

export function useDeleteUCTPRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: number) => {
      await api.deleteUCTPRun(runId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-runs'] });
      queryClient.invalidateQueries({ queryKey: ['uctp-dashboard-stats'] });
    },
  });
}
