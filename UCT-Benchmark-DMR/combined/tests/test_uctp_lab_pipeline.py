"""
Tests for the UCTP Lab pipeline orchestration.

Run with: uv run pytest tests/test_uctp_lab_pipeline.py -v
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from uct_benchmark.uctp_lab.config import (
    ClusteringConfig,
    ClusteringMethod,
    IODConfig,
    IODMethod,
    RefinementConfig,
    RefinementMethod,
    UCTPConfig,
)
from uct_benchmark.uctp_lab.pipeline import PipelineMetrics, PipelineResult, UCTPPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_observations(n_objects: int = 3, obs_per_object: int = 10) -> pd.DataFrame:
    """Generate synthetic observations for multiple objects."""
    rows = []
    base_time = datetime(2025, 6, 1, 12, 0, 0)
    rng = np.random.default_rng(42)

    for obj in range(n_objects):
        # Each object at a distinct RA/Dec
        base_ra = 60.0 + obj * 30.0
        base_dec = 10.0 + obj * 15.0

        for i in range(obs_per_object):
            rows.append({
                "id": f"obs_{obj}_{i}",
                "ob_time": (base_time + timedelta(minutes=i * 10)).isoformat(),
                "ra": base_ra + rng.normal(0, 0.02),
                "declination": base_dec + rng.normal(0, 0.02),
                "sat_no": 25544 + obj,
            })

    return pd.DataFrame(rows)


@pytest.fixture
def sample_observations():
    return _make_observations()


@pytest.fixture
def default_config():
    return UCTPConfig(
        clustering=ClusteringConfig(
            method=ClusteringMethod.ANGULAR_DBSCAN,
            eps_deg=2.0,
            min_samples=3,
        ),
        iod=IODConfig(
            method=IODMethod.GAUSS,
            min_observations=3,
        ),
        refinement=RefinementConfig(
            method=RefinementMethod.NONE,
        ),
        name="test_run",
    )


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestUCTPConfig:
    def test_default_config(self):
        cfg = UCTPConfig()
        assert cfg.clustering.method == ClusteringMethod.ANGULAR_DBSCAN
        assert cfg.iod.method == IODMethod.GAUSS
        assert cfg.refinement.method == RefinementMethod.NONE
        assert cfg.reference_frame == "J2000"

    def test_serialize_roundtrip(self):
        cfg = UCTPConfig(
            name="test",
            clustering=ClusteringConfig(eps_deg=1.0, min_samples=5),
            iod=IODConfig(max_iterations=50),
        )
        d = cfg.to_dict()
        restored = UCTPConfig.from_dict(d)
        assert restored.name == "test"
        assert restored.clustering.eps_deg == 1.0
        assert restored.clustering.min_samples == 5
        assert restored.iod.max_iterations == 50

    def test_enum_values(self):
        assert ClusteringMethod.ANGULAR_DBSCAN.value == "angular_dbscan"
        assert IODMethod.GAUSS.value == "gauss"
        assert RefinementMethod.BATCH_LEAST_SQUARES.value == "batch_least_squares"


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------


class TestPipeline:
    def test_pipeline_runs_with_observations(self, sample_observations, default_config):
        pipeline = UCTPPipeline(default_config)
        result = pipeline.run(observations=sample_observations)

        assert isinstance(result, PipelineResult)
        assert result.error is None
        assert result.metrics.total_observations == 30
        assert result.metrics.clusters_found > 0
        assert result.metrics.elapsed_seconds > 0
        assert len(result.logs) > 0

    def test_pipeline_empty_observations(self, default_config):
        pipeline = UCTPPipeline(default_config)
        empty = pd.DataFrame(columns=["id", "ob_time", "ra", "declination"])
        result = pipeline.run(observations=empty)

        assert result.error == "No observations to process"
        assert result.metrics.total_observations == 0

    def test_pipeline_progress_callback(self, sample_observations, default_config):
        stages = []

        def on_progress(stage: str, pct: float):
            stages.append((stage, pct))

        pipeline = UCTPPipeline(default_config, progress_callback=on_progress)
        pipeline.run(observations=sample_observations)

        assert len(stages) > 0
        stage_names = [s[0] for s in stages]
        assert "ingest" in stage_names
        assert "clustering" in stage_names

    def test_pipeline_no_input_raises(self, default_config):
        pipeline = UCTPPipeline(default_config)
        result = pipeline.run()
        assert result.error is not None

    def test_pipeline_metrics_to_dict(self):
        m = PipelineMetrics(
            total_observations=100,
            clusters_found=5,
            iod_attempted=5,
            iod_succeeded=3,
        )
        d = m.to_dict()
        assert d["total_observations"] == 100
        assert d["iod_succeeded"] == 3


# ---------------------------------------------------------------------------
# Output format tests
# ---------------------------------------------------------------------------


class TestOutputFormat:
    def test_build_output_structure(self, sample_observations, default_config):
        pipeline = UCTPPipeline(default_config)
        result = pipeline.run(observations=sample_observations)

        if result.output:
            entry = result.output[0]
            assert "idStateVector" in entry
            assert "sourcedData" in entry
            assert "epoch" in entry
            assert "xpos" in entry or "state" in entry
            assert "referenceFrame" in entry

    def test_result_to_dict(self, sample_observations, default_config):
        pipeline = UCTPPipeline(default_config)
        result = pipeline.run(observations=sample_observations)
        d = result.to_dict()
        assert "config" in d
        assert "metrics" in d
        assert "output_count" in d
