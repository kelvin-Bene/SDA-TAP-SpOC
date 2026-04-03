/**
 * Type definitions for the Event Labelling System.
 */

export interface SpaceEvent {
  id: number;
  eventType: string;
  confidence: string;
  primarySatNos: number[];
  secondarySatNos: number[];
  startTime: string;
  endTime: string;
  peakTime?: string;
  datasetId?: number;
  metadata: Record<string, unknown>;
}

export interface EventType {
  id: number;
  name: string;
  description?: string;
}

export interface EventDetail extends SpaceEvent {
  externalId?: string;
  labelledBy?: string;
  labelledAt?: string;
  notes?: string;
  detectionConfig?: string;
  observations: EventObservation[];
}

export interface EventObservation {
  id: string;
  satNo?: number;
  obTime?: string;
  ra?: number;
  declination?: number;
}

export interface EventFilters {
  eventType?: string;
  satNo?: number;
  startTime?: string;
  endTime?: string;
  datasetId?: number;
}

export interface DetectEventsRequest {
  sat_nos: number[];
  time_window_start: string;
  time_window_end: string;
  detector_types: string[];
}

export interface DetectEventsResponse {
  job_id: string;
  message: string;
}
