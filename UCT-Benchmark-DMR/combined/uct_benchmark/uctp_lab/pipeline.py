"""
UCTP Pipeline orchestrator.

Manages the full pipeline: Ingest -> Cluster -> IOD -> Refine -> Output.
Provides progress callbacks and logging throughout execution.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from loguru import logger

from .clustering.angular_clustering import AngularDBSCANClusterer
from .clustering.base import AbstractClusterer
from .config import (
    ClusteringMethod,
    IODMethod,
    RefinementMethod,
    UCTPConfig,
)
from .iod.base import AbstractIOD, IODResult
from .iod.gauss_iod import GaussIOD
from .ingest import (
    load_observations_from_database,
    load_observations_from_dataframe,
    load_observations_from_json,
)
from .output import build_output, save_output
from .refinement.base import AbstractRefiner


@dataclass
class PipelineMetrics:
    """Metrics collected during pipeline execution."""
    total_observations: int = 0
    clusters_found: int = 0
    noise_observations: int = 0
    iod_attempted: int = 0
    iod_succeeded: int = 0
    refinement_attempted: int = 0
    refinement_succeeded: int = 0
    objects_resolved: int = 0
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_observations": self.total_observations,
            "clusters_found": self.clusters_found,
            "noise_observations": self.noise_observations,
            "iod_attempted": self.iod_attempted,
            "iod_succeeded": self.iod_succeeded,
            "refinement_attempted": self.refinement_attempted,
            "refinement_succeeded": self.refinement_succeeded,
            "objects_resolved": self.objects_resolved,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


@dataclass
class PipelineResult:
    """Result from a complete pipeline run."""
    config: UCTPConfig
    metrics: PipelineMetrics
    output: List[Dict[str, Any]]
    output_path: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "metrics": self.metrics.to_dict(),
            "output_count": len(self.output),
            "output_path": self.output_path,
            "error": self.error,
        }


ProgressCallback = Callable[[str, float], None]


class UCTPPipeline:
    """
    Orchestrates the full UCTP processing pipeline.

    Usage:
        config = UCTPConfig(...)
        pipeline = UCTPPipeline(config)
        result = pipeline.run()
    """

    def __init__(
        self,
        config: UCTPConfig,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.config = config
        self.progress_callback = progress_callback or (lambda stage, pct: None)
        self.metrics = PipelineMetrics()
        self.logs: List[str] = []
        self._clusterer: Optional[AbstractClusterer] = None
        self._iod: Optional[AbstractIOD] = None
        self._refiner: Optional[AbstractRefiner] = None

    def run(
        self,
        observations: Optional[pd.DataFrame] = None,
    ) -> PipelineResult:
        """
        Execute the full pipeline.

        Args:
            observations: Pre-loaded observations DataFrame. If None,
                         loads from config.input_path or config.dataset_id.

        Returns:
            PipelineResult with metrics, output, and logs.
        """
        start_time = time.time()
        self._log("Pipeline started")

        try:
            # Step 1: Ingest
            self._report_progress("ingest", 0.0)
            if observations is None:
                observations = self._ingest()
            else:
                from .ingest import load_observations_from_dataframe
                observations = load_observations_from_dataframe(observations)

            self.metrics.total_observations = len(observations)
            self._log(f"Ingested {len(observations)} observations")
            self._report_progress("ingest", 1.0)

            if len(observations) == 0:
                return self._finalize([], start_time, error="No observations to process")

            # Step 2: Cluster
            self._report_progress("clustering", 0.0)
            clusterer = self._get_clusterer()
            clusters = clusterer.cluster(observations)
            self.metrics.clusters_found = len([k for k in clusters if k != -1])
            self.metrics.noise_observations = len(clusters.get(-1, []))
            self._log(
                f"Clustering: {self.metrics.clusters_found} clusters, "
                f"{self.metrics.noise_observations} noise"
            )
            self._report_progress("clustering", 1.0)

            # Step 3: IOD per cluster
            self._report_progress("iod", 0.0)
            iod_engine = self._get_iod()
            resolved_clusters = []
            valid_clusters = {k: v for k, v in clusters.items() if k != -1}
            total = len(valid_clusters)

            for idx, (cluster_id, obs_ids) in enumerate(valid_clusters.items()):
                cluster_obs = observations[observations["id"].isin(obs_ids)]
                self.metrics.iod_attempted += 1

                result = iod_engine.determine_orbit(cluster_obs)
                if result is not None:
                    self.metrics.iod_succeeded += 1

                    # Step 4: Refinement (per cluster)
                    if self.config.refinement.method != RefinementMethod.NONE:
                        refiner = self._get_refiner()
                        if refiner is not None:
                            self.metrics.refinement_attempted += 1
                            refined = refiner.refine(result, cluster_obs)
                            if refined is not None:
                                result = refined
                                self.metrics.refinement_succeeded += 1

                    resolved_clusters.append({
                        "observation_ids": result.observation_ids,
                        "state": result.state.tolist(),
                        "epoch": result.epoch,
                        "covariance": result.covariance,
                    })

                if total > 0:
                    self._report_progress("iod", (idx + 1) / total)

            self.metrics.objects_resolved = len(resolved_clusters)
            self._log(
                f"IOD: {self.metrics.iod_succeeded}/{self.metrics.iod_attempted} succeeded, "
                f"{self.metrics.objects_resolved} objects resolved"
            )

            # Step 5: Output
            self._report_progress("output", 0.0)
            output = build_output(resolved_clusters, self.config.reference_frame)
            self._report_progress("output", 1.0)

            return self._finalize(output, start_time)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self._log(f"Pipeline error: {error_msg}")
            logger.error(f"UCTP Pipeline error: {error_msg}")
            return self._finalize([], start_time, error=error_msg)

    def _ingest(self) -> pd.DataFrame:
        """Load observations from configured source."""
        if self.config.input_path:
            return load_observations_from_json(self.config.input_path)
        elif self.config.dataset_id:
            return load_observations_from_database(self.config.dataset_id)
        else:
            raise ValueError("No input source: set input_path or dataset_id in config")

    def _get_clusterer(self) -> AbstractClusterer:
        """Get or create the clustering algorithm."""
        if self._clusterer is None:
            method = self.config.clustering.method
            if method == ClusteringMethod.ANGULAR_DBSCAN:
                self._clusterer = AngularDBSCANClusterer(self.config.clustering)
            elif method == ClusteringMethod.STONESOUP_MHT:
                try:
                    from .clustering.stonesoup_tracker import StoneSoupMHTClusterer
                    self._clusterer = StoneSoupMHTClusterer(self.config.clustering)
                except ImportError:
                    logger.warning("Stone Soup not installed, falling back to Angular DBSCAN")
                    self._clusterer = AngularDBSCANClusterer(self.config.clustering)
            elif method == ClusteringMethod.STONESOUP_GNN:
                try:
                    from .clustering.stonesoup_tracker import StoneSoupGNNClusterer
                    self._clusterer = StoneSoupGNNClusterer(self.config.clustering)
                except ImportError:
                    logger.warning("Stone Soup not installed, falling back to Angular DBSCAN")
                    self._clusterer = AngularDBSCANClusterer(self.config.clustering)
            else:
                self._clusterer = AngularDBSCANClusterer(self.config.clustering)
        return self._clusterer

    def _get_iod(self) -> AbstractIOD:
        """Get or create the IOD algorithm."""
        if self._iod is None:
            method = self.config.iod.method
            if method == IODMethod.GAUSS:
                self._iod = GaussIOD(self.config.iod)
            elif method == IODMethod.ORBDETPY_LAPLACE:
                try:
                    from .iod.orbdetpy_iod import OrbdetpyLaplaceIOD
                    self._iod = OrbdetpyLaplaceIOD(self.config.iod)
                except ImportError:
                    logger.warning("orbdetpy not installed, falling back to Gauss IOD")
                    self._iod = GaussIOD(self.config.iod)
            elif method == IODMethod.OREKIT_GOODING:
                try:
                    from .iod.orekit_iod import OrekitGoodingIOD
                    self._iod = OrekitGoodingIOD(self.config.iod)
                except ImportError:
                    logger.warning("Orekit not available, falling back to Gauss IOD")
                    self._iod = GaussIOD(self.config.iod)
            else:
                self._iod = GaussIOD(self.config.iod)
        return self._iod

    def _get_refiner(self) -> Optional[AbstractRefiner]:
        """Get or create the refinement algorithm."""
        if self._refiner is None:
            method = self.config.refinement.method
            if method == RefinementMethod.NONE:
                return None
            elif method == RefinementMethod.BATCH_LEAST_SQUARES:
                try:
                    from .refinement.least_squares import BatchLeastSquaresRefiner
                    self._refiner = BatchLeastSquaresRefiner(self.config.refinement)
                except ImportError:
                    logger.warning("orbdetpy not installed, skipping refinement")
                    return None
            elif method == RefinementMethod.EKF:
                try:
                    from .refinement.kalman_filter import EKFRefiner
                    self._refiner = EKFRefiner(self.config.refinement)
                except ImportError:
                    logger.warning("Kalman filter refinement unavailable, skipping")
                    return None
            elif method == RefinementMethod.UKF:
                try:
                    from .refinement.kalman_filter import UKFRefiner
                    self._refiner = UKFRefiner(self.config.refinement)
                except ImportError:
                    logger.warning("UKF refinement unavailable, skipping")
                    return None
        return self._refiner

    def _finalize(
        self,
        output: List[Dict[str, Any]],
        start_time: float,
        error: Optional[str] = None,
    ) -> PipelineResult:
        """Create the final result and optionally save output."""
        self.metrics.elapsed_seconds = time.time() - start_time
        self._log(f"Pipeline completed in {self.metrics.elapsed_seconds:.2f}s")

        output_path = None
        if output and self.config.output_path:
            output_path = save_output(output, self.config.output_path)

        return PipelineResult(
            config=self.config,
            metrics=self.metrics,
            output=output,
            output_path=output_path,
            logs=self.logs,
            error=error,
        )

    def _log(self, message: str) -> None:
        """Add a timestamped log entry."""
        entry = f"[{datetime.utcnow().isoformat()}] {message}"
        self.logs.append(entry)
        logger.info(f"UCTP: {message}")

    def _report_progress(self, stage: str, fraction: float) -> None:
        """Report pipeline progress."""
        self.progress_callback(stage, fraction)
