import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { api } from '@/api/client';

export interface OrbitPosition {
  time: Date;
  x: number;
  y: number;
  z: number;
}

export interface OrbitSatellite {
  id: string;
  name: string;
  regime: 'LEO' | 'MEO' | 'GEO' | 'HEO';
  positions: OrbitPosition[];
  color?: string;
}

export interface ReferenceOrbitsData {
  datasetId: string;
  startTime: Date;
  endTime: Date;
  satellites: OrbitSatellite[];
}

interface RawPosition {
  time: string;
  x: number;
  y: number;
  z: number;
}

interface RawSatellite {
  id: string;
  name: string;
  regime: OrbitSatellite['regime'];
  positions: RawPosition[];
  color?: string;
}

interface RawResponse {
  dataset_id: string;
  start_time: string;
  end_time: string;
  satellites: RawSatellite[];
}

function parseDate(iso: string): Date {
  return new Date(iso);
}

export interface UseDatasetReferenceOrbitsResult {
  data: ReferenceOrbitsData | undefined;
  isLoading: boolean;
  error: Error | null;
  forbidden: boolean;
}

/**
 * Fetch time-sampled reference orbits for a dataset.
 *
 * Reference orbits are the dataset answer key; the backend returns 403 for
 * non-owner, non-admin users. We surface that as `forbidden: true` so the
 * caller can hide the entire 3D section rather than showing an error.
 */
export function useDatasetReferenceOrbits(
  datasetId: string | undefined,
  options?: { enabled?: boolean; maxSamples?: number },
): UseDatasetReferenceOrbitsResult {
  const enabled = Boolean(datasetId) && (options?.enabled ?? true);

  const query = useQuery<ReferenceOrbitsData, AxiosError>({
    queryKey: ['dataset-reference-orbits', datasetId, options?.maxSamples],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.maxSamples) params.max_samples = options.maxSamples;
      const response = await api.getDatasetReferenceOrbits(datasetId!, params as { max_samples?: number });
      const raw = response.data as RawResponse;
      return {
        datasetId: raw.dataset_id,
        startTime: parseDate(raw.start_time),
        endTime: parseDate(raw.end_time),
        satellites: raw.satellites.map((s) => ({
          id: s.id,
          name: s.name,
          regime: s.regime,
          positions: s.positions.map((p) => ({
            time: parseDate(p.time),
            x: p.x,
            y: p.y,
            z: p.z,
          })),
          color: s.color,
        })),
      };
    },
    enabled,
    retry: (failureCount, error) => {
      // Don't retry 403 — the user is not authorized; no point hammering.
      if (error?.response?.status === 403) return false;
      return failureCount < 2;
    },
    staleTime: 5 * 60 * 1000, // 5 min — reference orbits are stable per dataset
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error ?? null,
    forbidden: query.error?.response?.status === 403,
  };
}
