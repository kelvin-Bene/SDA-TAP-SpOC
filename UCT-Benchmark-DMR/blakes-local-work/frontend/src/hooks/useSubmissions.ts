import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Submission, SubmissionForm, SubmissionResults } from '@/types';

export function useSubmissions() {
  return useQuery({
    queryKey: ['submissions'],
    queryFn: async () => {
      // Mock data for now
      const mockSubmissions: Submission[] = [
        {
          id: '1',
          datasetId: 'ds-1',
          datasetName: 'LEO-T2-2026-01-15',
          algorithmName: 'MyUCTP',
          version: 'v2.1',
          status: 'completed',
          createdAt: '2026-01-18T10:30:00Z',
          completedAt: '2026-01-18T11:15:00Z',
          results: {
            truePositives: 38,
            falsePositives: 2,
            falseNegatives: 4,
            precision: 0.95,
            recall: 0.905,
            f1Score: 0.923,
            positionRmsKm: 2.34,
            velocityRmsKmS: 0.12,
            mahalanobisDistance: 1.89,
            raResidualRmsArcsec: 0.87,
            decResidualRmsArcsec: 0.92,
            satelliteResults: [],
            rank: 3,
            previousRank: 5,
          },
        },
      ];
      return mockSubmissions;
    },
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useSubmission(id: string) {
  return useQuery({
    queryKey: ['submission', id],
    queryFn: async () => {
      const response = await api.getSubmission(id);
      return response.data as Submission;
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
      formData.append('datasetId', data.datasetId);
      formData.append('algorithmName', data.algorithmName);
      formData.append('version', data.version);
      if (data.description) {
        formData.append('description', data.description);
      }

      const response = await api.createSubmission(formData);
      return response.data;
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
      return response.data as SubmissionResults;
    },
    enabled: !!submissionId,
  });
}
