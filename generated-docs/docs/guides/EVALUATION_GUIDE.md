# Evaluation Guide

This guide explains how to evaluate UCTP algorithm submissions against benchmark datasets.

## Overview

The evaluation pipeline:
1. Associates estimated orbits with reference (truth) orbits
2. Computes binary metrics (precision, recall, F1)
3. Computes state accuracy metrics (position/velocity error)
4. Generates a comprehensive evaluation report

## Evaluation Metrics

### Binary Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| True Positives (TP) | Correctly identified satellites | - |
| False Positives (FP) | Estimated orbits without truth match | - |
| False Negatives (FN) | Truth orbits without estimate | - |
| Precision | Fraction of estimates that are correct | TP / (TP + FP) |
| Recall | Fraction of truth orbits found | TP / (TP + FN) |
| F1 Score | Harmonic mean of precision/recall | 2 * P * R / (P + R) |

### State Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| Position Error Mean | Average position difference | km |
| Position Error RMS | Root mean square position error | km |
| Velocity Error Mean | Average velocity difference | km/s |
| Velocity Error RMS | Root mean square velocity error | km/s |
| Mahalanobis Distance | Normalized error (covariance-weighted) | unitless |

### Residual Metrics

| Metric | Description | Units |
|--------|-------------|-------|
| RA Residual RMS | Right ascension residual | arcsec |
| Dec Residual RMS | Declination residual | arcsec |

## Method 1: Web Interface

### Submit Results

1. Navigate to **Submit** in the web interface
2. Select the benchmark dataset used
3. Upload your algorithm output (JSON format)
4. Click **Submit for Evaluation**

### View Results

1. Navigate to **My Submissions**
2. Click on a completed submission
3. View detailed metrics and visualizations

### Compare on Leaderboard

1. Navigate to **Leaderboard**
2. Filter by orbital regime or tier
3. Compare your ranking against other submissions

## Method 2: Python API

### Basic Evaluation

```python
from uct_benchmark.Evaluation import evaluate_submission
from uct_benchmark.api.apiIntegration import loadDataset

# Load benchmark dataset
obs_truth, track_truth, state_truth, elset_truth = loadDataset("path/to/dataset.json")

# Load UCTP output
import json
with open("path/to/submission.json") as f:
    uctp_output = json.load(f)

# Run evaluation
results = evaluate_submission(
    uctp_output=uctp_output,
    ref_obs=obs_truth,
    ref_sv=state_truth,
    ref_elset=elset_truth,
    propagator="tle"  # or "sv" for state vector
)

# Display results
print(f"Precision: {results['precision']:.3f}")
print(f"Recall: {results['recall']:.3f}")
print(f"F1 Score: {results['f1_score']:.3f}")
print(f"Position RMS: {results['position_rms_km']:.2f} km")
```

### Detailed Evaluation

```python
from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
from uct_benchmark.evaluation.stateMetrics import stateMetrics
from uct_benchmark.evaluation.residualMetrics import residualMetrics

# Step 1: Associate orbits
associated, results_dict, nonassociated = orbitAssociation(
    truth=state_truth,
    est=uctp_output,
    propagator="tle",
    elset_mode=False
)

# Step 2: Binary metrics
binary_results = binaryMetrics(ref_obs=obs_truth, associated_orbits=associated)
print(f"TP: {binary_results['True Positives']}")
print(f"FP: {binary_results['False Positives']}")
print(f"FN: {binary_results['False Negatives']}")

# Step 3: State metrics
state_results = stateMetrics(
    ref_sv=state_truth,
    associated_orbits=associated,
    propagator="tle"
)
print(f"Position Error: {state_results['Position Error Mean']:.2f} km")

# Step 4: Residual metrics
residual_results = residualMetrics(
    ref_obs=obs_truth,
    orbits=associated,
    propagator="tle",
    is_reference=False
)
print(f"RA Residual RMS: {residual_results['RA Residual RMS']:.2f} arcsec")
```

### Generate PDF Report

```python
from uct_benchmark.utils.generatePDF import generate_evaluation_report

# Generate comprehensive report
generate_evaluation_report(
    evaluation_results=results,
    dataset_metadata=dataset_metadata,
    output_path="reports/evaluation_report.pdf"
)
```

## UCTP Output Format

Your algorithm output must follow this JSON format:

```json
[
  {
    "idStateVector": 0,
    "sourcedData": ["obs-id-1", "obs-id-2", "obs-id-3"],
    "epoch": "2026-01-15T12:00:00.000000",
    "uct": true,
    "xpos": -7365.971,
    "ypos": -1331.400,
    "zpos": 1514.249,
    "xvel": 1.977,
    "yvel": -5.225,
    "zvel": 4.473,
    "referenceFrame": "J2000",
    "cov": [
      1.0, 0.0, 0.0, 0.0, 0.0, 0.0,
      0.0, 1.0, 0.0, 0.0, 0.0, 0.0,
      0.0, 0.0, 1.0, 0.0, 0.0, 0.0,
      0.0, 0.0, 0.0, 0.001, 0.0, 0.0,
      0.0, 0.0, 0.0, 0.0, 0.001, 0.0,
      0.0, 0.0, 0.0, 0.0, 0.0, 0.001
    ],
    "rms": 1.234
  }
]
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| idStateVector | int | Unique identifier |
| sourcedData | list[str] | IDs of observations used |
| epoch | str | State epoch (ISO format) |
| xpos, ypos, zpos | float | Position (km, J2000 ECI) |
| xvel, yvel, zvel | float | Velocity (km/s, J2000 ECI) |
| referenceFrame | str | Coordinate frame (J2000) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| uct | bool | Is this an uncorrelated track |
| cov | list[float] | 6x6 covariance matrix (21 elements, upper triangular) |
| rms | float | Fit RMS from IOD |

## Understanding Results

### Good Results

- **Precision > 0.9**: Most estimates are correct
- **Recall > 0.9**: Most truth orbits were found
- **Position RMS < 1 km**: Accurate orbit determination
- **Mahalanobis < 3**: Covariance is realistic

### Common Issues

| Issue | Possible Cause |
|-------|----------------|
| Low Precision | Algorithm produces too many false associations |
| Low Recall | Algorithm misses valid satellites |
| High Position Error | Initial orbit determination quality |
| High Mahalanobis | Covariance is too optimistic |

## Validation Testing

Before submitting, validate your output:

```python
from uct_benchmark.evaluation import validate_submission

# Check format compliance
is_valid, errors = validate_submission("path/to/submission.json")

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
else:
    print("Submission format is valid")
```

---

## Related Documentation

- [Evaluation Metrics](../technical/EVALUATION_METRICS.md)
- [Architecture Overview](../technical/ARCHITECTURE.md)
- [Dataset Generation](DATASET_GENERATION.md)
