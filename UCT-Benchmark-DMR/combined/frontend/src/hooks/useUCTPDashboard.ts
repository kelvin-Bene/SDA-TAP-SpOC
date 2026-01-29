import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { UCTPDashboardStats } from '@/types/uctp';

export function useUCTPDashboard() {
  return useQuery({
    queryKey: ['uctp-dashboard-stats'],
    queryFn: async () => {
      const res = await api.getUCTPDashboardStats();
      return res.data as UCTPDashboardStats;
    },
    staleTime: 1000 * 15,
  });
}
