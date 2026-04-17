// Orbital Regimes (includes combo regimes per Louis's documentation)
export type OrbitalRegime = 'LEO' | 'MEO' | 'GEO' | 'HEO' | 'ALL'
  | 'LMO' | 'LGO' | 'LHO' | 'MGO' | 'MHO' | 'GHO'   // 2-regime combos
  | 'LMG' | 'LMH' | 'LGH' | 'MGH';                     // 3-regime combos

// Data Tiers (T5 = impossible criteria detected, per Aug 2025 transcript)
export type DataTier = 'T1' | 'T2' | 'T3' | 'T4' | 'T5';

// Sensor Types (fusion = combined sensor data, per Jan 22 transcript)
export type SensorType = 'optical' | 'radar' | 'rf' | 'fusion';

// Search Strategy for data fetching
export type SearchStrategy = 'fast' | 'windowed' | 'hybrid';

// ============================================================
// Legacy 16-Character Dataset Code Types (Louis's Documentation)
// ============================================================

// Legacy Object Type (Position 1)
export type LegacyObjectType = 'H' | 'C' | 'A' | 'U' | 'N';
export const LEGACY_OBJECT_TYPES: Record<LegacyObjectType, string> = {
  H: 'HAMR (High Area-to-Mass Ratio)',
  C: 'Close physical proximity',
  A: 'Apparent angular proximity',
  U: 'Unspecified/Normal',
  N: 'Calibration satellites',
};

// Target Percentage (Positions 2-3)
export type TargetPercentage = '50' | '10' | '01' | 'UN';
export const TARGET_PERCENTAGES: Record<TargetPercentage, string> = {
  '50': '50% target objects',
  '10': '10% target objects',
  '01': '1% target objects',
  'UN': 'Unspecified',
};

// Legacy Event Type (Positions 7-8)
export type LegacyEventType = 'MB' | 'BU' | 'LL' | 'NE';
export const LEGACY_EVENT_TYPES: Record<LegacyEventType, string> = {
  MB: 'Maneuver between observations',
  BU: 'Breakup event',
  LL: 'Long-duration/Low-thrust',
  NE: 'No events (normal)',
};

// Legacy Sensor Type (Positions 9-10)
export type LegacySensorType = 'OP' | 'RA' | 'RF' | 'FU' | 'OR' | 'RO' | 'RR';
export const LEGACY_SENSOR_TYPES: Record<LegacySensorType, string> = {
  OP: 'Optical only',
  RA: 'Radar only',
  RF: 'RF only',
  FU: 'Fusion (all sensors)',
  OR: 'Optical + Radar',
  RO: 'Radar + Optical',
  RR: 'Radar + RF',
};

// Quality Level (Positions 11-13 for coverage, track gap, obs count)
// Per Louis's documentation, A/S/N refer to % of objects with LOW quality:
// A = >90% objects have LOW quality (sparse dataset)
// S = 40-60% objects have LOW quality (mixed)
// N = <10% objects have LOW quality (dense/high-quality dataset)
export type QualityLevel = 'A' | 'S' | 'N';
export const QUALITY_LEVELS: Record<QualityLevel, string> = {
  A: 'Sparse (>90% low quality)',
  S: 'Mixed (40-60% low quality)',
  N: 'Dense (<10% low quality)',
};

// Object Count Level (Position 14)
export type ObjectCountLevel = 'H' | 'S' | 'L';
export const OBJECT_COUNT_LEVELS: Record<ObjectCountLevel, { label: string; count: number; tolerance: number }> = {
  H: { label: 'High', count: 80, tolerance: 2 },
  S: { label: 'Standard', count: 40, tolerance: 2 },
  L: { label: 'Low', count: 10, tolerance: 2 },
};

// Legacy Dataset Code Configuration
export interface LegacyDatasetCodeConfig {
  objectType: LegacyObjectType;
  targetPercentage: TargetPercentage;
  orbitalRegime: OrbitalRegime;
  event: LegacyEventType;
  sensorType: LegacySensorType;
  orbitCoverage: QualityLevel;
  trackGap: QualityLevel;
  observationCount: QualityLevel;
  objectCount: ObjectCountLevel;
  fitspanDays: number;
}

// Generate legacy code from config
export function generateLegacyCode(config: LegacyDatasetCodeConfig): string {
  return (
    config.objectType +
    config.targetPercentage +
    config.orbitalRegime +
    config.event +
    config.sensorType +
    config.orbitCoverage +
    config.trackGap +
    config.observationCount +
    config.objectCount +
    config.fitspanDays.toString().padStart(2, '0')
  );
}

