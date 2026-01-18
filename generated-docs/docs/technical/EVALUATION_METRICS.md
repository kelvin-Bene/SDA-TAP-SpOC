# Evaluation Metrics

## Overview

The evaluation system assesses UCTP algorithm performance through three categories of metrics:
1. **Binary Metrics** - Classification performance
2. **State Metrics** - Orbital state accuracy
3. **Residual Metrics** - Observation fit quality

---

## Evaluation Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Reference      │     │  UCTP Output    │     │  Association    │
│  Ground Truth   │────▶│  State Vectors  │────▶│  Results        │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
         ┌───────────────────────────────────────────────┼───────┐
         │                                               │       │
         ▼                                               ▼       ▼
┌─────────────────┐                             ┌─────────────────┐
│  Binary         │                             │  State          │
│  Metrics        │                             │  Metrics        │
└─────────────────┘                             └─────────────────┘
         │                                               │
         └───────────────────────┬───────────────────────┘
                                 ▼
                        ┌─────────────────┐
                        │  Residual       │
                        │  Metrics        │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  PDF Report     │
                        └─────────────────┘
```

---

## 1. Orbit Association

Before computing metrics, UCTP output must be associated with reference orbits. The UCTP does not tell us which reference object corresponds to which candidate - it just says "these observations are correlated and this is the orbit."

Per tech lead Lewis:
> "The UCT processor is not going to tell us 'Oh, we think this is this object.' It's just gonna say all of these observations are correlated with each other and this is the orbit the object is in. So we need to figure out which one of the candidate orbits that the UCT processor identified corresponds to which one of the reference objects that we put into the initial data set."

### Algorithm: Hungarian Method (with Euclidean Norm)

The association process uses the Hungarian algorithm (linear sum assignment) to find globally optimal matches.

**Process** (as described by Lewis):
1. Take the candidate orbit from UCTP output
2. Propagate it to the same time epoch as the reference orbit
3. Compute the Euclidean norm (closest in position/velocity space)
4. Build cost matrix C[i,j] = position error between estimated orbit i and reference orbit j
5. Solve assignment problem to minimize total error
6. Each candidate orbit maps one-to-one with reference orbits

**Code Location**: `uct_benchmark/evaluation/orbitAssociation.py`

### Association Results

| Metric | Description |
|--------|-------------|
| Associated Orbit Count | Number of successful matches |
| Non-Associated Orbit Count | UCTP outputs without matches (false discoveries) |
| Undiscovered Reference Orbits | Reference orbits not matched (missed detections) |
| Association Time | Computation time |

---

## 2. Binary Metrics

Classification metrics measure how well the UCTP identifies and associates observations.

### Definitions

| Metric | Formula | Description |
|--------|---------|-------------|
| True Positive (TP) | - | Correct observation-to-orbit association |
| False Positive (FP) | - | Incorrect association (wrong orbit assigned) |
| False Negative (FN) | - | Missed association (observation not correlated) |
| True Negative (TN) | - | Correctly rejected spurious detection |

### Computed Metrics

```
Precision = TP / (TP + FP)
    - Of all associations made, what fraction are correct?

Recall = TP / (TP + FN)
    - Of all true associations, what fraction were found?

F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
    - Harmonic mean balancing precision and recall

Accuracy = (TP + TN) / (TP + TN + FP + FN)
    - Overall correctness rate
```

### Interpretation

| Metric | Good | Moderate | Poor |
|--------|------|----------|------|
| Precision | >0.95 | 0.80-0.95 | <0.80 |
| Recall | >0.90 | 0.70-0.90 | <0.70 |
| F1-Score | >0.92 | 0.75-0.92 | <0.75 |

**Code Location**: `uct_benchmark/evaluation/binaryMetrics.py`

---

## 3. State Metrics

State metrics compare estimated orbital states to reference truth.

### Position Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| Position Error Mean | Average position difference | km |
| Position Error Std | Standard deviation of position error | km |
| Position Error Max | Maximum position error | km |
| Position Error 95th Percentile | 95% of errors below this value | km |

### Velocity Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| Velocity Error Mean | Average velocity difference | km/s |
| Velocity Error Std | Standard deviation of velocity error | km/s |
| Velocity Error Max | Maximum velocity error | km/s |

### Statistical Measures

```
Mahalanobis Distance = sqrt((x_est - x_ref)^T * P^-1 * (x_est - x_ref))
    - Normalized error accounting for covariance
    - Values near 1.0 indicate well-calibrated uncertainty

RMS Error = sqrt(mean(error^2))
    - Root mean square of position or velocity errors
```

### Covariance Consistency

The covariance provided by the UCTP is evaluated for consistency:

```
Normalized Estimation Error Squared (NEES):
    NEES = (x_est - x_ref)^T * P_est^-1 * (x_est - x_ref)

