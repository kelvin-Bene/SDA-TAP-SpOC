// =============================================================================
// Mock Data for SDA-TAP / SpOC Demo Mode
// =============================================================================
// This file provides realistic Space Domain Awareness data for when no backend
// is available. Data shapes match the snake_case backend response formats that
// the frontend hooks transform into camelCase.

// ---------------------------------------------------------------------------
// Dataset IDs (stable UUIDs used across datasets, submissions, results)
// ---------------------------------------------------------------------------
const DS_LEO_ISS   = 'd1a0e7c2-3f41-4b8a-9e12-a1b2c3d4e5f6';
const DS_MEO_GPS   = 'd2b1f8d3-4a52-5c9b-af23-b2c3d4e5f6a7';
const DS_GEO_BELT  = 'd3c2a9e4-5b63-6dac-b034-c3d4e5f6a7b8';
const DS_LEO_DEB   = 'd4d3baf5-6c74-7ebd-c145-d4e5f6a7b8c9';
const DS_HEO_MOL   = 'd5e4cbf6-7d85-8fce-d256-e5f6a7b8c9d0';
const DS_LMO_XORB  = 'd6f5dc07-8e96-90df-e367-f6a7b8c9d0e1';

// Submission IDs
const SUB_ORBTRACK  = 's1a0e7c2-1111-4b8a-9e12-a1b2c3d4e5f6';
const SUB_COSMOS    = 's2b1f8d3-2222-5c9b-af23-b2c3d4e5f6a7';
const SUB_TRACKNET  = 's3c2a9e4-3333-6dac-b034-c3d4e5f6a7b8';
const SUB_BASICG    = 's4d3baf5-4444-7ebd-c145-d4e5f6a7b8c9';
const SUB_HYBRID    = 's5e4cbf6-5555-8fce-d256-e5f6a7b8c9d0';

// Job IDs
const JOB_COMPLETED = 'j1a0e7c2-aaaa-4b8a-9e12-a1b2c3d4e5f6';

// ---------------------------------------------------------------------------
// Datasets (backend response format: snake_case)
// ---------------------------------------------------------------------------
export const mockDatasets = [
  {
    id: DS_LEO_ISS,
    name: 'LEO-ISS-Corridor-2026Q1',
    description: 'Low Earth Orbit ISS corridor tracking — 15 resident space objects observed via GEODSS optical sensors over 14-day fitspan. Includes proximity events for close-approach analysis.',
    regime: 'LEO',
    tier: 'T1',
    status: 'ready',
    created_at: '2026-01-15T08:30:00Z',
    observation_count: 2437,
    satellite_count: 15,
    coverage: 0.87,
    size_bytes: 14_680_064, // ~14 MB
    sensor_types: ['optical'],
    version: 1,
    parent_id: null,
  },
  {
    id: DS_MEO_GPS,
    name: 'MEO-GPS-BlockIII-2026Q1',
    description: 'Medium Earth Orbit GPS Block III constellation radar tracking. 8 satellites with high-cadence AN/FPS-85 Eglin and C-band observations.',
    regime: 'MEO',
    tier: 'T2',
    status: 'ready',
    created_at: '2026-01-22T14:15:00Z',
    observation_count: 1248,
    satellite_count: 8,
    coverage: 0.72,
    size_bytes: 8_912_896, // ~8.5 MB
    sensor_types: ['radar'],
    version: 1,
    parent_id: null,
  },
  {
    id: DS_GEO_BELT,
    name: 'GEO-Belt-SBSS-2026Q1',
    description: 'Geostationary belt survey via SBSS and ground-based GEODSS. 5 GEO objects including AEHF-6 and WGS-11 with 7-day arc.',
    regime: 'GEO',
    tier: 'T1',
    status: 'ready',
    created_at: '2026-02-03T11:00:00Z',
    observation_count: 816,
    satellite_count: 5,
    coverage: 0.93,
    size_bytes: 5_242_880, // 5 MB
    sensor_types: ['optical'],
    version: 2,
    parent_id: null,
  },
  {
    id: DS_LEO_DEB,
    name: 'LEO-Debris-Fusion-2026Q1',
    description: 'Low Earth Orbit debris field characterization using fused optical, radar, and RF observations. 25 tracked objects including fragmentation debris from COSMOS-1408 ASAT event.',
    regime: 'LEO',
    tier: 'T3',
    status: 'ready',
    created_at: '2026-02-18T09:45:00Z',
    observation_count: 4521,
    satellite_count: 25,
    coverage: 0.64,
    size_bytes: 28_311_552, // ~27 MB
    sensor_types: ['optical', 'radar', 'rf', 'fusion'],
    version: 1,
    parent_id: null,
  },
  {
    id: DS_HEO_MOL,
    name: 'HEO-Molniya-Optical-2026Q1',
    description: 'Highly Elliptical Orbit Molniya-type tracking. 3 satellites on 12-hour Molniya orbits with GEODSS optical coverage during apogee passes.',
    regime: 'HEO',
    tier: 'T2',
    status: 'ready',
    created_at: '2026-03-01T16:20:00Z',
    observation_count: 612,
    satellite_count: 3,
    coverage: 0.51,
    size_bytes: 3_670_016, // ~3.5 MB
    sensor_types: ['optical'],
    version: 1,
    parent_id: null,
  },
  {
    id: DS_LMO_XORB,
    name: 'LMO-CrossRegime-2026Q1',
    description: 'Cross-regime LEO-MEO transition orbit dataset. Objects with perigee in LEO and apogee in MEO captured via combined radar and optical tracking.',
    regime: 'LMO',
    tier: 'T2',
    status: 'ready',
    created_at: '2026-03-12T07:10:00Z',
    observation_count: 934,
    satellite_count: 6,
    coverage: 0.68,
    size_bytes: 6_291_456, // 6 MB
    sensor_types: ['optical', 'radar'],
    version: 1,
    parent_id: null,
  },
];

