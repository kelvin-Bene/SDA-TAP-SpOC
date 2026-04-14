# Evaluation Metrics

<!-- AI_METADATA
purpose: Document evaluation metrics and scoring algorithms for UCTP performance assessment
status: active
related_files: [technical/PIPELINE.md, planning/PROJECT_STATUS.md]
last_updated: 2026-04-14
-->

## Overview

The evaluation system assesses UCTP algorithm performance through four stages:

1. **Orbit Association** - Match candidate orbits to reference truth objects
2. **Binary Metrics** - Classification performance (TP/TN/FP/FN and derived scores)
3. **State Metrics** - Orbital state estimation accuracy (error norms, Mahalanobis, NEES, RIC)
4. **Residual Metrics** - Observation fit quality (great-circle angular residuals, TLE element residuals)

All metrics are persisted to a JSON evaluation file via `evaluationReport()`. A subset is visualized in the PDF report.

---

## Evaluation Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Reference      │     │  UCTP Output    │     │  Orbit          │
│  Ground Truth   │────>│  State Vectors  │────>│  Association    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
         ┌───────────────────────────────────────────────┼───────┐
         │                                               │       │
         v                                               v       v
┌─────────────────┐                             ┌─────────────────┐
│  Binary         │                             │  State          │
│  Metrics        │                             │  Metrics        │
└─────────────────┘                             └─────────────────┘
         │                                               │
         └───────────────────────┬───────────────────────┘
                                 v
                        ┌─────────────────┐
                        │  Residual       │
                        │  Metrics        │
                        └─────────────────┘
                                 │
                                 v
                  ┌──────────────────────────┐
                  │  evaluationReport()      │
                  │  -> JSON + PDF Report    │
                  └──────────────────────────┘
