"""Per-sensor systematic bias generation for the CTF poor-calibration
challenge (SDA TAP Lab UCT challenge #10).

Background
----------
The "Need to Benchmark Uncorrelated Track (UCT) Processing" paper from the
SDA TAP Lab lists ten UCT challenges. Item #10 is "Tracks from sensors with
poor/unknown calibration." The Transition Document also names this as a
deferred TODO under "Dataset features to implement -> Poor sensor Calibration."

This module generates the per-sensor biases that simulate miscalibrated
sensors. The biases are persisted on the dataset row and applied virtually
at download time and at eval time so the shared `observations` table stays
pristine.

Why ±3 arcsec
-------------
- The Smear Explanation document's percentile chart puts realistic
  atmospheric seeing in the 0.25–1.32 arcsec range. A "really bad day"
  sigma is ~0.7 arcsec.
- We want the systematic bias to be MUCH larger than the random seeing
  noise so a real UCTP can notice it (otherwise the bias would be
  indistinguishable from noise and the test would be unfair).
- Real-world sensor calibration errors for well-maintained ground sensors
  are typically 0.1–1 arcsec. ±3 arcsec is "obviously poor" without
  breaking the geometry math (3 arcsec is well within the field of view
  of any practical optical telescope).

Why uniform and not Gaussian
----------------------------
A uniform distribution puts equal mass across the whole range, which means
the worst-case sensor consistently gets near-maximum bias. Gaussian would
let most sensors have small biases and rarely produce extreme cases, which
is closer to reality but defeats the "stress-test" purpose of the
poor-calibration challenge. Uniform is the right call for a benchmark
that wants to consistently push UCTPs.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def generate_sensor_biases(
    sensor_ids: List[str],
    seed: int | None = None,
    bias_range_arcsec: float = 3.0,
) -> Dict[str, Dict[str, float]]:
    """Draw a per-sensor systematic bias from a uniform distribution.

    Args:
        sensor_ids: List of unique sensor identifiers (strings) appearing
            in the dataset. ``None`` values are skipped, duplicates are
            deduplicated, and the result is keyed by ``str(sensor_id)``.
        seed: RNG seed for reproducibility. Use the dataset_id so the same
            dataset always gets the same biases (idempotent regeneration).
        bias_range_arcsec: Half-width of the uniform distribution. Each
            sensor draws an independent ``ra_arcsec`` and ``dec_arcsec``
            in ``[-bias_range_arcsec, +bias_range_arcsec]``.

    Returns:
        Dict mapping ``sensor_id`` (str) to
        ``{"ra_arcsec": float, "dec_arcsec": float}``. Empty dict if
        ``sensor_ids`` is empty or contains only ``None``.

    Edge cases:
        - Empty input -> empty output, no error.
        - All-None input -> empty output, no error.
        - Duplicate sensor IDs (same string repeated) -> single entry.
        - Numeric sensor IDs are coerced to strings via ``str()``.
    """
    if not sensor_ids:
        return {}

    # Dedupe + drop None + stringify, then sort for stable iteration so
    # the same seed always produces the same result regardless of input
    # ordering.
    unique_ids = sorted({str(s) for s in sensor_ids if s is not None})
    if not unique_ids:
        return {}

    rng = np.random.default_rng(seed)
    biases: Dict[str, Dict[str, float]] = {}
    for sensor_id in unique_ids:
        biases[sensor_id] = {
            "ra_arcsec": float(rng.uniform(-bias_range_arcsec, bias_range_arcsec)),
            "dec_arcsec": float(rng.uniform(-bias_range_arcsec, bias_range_arcsec)),
        }
    return biases