// Parse legacy code into config
export function parseLegacyCode(code: string): LegacyDatasetCodeConfig | null {
  if (!validateLegacyCode(code).valid) return null;
  try {
    return {
      objectType: code[0] as LegacyObjectType,
      targetPercentage: code.slice(1, 3) as TargetPercentage,
      orbitalRegime: code.slice(3, 6) as OrbitalRegime,
      event: code.slice(6, 8) as LegacyEventType,
      sensorType: code.slice(8, 10) as LegacySensorType,
      orbitCoverage: code[10] as QualityLevel,
      trackGap: code[11] as QualityLevel,
      observationCount: code[12] as QualityLevel,
      objectCount: code[13] as ObjectCountLevel,
      fitspanDays: parseInt(code.slice(14, 16), 10),
    };
  } catch {
    return null;
  }
}

// Validate legacy code format
export function validateLegacyCode(code: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (code.length !== 16) {
    errors.push(`Code must be 16 characters (got ${code.length})`);
    return { valid: false, errors };
  }

  if (!['H', 'C', 'A', 'U', 'N'].includes(code[0])) {
    errors.push(`Invalid object type '${code[0]}' at position 1. Valid: H, C, A, U, N`);
  }
  if (!['50', '10', '01', 'UN'].includes(code.slice(1, 3))) {
    errors.push(`Invalid target percentage '${code.slice(1, 3)}' at positions 2-3. Valid: 50, 10, 01, UN`);
  }
  // Per Lewis's Benchmarking Doc: singles + all 2-regime and 3-regime combos
  // (convention: "first letter of each regime in the order LEO/MEO/GEO/HEO").
  if (!['LEO', 'MEO', 'GEO', 'HEO', 'ALL',
        'LMO', 'LGO', 'LHO', 'MGO', 'MHO', 'GHO',   // 2-regime combos
        'LMG', 'LMH', 'LGH', 'MGH',                  // 3-regime combos
       ].includes(code.slice(3, 6))) {
    errors.push(`Invalid regime '${code.slice(3, 6)}' at positions 4-6`);
  }
  if (!['MB', 'BU', 'LL', 'NE'].includes(code.slice(6, 8))) {
    errors.push(`Invalid event '${code.slice(6, 8)}' at positions 7-8. Valid: MB, BU, LL, NE`);
  }
  if (!['OP', 'RA', 'RF', 'FU', 'OR', 'RO', 'RR'].includes(code.slice(8, 10))) {
    errors.push(`Invalid sensor '${code.slice(8, 10)}' at positions 9-10`);
  }
  if (!['A', 'S', 'N'].includes(code[10])) {
    errors.push(`Invalid coverage level '${code[10]}' at position 11. Valid: A, S, N`);
  }
  if (!['A', 'S', 'N'].includes(code[11])) {
    errors.push(`Invalid track gap '${code[11]}' at position 12. Valid: A, S, N`);
  }
  if (!['A', 'S', 'N'].includes(code[12])) {
    errors.push(`Invalid obs count '${code[12]}' at position 13. Valid: A, S, N`);
  }
  if (!['H', 'S', 'L'].includes(code[13])) {
    errors.push(`Invalid object count '${code[13]}' at position 14. Valid: H, S, L`);
  }

  const fitspan = parseInt(code.slice(14, 16), 10);
  if (isNaN(fitspan) || fitspan < 1 || fitspan > 14) {
    errors.push(`Invalid fitspan '${code.slice(14, 16)}' at positions 15-16. Valid: 01-14`);
  }

  return { valid: errors.length === 0, errors };
}

// EO Observation Dataset (per Benchmarking Documentation)
export interface EOObservation {
  id: string;
  classificationMarking: string;
  obTime: string;
  idOnOrbit: string;
  idSensor: string;
  satNo: number;
  taskId: string;
  origObjectId: string;
  origSensorId: string;
  uct: boolean;
  azimuth: number;
  elevation: number;
  range: number;
  ra: number;
  declination: number;
  losUnc: number;
  senlat: number;
  senlon: number;
  senalt: number;
  senx: number;
  seny: number;
  senz: number;
  senvelx: number;
  senvely: number;
  senvelz: number;
  expDuration: number;
  zeroptd: number;
  netObjSig: number;
  netObjSigUnc: number;
  mag: number;
  magUnc: number;
  geolat: number;
  geolon: number;
  geoalt: number;
  georange: number;
  solarPhaseAngle: number;
  solarEqPhaseAngle: number;
  solarDecAngle: number;
  shutterDelay: number;
  rawFileURI: string;
  source: string;
  dataMode: string;
  createdAt: string;
  createdBy: string;
  origNetwork: string;
  type: string;
}

// Dataset Types
export type DatasetStatus = 'created' | 'generating' | 'available' | 'complete' | 'failed';

