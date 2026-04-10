"""Tests for the synthetic maneuver injection helpers (CTF UCT
challenge #6 — objects maneuvering during long sensor coverage gaps).

The math lives in ``uct_benchmark/data/maneuver_injection.py`` and is
called from ``backend_api/jobs/workers.py`` ``run_dataset_generation``
when the user requests ``maneuver_during_gap=True``. These tests verify
the properties the plan requires without spinning up Orekit (the
propagator is mocked), so they run in well under a second.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from uct_benchmark.data.maneuver_injection import (
    DELTA_V_MAX_M_S,
    DELTA_V_MIN_M_S,
    GAP_DURATION_HOURS,
    compute_gap_window,
    compute_post_maneuver_state,
    pick_maneuvering_satellites,
)


# ---------------------------------------------------------------------------
# pick_maneuvering_satellites
# ---------------------------------------------------------------------------


class TestPickManeuveringSatellites:
    def test_default_fraction_picks_about_twenty_percent(self):
        sat_nos = list(range(100))
        picked = pick_maneuvering_satellites(sat_nos, seed=42)
        assert len(picked) == 20  # 100 * 0.20 = 20 exactly

    def test_minimum_one_satellite_when_fraction_rounds_to_zero(self):
        # 3 satellites at 20% rounds to 1, but the floor of `round` could
        # give 0 for very small inputs. The helper should always pick at
        # least one satellite when the input is non-empty.
        picked = pick_maneuvering_satellites([42], seed=1)
        assert picked == [42]

    def test_empty_input_returns_empty_list(self):
        assert pick_maneuvering_satellites([], seed=1) == []

    def test_deterministic_for_same_seed(self):
        sat_nos = list(range(50))
        first = pick_maneuvering_satellites(sat_nos, seed=12345)
        second = pick_maneuvering_satellites(sat_nos, seed=12345)
        assert first == second

    def test_different_seeds_pick_different_subsets(self):
        # Not strictly required, but a quick sanity check that the seed
        # actually influences the choice (otherwise our determinism test
        # would be vacuously true).
        sat_nos = list(range(50))
        a = pick_maneuvering_satellites(sat_nos, seed=1)
        b = pick_maneuvering_satellites(sat_nos, seed=2)
        assert a != b

    def test_returns_sorted_list(self):
        picked = pick_maneuvering_satellites(list(range(100)), seed=7)
        assert picked == sorted(picked)


# ---------------------------------------------------------------------------
# compute_gap_window
# ---------------------------------------------------------------------------


class TestComputeGapWindow:
    def test_gap_centered_on_dataset_midpoint(self):
        start = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 8, 0, 0, 0, tzinfo=timezone.utc)  # 7 days
        gap_start, maneuver_epoch, gap_end = compute_gap_window(start, end)

        # Midpoint of a 7-day window is day 3.5 -> 2026-04-04 12:00 UTC
        expected_midpoint = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
        assert maneuver_epoch == expected_midpoint

        # Gap is GAP_DURATION_HOURS wide, centered on the midpoint.
        half_gap = timedelta(hours=GAP_DURATION_HOURS / 2.0)
        assert gap_start == expected_midpoint - half_gap
        assert gap_end == expected_midpoint + half_gap

    def test_gap_width_is_six_hours(self):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 2, tzinfo=timezone.utc)
        gap_start, _, gap_end = compute_gap_window(start, end)
        assert gap_end - gap_start == timedelta(hours=GAP_DURATION_HOURS)


# ---------------------------------------------------------------------------
# compute_post_maneuver_state
# ---------------------------------------------------------------------------


def _identity_propagator(state, _epoch, target_epochs, **_kwargs):
    """Mock propagator that returns the input state for every target epoch.

    The real ``ephemerisPropagator`` returns a list of state vectors at
    the requested epochs. This stub matches that contract without
    needing Orekit, so we can verify the delta-V math in isolation.
    """
    return [np.asarray(state, dtype=float).copy() for _ in target_epochs]


class TestComputePostManeuverState:
    @pytest.fixture
    def base_inputs(self):
        # GEO-ish state vector in km / km·s^-1, J2000 ECI.
        pre_state = np.array(
            [42164.0, 0.0, 0.0, 0.0, 3.0746, 0.0], dtype=float
        )
        pre_epoch = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
        maneuver_epoch = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        gap_end_epoch = datetime(2026, 4, 1, 15, 0, 0, tzinfo=timezone.utc)
        return pre_state, pre_epoch, maneuver_epoch, gap_end_epoch

    def test_delta_v_added_to_velocity_components(self, base_inputs):
        pre_state, pre_epoch, maneuver_epoch, gap_end_epoch = base_inputs
        post_maneuver_state, delta_v_m_s, _ = compute_post_maneuver_state(
            pre_state_km=pre_state,
            pre_epoch=pre_epoch,
            maneuver_epoch=maneuver_epoch,
            gap_end_epoch=gap_end_epoch,
            propagator=_identity_propagator,
            seed=42,
        )
        # With the identity propagator the position at the maneuver epoch
        # is identical to the pre-maneuver position.
        np.testing.assert_allclose(
            post_maneuver_state[0:3], pre_state[0:3]
        )
        # The velocity differs from the pre-maneuver velocity by exactly
        # the delta-V (converted from m/s to km/s).
        delta_v_km_s = delta_v_m_s / 1000.0
        np.testing.assert_allclose(
            post_maneuver_state[3:6] - pre_state[3:6], delta_v_km_s
        )

    def test_delta_v_magnitude_within_expected_envelope(self, base_inputs):
        pre_state, pre_epoch, maneuver_epoch, gap_end_epoch = base_inputs
        # Each axis is uniform in [DELTA_V_MIN, DELTA_V_MAX] with random
        # sign, so the magnitude is bounded above by the cube diagonal
        # sqrt(3) * DELTA_V_MAX and below by sqrt(3) * DELTA_V_MIN.
        max_mag = np.sqrt(3.0) * DELTA_V_MAX_M_S
        min_mag = np.sqrt(3.0) * DELTA_V_MIN_M_S
        for seed in range(20):
            _, delta_v_m_s, _ = compute_post_maneuver_state(
                pre_state_km=pre_state,
                pre_epoch=pre_epoch,
                maneuver_epoch=maneuver_epoch,
                gap_end_epoch=gap_end_epoch,
                propagator=_identity_propagator,
                seed=seed,
            )
            mag = float(np.linalg.norm(delta_v_m_s))
            assert min_mag <= mag <= max_mag
            # Each axis is also individually inside [-MAX, +MAX].
            for component in delta_v_m_s:
                assert DELTA_V_MIN_M_S <= abs(component) <= DELTA_V_MAX_M_S

    def test_deterministic_for_same_seed(self, base_inputs):
        pre_state, pre_epoch, maneuver_epoch, gap_end_epoch = base_inputs
        result_a = compute_post_maneuver_state(
            pre_state_km=pre_state,
            pre_epoch=pre_epoch,
            maneuver_epoch=maneuver_epoch,
            gap_end_epoch=gap_end_epoch,
            propagator=_identity_propagator,
            seed=12345,
        )
        result_b = compute_post_maneuver_state(
            pre_state_km=pre_state,
            pre_epoch=pre_epoch,
            maneuver_epoch=maneuver_epoch,
            gap_end_epoch=gap_end_epoch,
            propagator=_identity_propagator,
            seed=12345,
        )
        np.testing.assert_allclose(result_a[0], result_b[0])
        np.testing.assert_allclose(result_a[1], result_b[1])
        np.testing.assert_allclose(result_a[2], result_b[2])

    def test_skips_first_propagation_when_pre_epoch_equals_maneuver_epoch(
        self, base_inputs
    ):
        # When the pre_epoch and maneuver_epoch coincide, the helper
        # should NOT call the propagator for step 1 — it already has the
        # state at the maneuver epoch. We verify by giving it a
        # propagator that asserts it is only called for step 3.
        pre_state, _, maneuver_epoch, gap_end_epoch = base_inputs
        call_log = []

        def tracked_propagator(state, epoch, targets, **_kwargs):
            call_log.append((epoch, list(targets)))
            return [np.asarray(state, dtype=float).copy() for _ in targets]

        compute_post_maneuver_state(
            pre_state_km=pre_state,
            pre_epoch=maneuver_epoch,  # same as maneuver_epoch
            maneuver_epoch=maneuver_epoch,
            gap_end_epoch=gap_end_epoch,
            propagator=tracked_propagator,
            seed=1,
        )
        # Only step 3 should have called the propagator.
        assert len(call_log) == 1
        assert call_log[0][0] == maneuver_epoch
        assert call_log[0][1] == [gap_end_epoch]
