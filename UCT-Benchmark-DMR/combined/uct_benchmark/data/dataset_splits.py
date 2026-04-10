"""CTF train/validation/test split assignment for the UCT Benchmark.

Implements the train/validation/test partitioning prescribed by the LLNL/SDA
TAP Lab Common Task Framework paper (LLNL-PROC-868468), Section 3:

    "Following convention and best practice, data sets are divided into
    training, testing, and validation subsets. The complete training data
    set and solutions are provided to challenge participants to develop
    their algorithms ... The validation data set provides the data for
    each case but not the solutions ... The testing data set is withheld
    from the participants until the end of a competition. ... Typical
    splits ... are 80%, 10%, and 10%, or 60%, 20%, and 20%."

The same paper emphasises stratification:

    "Care taken to ensure that the training and validation data sets have
    similar properties, such as the proportion of positive to negative
    cases."

For the UCT use case the analog is "each split should contain observations
from a representative sample of satellites." A purely random split would
let some satellites end up entirely in one partition, breaking the
evaluator's ability to score that satellite from the other partitions.

The single function exported here, ``assign_stratified_splits``, splits
each satellite's observations independently using the requested ratios so
the joint distribution over (satellite, split) is preserved. It is called
from ``backend_api/jobs/workers.py`` immediately before the dataset
generation worker writes ``dataset_observations`` rows.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


def assign_stratified_splits(
    obs_truth_df: pd.DataFrame,
    split_ratios: Tuple[float, float, float] = (0.6, 0.2, 0.2),
    seed: int | None = None,
) -> Dict[str, str]:
    """Stratified train/validation/test assignment per the LLNL CTF paper.

    Each satellite's observations are split independently using the same
    ratios so each partition contains a representative slice of the
    dataset. Within a satellite, observations are shuffled deterministically
    using ``seed`` so the same dataset always splits the same way.

    Args:
        obs_truth_df: DataFrame with at least ``id`` and ``satNo`` columns.
            Other columns are ignored. The ``id`` column must be unique.
        split_ratios: ``(train, validation, test)`` ratios. Must sum to 1.0.
            Defaults to ``(0.6, 0.2, 0.2)`` per the LLNL paper's "60/20/20"
            recommendation. The other recommended split is ``(0.8, 0.1, 0.1)``.
        seed: RNG seed for reproducibility. When omitted, the assignment
            varies per call.

    Returns:
        Dict mapping observation id (str) -> split label
        (one of ``'train'``, ``'validation'``, ``'test'``).

    Edge cases:
        - Empty DataFrame returns an empty dict.
        - A satellite with fewer observations than ``len(split_ratios)``
          may end up with empty validation or test partitions; that's
          accepted because the eval pipeline handles empty splits gracefully.
        - The ``test`` partition absorbs floating-point rounding so the
          requested test ratio is honoured even when n is not divisible by
          the denominator.
    """
    if obs_truth_df is None or len(obs_truth_df) == 0:
        return {}

    train_r, val_r, test_r = split_ratios
    if abs(train_r + val_r + test_r - 1.0) > 1e-9:
        raise ValueError(
            f"split_ratios must sum to 1.0; got "
            f"train={train_r}, validation={val_r}, test={test_r}"
        )

    if "id" not in obs_truth_df.columns or "satNo" not in obs_truth_df.columns:
        raise ValueError(
            "obs_truth_df must have 'id' and 'satNo' columns; got "
            f"{list(obs_truth_df.columns)}"
        )

    rng = np.random.default_rng(seed)

    assignment: Dict[str, str] = {}
    for _, group in obs_truth_df.groupby("satNo"):
        ids = group["id"].astype(str).tolist()
        rng.shuffle(ids)
        n = len(ids)
        # Use round() so a 60/20/20 split on n=10 gives (6, 2, 2) and not
        # (6, 2, 2) vs (6, 2, 2) — int() truncation would underweight test.
        n_train = int(round(n * train_r))
        n_val = int(round(n * val_r))
        # The test partition absorbs floating-point rounding.
        for i, obs_id in enumerate(ids):
            if i < n_train:
                assignment[obs_id] = "train"
            elif i < n_train + n_val:
                assignment[obs_id] = "validation"
            else:
                assignment[obs_id] = "test"

    return assignment
