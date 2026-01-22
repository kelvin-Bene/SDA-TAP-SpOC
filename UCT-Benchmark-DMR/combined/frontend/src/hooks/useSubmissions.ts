import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Submission, SubmissionForm, SubmissionResults } from '@/types';

// Response types from backend
interface SubmissionResponse {
  id: string;
  dataset_id: string;
  dataset_name?: string;
  algorithm_name: string;
  version: string;
  status: string;
  created_at: string;
  completed_at?: string;
  score?: number;
  job_id?: string;
  queue_position?: number;
}

interface ResultsResponse {
  submission_id: string;
  dataset_id: string;
  algorithm_name: string;
  status: string;
  completed_at?: string;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  position_rms_km: number;
  velocity_rms_km_s: number;
  mahalanobis_distance?: number;
  ra_residual_rms_arcsec?: number;
  dec_residual_rms_arcsec?: number;
  satellite_results: Array<{
    satellite_id: string;
    status: string;
    observations_used: number;
    total_observations: number;
    position_error_km?: number;
    velocity_error_km_s?: number;
    confidence?: number;
  }>;
  rank?: number;
  previous_rank?: number;
  processing_time_seconds?: number;
}

// Transform backend response to frontend type
function transformSubmission(data: SubmissionResponse): Submission {
  return {
    id: data.id,
    datasetId: data.dataset_id,
    datasetName: data.dataset_name || `Dataset ${data.dataset_id}`,
    algorithmName: data.algorithm_name,
    version: data.version,
    status: data.status as Submission['status'],
    createdAt: data.created_at,
    completedAt: data.completed_at,
    queuePosition: data.queue_position,
    results: data.score !== undefined ? {
      truePositives: 0,
      falsePositives: 0,
      falseNegatives: 0,
      precision: 0,
      recall: 0,
      f1Score: data.score,
      positionRmsKm: 0,
      velocityRmsKmS: 0,
      mahalanobisDistance: 0,
      raResidualRmsArcsec: 0,
      decResidualRmsArcsec: 0,
      satelliteResults: [],
      rank: 0,
    } : undefined,
  };
}

function transformResults(data: ResultsResponse): SubmissionResults {
  return {
    truePositives: data.true_positives,
    falsePositives: data.false_positives,
    falseNegatives: data.false_negatives,
    precision: data.precision,
    recall: data.recall,
    f1Score: data.f1_score,
    positionRmsKm: data.position_rms_km,
    velocityRmsKmS: data.velocity_rms_km_s,
    mahalanobisDistance: data.mahalanobis_distance || 0,
    raResidualRmsArcsec: data.ra_residual_rms_arcsec || 0,
    decResidualRmsArcsec: data.dec_residual_rms_arcsec || 0,
    satelliteResults: data.satellite_results.map((sr) => ({
      satelliteId: sr.satellite_id,
      status: sr.status as 'TP' | 'FP' | 'FN',
      observationsUsed: sr.observations_used,
      totalObservations: sr.total_observations,
      positionErrorKm: sr.position_error_km,
      velocityErrorKmS: sr.velocity_error_km_s,
      confidence: sr.confidence,
    })),
    rank: data.rank || 0,
    previousRank: data.previous_rank,
  };
}

export function useSubmissions(filters?: { datasetId?: string; status?: string }) {
  return useQuery({
    queryKey: ['submissions', filters],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filters?.datasetId) {
        params.dataset_id = filters.datasetId;
      }
      if (filters?.status) {
        params.status = filters.status;
      }

      const response = await api.getSubmissions(params);
      const submissions = response.data as SubmissionResponse[];
      return submissions.map(transformSubmission);
    },
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useSubmission(id: string) {
  return useQuery({
    queryKey: ['submission', id],
    queryFn: async () => {
      const response = await api.getSubmission(id);
      return transformSubmission(response.data as SubmissionResponse);
    },
    enabled: !!id,
  });
}

export function useCreateSubmission() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SubmissionForm) => {
      const formData = new FormData();
      formData.append('file', data.file);
      formData.append('dataset_id', data.datasetId);
      formData.append('algorithm_name', data.algorithmName);
      formData.append('version', data.version);
      if (data.description) {
        formData.append('description', data.description);
      }

      const response = await api.createSubmission(formData);
      return response.data as SubmissionResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['submissions'] });
    },
  });
}

export function useResults(submissionId: string) {
  return useQuery({
    queryKey: ['results', submissionId],
    queryFn: async () => {
      const response = await api.getResults(submissionId);
      return transformResults(response.data as ResultsResponse);
    },
    enabled: !!submissionId,
  });
}

// Hook for polling submission status during processing
export function useSubmissionStatus(submissionId: string | null) {
  return useQuery({
    queryKey: ['submission-status', submissionId],
    queryFn: async () => {
      if (!submissionId) return null;
      const response = await api.getSubmission(submissionId);
      return transformSubmission(response.data as SubmissionResponse);
    },
    enabled: !!submissionId,
    refetchInterval: (query) => {
      const data = query.state.data as Submission | null | undefined;
      // Poll every 3 seconds while processing, stop when done
      if (data?.status === 'queued' || data?.status === 'validating' || data?.status === 'processing') {
        return 3000;
      }
      return false;
    },
  });
}

// Hook for detailed metrics
interface DetailedMetrics {
  submission_id: string;
  per_satellite_metrics: Array<{
    satellite_id: string;
    status: string;
    position_error_km?: number;
    velocity_error_km_s?: number;
  }>;
  per_track_metrics: Array<{
    track_id: string;
    association_accuracy: number;
  }>;
  temporal_breakdown: Array<{
    time_bucket: string;
    f1_score: number;
  }>;
}

export function useDetailedMetrics(submissionId: string) {
  return useQuery({
    queryKey: ['detailed-metrics', submissionId],
    queryFn: async () => {
      const response = await api.getDetailedMetrics(submissionId);
      return response.data as DetailedMetrics;
    },
    enabled: !!submissionId,
  });
}

// Hook for export
export function useExportResults() {
  return useMutation({
    mutationFn: async ({ submissionId, format }: { submissionId: string; format: 'pdf' | 'csv' | 'json' }) => {
      const response = await api.exportResults(submissionId, format);
      return response.data;
    },
  });
}
