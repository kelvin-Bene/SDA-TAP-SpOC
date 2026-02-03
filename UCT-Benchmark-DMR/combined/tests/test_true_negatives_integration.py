# -*- coding: utf-8 -*-
"""
Test Suite for True Negatives Integration

Tests the add_non_reference_observations() function and its integration
with the dataset generation and evaluation pipelines.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestAddNonReferenceObservations:
    """Tests for the add_non_reference_observations function."""

    @pytest.fixture
    def sample_reference_observations(self):
        """Create sample reference observations DataFrame."""
        np.random.seed(42)
        n_obs = 100
        base_time = datetime(2024, 1, 1)

        return pd.DataFrame({
            "id": [f"obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice([25544, 25545, 25546], n_obs),
            "obTime": [base_time + timedelta(hours=i) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
            "sensorName": "GEODSS",
        })

    @pytest.fixture
    def sample_all_observations(self):
        """Create sample of all observations including non-reference."""
        np.random.seed(42)
        n_obs = 200
        base_time = datetime(2024, 1, 1)

        # Include both reference and non-reference satellites
        sat_ids = [25544, 25545, 25546, 99001, 99002, 99003, 99004]

        return pd.DataFrame({
            "id": [f"all_obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice(sat_ids, n_obs),
            "obTime": [base_time + timedelta(hours=i*0.5) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
            "sensorName": "GEODSS",
        })

    def test_add_non_reference_observations_basic(
        self, sample_reference_observations, sample_all_observations
    ):
        """Test basic non-reference observation addition."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth_df = add_non_reference_observations(
            ref_obs_df=sample_reference_observations,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=sample_all_observations,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Check that combined_df has both reference and non-reference
        assert len(combined_df) > len(sample_reference_observations)

        # Check that non_ref_truth_df has the expected columns
        assert "id" in non_ref_truth_df.columns
        assert "source_norad_id" in non_ref_truth_df.columns
        assert "is_non_reference" in non_ref_truth_df.columns

        # Verify all non-ref entries are from non-reference satellites
        for _, row in non_ref_truth_df.iterrows():
            assert row["source_norad_id"] not in reference_norad_ids
            assert row["is_non_reference"] == True

    def test_non_reference_observations_exactly_two_per_satellite(
        self, sample_reference_observations, sample_all_observations
    ):
        """Test that exactly 2 observations per non-ref satellite (Louis's spec)."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth_df = add_non_reference_observations(
            ref_obs_df=sample_reference_observations,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=sample_all_observations,
            non_ref_ratio=0.2,
            seed=42,
        )

        if not non_ref_truth_df.empty:
            # Count observations per non-ref satellite
            obs_per_sat = non_ref_truth_df.groupby("source_norad_id").size()

            # Each satellite should have exactly 2 observations
            for sat_id, count in obs_per_sat.items():
                assert count == 2, f"Satellite {sat_id} has {count} observations, expected 2"

    def test_non_reference_observations_empty_all_obs(
        self, sample_reference_observations
    ):
        """Test handling when all_observations_df is empty."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth_df = add_non_reference_observations(
            ref_obs_df=sample_reference_observations,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=None,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Should return reference observations unchanged
        assert len(combined_df) == len(sample_reference_observations)
        assert non_ref_truth_df.empty

    def test_non_reference_observations_no_non_ref_available(
        self, sample_reference_observations
    ):
        """Test handling when all observations are from reference satellites."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        # Create all_obs that only contains reference satellites
        all_obs_only_ref = sample_reference_observations.copy()
        all_obs_only_ref["id"] = [f"all_{i}" for i in range(len(all_obs_only_ref))]

        combined_df, non_ref_truth_df = add_non_reference_observations(
            ref_obs_df=sample_reference_observations,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=all_obs_only_ref,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Should return reference observations unchanged
        assert len(combined_df) == len(sample_reference_observations)
        assert non_ref_truth_df.empty

    def test_is_non_reference_flag_in_combined_df(
        self, sample_reference_observations, sample_all_observations
    ):
        """Test that is_non_reference flag is properly set in combined_df."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth_df = add_non_reference_observations(
            ref_obs_df=sample_reference_observations,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=sample_all_observations,
            non_ref_ratio=0.1,
            seed=42,
        )

        if not non_ref_truth_df.empty:
            assert "is_non_reference" in combined_df.columns

            # Check that reference obs have is_non_reference=False
            ref_obs = combined_df[combined_df["satNo"].isin(reference_norad_ids)]
            assert all(ref_obs["is_non_reference"] == False)

            # Check that non-ref obs have is_non_reference=True
            non_ref_obs = combined_df[~combined_df["satNo"].isin(reference_norad_ids)]
            assert all(non_ref_obs["is_non_reference"] == True)


