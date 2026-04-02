import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
  CredentialServiceInfo,
  CredentialSaveResponse,
  CredentialTestResponse,
} from '@/types/credentials';

export function useCredentials() {
  return useQuery({
    queryKey: ['credentials'],
    queryFn: async () => {
      const res = await api.getCredentials();
      return res.data as CredentialServiceInfo[];
    },
    staleTime: 1000 * 30, // 30 seconds
  });
}

export function useCredential(serviceName: string) {
  return useQuery({
    queryKey: ['credentials', serviceName],
    queryFn: async () => {
      const res = await api.getCredential(serviceName);
      return res.data as CredentialServiceInfo;
    },
    enabled: !!serviceName,
    staleTime: 1000 * 30,
  });
}

export function useSaveCredential() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      serviceName,
      primary,
      secondary,
    }: {
      serviceName: string;
      primary: string;
      secondary?: string;
    }) => {
      const res = await api.saveCredential(serviceName, { primary, secondary });
      return res.data as CredentialSaveResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
    },
  });
}

export function useDeleteCredential() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (serviceName: string) => {
      const res = await api.deleteCredential(serviceName);
      return res.data as CredentialSaveResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
    },
  });
}

export function useTestCredential() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (serviceName: string) => {
      const res = await api.testCredential(serviceName);
      return res.data as CredentialTestResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] });
    },
  });
}