```

---

## 1. Orbit Association

**Code**: `uct_benchmark/evaluation/orbitAssociation.py` -- `orbitAssociation()`

Before computing any metrics, each UCTP candidate orbit must be matched to a reference (truth) orbit. The UCTP does not identify which reference object a candidate corresponds to -- it only groups correlated observations and outputs an orbit estimate. The association step determines which candidate maps to which truth object.

### Algorithm: Hungarian Method (Linear Sum Assignment)

The association uses `scipy.optimize.linear_sum_assignment` (the Hungarian algorithm) to find the globally optimal one-to-one matching that minimizes total error.

**Steps:**

1. For each truth orbit `j`, propagate it to every candidate epoch to get a propagated state vector at each candidate's time.
2. For each (candidate `i`, truth `j`) pair, compute the cost as the Euclidean norm of the state-vector difference:
   ```
   cost_matrix[i, j] = ||state_candidate_i - state_truth_j_propagated||_2
   ```
3. Solve the linear sum assignment problem on the cost matrix. This produces a one-to-one mapping that minimizes total assignment cost.
4. Unmatched candidates (when `n_candidates > n_truth`) become "non-associated" (bogus/UCT) orbits.
5. Unmatched truth objects (when `n_truth > n_candidates`) become "undiscovered" reference orbits.

**Modes:**

| Mode | Inputs | Cost Metric |
|------|--------|-------------|
| State Vector (default) | 6D state + 6x6 covariance | L2 norm of propagated state difference |
| TLE (`elset_mode=True`) | TLE line1/line2 | L2 norm after converting TLEs to state vectors via `TLEToSV()` |

Propagation is parallelized across truth objects using `ProcessPoolExecutor`.

### Association Output Columns

| Output Field | Description |
|---|---|
| `Associated Orbit Count` | Number of candidate orbits successfully matched to truth |
| `Non-Associated Orbit Count` | Candidate orbits with no truth match (false discoveries / bogus orbits) |
| `Undiscovered Reference Orbits` | Truth orbits not matched by any candidate (missed detections) |
| `Expected State Count` | Total number of truth objects |
| `Time Elapsed` | Wall-clock time for association (stripped before JSON persistence) |

---

## 2. Binary Metrics

**Code**: `uct_benchmark/evaluation/binaryMetrics.py` -- `binaryMetrics()`

Binary metrics treat the observation-to-orbit association as a classification problem.

### Confusion Matrix Definitions

Per Louis's Benchmarking Documentation:

| Label | Definition |
|---|---|
| **True Positive (TP)** | Reference observation correctly matched to the correct reference satellite |
| **True Negative (TN)** | Non-reference observation correctly NOT matched to any reference satellite |
| **False Positive (FP)** | Observation matched to the wrong satellite, OR a non-reference observation incorrectly matched to a reference satellite |
| **False Negative (FN)** | Reference observation not matched at all (no predicted association) |

True Negatives require **non-reference satellite observations** in the dataset -- observations that the algorithm should NOT match to any candidate orbit. When `non_ref_observations` is `None`, TN = 0 (backwards-compatible behavior).

### Complete Metric Table

| Metric | Column Name | Formula / Source | Description |
|---|---|---|---|
| Total Observations | `TotalObs` | `len(ref_obs)` | Total reference observations in the dataset |
| Total Correlated | `TotalCorrelated` | Count of ref obs with a prediction | Reference observations that received a predicted satellite |
| True Positives | `TruePositives` | See above | Correctly matched reference observations |
| False Positives | `FalsePositives` | See above | Incorrectly matched observations |
| True Negatives | `TrueNegatives` | See above | Non-ref observations correctly not matched |
| False Negatives | `FalseNegatives` | See above | Reference observations with no match |
| **Accuracy** | `Accuracy` | `(TP + TN) / (TP + TN + FP + FN)` | Overall correctness rate (includes TN) |
| **Balanced Accuracy** | `BalancedAccuracy` | `(Sensitivity + Specificity) / 2` | Adjusts for class imbalance; via `sklearn.metrics.balanced_accuracy_score` |
| **Cohen's Kappa** | `CohenKappa` | `(p_o - p_e) / (1 - p_e)` | Agreement corrected for chance; via `sklearn.metrics.cohen_kappa_score` |
| **Matthews Correlation Coefficient** | `MatthewsCorrCoef` | `(TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))` | Balanced measure for all four confusion matrix quadrants; via `sklearn.metrics.matthews_corrcoef` |
| **F1 Score** | `F1Score` | `2 * Precision * Recall / (Precision + Recall)` | Harmonic mean of precision and recall; via `sklearn.metrics.f1_score` |
| **Sensitivity / Recall** | `Sensitivity` | `TP / (TP + FN)` | Fraction of true associations found; via `sklearn.metrics.recall_score` |
| **Specificity** | `Specificity` | `TN / (TN + FP)` | Fraction of non-ref observations correctly rejected |
| **Precision** | `Precision` | `TP / (TP + FP)` | Fraction of associations that are correct |
| Non-Ref Obs Count | `NonRefObsCount` | `len(non_ref_observations)` | Count of non-reference observations in dataset |
| Non-Ref Matched | `NonRefMatched` | Count of non-ref obs incorrectly matched | Should be 0 for a perfect classifier |

### sklearn Integration Detail

The code constructs synthetic `y_true` / `y_pred` vectors directly from the confusion matrix counts to ensure sklearn's metrics are mathematically consistent with the manually-computed counts:

```python
y_true = [1]*TP + [1]*FN + [0]*FP + [0]*TN
y_pred = [1]*TP + [0]*FN + [1]*FP + [0]*TN
```

This avoids semantic mismatches that could arise from naively comparing DataFrame columns.

### Interpretation Guidelines

| Metric | Good | Moderate | Poor |
|---|---|---|---|
| Precision | > 0.95 | 0.80 -- 0.95 | < 0.80 |
| Recall / Sensitivity | > 0.90 | 0.70 -- 0.90 | < 0.70 |
| F1 Score | > 0.92 | 0.75 -- 0.92 | < 0.75 |
| Balanced Accuracy | > 0.90 | 0.70 -- 0.90 | < 0.70 |
| Cohen's Kappa | > 0.80 | 0.60 -- 0.80 | < 0.60 |
| MCC | > 0.80 | 0.50 -- 0.80 | < 0.50 |

---

## 3. State Metrics

**Code**: `uct_benchmark/evaluation/stateMetrics.py` -- `stateMetrics()`, `calculate_state_metrics_single()`, `calculate_comprehensive_state_metrics()`, `calculate_radial_in_track_cross_track_errors()`, `calculate_batch_nees()`

State metrics compare each candidate orbit's estimated state vector to the propagated reference truth at the same epoch. The reference is propagated to the candidate's epoch using a Monte Carlo propagator (SV mode) or a TLE propagator (TLE mode).

### 3.1 Error Norms

| Metric | Column Name | Formula | Unit |
|---|---|---|---|
| Total Error Norm | `Total Error Norm` | `\|\|x_est - x_truth\|\|_2` (all 6 components) | km (mixed) |
| Position Error Norm | `Position Error Norm` | `\|\|pos_est - pos_truth\|\|_2` (3 position components) | km |
| Velocity Error Norm | `Velocity Error Norm` | `\|\|vel_est - vel_truth\|\|_2` (3 velocity components) | km/s |

These are always computed in both SV and TLE modes.

### 3.2 Mahalanobis Distance (SV mode only)

The Mahalanobis Distance measures how far the estimate is from truth, normalized by the **combined** covariance of both truth and estimate.

**Formula (squared):**

```
MD^2 = delta^T * (C_truth + C_est)^{-1} * delta
```

where:
- `delta = x_est - x_truth` (6D state difference)
- `C_truth` = 6x6 covariance of the propagated truth
- `C_est` = 6x6 covariance of the candidate estimate
- Inverse uses `numpy.linalg.pinv` with PSD safety fallback

| Metric | Column Name | Formula | Unit |
|---|---|---|---|
| Mahalanobis Distance | `Mahalanobis Distance` | `MD^2` (squared, not square root) | dimensionless |
| MD P-Score | `MD P-Score` | `1 - chi2.cdf(MD^2, df=6)` | probability [0, 1] |

**Key distinction**: The `stateMetrics()` function stores MD **squared** (not the square root). The `calculate_state_metrics_single()` function stores both `mahalanobis_squared` and `mahalanobis_distance` (the square root).

The P-Score is the survival function of the chi-squared distribution with 6 degrees of freedom (one per state dimension). A high P-Score (close to 1) means the error is well within the expected covariance envelope; a low P-Score (close to 0) suggests the covariance is too optimistic.

### 3.3 NEES -- Normalized Estimation Error Squared (SV mode only)

NEES measures the consistency of the **estimation covariance** alone (not the combined covariance).

**Formula:**

```
NEES = delta^T * C_est^{-1} * delta
```

where:
- `delta = x_est - x_truth` (6D state difference)
- `C_est` = 6x6 covariance of the **candidate estimate only**
- Inverse uses `numpy.linalg.pinv` with PSD safety fallback

| Metric | Column Name | Formula | Unit |
|---|---|---|---|
| NEES | `NEES` | `delta^T * C_est^{-1} * delta` | dimensionless |
| NEES P-Score | `NEES P-Score` | `1 - chi2.cdf(NEES, df=6)` | probability [0, 1] |

**Interpretation**: For a consistent (well-calibrated) estimator, the expected value of NEES equals the state dimension: `E[NEES] = 6`. If NEES >> 6, the covariance is too small (overconfident). If NEES << 6, the covariance is too large (underconfident).

### 3.4 Batch NEES Consistency Test

**Code**: `calculate_batch_nees()`

Evaluates NEES in aggregate across N samples using a chi-squared hypothesis test.

**Procedure:**

1. Compute NEES for each of N state comparisons (skip samples with non-invertible covariance).
2. Compute average NEES = `mean(NEES_values)`.
3. Under H0 (consistent estimator), `sum(NEES) ~ chi2(6 * N)`, so `avg(NEES)` has known bounds.
4. Compute chi-squared confidence interval at the specified confidence level (default 95%):
   ```
   lower = chi2.ppf(alpha/2, df=6*N) / N
   upper = chi2.ppf(1 - alpha/2, df=6*N) / N
   ```
5. The estimator is "consistent" if `lower <= average_NEES <= upper`.

| Output Field | Description |
|---|---|
| `average_nees` | Mean NEES across valid samples |
| `expected_nees` | Expected value under consistency (always 6.0) |
| `nees_std` | Standard deviation of NEES values |
| `nees_lower_bound` | Lower chi-squared bound for average NEES |
| `nees_upper_bound` | Upper chi-squared bound for average NEES |
| `is_consistent` | Boolean: average NEES within bounds |
| `confidence_level` | Confidence level used (default 0.95) |
| `n_samples` | Total input samples |
| `n_valid` | Samples with valid (invertible) covariance |

### 3.5 Per-Dimension Bias (SV mode only)

Raw per-pair, per-dimension state differences. Each row stores the bias independently; aggregate statistics (mean bias, etc.) are derived downstream.

| Metric | Column Name | Unit |
|---|---|---|
| X Position Bias | `xpos Bias` | km |
| Y Position Bias | `ypos Bias` | km |
| Z Position Bias | `zpos Bias` | km |
| X Velocity Bias | `xvel Bias` | km/s |
| Y Velocity Bias | `yvel Bias` | km/s |
| Z Velocity Bias | `zvel Bias` | km/s |
| Total Bias | `Total Bias` | sum of all 6 per-dimension biases |

### 3.6 RIC Frame Errors

**Code**: `calculate_radial_in_track_cross_track_errors()`

Transforms the ECI-frame error into the Radial-In-track-Cross-track (RIC) frame, which is more physically meaningful for orbit analysis.

**RIC frame construction from the true state:**

```
r_hat = r_true / ||r_true||                  (Radial: along position vector)
h     = r_true x v_true                      (Angular momentum vector)
c_hat = h / ||h||                            (Cross-track: normal to orbital plane)
i_hat = c_hat x r_hat                        (In-track: completes right-handed triad)