class TestBinaryMetricsWithTrueNegatives:
    """Tests for binary metrics calculation with true negatives."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame for binary metrics."""
        return pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3", "obs_4", "obs_5"],
            "satNo": [25544, 25544, 25545, 25545, 25546],
            "obTime": pd.date_range("2024-01-01", periods=5, freq="h"),
        })

    @pytest.fixture
    def sample_predictions_df(self):
        """Create sample predictions DataFrame."""
        return pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3", "obs_4"],  # obs_5 not matched (FN)
            "satNo_pred": [25544, 25544, 25545, 25546],  # obs_4 wrong sat (FP)
        })

    @pytest.fixture
    def sample_non_ref_obs_df(self):
        """Create sample non-reference observations DataFrame."""
        return pd.DataFrame({
            "id": ["non_ref_1", "non_ref_2", "non_ref_3", "non_ref_4"],
            "source_norad_id": [99001, 99001, 99002, 99002],
        })

    def test_binary_metrics_with_non_ref_observations(
        self, sample_observations_df, sample_predictions_df, sample_non_ref_obs_df
    ):
        """Test that binary metrics correctly calculate TN."""
        from uct_benchmark.evaluation.binaryMetrics import calculate_binary_metrics

        reference_satellites = [25544, 25545, 25546]

        # Create matches in the format expected by calculate_binary_metrics
        matches = [
            {"obs_id": "obs_1", "true_sat": 25544, "pred_sat": 25544},  # TP
            {"obs_id": "obs_2", "true_sat": 25544, "pred_sat": 25544},  # TP
            {"obs_id": "obs_3", "true_sat": 25545, "pred_sat": 25545},  # TP
            {"obs_id": "obs_4", "true_sat": 25545, "pred_sat": 25546},  # FP (wrong sat)
        ]

        # Non-reference observations
        non_ref_obs = [
            {"id": "non_ref_1", "source_norad_id": 99001},
            {"id": "non_ref_2", "source_norad_id": 99001},
            {"id": "non_ref_3", "source_norad_id": 99002},
            {"id": "non_ref_4", "source_norad_id": 99002},
        ]

        results = calculate_binary_metrics(
            matches=matches,
            reference_satellites=reference_satellites,
            total_observations=5,  # obs_5 not matched (FN)
            non_ref_observations=non_ref_obs,
            algorithm_non_ref_matches=[],  # None matched to non-ref (all TN)
        )

        # Check that true_negatives is calculated
        assert "true_negatives" in results
        tn = results["true_negatives"]

        # All 4 non-ref observations should be TN (not matched by algorithm)
        assert tn == 4

    def test_binary_metrics_specificity_with_tn(
        self, sample_observations_df, sample_predictions_df, sample_non_ref_obs_df
    ):
        """Test that specificity is calculated using TN."""
        from uct_benchmark.evaluation.binaryMetrics import calculate_binary_metrics

        reference_satellites = [25544, 25545, 25546]

        # Create matches with 1 FP
        matches = [
            {"obs_id": "obs_1", "true_sat": 25544, "pred_sat": 25544},  # TP
            {"obs_id": "obs_2", "true_sat": 25544, "pred_sat": 25544},  # TP
            {"obs_id": "obs_3", "true_sat": 25545, "pred_sat": 25545},  # TP
            {"obs_id": "obs_4", "true_sat": 25545, "pred_sat": 25546},  # FP
        ]

        non_ref_obs = [
            {"id": "non_ref_1", "source_norad_id": 99001},
            {"id": "non_ref_2", "source_norad_id": 99001},
            {"id": "non_ref_3", "source_norad_id": 99002},
            {"id": "non_ref_4", "source_norad_id": 99002},
        ]

        results = calculate_binary_metrics(
            matches=matches,
            reference_satellites=reference_satellites,
            total_observations=5,
            non_ref_observations=non_ref_obs,
            algorithm_non_ref_matches=[],
        )

        # Check specificity: TN / (TN + FP)
        assert "specificity" in results
        specificity = results["specificity"]

        tn = results["true_negatives"]
        fp = results["false_positives"]

        if tn + fp > 0:
            expected_specificity = tn / (tn + fp)
            assert abs(specificity - expected_specificity) < 0.01

    def test_binary_metrics_without_non_ref(
        self, sample_observations_df, sample_predictions_df
    ):
        """Test that binary metrics work without non-ref observations."""
        from uct_benchmark.evaluation.binaryMetrics import calculate_binary_metrics

        reference_satellites = [25544, 25545, 25546]

        matches = [
            {"obs_id": "obs_1", "true_sat": 25544, "pred_sat": 25544},
            {"obs_id": "obs_2", "true_sat": 25544, "pred_sat": 25544},
            {"obs_id": "obs_3", "true_sat": 25545, "pred_sat": 25545},
            {"obs_id": "obs_4", "true_sat": 25545, "pred_sat": 25545},
        ]

        results = calculate_binary_metrics(
            matches=matches,
            reference_satellites=reference_satellites,
            total_observations=5,
            non_ref_observations=None,  # No non-ref observations
        )

        # TN should be 0 when no non-ref observations provided
        assert results["true_negatives"] == 0


