import { useQuery, UseQueryOptions } from '@tanstack/react-query';

/**
 * Generic polling configuration.
 */
export interface PollingConfig<TData> {
  /** Query key for React Query caching */
  queryKey: unknown[];
  /** Function to fetch data */
  queryFn: () => Promise<TData>;
  /** Whether polling is enabled */
  enabled?: boolean;
  /** Polling interval in milliseconds (default: 2000) */
  intervalMs?: number;
  /** Function to determine if polling should continue based on data */
  shouldContinue?: (data: TData | null | undefined) => boolean;
  /** Stale time in milliseconds (default: 0) */
  staleTime?: number;
}

/**
 * Generic polling hook for status checks.
 *
 * This hook consolidates the polling logic used in useJobStatus and
 * useSubmissionStatus into a reusable utility.
 *
 * @example
 * // Poll for job status until completed or failed
 * const { data, isLoading } = usePolling({
 *   queryKey: ['job', jobId],
 *   queryFn: () => api.getJobStatus(jobId),
 *   enabled: !!jobId,
 *   shouldContinue: (data) => data?.status === 'running' || data?.status === 'pending',
 * });
 */
export function usePolling<TData>({
  queryKey,
  queryFn,
  enabled = true,
  intervalMs = 2000,
  shouldContinue,
  staleTime = 0,
}: PollingConfig<TData>) {
  return useQuery({
    queryKey,
    queryFn,
    enabled,
    staleTime,
    refetchInterval: (query) => {
      if (shouldContinue) {
        const data = query.state.data as TData | null | undefined;
        return shouldContinue(data) ? intervalMs : false;
      }
      return intervalMs;
    },
  } as UseQueryOptions<TData, Error, TData, unknown[]>);
}

/**
 * Predefined status check functions for common use cases.
 */
export const StatusChecks = {
  /**
   * Check if a job is still running (pending or running status).
   */
  isJobRunning: <T extends { status?: string }>(data: T | null | undefined): boolean => {
    return data?.status === 'running' || data?.status === 'pending';
  },

  /**
   * Check if a submission is still processing.
   */
  isSubmissionProcessing: <T extends { status?: string }>(data: T | null | undefined): boolean => {
    return (
      data?.status === 'queued' ||
      data?.status === 'validating' ||
      data?.status === 'processing'
    );
  },

  /**
   * Check if any status is in a "pending" state.
   */
  isPending: <T extends { status?: string }>(
    pendingStatuses: string[]
  ): ((data: T | null | undefined) => boolean) => {
    return (data) => !!data?.status && pendingStatuses.includes(data.status);
  },
};
