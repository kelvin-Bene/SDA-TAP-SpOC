# -*- coding: utf-8 -*-
"""
Enhanced logging configuration for UCT Benchmarking.

Provides:
- Structured file logging
- API call logging
- Metrics collection
- Log rotation

Created for UCT Benchmarking Enhancement.
"""

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from uct_benchmark.settings import DatasetMetrics, LoggingConfig

# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logging(config: LoggingConfig = None, run_id: str = None) -> Dict[str, Path]:
    """
    Setup enhanced logging with file handlers.

    Args:
        config: LoggingConfig instance (uses defaults if None)
        run_id: Optional run identifier for log file naming

    Returns:
        Dict with paths to created log files
    """
    if config is None:
        config = LoggingConfig()

    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure log directory exists
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Define log file paths
    log_paths = {
        "main": log_dir / f"uctp_{run_id}.log",
        "api": log_dir / f"api_{run_id}.log",
        "metrics": log_dir / f"metrics_{run_id}.json",
    }

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        level=config.console_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # Add main log file handler
    logger.add(
        str(log_paths["main"]),
        level=config.file_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=f"{config.rotation_size_mb} MB",
        retention=f"{config.retention_days} days",
        compression="zip",
    )

    # Add API-specific log handler
    if config.log_api_calls:
        logger.add(
            str(log_paths["api"]),
            level=config.api_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            filter=lambda record: record["extra"].get("name") == "udl.api",
            rotation=f"{config.rotation_size_mb} MB",
            retention=f"{config.retention_days} days",
        )

    logger.info(f"Logging initialized - run_id: {run_id}")

    return log_paths


def get_api_logger():
    """Get a logger instance configured for API calls."""
    return logger.bind(name="udl.api")


# =============================================================================
# METRICS COLLECTION
# =============================================================================


class MetricsCollector:
    """Collects and aggregates metrics during dataset generation."""

    def __init__(self, run_id: str = None):
        self.run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.utcnow()
        self.metrics = DatasetMetrics(
            run_id=self.run_id,
            start_time=self.start_time.isoformat() + "Z",
        )
        self._api_calls: List[Dict] = []
        self._satellite_stats: Dict[int, Dict] = {}

    def log_api_call(
        self,
        service: str,
        params: Dict,
        records: int,
        elapsed_ms: float,
        success: bool = True,
        error: str = None,
    ) -> None:
        """Log an API call."""
        call_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service,
            "params": {k: str(v)[:100] for k, v in params.items()},
            "records": records,
            "elapsed_ms": elapsed_ms,
            "success": success,
            "error": error,
        }
        self._api_calls.append(call_record)

        self.metrics.total_api_calls += 1
        self.metrics.total_records_fetched += records
        if not success:
            self.metrics.api_errors += 1

    def log_satellite_processed(
        self,
        sat_no: int,
        raw_obs: int,
        final_obs: int,
        synthetic_obs: int,
        tier: str,
        coverage: float,
        max_gap: float,
    ) -> None:
        """Log processing stats for a satellite."""
        self._satellite_stats[sat_no] = {
            "raw_obs": raw_obs,
            "final_obs": final_obs,
            "synthetic_obs": synthetic_obs,
            "tier": tier,
            "coverage": coverage,
            "max_gap": max_gap,
        }

        self.metrics.satellites_processed += 1
        self.metrics.observations_raw += raw_obs
        self.metrics.observations_final += final_obs
        self.metrics.synthetic_observations += synthetic_obs

        # Update tier distribution
        if tier not in self.metrics.tier_distribution:
            self.metrics.tier_distribution[tier] = 0
        self.metrics.tier_distribution[tier] += 1

    def finalize(self, config_hash: str = None) -> DatasetMetrics:
        """Finalize metrics collection."""
        self.metrics.end_time = datetime.utcnow().isoformat() + "Z"

        if config_hash:
            self.metrics.config_hash = config_hash

        # Compute coverage stats
        if self._satellite_stats:
            coverages = [s["coverage"] for s in self._satellite_stats.values()]
            gaps = [s["max_gap"] for s in self._satellite_stats.values()]

            self.metrics.coverage_stats = {
                "min": min(coverages),
                "max": max(coverages),
                "mean": sum(coverages) / len(coverages),
            }
            self.metrics.gap_stats = {
                "min": min(gaps),
                "max": max(gaps),
                "mean": sum(gaps) / len(gaps),
            }

        return self.metrics

    def save(self, output_path: Path) -> None:
        """Save metrics to JSON file."""
        metrics_dict = asdict(self.metrics)
        metrics_dict["api_calls"] = self._api_calls[-100:]  # Keep last 100 calls
        metrics_dict["satellite_stats"] = self._satellite_stats

        with open(output_path, "w") as f:
            json.dump(metrics_dict, f, indent=2, default=str)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics."""
        return {
            "run_id": self.run_id,
            "duration_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
            "api_calls": self.metrics.total_api_calls,
            "api_errors": self.metrics.api_errors,
            "satellites": self.metrics.satellites_processed,
            "observations": {
                "raw": self.metrics.observations_raw,
                "final": self.metrics.observations_final,
                "synthetic": self.metrics.synthetic_observations,
            },
            "tiers": self.metrics.tier_distribution,
        }


# =============================================================================
# PERFORMANCE TIMING
# =============================================================================


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str, logger_instance=None):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.utcnow()
        elapsed = (self.end_time - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"Completed: {self.operation_name} ({elapsed:.2f}s)")
        else:
            self.logger.error(f"Failed: {self.operation_name} ({elapsed:.2f}s) - {exc_val}")

        return False  # Don't suppress exceptions

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


def timed_operation(operation_name: str):
    """Decorator for timing function execution."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceTimer(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# LOG ANALYSIS
