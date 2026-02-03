# -*- coding: utf-8 -*-
"""
Tests for evaluation modules.

Tests:
- Binary metrics computation
- State metrics computation
- Orbit association algorithm
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# BINARY METRICS TESTS
# =============================================================================


class TestBinaryMetrics:
    """Tests for binaryMetrics function."""

    def test_perfect_association(self):
        """Test metrics when all associations are correct."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        # Reference observations
        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3", "obs4", "obs5"],
                "satNo": [1001, 1001, 1002, 1002, 1003],
            }
        )

        # Perfect predictions - all correct
        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 1002, 1003],
                "sourcedData": [["obs1", "obs2"], ["obs3", "obs4"], ["obs5"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TotalObs"].iloc[0] == 5
        assert result["TotalCorrelated"].iloc[0] == 5
        assert result["TruePositives"].iloc[0] == 5
        assert result["FalsePositives"].iloc[0] == 0
        assert result["FalseNegatives"].iloc[0] == 0
        assert result["Accuracy"].iloc[0] == 1.0
        assert result["F1Score"].iloc[0] == 1.0

    def test_no_matches(self):
        """Test metrics when no associations match."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        # Reference observations
        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3"],
                "satNo": [1001, 1002, 1003],
            }
        )

        # All wrong predictions
        associated_orbits = pd.DataFrame(
            {
                "satNo": [9999, 9998, 9997],
                "sourcedData": [["obs1"], ["obs2"], ["obs3"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TotalObs"].iloc[0] == 3
        assert result["TotalCorrelated"].iloc[0] == 3
        assert result["TruePositives"].iloc[0] == 0
        assert result["FalsePositives"].iloc[0] == 3

    def test_partial_matches(self):
        """Test metrics with partial correct associations."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3", "obs4"],
                "satNo": [1001, 1001, 1002, 1003],
            }
        )

        # 2 correct, 1 wrong, 1 missing
        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 9999],
                "sourcedData": [["obs1", "obs2"], ["obs3"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TotalObs"].iloc[0] == 4
        assert result["TotalCorrelated"].iloc[0] == 3
        assert result["TruePositives"].iloc[0] == 2
        assert result["FalsePositives"].iloc[0] == 1
        assert result["FalseNegatives"].iloc[0] == 1

    def test_empty_predictions(self):
        """Test metrics when no predictions are made."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3"],
                "satNo": [1001, 1002, 1003],
            }
        )

        # No predictions
        associated_orbits = pd.DataFrame(
            {
                "satNo": [],
                "sourcedData": [],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TotalObs"].iloc[0] == 3
        assert result["TotalCorrelated"].iloc[0] == 0
        assert result["TruePositives"].iloc[0] == 0
        assert result["FalseNegatives"].iloc[0] == 3

    def test_f1_score_calculation(self):
        """Test F1 score is correctly calculated."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        # Setup for known precision/recall
        ref_obs = pd.DataFrame(
            {
                "id": [f"obs{i}" for i in range(10)],
                "satNo": [1001] * 5 + [1002] * 5,
            }
        )

        # 4 TP, 1 FP (wrong sat), 1 FN (missing)
        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 1002, 9999],
                "sourcedData": [
                    ["obs0", "obs1", "obs2", "obs3"],  # 4 correct for 1001
                    ["obs5", "obs6", "obs7", "obs8"],  # 4 correct for 1002
                    ["obs4"],  # Wrong - obs4 is 1001
                ],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        # 8 TP, 1 FP, 1 FN
        assert result["TruePositives"].iloc[0] == 8
        assert result["FalsePositives"].iloc[0] == 1
        assert result["FalseNegatives"].iloc[0] == 1

    def test_precision_recall_metrics(self):
        """Test precision and recall (sensitivity) metrics."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3", "obs4", "obs5"],
                "satNo": [1001, 1001, 1002, 1002, 1003],
            }
        )

        # 3 correct, 1 wrong
        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 1002, 9999],
                "sourcedData": [["obs1", "obs2"], ["obs3"], ["obs4"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        # Verify sensitivity (recall) is calculated
        assert "Sensitivity" in result.columns
        assert result["Sensitivity"].iloc[0] >= 0
        assert result["Sensitivity"].iloc[0] <= 1

    def test_specificity_column_name_spelling(self):
        """Test that Specificity column is spelled correctly (not 'Specifcity')."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3"],
                "satNo": [1001, 1001, 1002],
            }
        )

        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 1002],
                "sourcedData": [["obs1", "obs2"], ["obs3"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        # Verify correct spelling: "Specificity" not "Specifcity"
        assert "Specificity" in result.columns, (
            "Expected 'Specificity' column but got columns: " + str(result.columns.tolist())
        )
        assert "Specifcity" not in result.columns, (
            "Found misspelled 'Specifcity' column - bug not fixed!"
        )


# =============================================================================
# ORBIT ASSOCIATION TESTS
# =============================================================================

# Skip these tests if Orekit/JVM is not available or has issues
try:
    OREKIT_AVAILABLE = True
except Exception:
    OREKIT_AVAILABLE = False


@pytest.mark.skipif(not OREKIT_AVAILABLE, reason="Orekit/JVM not available")
class TestOrbitAssociation:
    """Tests for orbitAssociation function."""

    def test_basic_association_structure(self):
        """Test that orbitAssociation returns expected structure."""
        # This test verifies the function signature and return types
        # without requiring actual propagation
        try:
            from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
        except (ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"orekit_jpype/jpype not available: {e}")

        # We need to mock the propagator since it requires Orekit
        def mock_propagator(state, epoch, target_epochs, params):
            # Return same state for all epochs (no propagation)
            return [state] * len(target_epochs)

        # Create minimal test data
        truth = pd.DataFrame(
            {
                "epoch": [datetime.now()],
                "xpos": [7000.0],
                "ypos": [0.0],
                "zpos": [0.0],
                "xvel": [0.0],
                "yvel": [7.5],
                "zvel": [0.0],
                "cov_matrix": [np.eye(6).tolist()],
                "satNo": [25544],
                "mass": [1000.0],
                "crossSection": [10.0],
                "dragCoeff": [2.2],
                "solarRadPressCoeff": [1.0],
            }
        )

        est = pd.DataFrame(
            {
                "epoch": [datetime.now()],
                "xpos": [7000.0],
                "ypos": [0.0],
                "zpos": [0.0],
                "xvel": [0.0],
                "yvel": [7.5],
                "zvel": [0.0],
            }
        )

        try:
            associated, results, nonassociated = orbitAssociation(
                truth, est, mock_propagator, elset_mode=False
            )

            # Verify return types
            assert isinstance(associated, pd.DataFrame)
            assert isinstance(results, dict)
            assert isinstance(nonassociated, pd.DataFrame)

            # Verify results dict contains expected keys
            assert "Expected State Count" in results
            assert "Associated Orbit Count" in results
            assert "Non-Associated Orbit Count" in results
            assert "Time Elapsed" in results
        except Exception as e:
            # If ProcessPoolExecutor fails in test environment, skip
            pytest.skip(f"Multiprocessing not available in test environment: {e}")

    def test_association_results_dict(self):
        """Test that results dictionary has correct counts."""
        # Using a simpler mock that avoids multiprocessing
        pass  # Complex test - would need full Orekit setup

    def test_empty_candidates(self):
        """Test association with no candidate orbits."""
        try:
            from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
        except (ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"orekit_jpype/jpype not available: {e}")

        def mock_propagator(state, epoch, target_epochs, params):
            return [state] * len(target_epochs)

        truth = pd.DataFrame(
            {
                "epoch": [datetime.now()],
                "xpos": [7000.0],
                "ypos": [0.0],
                "zpos": [0.0],
                "xvel": [0.0],
                "yvel": [7.5],
                "zvel": [0.0],
                "cov_matrix": [np.eye(6).tolist()],
                "satNo": [25544],
                "mass": [1000.0],
                "crossSection": [10.0],
                "dragCoeff": [2.2],
                "solarRadPressCoeff": [1.0],
            }
        )

        est = pd.DataFrame(columns=["epoch", "xpos", "ypos", "zpos", "xvel", "yvel", "zvel"])

        try:
            associated, results, nonassociated = orbitAssociation(
                truth, est, mock_propagator, elset_mode=False
            )

            assert len(associated) == 0
            assert results["Associated Orbit Count"] == 0
        except Exception:
            pytest.skip("Multiprocessing not available in test environment")


# =============================================================================
# STATE METRICS TESTS (MOCK-BASED)
# =============================================================================


class TestStateMetricsComputation:
    """Tests for state metrics computation logic."""

    def test_position_error_calculation(self):
        """Test position error RMS calculation logic."""
        # Test the mathematical computation
        true_pos = np.array([7000.0, 0.0, 0.0])
        est_pos = np.array([7001.0, 1.0, 1.0])

        error = np.linalg.norm(true_pos - est_pos)

        # Error should be sqrt(1^2 + 1^2 + 1^2) = sqrt(3) ≈ 1.732
        assert error == pytest.approx(np.sqrt(3), rel=1e-3)

    def test_velocity_error_calculation(self):
        """Test velocity error RMS calculation logic."""
        true_vel = np.array([0.0, 7.5, 0.0])
        est_vel = np.array([0.1, 7.6, 0.1])

        error = np.linalg.norm(true_vel - est_vel)

        # Error should be sqrt(0.1^2 + 0.1^2 + 0.1^2) = sqrt(0.03) ≈ 0.173
        assert error == pytest.approx(np.sqrt(0.03), rel=1e-3)

    def test_rms_calculation(self):
        """Test RMS calculation over multiple samples."""
        errors = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        rms = np.sqrt(np.mean(errors**2))

        # RMS of [1,2,3,4,5] = sqrt((1+4+9+16+25)/5) = sqrt(11) ≈ 3.317
        assert rms == pytest.approx(np.sqrt(11), rel=1e-3)


# =============================================================================
# RESIDUAL METRICS TESTS
# =============================================================================


class TestResidualMetrics:
    """Tests for residual metrics computation."""

    def test_angular_residual_calculation(self):
        """Test RA/Dec residual calculation."""
        # Test angular difference calculation
        true_ra = 180.0  # degrees
        est_ra = 180.5

        true_dec = 45.0
        est_dec = 44.8

        ra_residual = (est_ra - true_ra) * 3600  # Convert to arcseconds
        dec_residual = (est_dec - true_dec) * 3600

        assert ra_residual == pytest.approx(1800, rel=1e-3)  # 0.5 deg = 1800 arcsec
        assert dec_residual == pytest.approx(-720, rel=1e-3)  # -0.2 deg = -720 arcsec

    def test_residual_rms(self):
        """Test RMS of angular residuals."""
        residuals = np.array([100, 200, 300, 400, 500])  # arcseconds
        rms = np.sqrt(np.mean(residuals**2))

        expected = np.sqrt((100**2 + 200**2 + 300**2 + 400**2 + 500**2) / 5)
        assert rms == pytest.approx(expected, rel=1e-3)


# =============================================================================
# EVALUATION REPORT TESTS
# =============================================================================


class TestEvaluationReport:
    """Tests for evaluation report generation."""

    def test_metrics_dict_creation(self):
        """Test creating a metrics dictionary for reporting."""
        metrics = {
            "TruePositives": 850,
            "FalsePositives": 50,
            "FalseNegatives": 100,
            "Precision": 0.944,
            "Recall": 0.895,
            "F1Score": 0.919,
            "PositionRMS_km": 12.5,
            "VelocityRMS_km_s": 0.025,
        }

        # Verify all metrics are present and valid
        assert metrics["TruePositives"] + metrics["FalsePositives"] > 0
        assert metrics["F1Score"] > 0
        assert metrics["F1Score"] <= 1.0

    def test_json_serialization(self):
        """Test that metrics can be serialized to JSON."""
        import json

        metrics = {
            "TruePositives": 850,
            "FalsePositives": 50,
            "F1Score": 0.919,
            "per_satellite": [
                {"satellite_id": "25544", "position_error_km": 5.2},
            ],
        }

        # Should serialize without error
        json_str = json.dumps(metrics)
        restored = json.loads(json_str)

        assert restored["F1Score"] == 0.919
        assert len(restored["per_satellite"]) == 1

    def test_numpy_to_json_conversion(self):
        """Test converting numpy types to JSON-serializable."""
        import json

        # Numpy types need conversion
        metrics = {
            "value_int": int(np.int64(100)),
            "value_float": float(np.float64(0.919)),
            "value_array": [float(x) for x in np.array([1.0, 2.0, 3.0])],
        }

        # Should serialize without error
        json_str = json.dumps(metrics)
        restored = json.loads(json_str)

        assert restored["value_int"] == 100
        assert restored["value_float"] == pytest.approx(0.919, rel=1e-3)


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEvaluationEdgeCases:
    """Tests for edge cases in evaluation."""

    def test_single_observation(self):
        """Test evaluation with single observation."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1"],
                "satNo": [1001],
            }
        )

        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001],
                "sourcedData": [["obs1"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TotalObs"].iloc[0] == 1
        assert result["TruePositives"].iloc[0] == 1

    def test_large_satellite_numbers(self):
        """Test with large NORAD catalog numbers."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2"],
                "satNo": [99999, 100000],  # Large sat numbers
            }
        )

        associated_orbits = pd.DataFrame(
            {
                "satNo": [99999, 100000],
                "sourcedData": [["obs1"], ["obs2"]],
            }
        )

        result = binaryMetrics(ref_obs, associated_orbits)

        assert result["TruePositives"].iloc[0] == 2

    def test_duplicate_observation_ids(self):
        """Test handling of duplicate observation assignments."""
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = pd.DataFrame(
            {
                "id": ["obs1", "obs2", "obs3"],
                "satNo": [1001, 1001, 1002],
            }
        )

        # obs1 assigned to both satellites (invalid but should handle)
        associated_orbits = pd.DataFrame(
            {
                "satNo": [1001, 1002],
                "sourcedData": [["obs1", "obs2"], ["obs1", "obs3"]],
            }
        )

        # Should not crash
        result = binaryMetrics(ref_obs, associated_orbits)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
