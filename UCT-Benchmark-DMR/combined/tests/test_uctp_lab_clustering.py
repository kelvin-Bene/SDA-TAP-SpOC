"""
Tests for UCTP Lab clustering algorithms.

Run with: uv run pytest tests/test_uctp_lab_clustering.py -v
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from uct_benchmark.uctp_lab.clustering.angular_clustering import AngularDBSCANClusterer
from uct_benchmark.uctp_lab.clustering.base import AbstractClusterer
from uct_benchmark.uctp_lab.clustering.tracklet_builder import TrackletBuilder
from uct_benchmark.uctp_lab.config import ClusteringConfig, ClusteringMethod
from uct_benchmark.uctp_lab.transforms import (
    angular_separation_deg,
    great_circle_distance,
    radec_to_unit_vector,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def well_separated_obs() -> pd.DataFrame:
    """Three well-separated clusters of observations."""
    rows = []
    base_time = datetime(2025, 6, 1, 12, 0, 0)
    rng = np.random.default_rng(123)

    for obj in range(3):
        base_ra = 30.0 + obj * 60.0  # 30, 90, 150 deg
        base_dec = 20.0
        for i in range(8):
            rows.append({
                "id": f"obs_{obj}_{i}",
                "ob_time": (base_time + timedelta(minutes=i * 5)).isoformat(),
                "ra": base_ra + rng.normal(0, 0.01),
                "declination": base_dec + rng.normal(0, 0.01),
            })
    return pd.DataFrame(rows)


@pytest.fixture
def single_cluster_obs() -> pd.DataFrame:
    """Observations all from one object."""
    rows = []
    base_time = datetime(2025, 6, 1, 12, 0, 0)
    rng = np.random.default_rng(456)
    for i in range(15):
        rows.append({
            "id": f"obs_0_{i}",
            "ob_time": (base_time + timedelta(minutes=i * 3)).isoformat(),
            "ra": 100.0 + rng.normal(0, 0.02),
            "declination": 30.0 + rng.normal(0, 0.02),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Transform tests
# ---------------------------------------------------------------------------


class TestTransforms:
    def test_radec_to_unit_vector_norm(self):
        for ra in [0, 45, 90, 180, 270, 359]:
            for dec in [-89, -45, 0, 45, 89]:
                v = radec_to_unit_vector(ra, dec)
                assert abs(np.linalg.norm(v) - 1.0) < 1e-10

    def test_angular_separation_same_point(self):
        assert angular_separation_deg(10, 20, 10, 20) < 1e-10

    def test_angular_separation_opposite(self):
        sep = angular_separation_deg(0, 0, 180, 0)
        assert abs(sep - 180.0) < 1e-6

    def test_great_circle_distance(self):
        d = great_circle_distance(0, 0, 0, 90)
        # Returns angular distance in degrees
        assert abs(d - 90.0) < 1e-6


# ---------------------------------------------------------------------------
# DBSCAN clustering tests
# ---------------------------------------------------------------------------


class TestAngularDBSCAN:
    def test_inherits_abstract(self):
        cfg = ClusteringConfig()
        clusterer = AngularDBSCANClusterer(cfg)
        assert isinstance(clusterer, AbstractClusterer)

    def test_finds_multiple_clusters(self, well_separated_obs):
        # After StandardScaler, distances are normalised.  Use eps ~1.0
        # and disable angular-rate features so the feature space is simpler.
        cfg = ClusteringConfig(
            eps_deg=1.0,
            min_samples=3,
            time_weight=0.0,
            use_angular_rate=False,
        )
        clusterer = AngularDBSCANClusterer(cfg)
        clusters = clusterer.cluster(well_separated_obs)

        valid_clusters = {k: v for k, v in clusters.items() if k != -1}
        assert len(valid_clusters) >= 2  # should find at least 2 of the 3

    def test_single_cluster(self, single_cluster_obs):
        cfg = ClusteringConfig(eps_deg=5.0, min_samples=3)
        clusterer = AngularDBSCANClusterer(cfg)
        clusters = clusterer.cluster(single_cluster_obs)

        valid_clusters = {k: v for k, v in clusters.items() if k != -1}
        assert len(valid_clusters) >= 1

    def test_returns_observation_ids(self, well_separated_obs):
        cfg = ClusteringConfig(eps_deg=5.0, min_samples=3)
        clusterer = AngularDBSCANClusterer(cfg)
        clusters = clusterer.cluster(well_separated_obs)

        all_ids = set()
        for obs_ids in clusters.values():
            all_ids.update(obs_ids)

        input_ids = set(well_separated_obs["id"].tolist())
        assert all_ids == input_ids

    def test_tight_eps_more_noise(self, well_separated_obs):
        cfg = ClusteringConfig(eps_deg=0.001, min_samples=3)
        clusterer = AngularDBSCANClusterer(cfg)
        clusters = clusterer.cluster(well_separated_obs)

        noise_count = len(clusters.get(-1, []))
        # With very tight eps, most should be noise
        assert noise_count > 0


# ---------------------------------------------------------------------------
# Tracklet builder tests
# ---------------------------------------------------------------------------


class TestTrackletBuilder:
    def test_builds_tracklets(self, well_separated_obs):
        builder = TrackletBuilder(max_gap_seconds=600.0, min_length=2)
        tracklets = builder.build_tracklets(well_separated_obs)

        assert len(tracklets) > 0
        for t in tracklets:
            assert isinstance(t, list)
            assert len(t) >= 2

    def test_summarize(self, well_separated_obs):
        builder = TrackletBuilder(max_gap_seconds=600.0, min_length=2)
        tracklets = builder.build_tracklets(well_separated_obs)
        summary = builder.summarize_tracklets(tracklets, well_separated_obs)

        assert isinstance(summary, pd.DataFrame)
        assert len(summary) > 0
        assert "tracklet_id" in summary.columns