# =============================================================================


def parse_api_log(log_path: Path) -> List[Dict]:
    """
    Parse an API log file into structured records.

    Args:
        log_path: Path to API log file

    Returns:
        List of parsed log records
    """
    records = []

    if not log_path.exists():
        return records

    with open(log_path, "r") as f:
        for line in f:
            try:
                # Parse timestamp and message
                parts = line.strip().split(" | ", 1)
                if len(parts) == 2:
                    timestamp, message = parts

                    # Try to parse JSON message
                    if message.startswith("{"):
                        record = json.loads(message)
                        record["timestamp"] = timestamp
                        records.append(record)
            except (json.JSONDecodeError, ValueError):
                continue

    return records


def summarize_api_performance(log_path: Path) -> Dict[str, Any]:
    """
    Generate API performance summary from log file.

    Args:
        log_path: Path to API log file

    Returns:
        Performance summary dictionary
    """
    records = parse_api_log(log_path)

    if not records:
        return {"status": "no_records"}

    # Aggregate by service
    service_stats: Dict[str, Dict] = {}

    for record in records:
        service = record.get("service", "unknown")
        if service not in service_stats:
            service_stats[service] = {
                "calls": 0,
                "records": 0,
                "total_ms": 0,
                "errors": 0,
            }

        service_stats[service]["calls"] += 1
        service_stats[service]["records"] += record.get("response_records", 0)
        service_stats[service]["total_ms"] += record.get("elapsed_ms", 0)
        if not record.get("success", True):
            service_stats[service]["errors"] += 1

    # Compute averages
    for service in service_stats:
        calls = service_stats[service]["calls"]
        if calls > 0:
            service_stats[service]["avg_ms"] = service_stats[service]["total_ms"] / calls
            service_stats[service]["avg_records"] = service_stats[service]["records"] / calls

    return {
        "total_calls": len(records),
        "by_service": service_stats,
    }


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

# Global metrics collector (initialized when needed)
_global_metrics: Optional[MetricsCollector] = None


def get_global_metrics() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics


def reset_global_metrics() -> None:
    """Reset the global metrics collector."""
    global _global_metrics
    _global_metrics = None