For consistent estimator: E[NEES] ≈ n (state dimension)
```

**Code Location**: `uct_benchmark/evaluation/stateMetrics.py`

---

## 4. Residual Metrics

Residual metrics assess how well the fitted orbit explains the observations.

### Observation Residuals

For each observation in the dataset, compute:

```
Predicted = propagate(estimated_orbit, observation_time)
Observed = actual_observation

Residual = Observed - Predicted
```

### Angular Residuals (Optical Sensors)

| Metric | Description | Unit |
|--------|-------------|------|
| RA Residual Mean | Mean right ascension residual | arcsec |
| RA Residual RMS | RMS right ascension residual | arcsec |
| Dec Residual Mean | Mean declination residual | arcsec |
| Dec Residual RMS | RMS declination residual | arcsec |
| Cross-Track Residual | Residual perpendicular to velocity | arcsec |
| Along-Track Residual | Residual parallel to velocity | arcsec |

### Range Residuals (Radar Sensors)

| Metric | Description | Unit |
|--------|-------------|------|
| Range Residual Mean | Mean range residual | km |
| Range Residual RMS | RMS range residual | km |
| Range Rate Residual Mean | Mean range rate residual | km/s |
| Range Rate Residual RMS | RMS range rate residual | km/s |

### Interpretation

| Regime | Good RMS | Moderate RMS | Poor RMS |
|--------|----------|--------------|----------|
| LEO | <5 arcsec | 5-20 arcsec | >20 arcsec |
| MEO | <10 arcsec | 10-30 arcsec | >30 arcsec |
| GEO | <2 arcsec | 2-10 arcsec | >10 arcsec |

**Code Location**: `uct_benchmark/evaluation/residualMetrics.py`

---

## 5. Dataset Tiering

During dataset creation, data quality is assessed using a tiering system:

### Tier Definitions

| Tier | Score | Description | Processing Required |
|------|-------|-------------|---------------------|
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

## 6. Report Generation

The evaluation results are compiled into a PDF report.

### Report Sections

1. **Executive Summary**
   - Overall performance score
   - Key metrics at a glance

2. **Association Results**
   - Number of associations
   - Discovery rate
   - False alarm rate

3. **Binary Metrics**
   - Precision/Recall curves
   - Confusion matrix
   - F1-Score breakdown

4. **State Accuracy**
   - Position/velocity error histograms
   - Error vs. time plots
   - Covariance consistency

5. **Residual Analysis**
   - Residual distributions
   - Residual vs. observation time
   - Sensor-specific breakdowns

### Report Output

```python
from uct_benchmark.utils.generatePDF import generatePDF

evals = evaluationReport(
    association_results,
    binary_results,
    state_results,
    residual_results_ref,
    residual_results_cand,
    output_path
)

generatePDF(evals, "evaluation_report.pdf")
```

**Code Location**: `uct_benchmark/utils/generatePDF.py`

---

## 7. Benchmark Comparison

For comparing multiple UCTP algorithms:

### Ranking Methodology

1. **Weighted Score**: Combine metrics with configurable weights
   ```
   Score = w1*F1 + w2*(1/PositionRMS) + w3*(1/ResidualRMS)
   ```

2. **Pareto Front**: Identify algorithms with best trade-offs

3. **Statistical Testing**: Determine significant differences

### Leaderboard Metrics

| Rank | Primary | Secondary | Tertiary |
|------|---------|-----------|----------|
| 1 | F1-Score | Position RMS | Residual RMS |
| 2 | Recall | Velocity RMS | Runtime |
| 3 | Precision | Covariance Consistency | - |

---

## Usage Example

```python
from uct_benchmark.api.apiIntegration import loadDataset
from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
from uct_benchmark.evaluation.stateMetrics import stateMetrics
from uct_benchmark.evaluation.residualMetrics import residualMetrics
from uct_benchmark.simulation.propagator import ephemerisPropagator

# Load data
ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset(
    "./data/output_dataset.json"
)
uctp_output = pd.read_json("./data/uctp_output.json")

# Associate orbits
associated, results, nonassociated = orbitAssociation(
    ref_sv, uctp_output, ephemerisPropagator
)

# Compute metrics
binary = binaryMetrics(ref_obs, associated)
state = stateMetrics(ref_sv, associated, monteCarloPropagator)
residual = residualMetrics(ref_obs, associated, ephemerisPropagator, True)

# Print results
print(f"F1-Score: {binary['F1-Score']:.3f}")
print(f"Position RMS: {state['Position Error RMS']:.2f} km")
print(f"Residual RMS: {residual['RA Residual RMS']:.2f} arcsec")
```
