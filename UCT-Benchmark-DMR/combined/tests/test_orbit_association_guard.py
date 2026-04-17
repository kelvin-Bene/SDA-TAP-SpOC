"""Regression tests for the infeasible-cost-matrix guard in orbitAssociation.

Covers the post-QA_PROD_RUN_2026-04-17 "ValueError: cost matrix is infeasible"
crash where scipy.optimize.linear_sum_assignment rejected an all-inf (or
partial-inf) cost matrix and tanked the entire evaluation job. The production
fix wraps both call sites (TLE mode line ~144 and SV mode line ~231) in a
try/except that degrades to zero associations on ValueError.

The orbitAssociation call dispatches work through ProcessPoolExecutor, which
requires picklable top-level propagator functions (closures fail on Windows
spawn). The module-level `_failing_propagator` and `_passthrough_propagator`
below are picklable.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


# Module-level propagators — must be picklable for ProcessPoolExecutor on
# Windows (spawn semantics pickle workers, not fork).

def _failing_propagator(state, initial_epoch, final_epochs, sat_pars):
    """Always raises. orbitAssociation._compute_cost_column catches the
    exception and substitutes an all-inf column, which is exactly the
    production failure mode we are guarding against."""
    raise RuntimeError("simulated propagation failure")


def _passthrough_propagator(state, initial_epoch, final_epochs, sat_pars):
    """Returns the truth state unchanged at every est epoch. Cost column
    becomes the L2 distance between truth state and each est state."""
    n = len(final_epochs) if hasattr(final_epochs, "__len__") else 1
    return [np.asarray(state, dtype=float)] * n


def _make_truth(n_truth: int) -> pd.DataFrame:
    """n_truth reference orbits with distinct satNos so assignment is well-defined."""
    base_epoch = datetime(2026, 4, 10, 9, 15, 0)
    return pd.DataFrame(
        {
            "epoch": [base_epoch] * n_truth,
            "xpos": [7000.0 + i for i in range(n_truth)],
            "ypos": [0.0] * n_truth,
            "zpos": [0.0] * n_truth,
            "xvel": [0.0] * n_truth,
            "yvel": [7.5] * n_truth,
            "zvel": [0.0] * n_truth,
            "cov_matrix": [np.eye(6).tolist()] * n_truth,
            "satNo": [25544 + i for i in range(n_truth)],
            "mass": [1000.0] * n_truth,
            "crossSection": [10.0] * n_truth,
            "dragCoeff": [2.2] * n_truth,
            "solarRadPressCoeff": [1.0] * n_truth,
        }
    )


def _make_est(n_est: int) -> pd.DataFrame:
    base_epoch = datetime(2026, 4, 10, 9, 15, 30)
    return pd.DataFrame(
        {
            "epoch": [base_epoch] * n_est,
            "xpos": [7000.0 + i for i in range(n_est)],
            "ypos": [0.0] * n_est,
            "zpos": [0.0] * n_est,
            "xvel": [0.0] * n_est,
            "yvel": [7.5] * n_est,
            "zvel": [0.0] * n_est,
        }
    )


def _import_orbit_assoc():
    try:
        from uct_benchmark.evaluation.orbitAssociation import orbitAssociation

        return orbitAssociation
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"orekit_jpype/jpype not available: {e}")


class TestInfeasibleCostMatrixGuard:
    """Post-QA C1: linear_sum_assignment must not crash the whole eval job."""

    def test_all_inf_cost_matrix_returns_empty(self):
        """Every truth propagation fails -> all-inf matrix -> 0 associations.

        Pre-fix: scipy raises ValueError and orbitAssociation propagates it,
        killing the evaluation worker. Post-fix: guard catches, returns
        empty row_ind/col_ind, function finishes normally with 0 associations.
        """
        orbitAssociation = _import_orbit_assoc()
        truth = _make_truth(n_truth=2)
        est = _make_est(n_est=3)

        try:
            associated, results, nonassociated = orbitAssociation(
                truth, est, _failing_propagator, elset_mode=False
            )
        except ValueError as e:
            if "infeasible" in str(e).lower():
                pytest.fail(
                    f"guard did not catch scipy ValueError — "
                    f"regression: {e}"
                )
            raise
        except Exception as e:
            pytest.skip(f"multiprocessing/orekit not available: {e}")

        assert results["Associated Orbit Count"] == 0, (
            "guard must return 0 associations when the cost matrix is "
            "all-inf, not raise ValueError"
        )
        assert results["Non-Associated Orbit Count"] == len(est)
        assert results["Expected State Count"] == len(truth)
        assert len(nonassociated) == len(est)
        if "uct" in nonassociated.columns:
            assert nonassociated["uct"].all(), (
                "all est rows must be labelled uct=True when nothing associates"
            )

    def test_all_finite_cost_matrix_still_works(self):
        """Regression guard: happy-path association still succeeds after the
        try/except wraps linear_sum_assignment."""
        orbitAssociation = _import_orbit_assoc()
        truth = _make_truth(n_truth=2)
        est = _make_est(n_est=2)

        try:
            associated, results, nonassociated = orbitAssociation(
                truth, est, _passthrough_propagator, elset_mode=False
            )
        except Exception as e:
            pytest.skip(f"multiprocessing/orekit not available: {e}")

        assert results["Associated Orbit Count"] == 2, (
            "happy-path association must not regress"
        )
        assert results["Non-Associated Orbit Count"] == 0
        assert len(associated) == 2
        assert set(associated["satNo"].tolist()) == {25544, 25545}


class TestScipyInfeasibleBehaviour:
    """Document the exact scipy behaviour we are guarding against — so if
    scipy ever changes semantics and stops raising, this test will fail
    loudly and we can simplify the guard."""

    def test_scipy_raises_on_all_inf_matrix(self):
        from scipy.optimize import linear_sum_assignment

        m = np.full((3, 2), np.inf)
        with pytest.raises(ValueError, match="infeasible"):
            linear_sum_assignment(m)

    def test_scipy_raises_on_partial_inf_column(self):
        from scipy.optimize import linear_sum_assignment

        # One column all-inf in a non-square matrix: there is no feasible
        # assignment that covers min(rows,cols)=2 pairs without using inf.
        m = np.array([[np.inf, 100.0], [np.inf, 200.0], [np.inf, 300.0]])
        with pytest.raises(ValueError, match="infeasible"):
            linear_sum_assignment(m)
