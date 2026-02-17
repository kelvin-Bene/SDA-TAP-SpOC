import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { ConnectorStatus, ConnectivityReport } from '@/types/uctp';

export function useAPIConnectivity() {
  return useQuery({
    queryKey: ['uctp-connectivity'],
    queryFn: async () => {
      const res = await api.getConnectivity();
      return res.data as ConnectorStatus[];
    },
    staleTime: 1000 * 60,
  });
}

export function useTestConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (serviceName: string) => {
      const res = await api.testConnection(serviceName);
      return res.data as ConnectorStatus;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-connectivity'] });
    },
  });
}

export function useTestAllConnections() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await api.testAllConnections();
      return res.data as ConnectivityReport;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['uctp-connectivity'] });
      queryClient.invalidateQueries({ queryKey: ['uctp-dashboard-stats'] });
    },
  });
}