R_eci_to_ric = [r_hat; i_hat; c_hat]         (3x3 rotation matrix)

pos_error_ric = R_eci_to_ric * (r_est - r_true)
vel_error_ric = R_eci_to_ric * (v_est - v_true)
```

| Metric | Output Key | Unit |
|---|---|---|
| Radial Position Error | `radial_error_km` | km |
| In-Track Position Error | `in_track_error_km` | km |
| Cross-Track Position Error | `cross_track_error_km` | km |
| Radial Velocity Error | `radial_vel_error_km_s` | km/s |
| In-Track Velocity Error | `in_track_vel_error_km_s` | km/s |
| Cross-Track Velocity Error | `cross_track_vel_error_km_s` | km/s |
| Total RIC Position Error | `total_ric_position_error_km` | km |
| Total RIC Velocity Error | `total_ric_velocity_error_km_s` | km/s |

### 3.7 Comprehensive State Metrics (Aggregate)

**Code**: `calculate_comprehensive_state_metrics()`

Computes aggregate statistics over N state comparisons, including position/velocity error distributions, RIC error distributions, and optionally batch NEES.

| Aggregate Statistic | Computed For |
|---|---|
| Mean | Position error, velocity error, radial/in-track/cross-track errors |
| Std | Position error, velocity error, radial/in-track/cross-track errors |
| RMS | Position error, velocity error |
| Median | Position error, velocity error |
| Max | Position error, velocity error |
| Min | Position error, velocity error |

---

## 4. Residual Metrics

Residual metrics assess how well a fitted orbit explains the original observations. Two separate subsystems handle angular (optical) residuals and TLE orbital-element residuals.

### 4.1 Great Circle Distance Residuals (Optical / RA-Dec)

**Code**: `uct_benchmark/evaluation/residualMetrics.py` -- `residualMetrics()` and `retrieveResiduals()`

Also available as a standalone function: `stateMetrics.py` -- `calculate_residual_metrics()`

For each observation associated with a candidate orbit:

1. Propagate the orbit to the observation's epoch.
2. Convert the propagated position to RA/Dec.
3. Compute the great-circle angular distance between observed and predicted RA/Dec using the **Haversine formula**:

```
delta_ra  = ra_pred - ra_obs        (radians)
delta_dec = dec_pred - dec_obs       (radians)

