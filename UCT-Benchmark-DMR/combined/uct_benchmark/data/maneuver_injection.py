"""Synthetic maneuver injection for the CTF maneuvering-during-gap
challenge (SDA TAP Lab UCT challenge #6).

Background
----------
The "Need to Benchmark Uncorrelated Track (UCT) Processing" paper from the
SDA TAP Lab lists ten UCT challenges. Item #6 is "Objects maneuvering
during long sensor coverage gaps." This is the **CCDM (Camouflage,
Concealment, Deception, Maneuver) tactic** that the SDA TAP Lab was
founded to counter — a satellite that quietly maneuvers when no one is
watching is exactly the failure mode the benchmark must test for.

This module is the math-only side of the implementation. It is
deliberately stateless and I/O-free so it can be unit-tested with a
mocked propagator (no Orekit / JVM startup needed). The dataset generation
worker is responsible for orchestration: calling the helpers here,
mutating ``obs_truth`` and ``state_truth``, and persisting the resulting
maneuver metadata to the ``datasets`` row.

Distinct from challenges #2 and #5
----------------------------------
Challenges #2 (long-duration low-thrust maneuvers) and #5 (event types
from real maneuver data) both depend on the AFRL ML labelling team's
output, which Louis Caves explicitly noted in the Jan 22 / Feb 19 2026
transcripts as not yet available. Challenge #6 doesn't need real
maneuver data because we **construct the maneuver synthetically** — the
worker picks satellites, applies a delta-V at a chosen midpoint epoch,
drops observations from a 6-hour gap window around it, and writes the
post-maneuver state vector to ``dataset_references`` as the canonical
truth.

Why uniform [1, 50] m/s
-----------------------
- Real-world station-keeping burns: 1-5 m/s (frequent, well-known)
- Real-world orbit-raising burns: 50-200 m/s (rare)
- Anti-satellite kinetic intercept: >500 m/s (unprecedented in benign ops)

A uniform distribution across [1, 50] gives a mix of subtle station-
keeping maneuvers (hard to detect) and significant orbit changes (easy
to detect) in the same dataset. Some satellites are near the noise floor,
others are obvious. That's what an honest stress test looks like.

Why 20% of satellites
---------------------
Enough to be statistically meaningful in scoring (a UCTP that handles
maneuvers will significantly outperform one that doesn't), but not so
many that the dataset becomes a "maneuver detection" dataset rather than
a UCT processing dataset. 20% mirrors typical adversarial scenarios
where a small subset of objects of interest are doing the manipulation.

Why 6-hour gap
--------------
Realistic for ground-based optical sensors which have ~6-12 hour
coverage gaps when objects are over the wrong hemisphere or in daylight.
Long enough to require real orbit determination from the post-gap
observations (not just interpolation), short enough that the propagation
error from the pre-maneuver state stays within physical bounds.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np


# Constants per the gap-5 design discussion. Tweak these and the unit
# tests in ``tests/test_maneuver_injection.py`` will catch any
# regressions in the worker's expectations.
DELTA_V_MIN_M_S = 1.0
DELTA_V_MAX_M_S = 50.0
GAP_DURATION_HOURS = 6.0
DEFAULT_MANEUVER_FRACTION = 0.20  # 20% of satellites


def pick_maneuvering_satellites(
    sat_nos: List[int],
    fraction: float = DEFAULT_MANEUVER_FRACTION,
    seed: Optional[int] = None,
) -> List[int]:
    """Pick a subset of satellites to maneuver.

    Args:
        sat_nos: All satellite NORAD IDs in the dataset.
        fraction: What fraction to maneuver (default 0.20 = 20%).
        seed: RNG seed for deterministic picking. Use the dataset_id so
            the same dataset always picks the same satellites
            (idempotent regeneration).

    Returns:
        Sorted list of satellite NORAD IDs that will maneuver. At least
        one satellite is always picked when ``sat_nos`` is non-empty so
        the challenge has something to test, even on small datasets.
    """
    if not sat_nos:
        return []
    rng = np.random.default_rng(seed)
    n_total = len(sat_nos)
    n_maneuver = max(1, int(round(n_total * fraction)))
    n_maneuver = min(n_maneuver, n_total)  # never pick more than we have
    chosen_indices = rng.choice(n_total, size=n_maneuver, replace=False)
    return sorted(int(sat_nos[i]) for i in chosen_indices)


def compute_gap_window(
    dataset_start: datetime, dataset_end: datetime
) -> Tuple[datetime, datetime, datetime]:
    """Compute the maneuver epoch and gap window for a dataset.

    The maneuver happens at the dataset midpoint. The gap is
    ``GAP_DURATION_HOURS`` long, centered on the maneuver epoch. So a
    7-day dataset has a 6-hour gap from day 3.5 - 3 hours to day 3.5 + 3
    hours.

    Args:
        dataset_start: Start of the dataset's observation window
            (timezone-aware datetime).
        dataset_end: End of the dataset's observation window
            (timezone-aware datetime).

    Returns:
        ``(gap_start, maneuver_epoch, gap_end)`` all as timezone-aware
        datetimes (preserved from the input timezones).
    """
    midpoint = dataset_start + (dataset_end - dataset_start) / 2
    half_gap = timedelta(hours=GAP_DURATION_HOURS / 2.0)
    return midpoint - half_gap, midpoint, midpoint + half_gap


def compute_post_maneuver_state(
    pre_state_km: np.ndarray,
    pre_epoch: datetime,
    maneuver_epoch: datetime,
    gap_end_epoch: datetime,
    propagator,
    sat_params: Optional[List[float]] = None,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply a synthetic delta-V at maneuver_epoch and propagate forward.

    The flow is:

    1. Propagate ``pre_state_km`` from ``pre_epoch`` forward to
       ``maneuver_epoch`` using the given propagator. (Skipped when
       the two epochs are equal.)
    2. Draw a uniform random delta-V in ``[DELTA_V_MIN_M_S, DELTA_V_MAX_M_S]``
       per axis with random signs, convert to km/s, add to the velocity
       components of the propagated state.
    3. Propagate the post-maneuver state forward to ``gap_end_epoch``
       so the worker can use it as the canonical reference state for
       the satellite at the gap-end epoch.

    Args:
        pre_state_km: 6-element ndarray ``[x, y, z, vx, vy, vz]`` in km
            and km/s (J2000 ECI). The state at ``pre_epoch``.
        pre_epoch: datetime of ``pre_state_km``. Typically the
            satellite's reference epoch from the truth state vector.
        maneuver_epoch: datetime when the delta-V is applied. Usually
            the dataset midpoint from ``compute_gap_window``.
        gap_end_epoch: datetime to propagate the post-maneuver state to.
            Usually ``maneuver_epoch + GAP_DURATION_HOURS / 2``.
        propagator: ``ephemerisPropagator`` from
            ``uct_benchmark.simulation.propagator`` (or any function
            with a compatible signature; mocked in unit tests).
        sat_params: ``[mass_kg, cross_section_m2, drag_coeff, srp_coeff]``.
            Defaults to ``[1000, 13.873, 0, 0]``, matching the existing
            propagator default.
        seed: RNG seed for the delta-V draw. Use ``sat_no`` for
            per-satellite determinism.

    Returns:
        Tuple of three ndarrays:

        - ``post_maneuver_state_km``: state at ``maneuver_epoch``
          immediately after the delta-V is applied (in km, km/s).
        - ``delta_v_m_s``: 3-vector of applied delta-V components in
          m/s (NOT km/s — uses the conventional reporting unit so it
          reads the same as orbit textbooks).
        - ``post_propagated_state_km``: ``post_maneuver_state_km``
          propagated forward to ``gap_end_epoch``.

    Raises:
        Whatever the propagator raises (e.g. Orekit errors). The caller
        catches these and falls back to skipping the maneuver for that
        satellite.
    """
    rng = np.random.default_rng(seed)
    if sat_params is None:
        sat_params = [1000.0, 13.873, 0.0, 0.0]

    # Step 1: propagate pre_state from pre_epoch to maneuver_epoch.
    if pre_epoch == maneuver_epoch:
        state_at_maneuver = np.asarray(pre_state_km, dtype=float).copy()
    else:
        propagated = propagator(
            pre_state_km, pre_epoch, [maneuver_epoch], satelliteParameters=sat_params
        )
        state_at_maneuver = np.asarray(propagated[0], dtype=float).copy()

    # Step 2: apply delta-V. Each axis gets an independent uniform draw
    # in [DELTA_V_MIN_M_S, DELTA_V_MAX_M_S] with a random sign so the
    # burn can go any direction in 3-space.
    delta_v_m_s = np.array(
        [
            rng.uniform(DELTA_V_MIN_M_S, DELTA_V_MAX_M_S) * rng.choice([-1.0, 1.0]),
            rng.uniform(DELTA_V_MIN_M_S, DELTA_V_MAX_M_S) * rng.choice([-1.0, 1.0]),
            rng.uniform(DELTA_V_MIN_M_S, DELTA_V_MAX_M_S) * rng.choice([-1.0, 1.0]),
        ]
    )
    delta_v_km_s = delta_v_m_s / 1000.0

    post_maneuver_state = state_at_maneuver.copy()
    post_maneuver_state[3:6] = post_maneuver_state[3:6] + delta_v_km_s

    # Step 3: propagate post_maneuver_state from maneuver_epoch to gap_end_epoch.
    if maneuver_epoch == gap_end_epoch:
        post_propagated_state = post_maneuver_state.copy()
    else:
        propagated_post = propagator(
            post_maneuver_state,
            maneuver_epoch,
            [gap_end_epoch],
            satelliteParameters=sat_params,
        )
        post_propagated_state = np.asarray(propagated_post[0], dtype=float).copy()

    return post_maneuver_state, delta_v_m_s, post_propagated_state
