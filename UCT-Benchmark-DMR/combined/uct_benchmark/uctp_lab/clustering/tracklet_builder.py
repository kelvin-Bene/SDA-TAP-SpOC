"""
Tracklet builder for forming short-arc observation sequences.

Groups temporally-close observations from the same sensor into tracklets
before full clustering, reducing the problem dimensionality.
"""

from typing import Dict, List, Tuple

import pandas as pd
from loguru import logger


class TrackletBuilder:
    """
    Forms tracklets from raw observations based on temporal proximity.

    A tracklet is a short sequence of observations from the same sensor
    within a maximum time gap, likely representing a single pass.
    """

    def __init__(self, max_gap_seconds: float = 60.0, min_length: int = 2):
        """
        Args:
            max_gap_seconds: Maximum time gap between consecutive observations in a tracklet.
            min_length: Minimum number of observations to form a valid tracklet.
        """
        self.max_gap_seconds = max_gap_seconds
        self.min_length = min_length

    def build_tracklets(self, observations: pd.DataFrame) -> List[List[str]]:
        """
        Build tracklets from observations.

        Groups observations by sensor (if available) and then by temporal proximity.

        Args:
            observations: DataFrame with [id, ob_time, ra, declination, sensor_name?].

        Returns:
            List of tracklets, each being a list of observation IDs.
        """
        if "sensor_name" in observations.columns:
            groups = observations.groupby("sensor_name", dropna=False)
        else:
            groups = [("all", observations)]

        tracklets = []
        for sensor, group in groups:
            group_sorted = group.sort_values("ob_time").reset_index(drop=True)
            sensor_tracklets = self._split_by_gap(group_sorted)
            tracklets.extend(sensor_tracklets)

        # Filter by minimum length
        valid = [t for t in tracklets if len(t) >= self.min_length]
        logger.info(
            f"Built {len(valid)} tracklets ({len(tracklets) - len(valid)} dropped below min_length={self.min_length})"
        )
        return valid

    def _split_by_gap(self, obs: pd.DataFrame) -> List[List[str]]:
        """Split sorted observations into tracklets based on time gaps."""
        if len(obs) == 0:
            return []

        times = pd.to_datetime(obs["ob_time"])
        tracklets = []
        current: List[str] = [obs.iloc[0]["id"]]

        for i in range(1, len(obs)):
            gap = (times.iloc[i] - times.iloc[i - 1]).total_seconds()
            if gap > self.max_gap_seconds:
                tracklets.append(current)
                current = []
            current.append(obs.iloc[i]["id"])

        if current:
            tracklets.append(current)

        return tracklets

    def summarize_tracklets(
        self, tracklets: List[List[str]], observations: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create a summary DataFrame with one row per tracklet.

        Computes mean RA/Dec, time midpoint, and angular extent for each tracklet.

        Returns:
            DataFrame with columns [tracklet_id, obs_ids, mean_ra, mean_dec,
            midpoint_time, n_obs, angular_extent_deg].
        """
        from ..transforms import great_circle_distance

        summaries = []
        obs_indexed = observations.set_index("id")

        for tid, obs_ids in enumerate(tracklets):
            track_obs = obs_indexed.loc[obs_ids]
            mean_ra = track_obs["ra"].mean()
            mean_dec = track_obs["declination"].mean()
            times = pd.to_datetime(track_obs["ob_time"])
            midpoint = times.min() + (times.max() - times.min()) / 2

            # Angular extent
            if len(obs_ids) >= 2:
                first = track_obs.iloc[0]
                last = track_obs.iloc[-1]
                extent = great_circle_distance(
                    first["ra"], first["declination"],
                    last["ra"], last["declination"],
                )
            else:
                extent = 0.0

            summaries.append({
                "tracklet_id": tid,
                "obs_ids": obs_ids,
                "mean_ra": mean_ra,
                "mean_dec": mean_dec,
                "midpoint_time": midpoint,
                "n_obs": len(obs_ids),
                "angular_extent_deg": extent,
            })

        return pd.DataFrame(summaries)
