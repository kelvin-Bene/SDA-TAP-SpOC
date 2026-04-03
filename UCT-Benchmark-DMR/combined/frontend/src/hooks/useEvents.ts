import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type {
  SpaceEvent,
  EventType,
  EventDetail,
  EventFilters,
  DetectEventsRequest,
  DetectEventsResponse,
} from '@/types/events';

// Backend response shape (snake_case from Python)
interface EventResponse {
  id: number;
  event_type: string;
  primary_sat_no: number;
  secondary_sat_no?: number;
  event_time_start?: string;
  event_time_end?: string;
  confidence?: number;
  detection_method?: string;
  source?: string;
  dataset_id?: number;
}

function transformEvent(data: EventResponse): SpaceEvent {
  return {
    id: data.id,
    eventType: data.event_type,
    confidence: data.confidence != null ? String(data.confidence) : 'unknown',
    primarySatNos: data.primary_sat_no ? [data.primary_sat_no] : [],
    secondarySatNos: data.secondary_sat_no ? [data.secondary_sat_no] : [],
    startTime: data.event_time_start || '',
    endTime: data.event_time_end || '',
    datasetId: data.dataset_id,
    metadata: {
      detection_method: data.detection_method,
      source: data.source,
    },
  };
}

export function useEvents(filters?: EventFilters) {
  return useQuery({
    queryKey: ['events', filters],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filters?.eventType) params.event_type = filters.eventType;
      if (filters?.satNo) params.sat_no = String(filters.satNo);
      if (filters?.startTime) params.start_time = filters.startTime;
      if (filters?.endTime) params.end_time = filters.endTime;
      if (filters?.datasetId) params.dataset_id = String(filters.datasetId);

      const response = await api.getEvents(params);
      return (response.data as EventResponse[]).map(transformEvent);
    },
  });
}

export function useEvent(eventId: number) {
  return useQuery({
    queryKey: ['events', eventId],
    queryFn: async () => {
      const response = await api.getEvent(String(eventId));
      return response.data as EventDetail;
    },
    enabled: eventId > 0,
  });
}

export function useEventTypes() {
  return useQuery({
    queryKey: ['event-types'],
    queryFn: async () => {
      const response = await api.getEventTypes();
      return response.data as EventType[];
    },
    staleTime: 1000 * 60 * 60, // 1 hour — types rarely change
  });
}

export function useDetectEvents() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DetectEventsRequest) => {
      const response = await api.detectEvents(request);
      return response.data as DetectEventsResponse;
    },
    onSuccess: () => {
      // Invalidate events list so new detections appear after the job completes
      queryClient.invalidateQueries({ queryKey: ['events'] });
    },
  });
}
