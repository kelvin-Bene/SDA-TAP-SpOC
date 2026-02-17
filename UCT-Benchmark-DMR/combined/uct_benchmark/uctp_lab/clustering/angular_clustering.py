"""
Angular DBSCAN clustering for observation grouping.

Uses DBSCAN on angular features (RA, Dec, time, angular rate) with
great-circle distance to group observations belonging to the same object.
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from ..config import ClusteringConfig
from ..transforms import radec_to_unit_vector
from .base import AbstractClusterer


class AngularDBSCANClusterer(AbstractClusterer):
    """
    DBSCAN-based clusterer using angular and temporal features.

    Feature vector per observation:
    - Unit direction vector (x, y, z) from RA/Dec
    - Normalized time (seconds from first observation)
    - Optional: angular rate features
    """

    def cluster(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        """
        Cluster observations using DBSCAN on angular+temporal features.

        Args:
            observations: DataFrame with [id, ob_time, ra, declination].

        Returns:
            Dict mapping cluster_id -> list of observation IDs.
        """
        if len(observations) < self.config.min_samples:
            logger.warning(
                f"Only {len(observations)} observations, fewer than min_samples={self.config.min_samples}"
            )
            return {-1: observations["id"].tolist()}

        features = self._build_features(observations)

        # Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        # Run DBSCAN
        dbscan = DBSCAN(
            eps=self.config.eps_deg,
            min_samples=self.config.min_samples,
            metric="euclidean",
        )
        labels = dbscan.fit_predict(features_scaled)

        # Group observation IDs by cluster label
        clusters: Dict[int, List[str]] = {}
        for idx, label in enumerate(labels):
            label_int = int(label)
            if label_int not in clusters:
                clusters[label_int] = []
            clusters[label_int].append(observations.iloc[idx]["id"])

        n_clusters = len([k for k in clusters if k != -1])
        n_noise = len(clusters.get(-1, []))
        logger.info(
            f"DBSCAN found {n_clusters} clusters, {n_noise} noise points "
            f"from {len(observations)} observations"
        )
        return clusters

    def _build_features(self, obs: pd.DataFrame) -> np.ndarray:
        """Build feature matrix from observations."""
        # Direction vectors from RA/Dec
        unit_vectors = np.array([
            radec_to_unit_vector(row["ra"], row["declination"])
            for _, row in obs.iterrows()
        ])

        # Normalized time (seconds from first observation)
        times = pd.to_datetime(obs["ob_time"])
        t0 = times.min()
        time_seconds = (times - t0).dt.total_seconds().values
        # Normalize to [0, 1] range, then scale by time_weight
        if time_seconds.max() > 0:
            time_norm = (time_seconds / time_seconds.max()) * self.config.time_weight
        else:
            time_norm = np.zeros_like(time_seconds)

        features = np.column_stack([unit_vectors, time_norm])

        # Optional angular rate features
        if self.config.use_angular_rate and len(obs) > 1:
            rates = self._compute_angular_rates(obs, time_seconds)
            rate_norm = rates * self.config.rate_weight
            features = np.column_stack([features, rate_norm])

        return features

    def _compute_angular_rates(
        self, obs: pd.DataFrame, time_seconds: np.ndarray
    ) -> np.ndarray:
        """Compute estimated angular rate for each observation using neighbors."""
        from ..transforms import great_circle_distance

        rates = np.zeros(len(obs))
        for i in range(len(obs)):
            # Use adjacent observations for rate estimation
            if i > 0:
                dt = abs(time_seconds[i] - time_seconds[i - 1])
                if dt > 0:
                    ang = great_circle_distance(
                        obs.iloc[i]["ra"], obs.iloc[i]["declination"],
                        obs.iloc[i - 1]["ra"], obs.iloc[i - 1]["declination"],
                    )
                    rates[i] = ang / dt
        return rates