// ---------------------------------------------------------------------------
// Submissions (backend response format)
// ---------------------------------------------------------------------------
export const mockSubmissions = [
  {
    id: SUB_ORBTRACK,
    dataset_id: DS_LEO_ISS,
    dataset_name: 'LEO-ISS-Corridor-2026Q1',
    algorithm_name: 'OrbTrack-Pro',
    version: 'v2.1',
    status: 'completed',
    created_at: '2026-02-10T10:00:00Z',
    completed_at: '2026-02-10T10:12:34Z',
    score: 0.934,
    job_id: JOB_COMPLETED,
    queue_position: null,
  },
  {
    id: SUB_COSMOS,
    dataset_id: DS_LEO_DEB,
    dataset_name: 'LEO-Debris-Fusion-2026Q1',
    algorithm_name: 'COSMOS-ML',
    version: 'v1.3',
    status: 'completed',
    created_at: '2026-02-22T14:30:00Z',
    completed_at: '2026-02-22T14:48:12Z',
    score: 0.891,
    job_id: null,
    queue_position: null,
  },
  {
    id: SUB_TRACKNET,
    dataset_id: DS_GEO_BELT,
    dataset_name: 'GEO-Belt-SBSS-2026Q1',
    algorithm_name: 'TrackAssoc-Net',
    version: 'v3.0',
    status: 'completed',
    created_at: '2026-03-05T08:15:00Z',
    completed_at: '2026-03-05T08:22:47Z',
    score: 0.952,
    job_id: null,
    queue_position: null,
  },
  {
    id: SUB_BASICG,
    dataset_id: DS_MEO_GPS,
    dataset_name: 'MEO-GPS-BlockIII-2026Q1',
    algorithm_name: 'BasicGauss',
    version: 'v1.0',
    status: 'processing',
    created_at: '2026-03-28T16:45:00Z',
    completed_at: null,
    score: null,
    job_id: null,
    queue_position: null,
  },
  {
    id: SUB_HYBRID,
    dataset_id: DS_HEO_MOL,
    dataset_name: 'HEO-Molniya-Optical-2026Q1',
    algorithm_name: 'HybridIOD',
    version: 'v2.5',
    status: 'queued',
    created_at: '2026-03-29T09:00:00Z',
    completed_at: null,
    score: null,
    job_id: null,
    queue_position: 2,
  },
];

