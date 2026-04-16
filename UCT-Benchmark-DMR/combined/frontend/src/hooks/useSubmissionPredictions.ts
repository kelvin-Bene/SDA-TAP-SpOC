import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { api } from '@/api/client';
import type { OrbitSatellite } from './useDatasetReferenceOrbits';

export interface SubmissionPredictionsData {
  submissionId: string;
  predicted: OrbitSatellite[];
  reference: OrbitSatellite[] | null;
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
  submission_id: string;
  predicted: RawSatellite[];
  reference: RawSatellite[] | null;
}

function parseSatellite(raw: RawSatellite): OrbitSatellite {
  return {
    id: raw.id,
    name: raw.name,
    regime: raw.regime,
    positions: raw.positions.map((p) => ({
      time: new Date(p.time),
      x: p.x,
      y: p.y,
      z: p.z,
    })),
    color: raw.color,
  };
}

export interface UseSubmissionPredictionsResult {
  data: SubmissionPredictionsData | undefined;
  isLoading: boolean;
  error: Error | null;
  notFound: boolean;
  gone: boolean;
}

export function useSubmissionPredictions(
  submissionId: string | undefined,
  options?: { enabled?: boolean; includeReference?: boolean; maxSamples?: number },
): UseSubmissionPredictionsResult {
  const enabled = Boolean(submissionId) && (options?.enabled ?? true);

  const query = useQuery<SubmissionPredictionsData, AxiosError>({
    queryKey: [
      'submission-predictions',
      submissionId,
      options?.includeReference ?? false,
      options?.maxSamples,
    ],
    queryFn: async () => {
      const params: Record<string, string | number> = {};
      if (options?.includeReference) params.include = 'reference';
      if (options?.maxSamples) params.max_samples = options.maxSamples;
      const response = await api.getSubmissionPredictions(submissionId!, params as { include?: string; max_samples?: number });
      const raw = response.data as RawResponse;
      return {
        submissionId: raw.submission_id,
        predicted: raw.predicted.map(parseSatellite),
        reference: raw.reference ? raw.reference.map(parseSatellite) : null,
      };
    },
    enabled,
    retry: (failureCount, error) => {
      const status = error?.response?.status;
      if (status === 404 || status === 410) return false;
      return failureCount < 2;
    },
    staleTime: 5 * 60 * 1000,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error ?? null,
    notFound: query.error?.response?.status === 404,
    gone: query.error?.response?.status === 410,
  };
}
