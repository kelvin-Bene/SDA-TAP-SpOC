"""Abstract interface for initial orbit determination algorithms."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import IODConfig


class IODResult:
    """Result from an IOD computation."""

    def __init__(
        self,
        state: np.ndarray,
        epoch: str,
        observation_ids: List[str],
        covariance: Optional[List[float]] = None,
        method: str = "",
        iterations: int = 0,
        residual: float = 0.0,
    ):
        """
        Args:
            state: [x, y, z, vx, vy, vz] in km, km/s.
            epoch: ISO-format epoch of the state.
            observation_ids: IDs of observations used.
            covariance: 21-element upper-triangle covariance (optional).
            method: Name of the IOD method used.
            iterations: Number of iterations to converge.
            residual: Final residual measure.
        """
        self.state = np.asarray(state, dtype=float)
        self.epoch = epoch
        self.observation_ids = observation_ids
        self.covariance = covariance
        self.method = method
        self.iterations = iterations
        self.residual = residual

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.tolist(),
            "epoch": self.epoch,
            "observation_ids": self.observation_ids,
            "covariance": self.covariance,
            "method": self.method,
            "iterations": self.iterations,
            "residual": self.residual,
        }


class AbstractIOD(ABC):
    """Base class for all IOD algorithms in the UCTP pipeline."""

    def __init__(self, config: IODConfig):
        self.config = config

    @abstractmethod
    def determine_orbit(self, observations: pd.DataFrame) -> Optional[IODResult]:
        """
        Determine an initial orbit from a set of observations.

        Args:
            observations: DataFrame with [id, ob_time, ra, declination].
                          Must have at least config.min_observations rows.

        Returns:
            IODResult if successful, None if IOD failed.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
