"""
Stone Soup tracker integration for UCTP Lab.

Wraps the Stone Soup multi-hypothesis tracker (MHT) and global
nearest-neighbour (GNN) data associators as clustering backends.
Falls back gracefully when Stone Soup is not installed.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import ClusteringConfig
from .base import AbstractClusterer


class StoneSoupMHTClusterer(AbstractClusterer):
    """
    Multi-Hypothesis Tracking via Stone Soup.

    Uses Stone Soup's MHT data associator to cluster observations
    into tracks.  Requires stonesoup to be installed.
    """

    def __init__(self, config: ClusteringConfig):
        super().__init__(config)
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import stonesoup  # noqa: F401

                self._available = True
            except ImportError:
                self._available = False
                logger.warning("Stone Soup is not installed – MHT clusterer disabled")
        return self._available

    def cluster(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        if not self.available:
            return {-1: observations["id"].tolist()}

        try:
            return self._run_mht(observations)
        except Exception as e:
            logger.warning(f"StoneSoupMHT clustering failed: {e}")
            return {-1: observations["id"].tolist()}

    def _run_mht(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        from stonesoup.types.detection import Detection
        from stonesoup.types.state import GaussianState
        from stonesoup.models.measurement.linear import LinearGaussian
        from stonesoup.predictor.kalman import KalmanPredictor
        from stonesoup.updater.kalman import KalmanUpdater
        from stonesoup.hypothesiser.mhf import PDAHypothesiser
        from stonesoup.dataassociator.mfa import MFADataAssociator
        from stonesoup.initiator.simple import SinglePointInitiator
        from stonesoup.deleter.time import UpdateTimeStepsDeleter
        from stonesoup.tracker.simple import MultiTargetTracker
        from stonesoup.models.transition.linear import (
            CombinedLinearGaussianTransitionModel,
            ConstantVelocity,
        )
        import datetime

        obs = observations.sort_values("ob_time").reset_index(drop=True)

        # Build detection sets grouped by timestamp
        detection_sets = {}
        for _, row in obs.iterrows():
            t = pd.to_datetime(row["ob_time"])
            dt_key = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
            ra = float(row["ra"])
            dec = float(row["declination"])
            det = Detection(
                state_vector=np.array([[ra], [dec]]),
                timestamp=dt_key,
                metadata={"id": row["id"]},
            )
            detection_sets.setdefault(dt_key, set()).add(det)

        # Models
        transition = CombinedLinearGaussianTransitionModel(
            [ConstantVelocity(0.5), ConstantVelocity(0.5)]
        )
        measurement_model = LinearGaussian(
            ndim_state=4,
            mapping=(0, 2),
            noise_covar=np.diag([0.01, 0.01]),
        )

        predictor = KalmanPredictor(transition)
        updater = KalmanUpdater(measurement_model)

        hypothesiser = PDAHypothesiser(
            predictor=predictor,
            updater=updater,
            clutter_spatial_density=1e-4,
            prob_detect=0.9,
        )

        data_associator = MFADataAssociator(hypothesiser=hypothesiser)

        prior = GaussianState(
            state_vector=np.array([[0], [0], [0], [0]]),
            covar=np.diag([10, 1, 10, 1]),
        )

        initiator = SinglePointInitiator(prior_state=prior, measurement_model=measurement_model)
        deleter = UpdateTimeStepsDeleter(time_steps_since_update=5)

        tracker = MultiTargetTracker(
            initiator=initiator,
            deleter=deleter,
            detector=iter(sorted(detection_sets.items())),
            data_associator=data_associator,
            updater=updater,
        )

        # Run tracker and collect tracks
        clusters: Dict[int, List[str]] = {}
        assigned_ids = set()
        cluster_id = 0

        for time, tracks in tracker:
            for track in tracks:
                obs_ids = []
                for state in track.states:
                    if hasattr(state, "hypothesis") and state.hypothesis:
                        det = state.hypothesis.measurement
                        if det and hasattr(det, "metadata") and "id" in det.metadata:
                            obs_ids.append(det.metadata["id"])
                if obs_ids:
                    clusters[cluster_id] = obs_ids
                    assigned_ids.update(obs_ids)
                    cluster_id += 1

        # Collect unassigned as noise
        all_ids = set(observations["id"].tolist())
        noise = list(all_ids - assigned_ids)
        if noise:
            clusters[-1] = noise

        return clusters


class StoneSoupGNNClusterer(AbstractClusterer):
    """
    Global Nearest Neighbour data association via Stone Soup.

    A simpler single-hypothesis approach that greedily assigns
    each detection to the nearest existing track.
    """

    def __init__(self, config: ClusteringConfig):
        super().__init__(config)
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import stonesoup  # noqa: F401

                self._available = True
            except ImportError:
                self._available = False
                logger.warning("Stone Soup is not installed – GNN clusterer disabled")
        return self._available

    def cluster(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        if not self.available:
            return {-1: observations["id"].tolist()}

        try:
            return self._run_gnn(observations)
        except Exception as e:
            logger.warning(f"StoneSoupGNN clustering failed: {e}")
            return {-1: observations["id"].tolist()}

    def _run_gnn(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        from stonesoup.types.detection import Detection
        from stonesoup.types.state import GaussianState
        from stonesoup.models.measurement.linear import LinearGaussian
        from stonesoup.predictor.kalman import KalmanPredictor
        from stonesoup.updater.kalman import KalmanUpdater
        from stonesoup.hypothesiser.distance import DistanceHypothesiser
        from stonesoup.dataassociator.neighbour import GNNWith2DAssignment
        from stonesoup.initiator.simple import SinglePointInitiator
        from stonesoup.deleter.time import UpdateTimeStepsDeleter
        from stonesoup.tracker.simple import MultiTargetTracker
        from stonesoup.measures import Mahalanobis
        from stonesoup.models.transition.linear import (
            CombinedLinearGaussianTransitionModel,
            ConstantVelocity,
        )
        import datetime

        obs = observations.sort_values("ob_time").reset_index(drop=True)

        detection_sets = {}
        for _, row in obs.iterrows():
            t = pd.to_datetime(row["ob_time"])
            dt_key = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
            ra = float(row["ra"])
            dec = float(row["declination"])
            det = Detection(
                state_vector=np.array([[ra], [dec]]),
                timestamp=dt_key,
                metadata={"id": row["id"]},
            )
            detection_sets.setdefault(dt_key, set()).add(det)

        transition = CombinedLinearGaussianTransitionModel(
            [ConstantVelocity(0.5), ConstantVelocity(0.5)]
        )
        measurement_model = LinearGaussian(
            ndim_state=4,
            mapping=(0, 2),
            noise_covar=np.diag([0.01, 0.01]),
        )

        predictor = KalmanPredictor(transition)
        updater = KalmanUpdater(measurement_model)

        hypothesiser = DistanceHypothesiser(
            predictor=predictor,
            updater=updater,
            measure=Mahalanobis(),
            missed_distance=5.0,
        )

        data_associator = GNNWith2DAssignment(hypothesiser=hypothesiser)

        prior = GaussianState(
            state_vector=np.array([[0], [0], [0], [0]]),
            covar=np.diag([10, 1, 10, 1]),
        )
        initiator = SinglePointInitiator(prior_state=prior, measurement_model=measurement_model)
        deleter = UpdateTimeStepsDeleter(time_steps_since_update=5)

        tracker = MultiTargetTracker(
            initiator=initiator,
            deleter=deleter,
            detector=iter(sorted(detection_sets.items())),
            data_associator=data_associator,
            updater=updater,
        )

        clusters: Dict[int, List[str]] = {}
        assigned_ids = set()
        cluster_id = 0

        for time, tracks in tracker:
            for track in tracks:
                obs_ids = []
                for state in track.states:
                    if hasattr(state, "hypothesis") and state.hypothesis:
                        det = state.hypothesis.measurement
                        if det and hasattr(det, "metadata") and "id" in det.metadata:
                            obs_ids.append(det.metadata["id"])
                if obs_ids:
                    clusters[cluster_id] = obs_ids
                    assigned_ids.update(obs_ids)
                    cluster_id += 1

        all_ids = set(observations["id"].tolist())
        noise = list(all_ids - assigned_ids)
        if noise:
            clusters[-1] = noise

        return clusters
