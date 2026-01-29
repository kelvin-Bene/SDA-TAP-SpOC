// UCTP Lab TypeScript types

// ============================================================
// ENUMS
// ============================================================

export type UCTPRunStatus = 'pending' | 'running' | 'completed' | 'failed';
export type UCTPModelStatus = 'training' | 'ready' | 'archived';
export type UCTPModelType = 'clustering_nn' | 'propagation_ml' | 'hybrid';
export type ConnectivityStatus = 'connected' | 'failed' | 'timeout' | 'unauthorized' | 'not_installed';

export type ClusteringMethod = 'angular_dbscan' | 'stonesoup_mht' | 'stonesoup_gnn';
export type IODMethod = 'gauss' | 'orbdetpy_laplace' | 'orekit_gooding';
export type RefinementMethod = 'none' | 'batch_least_squares' | 'ekf' | 'ukf';

// ============================================================
// ALGORITHM RUN TYPES
// ============================================================

export interface ClusteringConfig {
  method: ClusteringMethod;
  eps_deg: number;
  min_samples: number;
  time_weight: number;
  max_time_gap_hours: number;
  use_angular_rate: boolean;
  rate_weight: number;
}

export interface IODConfig {
  method: IODMethod;
  min_observations: number;
  angular_separation_lower_deg: number;
  angular_separation_upper_deg: number;
  max_iterations: number;
  convergence_tol: number;
  cull_states: boolean;
  cull_sigma: number;
}

export interface RefinementConfig {
  method: RefinementMethod;
  max_iterations: number;
  convergence_tol: number;
  process_noise_pos_km: number;
  process_noise_vel_km_s: number;
}

export interface UCTPRunCreate {
  dataset_id: number;
  algorithm_name: string;
  clustering: Partial<ClusteringConfig>;
  iod: Partial<IODConfig>;
  refinement: Partial<RefinementConfig>;
}

export interface UCTPRunMetrics {
  f1_score?: number;
  precision?: number;
  recall?: number;
  position_rms_km?: number;
  velocity_rms_km_s?: number;
  clusters_found?: number;
  objects_resolved?: number;
  total_observations?: number;
  noise_observations?: number;
  iod_success_rate?: number;
  elapsed_seconds?: number;
}

export interface UCTPRunSummary {
  id: number;
  dataset_id: number;
  algorithm_name: string;
  status: UCTPRunStatus;
  started_at?: string;
  completed_at?: string;
  metrics: UCTPRunMetrics;
  created_at: string;
  job_id?: string;
}

export interface UCTPRunDetail extends UCTPRunSummary {
  config: Record<string, unknown>;
  output_path?: string;
  log_output?: string;
  error_message?: string;
}

export interface UCTPRunComparison {
  runs: UCTPRunSummary[];
  config_diffs: Record<string, unknown[]>;
}

// ============================================================
// ML MODEL TYPES
// ============================================================

export interface UCTPModelTrainRequest {
  name: string;
  model_type: UCTPModelType;
  description?: string;
  training_dataset_ids: number[];
  training_config: Record<string, unknown>;
}

export interface UCTPModelSummary {
  id: number;
  name: string;
  model_type: UCTPModelType;
  version: string;
  description?: string;
  status: UCTPModelStatus;
  best_f1_score?: number;
  best_position_rms_km?: number;
  training_epochs?: number;
  created_at: string;
}

export interface UCTPModelDetail extends UCTPModelSummary {
  training_dataset_ids: number[];
  training_config: Record<string, unknown>;
  training_loss?: number;
  validation_loss?: number;
  model_path?: string;
}

// ============================================================
// CONNECTIVITY TYPES
// ============================================================

export interface ConnectorStatus {
  service_name: string;
  status: ConnectivityStatus;
  response_time_ms?: number;
  last_checked?: string;
  error_message?: string;
  metadata: Record<string, unknown>;
}

export interface ConnectivityReport {
  services: ConnectorStatus[];
  tested_at: string;
  total_connected: number;
  total_failed: number;
}

// ============================================================
// DASHBOARD TYPES
// ============================================================

export interface UCTPDashboardStats {
  total_runs: number;
  completed_runs: number;
  best_f1_score?: number;
  best_algorithm?: string;
  total_models: number;
  ready_models: number;
  api_health_pct: number;
  recent_runs: UCTPRunSummary[];
}

// ============================================================
// ALGORITHM OPTIONS
// ============================================================

export interface AlgorithmOption {
  value: string;
  label: string;
  description: string;
}

export interface AlgorithmOptions {
  clustering_methods: AlgorithmOption[];
  iod_methods: AlgorithmOption[];
  refinement_methods: AlgorithmOption[];
}