export interface Dataset {
  id: string;
  name: string;
  regime: OrbitalRegime;
  tier: DataTier;
  status: DatasetStatus;
  createdAt: string;
  objectCount: number;
  observationCount: number;
  coverage: number;
  sizeBytes: number;
  sensorTypes: SensorType[];
  description?: string;
  downloadUrl?: string;
  version?: number;
  parentId?: string;
  errorMessage?: string;
  // True iff dataset_references rows exist; gates the Submit dropdown so
  // evaluation can't be launched against datasets that would fail with
  // "no reference state vectors persisted" (QA_PROD_RUN_2026-04-17 C1).
  hasReferenceOrbits: boolean;
}

export interface DatasetFilters {
  regime?: OrbitalRegime | 'all';
  tier?: DataTier | 'all';
  sensor?: SensorType | 'all';
  search?: string;
  sortBy?: 'name' | 'created_at' | 'satellite_count' | 'observation_count';
  sortOrder?: 'asc' | 'desc';
  dateRange?: {
    start: Date;
    end: Date;
  };
  objectCountRange?: {
    min: number;
    max: number;
  };
  mine?: boolean;
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
  name?: string;
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
  // Non-reference observations for True Negative calculation (per Louis's spec)
  includeNonRefObs?: boolean;
  nonRefRatio?: number;          // 0.01 - 0.5
  // Object type and event codes (per Louis's 16-character code spec)
  objectTypeCode?: 'H' | 'C' | 'A' | 'U' | 'N';
  eventCode?: 'MB' | 'BU' | 'LL' | 'NE';
  // Target percentage (positions 2-3 of 16-char code)
  targetPercentage?: '50' | '10' | '01' | 'UN';
  // Sensor type code (positions 9-10 of 16-char code)
  sensorTypeCode?: 'OP' | 'RA' | 'RF' | 'FU' | 'OR' | 'RO' | 'RR';
  // Fitspan days (positions 15-16 of 16-char code)
  fitspanDays?: number;
  // Window selection algorithm (per Louis's bisecting search spec)
  useWindowSelection?: boolean;
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

// Composite scoring breakdown — mirror of workers.compute_composite_score().
// Louis Feb 19 ask: show *which* component cost a submission points.
export interface CompositeBreakdown {
  composite_score: number;
  binary_component: number;
  state_component: number | null;
  state_source: 'mahalanobis_pscore' | 'position_rms_heuristic' | null;
  residual_component: number | null;
  weights_used: {
    binary: number;
    state: number;
    residual: number;
  };
  fallback_reason: 'no_state' | 'no_residual' | 'no_state_or_residual' | null;
}

export interface SplitBreakdowns {
  train?: CompositeBreakdown | null;
  validation?: CompositeBreakdown | null;
  test?: CompositeBreakdown | null;
}

export interface SubmissionResults {
  // Binary Metrics
  truePositives?: number;
  trueNegatives?: number;  // Requires non-reference observations in dataset
  falsePositives?: number;
  falseNegatives?: number;
  precision?: number;
  recall?: number;
  f1Score: number;
  accuracy?: number;     // (TP+TN)/(TP+TN+FP+FN)
  specificity?: number;  // TN/(TN+FP)

  // State Metrics
  positionRmsKm?: number;
  velocityRmsKmS?: number;
  mahalanobisDistance?: number;

  // Residual Analysis
  raResidualRmsArcsec?: number;
  decResidualRmsArcsec?: number;

  // Composite scoring (Louis Feb 19 vision item)
  compositeScore?: number;
  trainCompositeScore?: number;
  valCompositeScore?: number;
  testCompositeScore?: number;
  compositeBreakdown?: CompositeBreakdown;
  splitBreakdowns?: SplitBreakdowns;

  // Per-satellite breakdown
  satelliteResults?: SatelliteResult[];

  // Histogram data (real distributions from evaluation pipeline)
  raResidualHistogram?: HistogramData;
  decResidualHistogram?: HistogramData;
  positionErrorHistogram?: HistogramData;

  // Rank info (computed by backend — ranked by composite score with fallback to F1)
  rank?: number;
  previousRank?: number;
}

// Histogram data from evaluation pipeline (real distribution data)
export interface HistogramData {
  labels: string[];
  counts: number[];
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
  compositeScore: number;
  // CTF train/validation/test breakdown. The headline `compositeScore`
  // above is sourced from `testCompositeScore` on the backend (the only
  // un-cheatable split) with fallback to the legacy whole-dataset score.
  trainCompositeScore?: number;
  valCompositeScore?: number;
  testCompositeScore?: number;
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
  datasetId?: string | 'all';
}

// User Types
export interface User {
  id: string;
  username: string;
  email: string;
  organization: string;
  role: 'authenticated' | 'evaluator' | 'admin';
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
  classificationMarking?: string;
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