// ---------------------------------------------------------------------------
// Leaderboard (backend response format — wraps entries[])
// ---------------------------------------------------------------------------
export const mockLeaderboard = {
  dataset_id: null,
  dataset_name: 'All Datasets',
  last_updated: '2026-03-29T12:00:00Z',
  total_entries: 6,
  entries: [
    {
      rank: 1,
      algorithm_name: 'TrackAssoc-Net',
      team: 'MIT Lincoln Lab',
      version: 'v3.0',
      f1_score: 0.952,
      precision: 0.961,
      recall: 0.943,
      position_rms_km: 0.82,
      submission_id: SUB_TRACKNET,
      submitted_at: '2026-03-05T08:22:47Z',
      is_current_user: false,
    },
    {
      rank: 2,
      algorithm_name: 'OrbTrack-Pro',
      team: 'Aerospace Corp',
      version: 'v2.1',
      f1_score: 0.934,
      precision: 0.947,
      recall: 0.921,
      position_rms_km: 1.15,
      submission_id: SUB_ORBTRACK,
      submitted_at: '2026-02-10T10:12:34Z',
      is_current_user: true,
    },
    {
      rank: 3,
      algorithm_name: 'COSMOS-ML',
      team: 'AGI Analytics',
      version: 'v1.3',
      f1_score: 0.891,
      precision: 0.912,
      recall: 0.871,
      position_rms_km: 2.34,
      submission_id: SUB_COSMOS,
      submitted_at: '2026-02-22T14:48:12Z',
      is_current_user: false,
    },
    {
      rank: 4,
      algorithm_name: 'HybridIOD',
      team: 'CU Boulder',
      version: 'v2.5',
      f1_score: 0.867,
      precision: 0.889,
      recall: 0.846,
      position_rms_km: 2.91,
      submission_id: SUB_HYBRID,
      submitted_at: '2026-03-15T11:30:00Z',
      is_current_user: false,
    },
    {
      rank: 5,
      algorithm_name: 'SpOC-Baseline',
      team: 'SpOC Internal',
      version: 'v1.2',
      f1_score: 0.845,
      precision: 0.862,
      recall: 0.829,
      position_rms_km: 3.47,
      submission_id: 's6f6ed18-6666-90ef-f478-a7b8c9d0e1f2',
      submitted_at: '2026-01-28T13:15:00Z',
      is_current_user: false,
    },
    {
      rank: 6,
      algorithm_name: 'BasicGauss',
      team: 'CU Boulder',
      version: 'v1.0',
      f1_score: 0.823,
      precision: 0.841,
      recall: 0.806,
      position_rms_km: 4.62,
      submission_id: SUB_BASICG,
      submitted_at: '2026-03-20T09:45:00Z',
      is_current_user: false,
    },
  ],
};

// ---------------------------------------------------------------------------
// Leaderboard Statistics (backend response format)
// ---------------------------------------------------------------------------
export const mockLeaderboardStatistics = {
  dataset_id: null,
  total_submissions: 23,
  unique_algorithms: 6,
  average_score: 0.879,
  best_score: 0.952,
  worst_score: 0.741,
  submission_trend: 'increasing',
};

// ---------------------------------------------------------------------------
// Leaderboard History (backend response format — for charts)
// ---------------------------------------------------------------------------
export const mockLeaderboardHistory = {
  dataset_id: null,
  period_days: 30,
  history: [
    { date: '2026-03-01', algorithm_name: 'TrackAssoc-Net', best_f1: 0.938 },
    { date: '2026-03-04', algorithm_name: 'TrackAssoc-Net', best_f1: 0.945 },
    { date: '2026-03-05', algorithm_name: 'TrackAssoc-Net', best_f1: 0.952 },
    { date: '2026-03-01', algorithm_name: 'OrbTrack-Pro', best_f1: 0.928 },
    { date: '2026-03-08', algorithm_name: 'OrbTrack-Pro', best_f1: 0.934 },
    { date: '2026-03-01', algorithm_name: 'COSMOS-ML', best_f1: 0.876 },
    { date: '2026-03-10', algorithm_name: 'COSMOS-ML', best_f1: 0.885 },
    { date: '2026-03-15', algorithm_name: 'COSMOS-ML', best_f1: 0.891 },
    { date: '2026-03-01', algorithm_name: 'HybridIOD', best_f1: 0.854 },
    { date: '2026-03-12', algorithm_name: 'HybridIOD', best_f1: 0.867 },
    { date: '2026-03-01', algorithm_name: 'SpOC-Baseline', best_f1: 0.845 },
    { date: '2026-03-20', algorithm_name: 'BasicGauss', best_f1: 0.811 },
    { date: '2026-03-25', algorithm_name: 'BasicGauss', best_f1: 0.823 },
  ],
};

