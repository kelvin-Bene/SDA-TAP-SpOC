"""Abstract interface for observation clustering algorithms."""

from abc import ABC, abstractmethod
from typing import Dict, List

import pandas as pd

from ..config import ClusteringConfig


class AbstractClusterer(ABC):
    """Base class for all clustering algorithms in the UCTP pipeline."""

    def __init__(self, config: ClusteringConfig):
        self.config = config

    @abstractmethod
    def cluster(self, observations: pd.DataFrame) -> Dict[int, List[str]]:
        """
        Cluster observations into groups believed to belong to the same object.

        Args:
            observations: DataFrame with columns [id, ob_time, ra, declination, ...].

        Returns:
            Dictionary mapping cluster_id -> list of observation IDs.
            Noise/unassigned observations should be in cluster_id = -1.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