a = sin(delta_dec/2)^2 + cos(dec_obs) * cos(dec_pred) * sin(delta_ra/2)^2
c = 2 * arctan2(sqrt(a), sqrt(1-a))

residual_arcsec = degrees(c) * 3600
```

All residuals are reported in **arcseconds**.

#### Per-Orbit Residual Statistics

| Metric | Key | Unit |
|---|---|---|
| Observation IDs | `id` | list of obs IDs |
| Epochs | `Epoch` | list of timestamps |
| Individual Residuals | `Residuals` | arcseconds (list) |
| RMSE | `RMSE` | arcseconds |
| Mean | `Mean` | arcseconds |
| Standard Deviation | `std` | arcseconds |

#### Aggregate Residual Statistics (`calculate_residual_metrics()`)

| Metric | Key | Unit |
|---|---|---|
| Count | `residual_count` | integer |
| Mean | `residual_mean_arcsec` | arcseconds |
| Standard Deviation | `residual_std_arcsec` | arcseconds |
| RMS | `residual_rms_arcsec` | arcseconds |
| Median | `residual_median_arcsec` | arcseconds |
| Max | `residual_max_arcsec` | arcseconds |
| Min | `residual_min_arcsec` | arcseconds |

#### Operating Modes

| `flag` | `flag2` | Description |
|---|---|---|
| `True` | `False` | Compare reference observations with associated orbits (SV input) |
| `False` | `False` | Compare reference observations with entire UCTP output (SV input) |
| `True` | `True` | Compare reference observations with associated orbits (TLE input) |
| `False` | `True` | Compare reference observations with entire UCTP output (TLE input) |

Propagation and residual computation are parallelized across orbits using `ProcessPoolExecutor`.

### 4.2 TLE Orbital Element Residuals

**Code**: `uct_benchmark/evaluation/residualMetrics.py` -- `residualMetricsTLE()` and `retrieveResidualsTLE()`

When evaluating TLE-mode submissions, residuals are computed on the six classical orbital elements rather than angular RA/Dec.

**Process:**

1. For each candidate TLE, propagate it to each reference TLE's epoch.
2. Parse both TLEs into orbital elements via `parse_tle()`.
3. Compute the element-by-element difference.

#### Compared Orbital Elements

| Element | Key | Unit | Derivation |
|---|---|---|---|
| Semi-Major Axis | `semiMajorAxis_km` | km | Kepler's third law from mean motion: `a = (mu * (T/(2*pi))^2)^(1/3)` |
| Eccentricity | `eccentricity` | dimensionless | Parsed directly from TLE line 2 |
| Inclination | `inclination_deg` | degrees | Parsed directly from TLE line 2 |
| RAAN | `raan_deg` | degrees | Right Ascension of Ascending Node |
| Argument of Perigee | `argPerigee_deg` | degrees | Parsed directly from TLE line 2 |
| Mean Anomaly | `meanAnomaly_deg` | degrees | Parsed directly from TLE line 2 |

#### Per-Orbit TLE Residual Statistics

For each orbital element, the following are computed across all observation-epoch comparisons:

| Statistic | Description |
|---|---|
| `RMSE` | Root mean square of element differences (array of 6 values) |
| `Mean` | Mean element difference (array of 6 values) |
| `std` | Standard deviation of element differences (array of 6 values) |

### 4.3 Residual Interpretation by Regime

| Regime | Good RMS | Moderate RMS | Poor RMS |
|---|---|---|---|
| LEO | < 5 arcsec | 5 -- 20 arcsec | > 20 arcsec |
| MEO | < 10 arcsec | 10 -- 30 arcsec | > 30 arcsec |
| GEO | < 2 arcsec | 2 -- 10 arcsec | > 10 arcsec |

---

## 5. Persistence: What Gets Saved vs. Computed On-Demand

**Code**: `uct_benchmark/evaluation/evaluationReport.py` -- `evaluationReport()`

The `evaluationReport()` function serializes all evaluation results to a JSON file. The table below clarifies which metrics are persisted and which are computed on-demand.

### Persisted to JSON (via `evaluationReport()`)

| Section | Key in JSON | Source |
|---|---|---|
| Association results | `association_results` | Dict from `orbitAssociation()` (minus `Time Elapsed`) |
| Binary metrics | `binary_results` | Full DataFrame from `binaryMetrics()`, serialized as list of records |
| State metrics | `state_results` | Full DataFrame from `stateMetrics()`, serialized as list of records |
| Reference residuals | `residual_ref_results` | DataFrame from `residualMetrics()` against reference orbits |
| Candidate residuals | `residual_cand_results` | DataFrame from `residualMetrics()` against candidate orbits |

### Computed On-Demand (not persisted by default)

| Function | Typical Usage |
|---|---|
| `calculate_state_metrics_single()` | Single-pair state comparison (API / ad-hoc analysis) |
| `calculate_comprehensive_state_metrics()` | Aggregate stats over multiple comparisons |
| `calculate_batch_nees()` | Batch NEES consistency testing |
| `calculate_radial_in_track_cross_track_errors()` | Single-pair RIC frame decomposition |
| `calculate_residual_metrics()` | Standalone great-circle residual stats |

The PDF report (`generate_pdf_report_matplotlib()` / `generate_pdf_report_reportlab()`) reads from the persisted JSON dict and produces visualizations including confusion-matrix bar charts, position-error histograms, and RA/Dec residual scatter plots.

---

## 6. Dataset Tiering

During dataset creation, data quality is assessed using a tiering system:

### Tier Definitions

| Tier | Score | Description | Processing Required |
|---|---|---|---|
| T1 | 4 | High quality | May require downsampling |
| T2 | 3 | Good quality | Requires downsampling |
| T3 | 2 | Moderate quality | Requires observation simulation |
| T4 | 1 | Low quality | Requires full object simulation |
| T5 | 0 | Unusable | Cannot create valid dataset |

### Scoring Criteria

```python
# From config.py
highPercentage = (0.9, 0.95, 1.0)     # Coverage targets
standardPercentage = (0.4, 0.5, 0.6)
lowPercentage = (0.0, 0.05, 0.1)