// ---------------------------------------------------------------------------
// Evaluation Results (backend response format for /results/:id)
// ---------------------------------------------------------------------------
function buildResultsForSubmission(submissionId: string) {
  const resultMap: Record<string, object> = {
    [SUB_ORBTRACK]: {
      submission_id: SUB_ORBTRACK,
      dataset_id: DS_LEO_ISS,
      algorithm_name: 'OrbTrack-Pro',
      status: 'completed',
      completed_at: '2026-02-10T10:12:34Z',
      true_positives: 138,
      true_negatives: 1842,
      false_positives: 9,
      false_negatives: 11,
      accuracy: 0.990,
      specificity: 0.995,
      precision: 0.939,
      recall: 0.926,
      f1_score: 0.934,
      position_rms_km: 1.15,
      velocity_rms_km_s: 0.0082,
      mahalanobis_distance: 1.43,
      ra_residual_rms_arcsec: 2.14,
      dec_residual_rms_arcsec: 1.87,
      satellite_results: [
        { satellite_id: 'ISS (ZARYA)',       status: 'TP', observations_used: 312, total_observations: 340, position_error_km: 0.42, velocity_error_km_s: 0.0031, confidence: 0.99 },
        { satellite_id: 'COSMOS 2251 DEB',   status: 'TP', observations_used: 187, total_observations: 210, position_error_km: 1.83, velocity_error_km_s: 0.0095, confidence: 0.91 },
        { satellite_id: 'CZ-6A DEB',         status: 'TP', observations_used: 142, total_observations: 165, position_error_km: 1.21, velocity_error_km_s: 0.0074, confidence: 0.94 },
        { satellite_id: 'STARLINK-5291',     status: 'TP', observations_used: 201, total_observations: 218, position_error_km: 0.67, velocity_error_km_s: 0.0045, confidence: 0.97 },
        { satellite_id: 'SL-4 R/B',          status: 'FN', observations_used: 28,  total_observations: 155, position_error_km: null, velocity_error_km_s: null,   confidence: 0.23 },
      ],
      ra_residual_histogram: {
        labels: ['-10', '-8', '-6', '-4', '-2', '0', '2', '4', '6', '8', '10'],
        counts: [2, 8, 24, 67, 148, 312, 156, 72, 28, 11, 3],
      },
      dec_residual_histogram: {
        labels: ['-10', '-8', '-6', '-4', '-2', '0', '2', '4', '6', '8', '10'],
        counts: [3, 11, 31, 78, 162, 298, 171, 69, 25, 9, 2],
      },
      position_error_histogram: {
        labels: ['0-0.5', '0.5-1', '1-2', '2-3', '3-5', '5-10', '>10'],
        counts: [42, 38, 31, 18, 7, 2, 0],
      },
      rank: 2,
      previous_rank: 3,
      processing_time_seconds: 754,
    },
    [SUB_COSMOS]: {
      submission_id: SUB_COSMOS,
      dataset_id: DS_LEO_DEB,
      algorithm_name: 'COSMOS-ML',
      status: 'completed',
      completed_at: '2026-02-22T14:48:12Z',
      true_positives: 412,
      true_negatives: 3210,
      false_positives: 41,
      false_negatives: 52,
      accuracy: 0.975,
      specificity: 0.987,
      precision: 0.910,
      recall: 0.888,
      f1_score: 0.891,
      position_rms_km: 2.34,
      velocity_rms_km_s: 0.0187,
      mahalanobis_distance: 2.18,
      ra_residual_rms_arcsec: 4.32,
      dec_residual_rms_arcsec: 3.91,
      satellite_results: [
        { satellite_id: 'COSMOS-1408 DEB A', status: 'TP', observations_used: 89,  total_observations: 102, position_error_km: 2.11, velocity_error_km_s: 0.0162, confidence: 0.88 },
        { satellite_id: 'COSMOS-1408 DEB B', status: 'TP', observations_used: 76,  total_observations: 95,  position_error_km: 2.54, velocity_error_km_s: 0.0198, confidence: 0.85 },
        { satellite_id: 'FENGYUN 1C DEB',   status: 'TP', observations_used: 112, total_observations: 130, position_error_km: 1.89, velocity_error_km_s: 0.0142, confidence: 0.92 },
        { satellite_id: 'IRIDIUM 33 DEB',   status: 'FP', observations_used: 45,  total_observations: 88,  position_error_km: 8.72, velocity_error_km_s: 0.0521, confidence: 0.41 },
        { satellite_id: 'BREEZE-M DEB',     status: 'FN', observations_used: 12,  total_observations: 67,  position_error_km: null, velocity_error_km_s: null,   confidence: 0.18 },
      ],
      ra_residual_histogram: {
        labels: ['-15', '-10', '-5', '-2', '0', '2', '5', '10', '15'],
        counts: [5, 18, 62, 134, 287, 141, 58, 22, 7],
      },
      dec_residual_histogram: {
        labels: ['-15', '-10', '-5', '-2', '0', '2', '5', '10', '15'],
        counts: [7, 22, 71, 128, 264, 139, 65, 26, 9],
      },
      position_error_histogram: {
        labels: ['0-1', '1-2', '2-3', '3-5', '5-10', '>10'],
        counts: [87, 124, 98, 62, 31, 10],
      },
      rank: 3,
      previous_rank: 4,
      processing_time_seconds: 1082,
    },
    [SUB_TRACKNET]: {
      submission_id: SUB_TRACKNET,
      dataset_id: DS_GEO_BELT,
      algorithm_name: 'TrackAssoc-Net',
      status: 'completed',
      completed_at: '2026-03-05T08:22:47Z',
      true_positives: 74,
      true_negatives: 698,
      false_positives: 3,
      false_negatives: 4,
      accuracy: 0.991,
      specificity: 0.996,
      precision: 0.961,
      recall: 0.949,
      f1_score: 0.952,
      position_rms_km: 0.82,
      velocity_rms_km_s: 0.0038,
      mahalanobis_distance: 0.97,
      ra_residual_rms_arcsec: 1.24,
      dec_residual_rms_arcsec: 1.08,
      satellite_results: [
        { satellite_id: 'AEHF-6',     status: 'TP', observations_used: 178, total_observations: 185, position_error_km: 0.51, velocity_error_km_s: 0.0022, confidence: 0.99 },
        { satellite_id: 'WGS-11',     status: 'TP', observations_used: 165, total_observations: 172, position_error_km: 0.73, velocity_error_km_s: 0.0034, confidence: 0.98 },
        { satellite_id: 'SBIRS GEO-5', status: 'TP', observations_used: 152, total_observations: 160, position_error_km: 0.64, velocity_error_km_s: 0.0029, confidence: 0.98 },
        { satellite_id: 'MUOS-5',     status: 'TP', observations_used: 148, total_observations: 155, position_error_km: 0.88, velocity_error_km_s: 0.0041, confidence: 0.97 },
        { satellite_id: 'GSSAP-2',    status: 'FN', observations_used: 31,  total_observations: 144, position_error_km: null, velocity_error_km_s: null,   confidence: 0.34 },
      ],
      ra_residual_histogram: {
        labels: ['-6', '-4', '-2', '-1', '0', '1', '2', '4', '6'],
        counts: [1, 5, 18, 42, 98, 45, 21, 6, 2],
      },
      dec_residual_histogram: {
        labels: ['-6', '-4', '-2', '-1', '0', '1', '2', '4', '6'],
        counts: [2, 6, 22, 38, 91, 41, 19, 8, 3],
      },
      position_error_histogram: {
        labels: ['0-0.25', '0.25-0.5', '0.5-1', '1-2', '2-5', '>5'],
        counts: [28, 22, 15, 7, 2, 0],
      },
      rank: 1,
      previous_rank: 1,
      processing_time_seconds: 467,
    },
  };

  return resultMap[submissionId] || null;
}

