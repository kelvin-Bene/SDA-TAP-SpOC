# -*- coding: utf-8 -*-
"""Tests for readData.py bug fixes."""

import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path


class TestReadDataBugFixes:
    """Tests verifying the critical bug fixes in readData.py."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data files for testing."""
        # Create ref_obs with distinct timestamps
        ref_obs_times = pd.date_range("2025-01-01", periods=5, freq="h")
        ref_obs = pd.DataFrame(
            {
                "id": [f"ref_{i}" for i in range(5)],
                "obTime": ref_obs_times,
                "trackId": ["T1", "T1", "T2", "T2", "T3"],
                "origin": ["SENSOR1"] * 5,
                "satNo": [12345] * 5,
            }
        )
        ref_obs_path = tmp_path / "ref_obs.csv"
        ref_obs.to_csv(ref_obs_path, index=False)

        # Create ref_orbits
        ref_orbits = pd.DataFrame(
            {
                "satNo": [12345],
                "epoch": ["2025-01-01T00:00:00Z"],
                "xpos": [7000.0],
                "ypos": [0.0],
                "zpos": [0.0],
                "xvel": [0.0],
                "yvel": [7.5],
                "zvel": [0.0],
                "cov_matrix": [json.dumps(np.eye(6).tolist())],
            }
        )
        ref_orbits_path = tmp_path / "ref_orbits.csv"
        ref_orbits.to_csv(ref_orbits_path, index=False)

        # Create dataset with DIFFERENT timestamps than ref_obs
        dataset_times = pd.date_range("2025-06-01", periods=5, freq="h")  # Different dates!
        dataset = pd.DataFrame(
            {
                "id": [f"ds_{i}" for i in range(5)],
                "obTime": dataset_times,
                "trackId": ["DT1", "DT1", "DT2", "DT2", "DT3"],
                "origin": ["SENSOR2"] * 5,
                "satNo": [12345] * 5,
            }
        )
        dataset_path = tmp_path / "dataset.csv"
        dataset.to_csv(dataset_path, index=False)

        # Create uctp_output at a CUSTOM path (not ./data/uctp_output.json)
        uctp_output = pd.DataFrame(
            {
                "satNo": [12345],
                "epoch": ["2025-01-01T00:00:00Z"],
                "xpos": [7000.0],
                "ypos": [0.0],
                "zpos": [0.0],
                "xvel": [0.0],
                "yvel": [7.5],
                "zvel": [0.0],
            }
        )
        custom_uctp_path = tmp_path / "custom_uctp_output.json"
        uctp_output.to_json(custom_uctp_path)

        return {
            "ref_obs_path": str(ref_obs_path),
            "ref_orbits_path": str(ref_orbits_path),
            "dataset_path": str(dataset_path),
            "uctp_output_path": str(custom_uctp_path),
            "expected_dataset_times": dataset_times,
            "ref_obs_times": ref_obs_times,
        }

    def test_dataset_obtime_uses_own_column(self, temp_data_dir):
        """
        Verify dataset obTime comes from dataset, not ref_obs.

        This tests the fix for the bug at line 28:
        BEFORE: dataset["obTime"] = pd.to_datetime(ref_obs["obTime"])  # BUG!
        AFTER:  dataset["obTime"] = pd.to_datetime(dataset["obTime"])  # FIXED
        """
        # Skip this test if orekit is not available or JVM can't initialize
        try:
            pytest.importorskip("orekit_jpype", reason="orekit_jpype required for readData")
            # Try importing readData to check if Orekit/JVM is properly initialized
            from uct_benchmark.data.readData import readData
        except (ImportError, OSError, RuntimeError) as e:
            pytest.skip(f"Orekit/JVM not available: {e}")

        ref_obs, ref_orbits, dataset, uctp_output = readData(
            temp_data_dir["ref_obs_path"],
            temp_data_dir["ref_orbits_path"],
            temp_data_dir["dataset_path"],
            temp_data_dir["uctp_output_path"],
        )

        # The dataset times should match the original dataset file (June 2025)
        # NOT the ref_obs times (January 2025)
        expected_times = pd.to_datetime(temp_data_dir["expected_dataset_times"])
        actual_times = pd.to_datetime(dataset["obTime"])

        # Check that times are from June (dataset), not January (ref_obs)
        assert actual_times.iloc[0].month == 6, (
            f"Dataset obTime should be from June (dataset file), "
            f"but got month={actual_times.iloc[0].month}"
        )

        # Additional check: times should NOT match ref_obs times
        ref_times = pd.to_datetime(temp_data_dir["ref_obs_times"])
        assert not actual_times.equals(ref_times), (
            "Dataset obTime incorrectly matches ref_obs times - bug not fixed!"
        )

    def test_uctp_output_path_parameter_used(self, temp_data_dir):
        """
        Verify uctp_output_path parameter is actually used.

        This tests the fix for the bug at line 31:
        BEFORE: uctp_output = pd.read_json("./data/uctp_output.json")  # BUG - ignores param!
        AFTER:  uctp_output = pd.read_json(uctp_output_path)  # FIXED - uses param
        """
        # Skip this test if orekit is not available or JVM can't initialize
        try:
            pytest.importorskip("orekit_jpype", reason="orekit_jpype required for readData")
            from uct_benchmark.data.readData import readData
        except (ImportError, OSError, RuntimeError) as e:
            pytest.skip(f"Orekit/JVM not available: {e}")

        # The custom path is in tmp_path, not ./data/uctp_output.json
        # If the parameter is ignored, this would fail (file not found)
        ref_obs, ref_orbits, dataset, uctp_output = readData(
            temp_data_dir["ref_obs_path"],
            temp_data_dir["ref_orbits_path"],
            temp_data_dir["dataset_path"],
            temp_data_dir["uctp_output_path"],
        )

        # If we got here without error, the parameter was used
        assert uctp_output is not None
        assert len(uctp_output) > 0


class TestReadDataIntegration:
    """Integration tests for readData function."""

    def test_readdata_returns_correct_types(self, tmp_path):
        """Verify readData returns DataFrames with expected structure."""
        pytest.importorskip("orekit_jpype", reason="orekit_jpype required for readData")

        # This is a minimal integration test
        # In practice, you'd want more comprehensive fixtures
        pass  # Placeholder for future integration tests
