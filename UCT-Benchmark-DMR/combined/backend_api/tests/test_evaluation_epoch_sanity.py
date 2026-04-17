"""Regression tests for the epoch-sanity pre-check in run_evaluation_pipeline.

Guards against the post-QA_PROD_RUN_2026-04-17 case where users submit a UCTP
generated against a different dataset. Without this check, the downstream
orbit-association propagator burns ~10s trying to close a months-wide gap
before degrading to "0 associations" via the orbitAssociation guard.
Failing fast here gives the user an actionable error message in seconds.

Tests exercise the standalone helper `_check_epoch_sanity` directly — pure
pandas, no DB coupling, no fixtures needed.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from backend_api.jobs.workers import _check_epoch_sanity


def _make_ref_obs(ob_times: list[datetime]) -> pd.DataFrame:
    return pd.DataFrame({"obTime": ob_times, "satNo": [26360] * len(ob_times)})


def _make_uctp(epochs: list[datetime]) -> pd.DataFrame:
    return pd.DataFrame({"epoch": epochs})


class TestEpochSanityCheck:
    """Tolerance is ±7 days by default."""

    def test_epochs_inside_window_passes(self):
        """Happy path: est epoch in the obs window raises nothing."""
        ref_obs = _make_ref_obs(
            [datetime(2026, 4, 10, 9, 0), datetime(2026, 4, 10, 9, 31)]
        )
        uctp = _make_uctp([datetime(2026, 4, 10, 9, 15)])
        _check_epoch_sanity(ref_obs, uctp)  # must not raise

    def test_epochs_far_before_window_raises(self):
        """Current production bug case: stale fixture at 2026-01-22 vs
        dataset 158 obs window at 2026-04-10 — 78 days gap, well beyond
        the ±7 day tolerance."""
        ref_obs = _make_ref_obs(
            [datetime(2026, 4, 10, 9, 0), datetime(2026, 4, 10, 9, 31)]
        )
        uctp = _make_uctp([datetime(2026, 1, 22, 10, 40)])
        with pytest.raises(ValueError, match="outside dataset observation window"):
            _check_epoch_sanity(ref_obs, uctp)

    def test_epochs_far_after_window_raises(self):
        """Symmetrical check — est epochs after the window also fail."""
        ref_obs = _make_ref_obs(
            [datetime(2026, 4, 10, 9, 0), datetime(2026, 4, 10, 9, 31)]
        )
        uctp = _make_uctp([datetime(2026, 5, 20, 0, 0)])
        with pytest.raises(ValueError, match="outside dataset observation window"):
            _check_epoch_sanity(ref_obs, uctp)

    def test_epochs_within_tolerance_passes(self):
        """Est epochs 6 days before the window should pass (tolerance = 7 days)."""
        ref_obs = _make_ref_obs([datetime(2026, 4, 10, 9, 0)])
        uctp = _make_uctp([datetime(2026, 4, 4, 9, 0)])
        _check_epoch_sanity(ref_obs, uctp)  # must not raise

    def test_epochs_just_outside_tolerance_raises(self):
        """Est epochs 8 days before the window should fail."""
        ref_obs = _make_ref_obs([datetime(2026, 4, 10, 9, 0)])
        uctp = _make_uctp([datetime(2026, 4, 2, 0, 0)])
        with pytest.raises(ValueError, match="outside dataset observation window"):
            _check_epoch_sanity(ref_obs, uctp)

    def test_custom_tolerance_honored(self):
        """A stricter tolerance catches smaller gaps."""
        ref_obs = _make_ref_obs([datetime(2026, 4, 10, 9, 0)])
        uctp = _make_uctp([datetime(2026, 4, 8, 0, 0)])
        # Within default ±7 -> no raise
        _check_epoch_sanity(ref_obs, uctp, tolerance_days=7)
        # But ±1 day tolerance catches the 2-day gap
        with pytest.raises(ValueError, match="outside dataset observation window"):
            _check_epoch_sanity(ref_obs, uctp, tolerance_days=1)

    def test_empty_ref_obs_no_raise(self):
        """Guard is permissive — empty input data is not our problem."""
        ref_obs = pd.DataFrame(columns=["obTime", "satNo"])
        uctp = _make_uctp([datetime(2026, 1, 22, 0, 0)])
        _check_epoch_sanity(ref_obs, uctp)  # must not raise

    def test_empty_uctp_no_raise(self):
        """Guard is permissive — empty submission is caught upstream."""
        ref_obs = _make_ref_obs([datetime(2026, 4, 10, 9, 0)])
        uctp = pd.DataFrame(columns=["epoch"])
        _check_epoch_sanity(ref_obs, uctp)  # must not raise

    def test_message_includes_actionable_guidance(self):
        """Error message must guide the user toward the likely fix."""
        ref_obs = _make_ref_obs([datetime(2026, 4, 10, 9, 0)])
        uctp = _make_uctp([datetime(2026, 1, 22, 0, 0)])
        with pytest.raises(ValueError) as exc_info:
            _check_epoch_sanity(ref_obs, uctp)
        msg = str(exc_info.value)
        assert "different dataset" in msg.lower(), (
            f"message should suggest dataset mismatch: {msg}"
        )
        assert "7 days" in msg, f"message should state the tolerance: {msg}"
