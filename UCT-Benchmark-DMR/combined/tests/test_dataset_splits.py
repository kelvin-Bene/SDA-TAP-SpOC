"""Tests for the CTF train/validation/test split assignment.

The split logic is in `uct_benchmark/data/dataset_splits.py` and is called
from `backend_api/jobs/workers.py` immediately before the dataset generation
worker writes `dataset_observations` rows. These tests verify the
mathematical properties the LLNL CTF paper requires:

1. Ratios are honoured at the dataset level (60/20/20 by default).
2. Stratification: each satellite's observations are spread across all
   three splits proportionally so no satellite is starved of any partition.
3. Determinism: same seed -> same assignment.
4. Edge cases: empty input, satellites with very few observations, ratio
   validation, missing required columns.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

from uct_benchmark.data.dataset_splits import assign_stratified_splits


def _make_obs_df(n_per_sat: int, sat_nos: list[int]) -> pd.DataFrame:
    """Build a synthetic observations DataFrame with id+satNo columns."""
    rows = []
    for sat in sat_nos:
        for i in range(n_per_sat):
            rows.append({"id": f"obs-{sat}-{i:04d}", "satNo": sat})
    return pd.DataFrame(rows)


class TestRatios:
    def test_60_20_20_total_counts(self):
        """5 satellites x 20 obs = 100 obs -> 60 train, 20 val, 20 test."""
        df = _make_obs_df(20, [25544, 25545, 25546, 25547, 25548])
        assignment = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        counts = Counter(assignment.values())
        assert counts["train"] == 60
        assert counts["validation"] == 20
        assert counts["test"] == 20

    def test_80_10_10_total_counts(self):
        """The other ratio recommended by the LLNL paper."""
        df = _make_obs_df(10, [25544, 25545, 25546, 25547, 25548])  # 50 obs total
        assignment = assign_stratified_splits(df, split_ratios=(0.8, 0.1, 0.1), seed=7)
        counts = Counter(assignment.values())
        assert counts["train"] == 40
        assert counts["validation"] == 5
        assert counts["test"] == 5


class TestStratification:
    def test_each_satellite_in_all_splits(self):
        """When each satellite has enough observations, every satellite
        should appear in all three splits with the right proportion."""
        df = _make_obs_df(20, [25544, 25545, 25546, 25547, 25548])
        assignment = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        for sat in [25544, 25545, 25546, 25547, 25548]:
            sat_split = Counter(
                s for o, s in assignment.items() if o.startswith(f"obs-{sat}-")
            )
            assert sat_split["train"] == 12
            assert sat_split["validation"] == 4
            assert sat_split["test"] == 4

    def test_satellite_total_preserved(self):
        """The sum across splits for each satellite must equal n_per_sat."""
        df = _make_obs_df(20, [25544, 25545])
        assignment = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        for sat in [25544, 25545]:
            n = sum(1 for o in assignment if o.startswith(f"obs-{sat}-"))
            assert n == 20


class TestEdgeCases:
    def test_empty_input(self):
        """Empty DataFrame returns an empty dict, no crash."""
        assignment = assign_stratified_splits(
            pd.DataFrame(), split_ratios=(0.6, 0.2, 0.2)
        )
        assert assignment == {}

    def test_none_input(self):
        """None input returns an empty dict (defensive)."""
        assignment = assign_stratified_splits(None, split_ratios=(0.6, 0.2, 0.2))
        assert assignment == {}

    def test_satellite_with_two_observations(self):
        """A satellite with only 2 observations doesn't crash. Both end up
        somewhere; the lopsided split is acceptable per the plan."""
        df = pd.DataFrame(
            [
                {"id": "obs-1", "satNo": 99999},
                {"id": "obs-2", "satNo": 99999},
            ]
        )
        assignment = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=1)
        # Both observations are placed
        assert len(assignment) == 2
        # Each value is a valid split label
        for v in assignment.values():
            assert v in ("train", "validation", "test")

    def test_satellite_with_single_observation(self):
        """A satellite with only 1 observation doesn't crash."""
        df = pd.DataFrame([{"id": "obs-1", "satNo": 99999}])
        assignment = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=1)
        assert len(assignment) == 1
        assert assignment["obs-1"] in ("train", "validation", "test")

    def test_invalid_ratios_raise(self):
        """Ratios that don't sum to 1.0 should raise ValueError."""
        df = _make_obs_df(10, [25544])
        with pytest.raises(ValueError, match="must sum to 1.0"):
            assign_stratified_splits(df, split_ratios=(0.5, 0.3, 0.3))

    def test_missing_required_columns_raise(self):
        """DataFrame without 'id' or 'satNo' columns should raise."""
        df = pd.DataFrame([{"foo": "bar"}])
        with pytest.raises(ValueError, match="must have 'id' and 'satNo'"):
            assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2))


class TestDeterminism:
    def test_same_seed_same_assignment(self):
        """Two calls with the same seed produce identical output."""
        df = _make_obs_df(20, [25544, 25545, 25546])
        a = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        b = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        assert a == b

    def test_different_seeds_different_assignment(self):
        """Different seeds should usually produce different assignments
        (this is probabilistic but very likely for n>=10)."""
        df = _make_obs_df(20, [25544, 25545, 25546])
        a = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=42)
        b = assign_stratified_splits(df, split_ratios=(0.6, 0.2, 0.2), seed=43)
        # Counts should still match (deterministic structure), but the
        # actual assignment dict is unlikely to be byte-identical.
        assert Counter(a.values()) == Counter(b.values())
        assert a != b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
