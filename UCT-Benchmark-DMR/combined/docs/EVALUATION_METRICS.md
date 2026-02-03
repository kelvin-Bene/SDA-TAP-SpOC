# Evaluation Metrics

This document describes the evaluation metrics used in the UCT Benchmark, aligned with Louis's Benchmarking Documentation.

## Binary Classification Metrics

Per Louis's Benchmarking Documentation, the following metrics are used to evaluate UCT algorithm performance:

| Metric | Definition | Formula |
|--------|------------|---------|
| True Positive (TP) | Observation correctly matched to reference satellite | - |
| True Negative (TN) | Non-reference observation correctly NOT matched | - |
| False Positive (FP) | Observation incorrectly matched to wrong satellite | - |
| False Negative (FN) | Reference observation not matched | - |

### Precision

Precision measures the accuracy of positive predictions:

```
Precision = TP / (TP + FP)
```

High precision means that when the algorithm matches an observation, it's usually correct.

### Recall (Sensitivity)

Recall measures how many reference observations were correctly matched:

```
Recall = TP / (TP + FN)
```

High recall means the algorithm finds most of the reference observations.

### F1 Score

The F1 Score is the harmonic mean of precision and recall:

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

F1 balances precision and recall, useful when both matter equally.

### Accuracy

Accuracy measures overall correctness including True Negatives:

```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

**Note:** Accuracy is only meaningful when True Negatives are calculated, which requires non-reference observations in the dataset.

### Specificity

Specificity measures how well the algorithm avoids matching non-reference observations:

```
Specificity = TN / (TN + FP)
```

High specificity means the algorithm correctly ignores observations that don't belong to reference satellites.

## True Negatives: Non-Reference Observations

True Negatives require the dataset to include observations from **non-reference satellites**. These are observations that the algorithm should NOT match to any candidate orbit.

### Why True Negatives Matter

Without True Negatives, we can only measure how well the algorithm finds matches. We cannot measure how well it avoids false matches. This is critical for real-world UCT applications where algorithms must distinguish between:

1. Observations belonging to known satellites (should be matched)
2. Observations from unknown/unrelated satellites (should NOT be matched)

### Generating Datasets with TN Support

To generate datasets that support True Negative calculation:

```python
from uct_benchmark.data.dataManipulation import generate_dataset_with_non_reference

# Generate dataset with 10% non-reference observations
dataset_df, non_ref_truth, metadata = generate_dataset_with_non_reference(
    obs_df=all_observations,
    sat_params=satellite_parameters,
    reference_norad_ids=[25544, 28654, 33591],  # ISS, ENVISAT, etc.
    include_non_ref_obs=True,
    non_ref_ratio=0.1,  # 10% of observations from non-reference satellites
    seed=42,
)
```

### Evaluating with True Negatives

When evaluating submissions:

```python
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

results = binaryMetrics(
    ref_obs=reference_observations,
    associated_orbits=algorithm_output,
    non_ref_observations=non_ref_truth,
    reference_satellites=reference_norad_ids,
)

# Results now include TN, Accuracy, and Specificity
print(f"True Positives: {results['TruePositives'].iloc[0]}")
print(f"True Negatives: {results['TrueNegatives'].iloc[0]}")
print(f"Accuracy: {results['Accuracy'].iloc[0]:.4f}")
print(f"Specificity: {results['Specificity'].iloc[0]:.4f}")
```

## Additional Metrics

### Matthews Correlation Coefficient (MCC)

MCC is a balanced measure that works well even with imbalanced datasets:

```
MCC = (TP*TN - FP*FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))
```

MCC ranges from -1 to +1, where +1 is perfect prediction.

### Cohen's Kappa

Cohen's Kappa measures agreement beyond chance:

```
Kappa = (Po - Pe) / (1 - Pe)
```

Where Po is observed agreement and Pe is expected agreement by chance.

### Balanced Accuracy

For imbalanced datasets:

```
Balanced Accuracy = (Sensitivity + Specificity) / 2
```

## Summary Table

| Metric | Range | Ideal Value | Notes |
|--------|-------|-------------|-------|
| Precision | 0-1 | 1.0 | High = few false matches |
| Recall | 0-1 | 1.0 | High = finds most observations |
| F1 Score | 0-1 | 1.0 | Balance of precision/recall |
| Accuracy | 0-1 | 1.0 | Requires TN for meaning |
| Specificity | 0-1 | 1.0 | High = avoids false matches |
| MCC | -1 to 1 | 1.0 | Best single metric |
| Kappa | 0-1 | 1.0 | Agreement beyond chance |

## References

- Louis's Benchmarking Documentation (UCT Benchmark Specification)
- MATLAB UCT Benchmark Implementation
- Space-Track UCT Competition Guidelines