// ---------------------------------------------------------------------------
// Dataset Generation Config (backend response format)
// ---------------------------------------------------------------------------
export const mockDatasetConfig = {
  coverage_thresholds: {
    high: 0.9,
    standard: 0.7,
    low: 0.4,
    mixed: 0.55,
  },
  track_gap_long_multiplier: 3.0,
  obs_count_low_threshold: 10,
};

// ---------------------------------------------------------------------------
// Jobs (backend response format)
// ---------------------------------------------------------------------------
export const mockJobCompleted = {
  id: JOB_COMPLETED,
  job_type: 'dataset_generation',
  status: 'completed',
  progress: 100,
  stage: 'Done',
  result: { dataset_id: DS_LEO_ISS },
  error: null,
};

// ---------------------------------------------------------------------------
// User Profile (backend response format)
// ---------------------------------------------------------------------------
export const mockUserProfile = {
  id: 'demo-user',
  username: 'Demo User',
  email: 'demo@spoc.mil',
  organization: 'SDA TAP Lab',
  role: 'admin',
  created_at: '2026-01-01T00:00:00Z',
  best_rank: 2,
  submission_count: 5,
  udl_token: '****-****-****-7f3a',
  esa_token: null,
};

// ---------------------------------------------------------------------------
// Detailed Metrics (backend response for /results/:id/metrics)
// ---------------------------------------------------------------------------
function buildDetailedMetrics(submissionId: string) {
  return {
    submission_id: submissionId,
    per_satellite_metrics: [
      { satellite_id: 'SAT-001', status: 'TP', position_error_km: 0.62, velocity_error_km_s: 0.0041 },
      { satellite_id: 'SAT-002', status: 'TP', position_error_km: 1.14, velocity_error_km_s: 0.0078 },
      { satellite_id: 'SAT-003', status: 'FN', position_error_km: null, velocity_error_km_s: null },
    ],
    per_track_metrics: [
      { track_id: 'TRK-001', association_accuracy: 0.97 },
      { track_id: 'TRK-002', association_accuracy: 0.93 },
      { track_id: 'TRK-003', association_accuracy: 0.88 },
      { track_id: 'TRK-004', association_accuracy: 0.91 },
    ],
    temporal_breakdown: [
      { time_bucket: '2026-02-10T00:00Z', f1_score: 0.91 },
      { time_bucket: '2026-02-10T06:00Z', f1_score: 0.93 },
      { time_bucket: '2026-02-10T12:00Z', f1_score: 0.95 },
      { time_bucket: '2026-02-10T18:00Z', f1_score: 0.92 },
    ],
  };
}

