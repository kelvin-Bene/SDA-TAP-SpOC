"""
Pipeline configuration dataclasses for UCTP Lab.

Defines all configurable parameters for the UCTP processing pipeline
including clustering, IOD, and refinement settings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ClusteringMethod(str, Enum):
    """Available clustering algorithms."""
    ANGULAR_DBSCAN = "angular_dbscan"
    STONESOUP_MHT = "stonesoup_mht"
    STONESOUP_GNN = "stonesoup_gnn"


class IODMethod(str, Enum):
    """Available initial orbit determination methods."""
    GAUSS = "gauss"
    ORBDETPY_LAPLACE = "orbdetpy_laplace"
    OREKIT_GOODING = "orekit_gooding"


class RefinementMethod(str, Enum):
    """Available orbit refinement methods."""
    NONE = "none"
    BATCH_LEAST_SQUARES = "batch_least_squares"
    EKF = "ekf"
    UKF = "ukf"


@dataclass
class ClusteringConfig:
    """Configuration for the clustering step."""
    method: ClusteringMethod = ClusteringMethod.ANGULAR_DBSCAN
    # DBSCAN parameters
    eps_deg: float = 0.5  # Angular separation threshold (degrees)
    min_samples: int = 3  # Minimum observations per cluster
    time_weight: float = 0.1  # Weight for temporal separation
    max_time_gap_hours: float = 24.0  # Max time gap within a cluster
    # Rate-based features
    use_angular_rate: bool = True
    rate_weight: float = 0.05


@dataclass
class IODConfig:
    """Configuration for the initial orbit determination step."""
    method: IODMethod = IODMethod.GAUSS
    min_observations: int = 3
    # Gauss-specific
    angular_separation_lower_deg: float = 1.0
    angular_separation_upper_deg: float = 30.0
    max_iterations: int = 100
    convergence_tol: float = 1e-5
    # Outlier culling
    cull_states: bool = True
    cull_sigma: float = 0.25  # Standard deviations for culling


@dataclass
class RefinementConfig:
    """Configuration for the orbit refinement step."""
    method: RefinementMethod = RefinementMethod.NONE
    max_iterations: int = 50
    convergence_tol: float = 1e-8
    # EKF/UKF specific
    process_noise_pos_km: float = 0.01
    process_noise_vel_km_s: float = 0.001


@dataclass
class UCTPConfig:
    """Complete UCTP pipeline configuration."""
    # Pipeline steps
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    iod: IODConfig = field(default_factory=IODConfig)
    refinement: RefinementConfig = field(default_factory=RefinementConfig)

    # General settings
    name: str = "default"
    description: str = ""
    reference_frame: str = "J2000"

    # Input/output
    dataset_id: Optional[int] = None
    input_path: Optional[str] = None
    output_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "reference_frame": self.reference_frame,
            "dataset_id": self.dataset_id,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "clustering": {
                "method": self.clustering.method.value,
                "eps_deg": self.clustering.eps_deg,
                "min_samples": self.clustering.min_samples,
                "time_weight": self.clustering.time_weight,
                "max_time_gap_hours": self.clustering.max_time_gap_hours,
                "use_angular_rate": self.clustering.use_angular_rate,
                "rate_weight": self.clustering.rate_weight,
            },
            "iod": {
                "method": self.iod.method.value,
                "min_observations": self.iod.min_observations,
                "angular_separation_lower_deg": self.iod.angular_separation_lower_deg,
                "angular_separation_upper_deg": self.iod.angular_separation_upper_deg,
                "max_iterations": self.iod.max_iterations,
                "convergence_tol": self.iod.convergence_tol,
                "cull_states": self.iod.cull_states,
                "cull_sigma": self.iod.cull_sigma,
            },
            "refinement": {
                "method": self.refinement.method.value,
                "max_iterations": self.refinement.max_iterations,
                "convergence_tol": self.refinement.convergence_tol,
                "process_noise_pos_km": self.refinement.process_noise_pos_km,
                "process_noise_vel_km_s": self.refinement.process_noise_vel_km_s,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UCTPConfig":
        """Deserialize config from a dictionary."""
        clustering_data = data.get("clustering", {})
        iod_data = data.get("iod", {})
        refinement_data = data.get("refinement", {})

        clustering = ClusteringConfig(
            method=ClusteringMethod(clustering_data.get("method", "angular_dbscan")),
            eps_deg=clustering_data.get("eps_deg", 0.5),
            min_samples=clustering_data.get("min_samples", 3),
            time_weight=clustering_data.get("time_weight", 0.1),
            max_time_gap_hours=clustering_data.get("max_time_gap_hours", 24.0),
            use_angular_rate=clustering_data.get("use_angular_rate", True),
            rate_weight=clustering_data.get("rate_weight", 0.05),
        )

        iod = IODConfig(
            method=IODMethod(iod_data.get("method", "gauss")),
            min_observations=iod_data.get("min_observations", 3),
            angular_separation_lower_deg=iod_data.get("angular_separation_lower_deg", 1.0),
            angular_separation_upper_deg=iod_data.get("angular_separation_upper_deg", 30.0),
            max_iterations=iod_data.get("max_iterations", 100),
            convergence_tol=iod_data.get("convergence_tol", 1e-5),
            cull_states=iod_data.get("cull_states", True),
            cull_sigma=iod_data.get("cull_sigma", 0.25),
        )

        refinement = RefinementConfig(
            method=RefinementMethod(refinement_data.get("method", "none")),
            max_iterations=refinement_data.get("max_iterations", 50),
            convergence_tol=refinement_data.get("convergence_tol", 1e-8),
            process_noise_pos_km=refinement_data.get("process_noise_pos_km", 0.01),
            process_noise_vel_km_s=refinement_data.get("process_noise_vel_km_s", 0.001),
        )

        return cls(
            clustering=clustering,
            iod=iod,
            refinement=refinement,
            name=data.get("name", "default"),
            description=data.get("description", ""),
            reference_frame=data.get("reference_frame", "J2000"),
            dataset_id=data.get("dataset_id"),
            input_path=data.get("input_path"),
            output_path=data.get("output_path"),
        )