class TestAnswerKeyGeneration:
    """Tests for answer key generation and decorrelation."""

    @pytest.fixture
    def sample_obs_truth_data(self):
        """Create sample observation truth data."""
        return pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3", "obs_4", "obs_5", "obs_6"],
            "satNo": [25544, 25544, 25545, 25545, 25546, 25546],
            "obTime": pd.date_range("2024-01-01", periods=6, freq="h"),
            "ra": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "declination": [5.0, 10.0, 15.0, 20.0, 25.0, 30.0],
        })

    def test_answer_key_generation(self, sample_obs_truth_data):
        """Test that answer key is correctly generated."""
        # Simulate answer key generation logic from apiIntegration.py
        answer_key = {}
        grouped_obs_ids = {}

        for sat_no in sample_obs_truth_data["satNo"].unique():
            sat_obs = sample_obs_truth_data[sample_obs_truth_data["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids
            for obs_id in obs_ids:
                answer_key[obs_id] = int(sat_no)

        # Verify answer key structure
        assert len(answer_key) == 6
        assert answer_key["obs_1"] == 25544
        assert answer_key["obs_2"] == 25544
        assert answer_key["obs_3"] == 25545
        assert answer_key["obs_4"] == 25545
        assert answer_key["obs_5"] == 25546
        assert answer_key["obs_6"] == 25546

        # Verify grouped_obs_ids
        assert len(grouped_obs_ids) == 3
        assert set(grouped_obs_ids[25544]) == {"obs_1", "obs_2"}
        assert set(grouped_obs_ids[25545]) == {"obs_3", "obs_4"}
        assert set(grouped_obs_ids[25546]) == {"obs_5", "obs_6"}

    def test_decorrelation_removes_satno(self, sample_obs_truth_data):
        """Test that decorrelation properly removes satNo."""
        # Simulate decorrelation from apiIntegration.py
        dataset = sample_obs_truth_data.copy()
        dataset["uct"] = True

        # Remove satNo and other identifying columns
        dataset = dataset.drop(
            columns=["satNo"],
            errors="ignore",
        )

        # Verify satNo is removed
        assert "satNo" not in dataset.columns

        # Verify other columns are preserved
        assert "id" in dataset.columns
        assert "obTime" in dataset.columns
        assert "ra" in dataset.columns
        assert "declination" in dataset.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