// ---------------------------------------------------------------------------
// Dataset Observations (backend response for /datasets/:id/observations)
// ---------------------------------------------------------------------------
function buildDatasetObservations(datasetId: string) {
  const sensorNames = ['GEODSS-Maui', 'GEODSS-Diego Garcia', 'GEODSS-Socorro', 'Eglin AN/FPS-85', 'Cavalier AFS'];
  const observations = [];
  const baseDate = new Date('2026-02-01T00:00:00Z');

  for (let i = 0; i < 25; i++) {
    const obsDate = new Date(baseDate.getTime() + i * 3_600_000 * 2.3); // ~2.3 hr intervals
    observations.push({
      id: `obs-${datasetId.slice(0, 8)}-${String(i).padStart(4, '0')}`,
      ob_time: obsDate.toISOString(),
      ra: 120.0 + Math.sin(i * 0.5) * 15.0,
      declination: -10.0 + Math.cos(i * 0.3) * 20.0,
      sensor_name: sensorNames[i % sensorNames.length],
      track_id: `TRK-${String(Math.floor(i / 5)).padStart(3, '0')}`,
    });
  }

  return {
    dataset_id: datasetId,
    total_count: mockDatasets.find(d => d.id === datasetId)?.observation_count ?? 100,
    limit: 25,
    offset: 0,
    observations,
  };
}

