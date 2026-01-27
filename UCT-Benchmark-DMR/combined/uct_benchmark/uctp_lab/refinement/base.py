"""Abstract interface for orbit refinement algorithms."""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from ..config import RefinementConfig
from ..iod.base import IODResult


class AbstractRefiner(ABC):
    """Base class for all orbit refinement algorithms."""

    def __init__(self, config: RefinementConfig):
        self.config = config

    @abstractmethod
    def refine(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        """
        Refine an initial orbit estimate using additional observations.

        Args:
            initial_orbit: IOD result to refine.
            observations: All observations in this cluster.

        Returns:
            Refined IODResult with updated state and covariance, or None if failed.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
