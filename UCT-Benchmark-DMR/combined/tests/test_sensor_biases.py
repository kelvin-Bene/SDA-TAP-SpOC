"""Tests for the per-sensor systematic bias generator (CTF UCT
challenge #10 — poor sensor calibration).

The bias logic lives in `uct_benchmark/data/sensor_biases.py` and is
called from `backend_api/jobs/workers.py` `run_dataset_generation` when
the user requests `calibration_quality='poor'`. These tests verify the
mathematical properties the plan requires:

1. The bias range stays inside [-3, +3] arcsec per axis.
2. Determinism: same seed -> same biases regardless of input order.
3. Edge cases: empty input, all-None input, duplicates, numeric IDs.
"""

from __future__ import annotations

import pytest

from uct_benchmark.data.sensor_biases import generate_sensor_biases


class TestEmptyAndDegenerate:
    def test_empty_list_returns_empty_dict(self):
        assert generate_sensor_biases([]) == {}

    def test_all_none_returns_empty_dict(self):
        assert generate_sensor_biases([None, None, None]) == {}

    def test_mixed_none_and_real_drops_none(self):
        biases = generate_sensor_biases([None, "MUI001", None], seed=1)
        assert set(biases.keys()) == {"MUI001"}


class TestRange:
    def test_single_sensor_within_default_range(self):
        biases = generate_sensor_biases(["MUI001"], seed=42)
        assert "MUI001" in biases
        assert -3.0 <= biases["MUI001"]["ra_arcsec"] <= 3.0
        assert -3.0 <= biases["MUI001"]["dec_arcsec"] <= 3.0

    def test_many_sensors_all_within_default_range(self):
        ids = [f"sensor-{i}" for i in range(50)]
        biases = generate_sensor_biases(ids, seed=99)
        assert len(biases) == 50
        for sensor_id, bias in biases.items():
            assert -3.0 <= bias["ra_arcsec"] <= 3.0
            assert -3.0 <= bias["dec_arcsec"] <= 3.0

    def test_custom_range_respected(self):
        biases = generate_sensor_biases(["S1", "S2", "S3"], seed=7, bias_range_arcsec=0.5)
        for bias in biases.values():
            assert -0.5 <= bias["ra_arcsec"] <= 0.5
            assert -0.5 <= bias["dec_arcsec"] <= 0.5

    def test_bias_keys_present(self):
        biases = generate_sensor_biases(["MUI001"], seed=1)
        assert set(biases["MUI001"].keys()) == {"ra_arcsec", "dec_arcsec"}
        assert isinstance(biases["MUI001"]["ra_arcsec"], float)
        assert isinstance(biases["MUI001"]["dec_arcsec"], float)


class TestDeterminism:
    def test_same_seed_same_biases(self):
        a = generate_sensor_biases(["MUI001", "MUI002", "MUI003"], seed=42)
        b = generate_sensor_biases(["MUI001", "MUI002", "MUI003"], seed=42)
        assert a == b

    def test_input_order_does_not_matter(self):
        """Internal sort should make assignment order-independent."""
        a = generate_sensor_biases(["MUI001", "MUI002", "MUI003"], seed=42)
        b = generate_sensor_biases(["MUI003", "MUI001", "MUI002"], seed=42)
        assert a == b

    def test_different_seeds_different_biases(self):
        a = generate_sensor_biases(["MUI001", "MUI002", "MUI003"], seed=1)
        b = generate_sensor_biases(["MUI001", "MUI002", "MUI003"], seed=999)
        assert set(a.keys()) == set(b.keys())
        # At least one of the values should differ. With 6 floats per dict
        # and a uniform distribution, the chance of byte-identical results
        # under different seeds is effectively zero.
        assert any(a[k] != b[k] for k in a)


class TestDuplicatesAndCoercion:
    def test_duplicate_sensor_ids_dedupe(self):
        biases = generate_sensor_biases(["MUI001", "MUI001", "MUI001"], seed=42)
        assert len(biases) == 1
        assert "MUI001" in biases

    def test_numeric_ids_coerced_to_strings(self):
        biases = generate_sensor_biases([12345, 67890], seed=42)
        assert set(biases.keys()) == {"12345", "67890"}

    def test_mixed_type_ids_coerced(self):
        biases = generate_sensor_biases([12345, "MUI001", 67890], seed=42)
        assert set(biases.keys()) == {"12345", "67890", "MUI001"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