// ---------------------------------------------------------------------------
// URL pattern matcher — returns mock data for a given request URL + method
// ---------------------------------------------------------------------------
export function getMockResponse(url: string, method: string): { data: unknown; status: number } | null {
  const normalizedUrl = url.replace(/\/$/, ''); // strip trailing slash
  const lowerMethod = method.toLowerCase();

  // Only intercept GET requests (write operations should fail visibly in demo)
  if (lowerMethod !== 'get') return null;

  // GET /datasets (list)
  if (/\/datasets$/.test(normalizedUrl)) {
    return { data: mockDatasets, status: 200 };
  }

  // GET /datasets/config
  if (/\/datasets\/config$/.test(normalizedUrl)) {
    return { data: mockDatasetConfig, status: 200 };
  }

  // GET /datasets/:id/observations
  const obsMatch = normalizedUrl.match(/\/datasets\/([a-f0-9-]+)\/observations$/);
  if (obsMatch) {
    return { data: buildDatasetObservations(obsMatch[1]), status: 200 };
  }

  // GET /datasets/:id/versions
  const verMatch = normalizedUrl.match(/\/datasets\/([a-f0-9-]+)\/versions$/);
  if (verMatch) {
    const ds = mockDatasets.find(d => d.id === verMatch[1]);
    return { data: ds ? [ds] : [], status: 200 };
  }

  // GET /datasets/:id (single)
  const dsMatch = normalizedUrl.match(/\/datasets\/([a-f0-9-]+)$/);
  if (dsMatch) {
    const ds = mockDatasets.find(d => d.id === dsMatch[1]);
    return ds ? { data: ds, status: 200 } : null;
  }

  // GET /submissions (list)
  if (/\/submissions$/.test(normalizedUrl)) {
    return { data: mockSubmissions, status: 200 };
  }

  // GET /submissions/:id (single)
  const subMatch = normalizedUrl.match(/\/submissions\/([a-f0-9-]+)$/);
  if (subMatch) {
    const sub = mockSubmissions.find(s => s.id === subMatch[1]);
    return sub ? { data: sub, status: 200 } : null;
  }

  // GET /results/:id/metrics (detailed metrics — must come before /results/:id)
  const metricsMatch = normalizedUrl.match(/\/results\/([a-f0-9-]+)\/metrics$/);
  if (metricsMatch) {
    return { data: buildDetailedMetrics(metricsMatch[1]), status: 200 };
  }

  // GET /results/:id/visualization
  const vizMatch = normalizedUrl.match(/\/results\/([a-f0-9-]+)\/visualization$/);
  if (vizMatch) {
    const result = buildResultsForSubmission(vizMatch[1]);
    return { data: result || {}, status: 200 };
  }

  // GET /results/:id (evaluation results)
  const resMatch = normalizedUrl.match(/\/results\/([a-f0-9-]+)$/);
  if (resMatch) {
    const result = buildResultsForSubmission(resMatch[1]);
    if (result) return { data: result, status: 200 };
  }

  // GET /leaderboard/statistics
  if (/\/leaderboard\/statistics$/.test(normalizedUrl)) {
    return { data: mockLeaderboardStatistics, status: 200 };
  }

  // GET /leaderboard/history
  if (/\/leaderboard\/history$/.test(normalizedUrl)) {
    return { data: mockLeaderboardHistory, status: 200 };
  }

  // GET /leaderboard (list)
  if (/\/leaderboard$/.test(normalizedUrl)) {
    return { data: mockLeaderboard, status: 200 };
  }

  // GET /jobs/:id
  const jobMatch = normalizedUrl.match(/\/jobs\/([a-f0-9-]+)$/);
  if (jobMatch) {
    return { data: { ...mockJobCompleted, id: jobMatch[1] }, status: 200 };
  }

  // GET /jobs (list)
  if (/\/jobs$/.test(normalizedUrl)) {
    return { data: [mockJobCompleted], status: 200 };
  }

  // GET /auth/me
  if (/\/auth\/me$/.test(normalizedUrl)) {
    return { data: mockUserProfile, status: 200 };
  }

  // No match — let the error propagate
  return null;
}