lowObsCount = 50                       # Observations per 3 days
highObsCount = 150

longTrackGap = 2                       # Orbital periods

highObjectCount = 80                   # Satellites in dataset
standardObjectCount = 40
lowObjectCount = 10
```

**Code Location**: `uct_benchmark/data/basicScoringFunction.py`

---

## 7. Usage Example

```python
from uct_benchmark.api.apiIntegration import loadDataset
from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
from uct_benchmark.evaluation.stateMetrics import (
    stateMetrics,
    calculate_batch_nees,
    calculate_radial_in_track_cross_track_errors,
)
from uct_benchmark.evaluation.residualMetrics import residualMetrics, residualMetricsTLE
from uct_benchmark.evaluation.evaluationReport import evaluationReport
from uct_benchmark.simulation.propagator import ephemerisPropagator

# Load data
ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset(
    "./data/output_dataset.json"
)
uctp_output = pd.read_json("./data/uctp_output.json")

# Step 1: Associate candidate orbits to reference truth
associated, assoc_results, nonassociated = orbitAssociation(
    ref_sv, uctp_output, ephemerisPropagator
)

# Step 2: Binary classification metrics
binary = binaryMetrics(ref_obs, associated, non_ref_observations=non_ref_df)

# Step 3: State estimation metrics (SV mode)
state = stateMetrics(ref_sv, associated, monteCarloPropagator)

