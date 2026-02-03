# -*- coding: utf-8 -*-
"""
Tests for True Negative calculation in binary metrics.

Per Louis's Benchmarking Documentation:
- True Positive (TP): Observation correctly matched to reference satellite
- True Negative (TN): Non-reference observation correctly NOT matched
- False Positive (FP): Observation incorrectly matched to wrong satellite
- False Negative (FN): Reference observation not matched

These tests verify:
1. TN calculated correctly with non-ref observations
2. TN=0 when no non-ref observations (backwards compat)
3. Accuracy includes TN: (TP+TN)/(TP+TN+FP+FN)
4. Specificity calculation: TN/(TN+FP)
5. Non-ref observation generation from different satellites
6. Non-ref ratio parameter is honored

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestBinaryMetricsWithTrueNegatives:
    """Test suite for True Negative support in binary metrics."""

    def test_tn_with_non_ref_observations(self):
        """Verify TN calculated correctly with non-ref obs."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        # Setup: Reference observations from satellites 1, 2, 3
        ref_obs = pd.DataFrame({
            "id": ["obs1", "obs2", "obs3", "obs4", "obs5"],
            "satNo": [1, 1, 2, 2, 3],
        })

        # Algorithm correctly matches all reference observations
        associated_orbits = pd.DataFrame({
            "satNo": [1, 2, 3],
            "sourcedData": [["obs1", "obs2"], ["obs3", "obs4"], ["obs5"]],
        })

        # Non-reference observations from satellite 99 (not in reference set)
        # These SHOULD NOT be matched by the algorithm
        non_ref_obs = pd.DataFrame({
            "id": ["nonref1", "nonref2", "nonref3"],
            "source_norad_id": [99, 99, 99],
        })

        # Algorithm correctly does NOT match the non-ref observations
        # (they don't appear in associated_orbits)

        result = binaryMetrics(
            ref_obs, associated_orbits,
            non_ref_observations=non_ref_obs,
            reference_satellites=[1, 2, 3],
        )

        # Should have:
        # TP = 5 (all ref obs correctly matched)
        # TN = 3 (all non-ref obs correctly NOT matched)
        # FP = 0
        # FN = 0
        assert result["TruePositives"].iloc[0] == 5
        assert result["TrueNegatives"].iloc[0] == 3
        assert result["FalsePositives"].iloc[0] == 0
        assert result["FalseNegatives"].iloc[0] == 0

    def test_tn_zero_when_no_non_ref(self):
        """Verify TN=0 when no non-ref observations (backwards compat)."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame({
            "id": ["obs1", "obs2", "obs3"],
            "satNo": [1, 2, 3],
        })

        associated_orbits = pd.DataFrame({
            "satNo": [1, 2, 3],
            "sourcedData": [["obs1"], ["obs2"], ["obs3"]],
        })

        # No non-reference observations provided
        result = binaryMetrics(ref_obs, associated_orbits)

        # TN should be 0 when no non-ref observations
        assert result["TrueNegatives"].iloc[0] == 0

    def test_accuracy_includes_tn(self):
        """Verify accuracy formula: (TP+TN)/(TP+TN+FP+FN)."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        # Setup: 4 ref obs, 2 non-ref obs
        ref_obs = pd.DataFrame({
            "id": ["obs1", "obs2", "obs3", "obs4"],
            "satNo": [1, 1, 2, 2],
        })

        # Algorithm matches 3 correctly, 1 wrong (FP), misses none
        associated_orbits = pd.DataFrame({
            "satNo": [1, 2, 3],  # 3 is wrong satellite for some obs
            "sourcedData": [["obs1", "obs2"], ["obs3"], ["obs4"]],  # obs4 matched to wrong sat
        })

        non_ref_obs = pd.DataFrame({
            "id": ["nonref1", "nonref2"],
            "source_norad_id": [99, 99],
        })

        result = binaryMetrics(
            ref_obs, associated_orbits,
            non_ref_observations=non_ref_obs,
            reference_satellites=[1, 2],
        )

        # TP = 3 (obs1, obs2, obs3 correctly matched)
        # TN = 2 (non-ref observations not matched)
        # FP = 1 (obs4 matched to wrong satellite 3)
        # FN = 0 (all obs matched)

        tp = result["TruePositives"].iloc[0]
        tn = result["TrueNegatives"].iloc[0]
        fp = result["FalsePositives"].iloc[0]
        fn = result["FalseNegatives"].iloc[0]

        expected_accuracy = (tp + tn) / (tp + tn + fp + fn)
        actual_accuracy = result["Accuracy"].iloc[0]

        assert abs(actual_accuracy - expected_accuracy) < 0.001

    def test_specificity_calculation(self):
        """Verify specificity formula: TN/(TN+FP)."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame({
            "id": ["obs1", "obs2"],
            "satNo": [1, 1],
        })

        # Algorithm correctly matches both
        associated_orbits = pd.DataFrame({
            "satNo": [1],
            "sourcedData": [["obs1", "obs2"]],
        })

        # 4 non-ref observations, algorithm incorrectly matches 1 to a ref satellite
        non_ref_obs = pd.DataFrame({
            "id": ["nonref1", "nonref2", "nonref3", "nonref4"],
            "source_norad_id": [99, 99, 99, 99],
        })

        # Simulate algorithm incorrectly matching nonref1 to satellite 1
        associated_orbits_with_error = pd.DataFrame({
            "satNo": [1],
            "sourcedData": [["obs1", "obs2", "nonref1"]],  # nonref1 incorrectly matched
        })

        result = binaryMetrics(
            ref_obs, associated_orbits_with_error,
            non_ref_observations=non_ref_obs,
            reference_satellites=[1],
        )

        # TN = 3 (nonref2, nonref3, nonref4 correctly not matched)
        # FP = 1 (nonref1 incorrectly matched to reference satellite)
        # Specificity = 3 / (3 + 1) = 0.75

        tn = result["TrueNegatives"].iloc[0]
        fp = result["FalsePositives"].iloc[0]

        assert tn == 3
        # FP should include the incorrectly matched non-ref observation
        assert fp >= 1

        if (tn + fp) > 0:
            expected_specificity = tn / (tn + fp)
            actual_specificity = result["Specificity"].iloc[0]
            assert abs(actual_specificity - expected_specificity) < 0.001


class TestNonRefObservationGeneration:
    """Tests for non-reference observation generation."""

    def test_non_ref_observation_generation(self):
        """Verify non-ref obs are from different satellites."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        # Reference observations from satellites 1, 2, 3
        ref_obs = pd.DataFrame({
            "id": [f"ref_{i}" for i in range(100)],
            "satNo": [1] * 30 + [2] * 40 + [3] * 30,
            "obTime": pd.date_range("2025-01-01", periods=100, freq="h"),
        })
        reference_norad_ids = [1, 2, 3]

        # All observations including non-reference
        all_obs = pd.DataFrame({
            "id": [f"ref_{i}" for i in range(100)] + [f"nonref_{i}" for i in range(50)],
            "satNo": [1] * 30 + [2] * 40 + [3] * 30 + [99] * 25 + [100] * 25,
            "obTime": pd.date_range("2025-01-01", periods=150, freq="h"),
        })

        combined, non_ref_truth = add_non_reference_observations(
            ref_obs,
            reference_norad_ids,
            all_observations_df=all_obs,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Verify non-ref observations are NOT from reference satellites
        if not non_ref_truth.empty:
            non_ref_sats = set(non_ref_truth["source_norad_id"].unique())
            ref_sat_set = set(reference_norad_ids)
            assert non_ref_sats.isdisjoint(ref_sat_set), \
                f"Non-ref satellites {non_ref_sats} should not overlap with reference {ref_sat_set}"

    def test_non_ref_ratio_respected(self):
        """Verify non_ref_ratio parameter affects number of non-ref satellites selected.

        Per Louis's specification, each non-ref satellite gets exactly 2 observations
        (to make IOD impossible). The ratio controls how many satellites are selected.
        """
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        ref_obs = pd.DataFrame({
            "id": [f"ref_{i}" for i in range(100)],
            "satNo": [1] * 50 + [2] * 50,
            "obTime": pd.date_range("2025-01-01", periods=100, freq="h"),
        })
        reference_norad_ids = [1, 2]

        # Include multiple non-reference satellites to test ratio-based selection
        all_obs = pd.DataFrame({
            "id": [f"ref_{i}" for i in range(100)] + [f"nonref_{i}" for i in range(200)],
            "satNo": [1] * 50 + [2] * 50 + [99] * 50 + [98] * 50 + [97] * 50 + [96] * 50,
            "obTime": list(pd.date_range("2025-01-01", periods=100, freq="h")) +
                     list(pd.date_range("2025-01-01", periods=200, freq="h")),
        })

        # Test with 20% ratio
        combined, non_ref_truth = add_non_reference_observations(
            ref_obs,
            reference_norad_ids,
            all_observations_df=all_obs,
            non_ref_ratio=0.2,
            seed=42,
        )

        # Per Louis's spec: each non-ref satellite gets exactly 2 observations
        # With 20% ratio of 100 = 20 target non-ref obs
        # 20 obs / 2 per satellite = 10 satellites max
        # But we only have 4 non-ref satellites, so max is 8 observations
        actual_non_ref = len(non_ref_truth)

        # Each satellite should have exactly 2 observations
        if not non_ref_truth.empty:
            for sat_id in non_ref_truth['source_norad_id'].unique():
                sat_count = len(non_ref_truth[non_ref_truth['source_norad_id'] == sat_id])
                assert sat_count == 2, \
                    f"Per Louis's spec, satellite {sat_id} should have exactly 2 obs, got {sat_count}"

        # Should have some non-ref observations (up to available satellites * 2)
        assert actual_non_ref > 0, "Should have at least some non-ref observations"
        assert actual_non_ref <= 8, "Should not exceed available non-ref satellites * 2"


class TestCalculateBinaryMetricsFunction:
    """Tests for the calculate_binary_metrics function."""

    def test_calculate_binary_metrics_basic(self):
        """Test calculate_binary_metrics with basic input."""
        from uct_benchmark.evaluation.binaryMetrics import calculate_binary_metrics

        matches = [
            {"obs_id": "1", "true_sat": 1, "pred_sat": 1},  # TP
            {"obs_id": "2", "true_sat": 1, "pred_sat": 1},  # TP
            {"obs_id": "3", "true_sat": 2, "pred_sat": 3},  # FP
            {"obs_id": "4", "true_sat": 2, "pred_sat": None},  # FN
        ]
        reference_satellites = [1, 2]
        total_observations = 4

        result = calculate_binary_metrics(
            matches=matches,
            reference_satellites=reference_satellites,
            total_observations=total_observations,
        )

        assert result["true_positives"] == 2
        assert result["false_positives"] == 1
        assert result["false_negatives"] == 1
        assert result["true_negatives"] == 0  # No non-ref obs provided

    def test_calculate_binary_metrics_with_non_ref(self):
        """Test calculate_binary_metrics with non-ref observations."""
        from uct_benchmark.evaluation.binaryMetrics import calculate_binary_metrics

        matches = [
            {"obs_id": "1", "true_sat": 1, "pred_sat": 1},  # TP
            {"obs_id": "2", "true_sat": 1, "pred_sat": 1},  # TP
        ]
        reference_satellites = [1]
        total_observations = 2

        non_ref_observations = [
            {"id": "nr1", "source_norad_id": 99},
            {"id": "nr2", "source_norad_id": 99},
            {"id": "nr3", "source_norad_id": 99},
        ]

        # Algorithm incorrectly matched 1 non-ref observation
        algorithm_non_ref_matches = [
            {"id": "nr1", "matched_to": 1},  # Incorrectly matched
        ]

        result = calculate_binary_metrics(
            matches=matches,
            reference_satellites=reference_satellites,
            total_observations=total_observations,
            non_ref_observations=non_ref_observations,
            algorithm_non_ref_matches=algorithm_non_ref_matches,
        )

        assert result["true_positives"] == 2
        assert result["true_negatives"] == 2  # 3 non-ref - 1 incorrectly matched
        assert result["non_ref_observation_count"] == 3
        assert result["non_ref_incorrectly_matched"] == 1


class TestIntegrationWithDatasetGeneration:
    """Integration tests with dataset generation pipeline."""

    def test_generate_dataset_with_non_reference(self):
        """Test generate_dataset_with_non_reference function."""
        pytest.importorskip("uct_benchmark.data.dataManipulation")
        from uct_benchmark.data.dataManipulation import generate_dataset_with_non_reference

        # Create mock observations
        obs_df = pd.DataFrame({
            "id": [f"obs_{i}" for i in range(200)],
            "satNo": [1] * 50 + [2] * 50 + [3] * 50 + [99] * 50,  # 99 is non-ref
            "obTime": pd.date_range("2025-01-01", periods=200, freq="h"),
            "ra": np.random.uniform(0, 360, 200),
            "declination": np.random.uniform(-90, 90, 200),
        })

        sat_params = {
            1: {"Semi-Major Axis": 7000, "Period": 5400},
            2: {"Semi-Major Axis": 7000, "Period": 5400},
            3: {"Semi-Major Axis": 7000, "Period": 5400},
            99: {"Semi-Major Axis": 7000, "Period": 5400},
        }

        reference_norad_ids = [1, 2, 3]

        # Generate dataset with non-reference observations
        dataset_df, non_ref_truth, metadata = generate_dataset_with_non_reference(
            obs_df=obs_df,
            sat_params=sat_params,
            reference_norad_ids=reference_norad_ids,
            include_non_ref_obs=True,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Verify results
        assert metadata["include_non_ref_obs"] == True
        assert metadata["reference_satellite_count"] > 0

        # If non-ref obs were added, verify they're from non-reference satellites
        if not non_ref_truth.empty:
            non_ref_sats = set(non_ref_truth["source_norad_id"].unique())
            ref_set = set(reference_norad_ids)
            assert non_ref_sats.isdisjoint(ref_set)
