// Orbital Regimes
export type OrbitalRegime = 'LEO' | 'MEO' | 'GEO' | 'HEO';

// Data Tiers
export type DataTier = 'T1' | 'T2' | 'T3' | 'T4';

// Sensor Types
export type SensorType = 'optical' | 'radar' | 'rf';

// Search Strategy for data fetching
export type SearchStrategy = 'fast' | 'windowed' | 'hybrid';

// Dataset Types
export interface Dataset {
  id: string;
  name: string;
  regime: OrbitalRegime;
  tier: DataTier;
  createdAt: string;
  objectCount: number;
  observationCount: number;
  coverage: number;
  sizeBytes: number;
  sensorTypes: SensorType[];
  description?: string;
  downloadUrl?: string;
}

export interface DatasetFilters {
  regime?: OrbitalRegime | 'all';
  tier?: DataTier | 'all';
  sensor?: SensorType | 'all';
  dateRange?: {
    start: Date;
    end: Date;
  };
  objectCountRange?: {
    min: number;
    max: number;
  };
}

// Downsampling Options
export interface DownsamplingOptions {
  enabled: boolean;
  targetCoverage: number;       // 0.01 - 1.0
  targetGap: number;            // 0.5 - 10.0 orbital periods
  maxObsPerSat: number;         // 5 - 500
  preserveTracks: boolean;
  seed?: number;
}

// Simulation Options
export interface SimulationOptions {
  enabled: boolean;
  fillGaps: boolean;
  sensorModel: 'GEODSS' | 'SBSS' | 'Commercial_EO';
  applyNoise: boolean;
  maxSyntheticRatio: number;    // 0.0 - 0.9
  seed?: number;
}

// Dataset Generation Configuration
export interface DatasetGenerationConfig {
  regime: OrbitalRegime;
  coverage: 'high' | 'standard' | 'low' | 'mixed';
  observationDensity: number;
  trackGapTarget: number;
  objectCount: number;
  includeHamr: boolean;
  startDate: string;
  endDate: string;
  sensors: SensorType[];
  // Downsampling and simulation options
  downsampling?: DownsamplingOptions;
  simulation?: SimulationOptions;
  // Search strategy options
  searchStrategy: SearchStrategy;
  windowSizeMinutes?: number;
}

// Submission Types
export type SubmissionStatus = 'queued' | 'validating' | 'processing' | 'completed' | 'failed';

export interface Submission {
  id: string;
  datasetId: string;
  datasetName: string;
  algorithmName: string;
  version: string;
  status: SubmissionStatus;
  createdAt: string;
  completedAt?: string;
  queuePosition?: number;
  results?: SubmissionResults;
  errorMessage?: string;
}

export interface SubmissionResults {
  // Binary Metrics
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  precision: number;
  recall: number;
  f1Score: number;

  // State Metrics
  positionRmsKm: number;
  velocityRmsKmS: number;
  mahalanobisDistance: number;

  // Residual Analysis
  raResidualRmsArcsec: number;
  decResidualRmsArcsec: number;

  // Per-satellite breakdown
  satelliteResults: SatelliteResult[];

  // Rank info
  rank: number;
  previousRank?: number;
}

export interface SatelliteResult {
  satelliteId: string;
  status: 'TP' | 'FP' | 'FN';
  observationsUsed: number;
  totalObservations: number;
  positionErrorKm?: number;
  velocityErrorKmS?: number;
  confidence?: number;
}

// Leaderboard Types
export interface LeaderboardEntry {
  rank: number;
  algorithmName: string;
  team: string;
  version: string;
  f1Score: number;
  precision: number;
  recall: number;
  positionRmsKm: number;
  submissionId: string;
  submittedAt: string;
  isCurrentUser: boolean;
}

export interface LeaderboardFilters {
  regime?: OrbitalRegime | 'all';
  tier?: DataTier | 'all';
  period?: 'all' | 'month' | 'week';
}

// User Types
export interface User {
  id: string;
  username: string;
  email: string;
  organization: string;
  role: 'developer' | 'evaluator' | 'admin';
  createdAt: string;
  bestRank?: number;
  submissionCount: number;
}

// Dashboard Stats
export interface DashboardStats {
  rank: number;
  rankChange: number;
  submissionCount: number;
  processingCount: number;
  bestF1Score: number;
  bestF1DatasetName: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Form Types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  organization: string;
  researchPurpose?: string;
}

export interface SubmissionForm {
  datasetId: string;
  algorithmName: string;
  version: string;
  description?: string;
  file: File;
}

// Notification Types
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  createdAt: string;
  read: boolean;
}