# Step 4: Residual metrics
residual_ref = residualMetrics(ref_obs, associated, ephemerisPropagator, flag=True)
residual_cand = residualMetrics(ref_obs, uctp_output, ephemerisPropagator, flag=False)

# Step 5: Persist results
evals = evaluationReport(
    assoc_results, binary, state, residual_ref, residual_cand, "evaluation.json"
)

# Print key results
print(f"F1 Score:          {binary['F1Score'].iloc[0]:.3f}")
print(f"Balanced Accuracy: {binary['BalancedAccuracy'].iloc[0]:.3f}")
print(f"Cohen's Kappa:     {binary['CohenKappa'].iloc[0]:.3f}")
print(f"MCC:               {binary['MatthewsCorrCoef'].iloc[0]:.3f}")
print(f"Position RMS:      {state['Position Error Norm'].mean():.2f} km")
print(f"Mean NEES:         {state['NEES'].mean():.2f}")

# Optional: RIC errors for a single pair
ric = calculate_radial_in_track_cross_track_errors(true_state, est_state)
print(f"Radial error:      {ric['radial_error_km']:.4f} km")
print(f"In-track error:    {ric['in_track_error_km']:.4f} km")
print(f"Cross-track error: {ric['cross_track_error_km']:.4f} km")
```
