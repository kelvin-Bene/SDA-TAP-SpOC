import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

interface JobUpdate {
  id: number;
  job_type: string;
  status: string;
  progress: number | null;
  result: unknown;
  error_message: string | null;
}

/**
 * Subscribe to real-time job status changes via Supabase Realtime.
 *
 * When Supabase is configured, this hook listens for INSERT and UPDATE
 * events on the `jobs` table and invalidates the relevant React Query
 * cache entries so the UI updates automatically — replacing polling.
 *
 * When Supabase is not configured (supabase === null), the hook is a
 * no-op and the existing polling in useDatasets / useUCTPRuns continues
 * to work as before.
 *
 * @param onJobUpdate Optional callback invoked with the changed row.
 */
export function useRealtimeJobs(onJobUpdate?: (job: JobUpdate) => void) {
  const queryClient = useQueryClient();
  const callbackRef = useRef(onJobUpdate);
  callbackRef.current = onJobUpdate;

  const invalidateJobQueries = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['jobs'] });
    queryClient.invalidateQueries({ queryKey: ['datasets'] });
    queryClient.invalidateQueries({ queryKey: ['uctp-runs'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
  }, [queryClient]);

  useEffect(() => {
    if (!supabase) return;

    const channel = supabase
      .channel('jobs-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'jobs',
        },
        (payload: any) => {
          invalidateJobQueries();
          if (callbackRef.current) {
            callbackRef.current(payload.new as JobUpdate);
          }
        },
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'jobs',
        },
        (payload: any) => {
          invalidateJobQueries();
          if (callbackRef.current) {
            callbackRef.current(payload.new as JobUpdate);
          }
        },
      )
      .subscribe();

    return () => {
      supabase!.removeChannel(channel);
    };
  }, [invalidateJobQueries]);
}
