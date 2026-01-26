"""
Progress tracking system for dataset generation pipeline.

Provides stage-aware progress callbacks that report both overall progress
and current stage descriptions for better user visibility.
"""

from enum import Enum
from typing import TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from . import JobManager


class DatasetStage(str, Enum):
    """Stages in the dataset generation pipeline."""

    INITIALIZING = "initializing"
    COLLECTING_OBSERVATIONS = "collecting_observations"
    COLLECTING_STATE_VECTORS = "collecting_state_vectors"
    COLLECTING_TLES = "collecting_tles"
    APPLYING_DOWNSAMPLING = "applying_downsampling"
    RUNNING_SIMULATION = "running_simulation"
    PERSISTING_DATABASE = "persisting_database"
    FINALIZING = "finalizing"


# Human-readable descriptions for each stage
STAGE_DESCRIPTIONS: Dict[DatasetStage, str] = {
    DatasetStage.INITIALIZING: "Initializing pipeline...",
    DatasetStage.COLLECTING_OBSERVATIONS: "Downloading observations from UDL...",
    DatasetStage.COLLECTING_STATE_VECTORS: "Fetching state vector data...",
    DatasetStage.COLLECTING_TLES: "Retrieving TLE data...",
    DatasetStage.APPLYING_DOWNSAMPLING: "Applying downsampling...",
    DatasetStage.RUNNING_SIMULATION: "Running TLE propagation simulation...",
    DatasetStage.PERSISTING_DATABASE: "Saving to database...",
    DatasetStage.FINALIZING: "Finalizing dataset...",
}


# Default stage weights (sum to 100)
# These are adjusted dynamically based on enabled features
DEFAULT_STAGE_WEIGHTS: Dict[DatasetStage, int] = {
    DatasetStage.INITIALIZING: 2,
    DatasetStage.COLLECTING_OBSERVATIONS: 30,
    DatasetStage.COLLECTING_STATE_VECTORS: 15,
    DatasetStage.COLLECTING_TLES: 8,
    DatasetStage.APPLYING_DOWNSAMPLING: 15,
    DatasetStage.RUNNING_SIMULATION: 20,
    DatasetStage.PERSISTING_DATABASE: 7,
    DatasetStage.FINALIZING: 3,
}


def calculate_stage_weights(
    downsampling_enabled: bool = False,
    simulation_enabled: bool = False,
) -> Dict[DatasetStage, int]:
    """
    Calculate stage weights based on which features are enabled.

    When downsampling or simulation is disabled, their weights are
    redistributed proportionally to other stages.

    Args:
        downsampling_enabled: Whether downsampling is enabled
        simulation_enabled: Whether simulation is enabled

    Returns:
        Dictionary mapping stages to their weight percentages
    """
    weights = DEFAULT_STAGE_WEIGHTS.copy()

    # Remove weight from disabled stages
    removed_weight = 0

    if not downsampling_enabled:
        removed_weight += weights[DatasetStage.APPLYING_DOWNSAMPLING]
        weights[DatasetStage.APPLYING_DOWNSAMPLING] = 0

    if not simulation_enabled:
        removed_weight += weights[DatasetStage.RUNNING_SIMULATION]
        weights[DatasetStage.RUNNING_SIMULATION] = 0

    # Redistribute removed weight proportionally to remaining stages
    if removed_weight > 0:
        active_weights = {k: v for k, v in weights.items() if v > 0}
        total_active = sum(active_weights.values())

        if total_active > 0:
            for stage in active_weights:
                # Add proportional share of removed weight
                share = (weights[stage] / total_active) * removed_weight
                weights[stage] += share

    return weights


def create_job_progress_callback(
    job_id: str,
    job_manager: "JobManager",
    downsampling_enabled: bool = False,
    simulation_enabled: bool = False,
) -> Callable[[DatasetStage, float], None]:
    """
    Create a progress callback function for a dataset generation job.

    The callback updates the job's progress and stage description based
    on the current stage and progress within that stage.

    Args:
        job_id: ID of the job to update
        job_manager: JobManager instance to use for updates
        downsampling_enabled: Whether downsampling is enabled
        simulation_enabled: Whether simulation is enabled

    Returns:
        A callback function that accepts (stage, stage_progress)
        where stage_progress is 0.0-1.0 within the stage
    """
    weights = calculate_stage_weights(downsampling_enabled, simulation_enabled)

    # Build cumulative progress boundaries for each stage
    stage_order = [
        DatasetStage.INITIALIZING,
        DatasetStage.COLLECTING_OBSERVATIONS,
        DatasetStage.COLLECTING_STATE_VECTORS,
        DatasetStage.COLLECTING_TLES,
        DatasetStage.APPLYING_DOWNSAMPLING,
        DatasetStage.RUNNING_SIMULATION,
        DatasetStage.PERSISTING_DATABASE,
        DatasetStage.FINALIZING,
    ]

    cumulative = 0
    stage_ranges: Dict[DatasetStage, tuple] = {}

    for stage in stage_order:
        start = cumulative
        end = cumulative + weights[stage]
        stage_ranges[stage] = (start, end)
        cumulative = end

    def progress_callback(stage: DatasetStage, stage_progress: float = 0.0) -> None:
        """
        Report progress for a pipeline stage.

        Args:
            stage: Current pipeline stage
            stage_progress: Progress within the current stage (0.0 to 1.0)
        """
        # Skip disabled stages
        if weights.get(stage, 0) == 0:
            return

        # Calculate overall progress
        start, end = stage_ranges[stage]
        overall_progress = start + (end - start) * min(1.0, max(0.0, stage_progress))

        # Get stage description
        description = STAGE_DESCRIPTIONS.get(stage, "Processing...")

        # Update the job
        job_manager.update_job(
            job_id,
            progress=int(overall_progress),
            stage=description,
        )

    return progress_callback


# Type alias for the progress callback
ProgressCallback = Callable[[DatasetStage, float], None]
