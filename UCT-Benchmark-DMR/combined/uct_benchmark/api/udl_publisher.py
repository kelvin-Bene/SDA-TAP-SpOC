# -*- coding: utf-8 -*-
"""
UDL Publisher Module - Push benchmark datasets to the Unified Data Library.

Provides the UDLPublisher class for publishing UCT Benchmark datasets,
observations, state vectors, and element sets to the UDL REST API.

Key features:
- Schema mapping from internal dataset format to UDL ingest format
- Provenance tagging based on benchmark tier (T1-T4)
- Dry-run mode for validation without write access
- Rate limiting and retry logic matching existing apiIntegration.py patterns
- Bulk upload via /udl/{service}/createBulk endpoints

Usage:
    from uct_benchmark.api import UDLPublisher

    publisher = UDLPublisher(token="your_base64_token")

    # Validate without pushing
    report = publisher.dry_run(dataset_json)

    # Push when write access is granted
    result = publisher.publish_dataset(dataset_json, dry_run=False)
"""

import base64
import datetime
import json
import time
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import requests
from loguru import logger

# Publisher-specific logger
pub_logger = logger.bind(name="udl.publisher")


# =============================================================================
# CONSTANTS & ENUMS
# =============================================================================

UDL_BASE_URL = "https://unifieddatalibrary.com"

# Default source identifier for this project
DEFAULT_SOURCE = "SDA-TAP-SpOC-UCT-Benchmark"

# Maximum records per createBulk request (conservative limit)
MAX_BULK_BATCH_SIZE = 1000


class DataMode(str, Enum):
    """UDL dataMode values per the OpenAPI spec."""

    REAL = "REAL"
    TEST = "TEST"
    SIMULATED = "SIMULATED"
    EXERCISE = "EXERCISE"


class UDLService(str, Enum):
    """UDL service endpoints for space domain data."""

    EOOBSERVATION = "eoobservation"
    RADAROBSERVATION = "radarobservation"
    RFOBSERVATION = "rfobservation"
    STATEVECTOR = "statevector"
    ELSET = "elset"
    CONJUNCTION = "conjunction"
    MANEUVER = "maneuver"
    SENSORCALIBRATION = "sensorcalibration"


# Tier-to-dataMode mapping per the integration plan
TIER_DATA_MODE_MAP: Dict[str, DataMode] = {
    "T1": DataMode.TEST,       # Real data, downsampled (high quality)
    "T1H": DataMode.TEST,
    "T1S": DataMode.TEST,
    "T2": DataMode.TEST,       # Real data, downsampled (standard quality)
    "T2H": DataMode.TEST,
    "T2S": DataMode.TEST,
    "T3": DataMode.EXERCISE,   # Real + simulated blend
    "T3L": DataMode.EXERCISE,
    "T4": DataMode.SIMULATED,  # Fully synthetic
    "T4L": DataMode.SIMULATED,
    "T5": DataMode.SIMULATED,  # Fully synthetic (edge cases)
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    service: str
    records_submitted: int
    records_accepted: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False
    elapsed_seconds: float = 0.0
    response_status: Optional[int] = None

    def __repr__(self) -> str:
        mode = "DRY-RUN" if self.dry_run else "LIVE"
        status = "OK" if self.success else "FAILED"
        return (
            f"PublishResult({mode} {status}: {self.records_submitted} submitted, "
            f"{self.records_accepted} accepted to {self.service}, "
            f"{len(self.errors)} errors, {self.elapsed_seconds:.2f}s)"
        )


@dataclass
class ValidationResult:
    """Result of payload validation."""

    valid: bool
    record_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        return (
            f"ValidationResult({status}: {self.record_count} records, "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings)"
        )


@dataclass
class DryRunReport:
    """Comprehensive report from a dry-run publish operation."""

    dataset_name: Optional[str]
    tier: Optional[str]
    data_mode: str
    source: str
    observation_validation: Optional[ValidationResult] = None
    state_vector_validation: Optional[ValidationResult] = None
    element_set_validation: Optional[ValidationResult] = None
    sample_payloads: Dict[str, List[Dict]] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "dataset_name": self.dataset_name,
            "tier": self.tier,
            "data_mode": self.data_mode,
            "source": self.source,
            "summary": self.summary,
        }
        if self.observation_validation:
            result["observations"] = {
                "valid": self.observation_validation.valid,
                "count": self.observation_validation.record_count,
                "errors": self.observation_validation.errors,
                "warnings": self.observation_validation.warnings,
            }
        if self.state_vector_validation:
            result["state_vectors"] = {
                "valid": self.state_vector_validation.valid,
                "count": self.state_vector_validation.record_count,
                "errors": self.state_vector_validation.errors,
                "warnings": self.state_vector_validation.warnings,
            }
        if self.element_set_validation:
            result["element_sets"] = {
                "valid": self.element_set_validation.valid,
                "count": self.element_set_validation.record_count,
                "errors": self.element_set_validation.errors,
                "warnings": self.element_set_validation.warnings,
            }
        if self.sample_payloads:
            result["sample_payloads"] = self.sample_payloads
        return result


# =============================================================================
# SCHEMA MAPPING FUNCTIONS
# =============================================================================


def _suppress_warnings() -> None:
    """Suppress SSL verification warnings (matching apiIntegration.py pattern)."""
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def _now_utc() -> str:
    """Current UTC timestamp in UDL format."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _format_datetime(dt: Any) -> Optional[str]:
    """Convert datetime to UDL-compatible ISO 8601 format."""
    if dt is None:
        return None
    if pd.isna(dt):
        return None
    if isinstance(dt, str):
        # Ensure the string ends with Z for UTC
        if dt and not dt.endswith("Z"):
            dt = dt.rstrip() + "Z"
        return dt
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return str(dt)


def map_observation_to_udl(
    obs: Dict[str, Any],
    source: str = DEFAULT_SOURCE,
    data_mode: str = DataMode.TEST,
    classification: str = "U",
) -> Dict[str, Any]:
    """
    Map an internal observation record to UDL eoobservation ingest format.

    The field names are based on the existing GET response schema from UDL
    eoobservation queries (which match the ingest schema per UDL API patterns).

    Args:
        obs: Internal observation dict (from export_dataset_to_json format)
        source: Data source name for UDL
        data_mode: UDL dataMode value
        classification: IC/CAPCO classification marking

    Returns:
        Dict matching UDL eoobservation ingest schema
    """
    udl_record: Dict[str, Any] = {
        # Required fields for all UDL records
        "classificationMarking": classification,
        "source": source,
        "dataMode": data_mode,
    }

    # Map observation time
    ob_time = _format_datetime(obs.get("ob_time"))
    if ob_time:
        udl_record["obTime"] = ob_time

    # Map positional data (electro-optical: RA/Dec)
    if obs.get("ra") is not None:
        udl_record["ra"] = float(obs["ra"])
    if obs.get("declination") is not None:
        udl_record["declination"] = float(obs["declination"])

    # Map satellite identification
    orig_id = obs.get("orig_object_id") or obs.get("sat_no")
    if orig_id is not None:
        udl_record["satNo"] = int(orig_id)

    # Map sensor information
    if obs.get("sensor_name"):
        udl_record["sensorName"] = obs["sensor_name"]

    # Map radar-specific fields
    if obs.get("range_km") is not None:
        udl_record["range"] = float(obs["range_km"])
    if obs.get("range_rate_km_s") is not None:
        udl_record["rangeRate"] = float(obs["range_rate_km_s"])
    if obs.get("azimuth") is not None:
        udl_record["azimuth"] = float(obs["azimuth"])
    if obs.get("elevation") is not None:
        udl_record["elevation"] = float(obs["elevation"])

    # Provenance: note the origin if this is enriched/processed data
    udl_record["origin"] = source

    return udl_record


def map_state_vector_to_udl(
    sv: Dict[str, Any],
    source: str = DEFAULT_SOURCE,
    data_mode: str = DataMode.TEST,
    classification: str = "U",
) -> Dict[str, Any]:
    """
    Map an internal state vector to UDL statevector ingest format.

    Args:
        sv: State vector dict with position_km [x,y,z] and velocity_km_s [x,y,z]
        source: Data source name
        data_mode: UDL dataMode value
        classification: IC/CAPCO classification marking

    Returns:
        Dict matching UDL statevector ingest schema
    """
    udl_record: Dict[str, Any] = {
        "classificationMarking": classification,
        "source": source,
        "dataMode": data_mode,
    }

    # Map epoch
    epoch = _format_datetime(sv.get("epoch"))
    if epoch:
        udl_record["epoch"] = epoch

    # Map satellite number
    if sv.get("sat_no") is not None:
        udl_record["satNo"] = int(sv["sat_no"])

    # Map position (ECI J2000, km)
    pos = sv.get("position_km")
    if pos and len(pos) >= 3:
        udl_record["xPosition"] = float(pos[0])
        udl_record["yPosition"] = float(pos[1])
        udl_record["zPosition"] = float(pos[2])

    # Map velocity (ECI J2000, km/s)
    vel = sv.get("velocity_km_s")
    if vel and len(vel) >= 3:
        udl_record["xVelocity"] = float(vel[0])
        udl_record["yVelocity"] = float(vel[1])
        udl_record["zVelocity"] = float(vel[2])

    # Map covariance if available (6x6 matrix)
    if sv.get("covariance"):
        udl_record["covariance"] = sv["covariance"]

    udl_record["origin"] = source
    return udl_record


def map_element_set_to_udl(
    elset: Dict[str, Any],
    source: str = DEFAULT_SOURCE,
    data_mode: str = DataMode.TEST,
    classification: str = "U",
) -> Dict[str, Any]:
    """
    Map an internal element set (TLE) to UDL elset ingest format.

    Args:
        elset: Element set dict with line1, line2, epoch
        source: Data source name
        data_mode: UDL dataMode value
        classification: IC/CAPCO classification marking

    Returns:
        Dict matching UDL elset ingest schema
    """
    udl_record: Dict[str, Any] = {
        "classificationMarking": classification,
        "source": source,
        "dataMode": data_mode,
    }

    # Map epoch
    epoch = _format_datetime(elset.get("epoch"))
    if epoch:
        udl_record["epoch"] = epoch

    # Map satellite number
    if elset.get("sat_no") is not None:
        udl_record["satNo"] = int(elset["sat_no"])

    # Map TLE lines
    if elset.get("line1"):
        udl_record["line1"] = str(elset["line1"])
    if elset.get("line2"):
        udl_record["line2"] = str(elset["line2"])

    udl_record["origin"] = source
    return udl_record


# =============================================================================
# VALIDATION
# =============================================================================


def validate_udl_record(record: Dict[str, Any], service: str) -> List[str]:
    """
    Validate a single UDL record has all required fields.

    Args:
        record: UDL-formatted record dict
        service: Target UDL service name

    Returns:
        List of error strings (empty if valid)
    """
    errors = []

    # Required fields for ALL UDL records
    required_fields = ["classificationMarking", "source", "dataMode"]
    for f in required_fields:
        if f not in record or record[f] is None:
            errors.append(f"Missing required field: {f}")

    # Validate classificationMarking format
    cm = record.get("classificationMarking", "")
    if cm and cm not in ("U", "C", "S", "TS", "U//FOUO"):
        # IC/CAPCO allows many formats; just warn on unusual values
        pass

    # Validate dataMode enum
    dm = record.get("dataMode", "")
    valid_modes = {m.value for m in DataMode}
    if dm and dm not in valid_modes:
        errors.append(
            f"Invalid dataMode: '{dm}'. Must be one of: {', '.join(valid_modes)}"
        )

    # Service-specific validation
    if service == UDLService.EOOBSERVATION:
        if "obTime" not in record:
            errors.append("eoobservation requires 'obTime' field")

    elif service == UDLService.STATEVECTOR:
        if "epoch" not in record:
            errors.append("statevector requires 'epoch' field")

    elif service == UDLService.ELSET:
        if "epoch" not in record:
            errors.append("elset requires 'epoch' field")

    return errors


def validate_payload(
    records: List[Dict[str, Any]], service: str
) -> ValidationResult:
    """
    Validate a batch of UDL records.

    Args:
        records: List of UDL-formatted record dicts
        service: Target UDL service name

    Returns:
        ValidationResult with overall status and per-record errors
    """
    all_errors = []
    all_warnings = []

    if not records:
        return ValidationResult(
            valid=False, record_count=0, errors=["No records to validate"]
        )

    for i, record in enumerate(records):
        record_errors = validate_udl_record(record, service)
        for err in record_errors:
            all_errors.append(f"Record {i}: {err}")

    # Check for potential issues (warnings, not errors)
    sources = set(r.get("source", "") for r in records)
    if len(sources) > 1:
        all_warnings.append(
            f"Multiple source values in batch: {sources}. "
            "Consider using a consistent source identifier."
        )

    modes = set(r.get("dataMode", "") for r in records)
    if len(modes) > 1:
        all_warnings.append(
            f"Multiple dataMode values in batch: {modes}. "
            "Verify this is intentional (e.g., mixed real+simulated dataset)."
        )

    return ValidationResult(
        valid=len(all_errors) == 0,
        record_count=len(records),
        errors=all_errors,
        warnings=all_warnings,
    )


# =============================================================================
# UDL PUBLISHER CLASS
# =============================================================================


class UDLPublisher:
    """
    Publishes UCT Benchmark data to the UDL REST API.

    Supports pushing observations, state vectors, and element sets via
    the /udl/{service}/createBulk endpoint (for initial integration)
    or /filedrop/udl-{service} endpoint (for automated feeds, requires
    specific role from UDL team).

    Default mode is dry_run=True, which validates payloads and logs
    what would be pushed without making actual API calls.

    Args:
        token: Base64-encoded UDL auth token (from UDLTokenGen)
        source: Data source identifier registered with UDL
        classification: Default classification marking (IC/CAPCO format)
        base_url: UDL API base URL
        dry_run: If True (default), validate only without pushing
        rate_limit_sec: Minimum delay between API requests
        max_retries: Maximum retry attempts on transient failures
        retry_backoff_factor: Exponential backoff multiplier
        batch_size: Maximum records per createBulk request
    """

    def __init__(
        self,
        token: Optional[str] = None,
        source: str = DEFAULT_SOURCE,
        classification: str = "U",
        base_url: str = UDL_BASE_URL,
        dry_run: bool = True,
        rate_limit_sec: float = 0.1,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        batch_size: int = MAX_BULK_BATCH_SIZE,
    ):
        self.token = token
        self.source = source
        self.classification = classification
        self.base_url = base_url.rstrip("/")
        self._dry_run = dry_run
        self.rate_limit_sec = rate_limit_sec
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.batch_size = batch_size

        # Track publish operations
        self._publish_history: List[PublishResult] = []

        if not dry_run and not token:
            raise ValueError(
                "A valid UDL auth token is required for live publishing. "
                "Use UDLTokenGen(username, password) to generate one, "
                "or set dry_run=True for validation-only mode."
            )

    @property
    def is_dry_run(self) -> bool:
        return self._dry_run

    @property
    def publish_history(self) -> List[PublishResult]:
        return list(self._publish_history)

    # -------------------------------------------------------------------------
    # CORE POST METHODS
    # -------------------------------------------------------------------------

    def _post_bulk(
        self, service: str, records: List[Dict[str, Any]]
    ) -> PublishResult:
        """
        POST records to /udl/{service}/createBulk endpoint.

        This is the primary ingestion endpoint for initial integration.
        For automated feeds, use _post_filedrop() (requires special role).

        Args:
            service: UDL service name
            records: List of UDL-formatted records

        Returns:
            PublishResult with operation outcome
        """
        _suppress_warnings()
        url = f"{self.base_url}/udl/{service}/createBulk"
        headers = {
            "Authorization": f"Basic {self.token}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        errors: List[str] = []
        accepted = 0
        status_code = None

        try:
            for attempt in range(self.max_retries):
                try:
                    resp = requests.post(
                        url,
                        headers=headers,
                        json=records,
                        verify=False,
                        timeout=120,
                    )
                    status_code = resp.status_code
                    elapsed = time.perf_counter() - start_time

                    if resp.status_code == 204:
                        # Success - 204 No Content is expected for createBulk
                        accepted = len(records)
                        pub_logger.info(
                            f"Published {accepted} records to {service}/createBulk "
                            f"in {elapsed:.2f}s"
                        )
                        break

                    elif resp.status_code == 202:
                        # Accepted - async processing (filedrop pattern)
                        accepted = len(records)
                        pub_logger.info(
                            f"Submitted {accepted} records to {service}/createBulk "
                            f"(async, 202 Accepted) in {elapsed:.2f}s"
                        )
                        break

                    elif resp.status_code == 429:
                        # Rate limited - back off and retry
                        wait = self.retry_backoff_factor ** attempt
                        pub_logger.warning(
                            f"Rate limited (429) on {service}/createBulk, "
                            f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait)
                        continue

                    elif resp.status_code == 500 and attempt < self.max_retries - 1:
                        # Server error - retry with backoff
                        wait = self.retry_backoff_factor ** attempt
                        pub_logger.warning(
                            f"Server error (500) on {service}/createBulk, "
                            f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait)
                        continue

                    else:
                        # Non-retryable error
                        error_body = ""
                        try:
                            error_body = resp.text[:500]
                        except Exception:
                            pass
                        error_msg = {
                            400: "Bad request - check payload schema",
                            401: "Unauthorized - invalid or missing credentials",
                            403: "Forbidden - user not authorized for write access",
                            415: "Unsupported media type - check Content-Type header",
                        }.get(
                            resp.status_code,
                            f"HTTP {resp.status_code}: {error_body}",
                        )
                        errors.append(error_msg)
                        pub_logger.error(
                            f"Failed to publish to {service}/createBulk: {error_msg}"
                        )
                        break

                except requests.exceptions.Timeout:
                    if attempt < self.max_retries - 1:
                        wait = self.retry_backoff_factor ** attempt
                        pub_logger.warning(
                            f"Timeout on {service}/createBulk, "
                            f"retrying in {wait:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait)
                        continue
                    errors.append("Request timed out after all retries")

                except requests.exceptions.ConnectionError as e:
                    if attempt < self.max_retries - 1:
                        wait = self.retry_backoff_factor ** attempt
                        pub_logger.warning(
                            f"Connection error on {service}/createBulk, "
                            f"retrying in {wait:.1f}s"
                        )
                        time.sleep(wait)
                        continue
                    errors.append(f"Connection error: {e}")

        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            pub_logger.error(f"Unexpected error publishing to {service}: {e}")

        elapsed = time.perf_counter() - start_time
        result = PublishResult(
            success=accepted > 0 and len(errors) == 0,
            service=service,
            records_submitted=len(records),
            records_accepted=accepted,
            errors=errors,
            dry_run=False,
            elapsed_seconds=elapsed,
            response_status=status_code,
        )
        self._publish_history.append(result)
        return result

    def _post_filedrop(
        self, service: str, records: List[Dict[str, Any]]
    ) -> PublishResult:
        """
        POST records to /filedrop/udl-{service} endpoint.

        This endpoint is for automated data feeds and requires a specific
        role from the UDL team. Use _post_bulk() for initial integration.

        Args:
            service: UDL service name
            records: List of UDL-formatted records

        Returns:
            PublishResult with operation outcome
        """
        _suppress_warnings()
        url = f"{self.base_url}/filedrop/udl-{service}"
        headers = {
            "Authorization": f"Basic {self.token}",
            "Content-Type": "application/json",
        }

        start_time = time.perf_counter()
        errors: List[str] = []
        accepted = 0
        status_code = None

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=records,
                verify=False,
                timeout=120,
            )
            status_code = resp.status_code
            elapsed = time.perf_counter() - start_time

            if resp.status_code == 202:
                accepted = len(records)
                pub_logger.info(
                    f"Submitted {accepted} records to filedrop/udl-{service} "
                    f"(202 Accepted) in {elapsed:.2f}s"
                )
            else:
                error_body = ""
                try:
                    error_body = resp.text[:500]
                except Exception:
                    pass
                errors.append(
                    f"Filedrop returned HTTP {resp.status_code}: {error_body}"
                )

        except Exception as e:
            errors.append(f"Filedrop error: {e}")

        elapsed = time.perf_counter() - start_time
        result = PublishResult(
            success=accepted > 0 and len(errors) == 0,
            service=f"filedrop/udl-{service}",
            records_submitted=len(records),
            records_accepted=accepted,
            errors=errors,
            dry_run=False,
            elapsed_seconds=elapsed,
            response_status=status_code,
        )
        self._publish_history.append(result)
        return result

    # -------------------------------------------------------------------------
    # PUBLIC PUBLISH METHODS
    # -------------------------------------------------------------------------

    def publish_observations(
        self,
        observations: List[Dict[str, Any]],
        data_mode: Optional[str] = None,
        dry_run: Optional[bool] = None,
        use_filedrop: bool = False,
    ) -> PublishResult:
        """
        Publish observation records to UDL eoobservation service.

        Maps internal observation format to UDL schema, validates,
        and POSTs in batches.

        Args:
            observations: List of observation dicts (internal format)
            data_mode: Override dataMode (defaults to TEST)
            dry_run: Override instance dry_run setting
            use_filedrop: Use /filedrop/ endpoint instead of /createBulk

        Returns:
            PublishResult with operation outcome
        """
        is_dry = dry_run if dry_run is not None else self._dry_run
        mode = data_mode or DataMode.TEST
        service = UDLService.EOOBSERVATION

        # Map observations to UDL format
        udl_records = [
            map_observation_to_udl(obs, self.source, mode, self.classification)
            for obs in observations
        ]

        # Validate
        validation = validate_payload(udl_records, service)
        if not validation.valid:
            pub_logger.error(
                f"Observation validation failed: {validation.errors}"
            )
            return PublishResult(
                success=False,
                service=service,
                records_submitted=len(udl_records),
                errors=validation.errors,
                dry_run=is_dry,
            )

        if validation.warnings:
            for w in validation.warnings:
                pub_logger.warning(f"Validation warning: {w}")

        if is_dry:
            pub_logger.info(
                f"DRY-RUN: Would publish {len(udl_records)} observations "
                f"to {service} (dataMode={mode})"
            )
            result = PublishResult(
                success=True,
                service=service,
                records_submitted=len(udl_records),
                records_accepted=len(udl_records),
                dry_run=True,
            )
            self._publish_history.append(result)
            return result

        # Live publish in batches
        return self._publish_in_batches(
            service, udl_records, use_filedrop
        )

    def publish_state_vectors(
        self,
        state_vectors: List[Dict[str, Any]],
        data_mode: Optional[str] = None,
        dry_run: Optional[bool] = None,
        use_filedrop: bool = False,
    ) -> PublishResult:
        """
        Publish state vector records to UDL statevector service.

        Args:
            state_vectors: List of state vector dicts with position_km/velocity_km_s
            data_mode: Override dataMode
            dry_run: Override instance dry_run setting
            use_filedrop: Use /filedrop/ endpoint instead of /createBulk

        Returns:
            PublishResult with operation outcome
        """
        is_dry = dry_run if dry_run is not None else self._dry_run
        mode = data_mode or DataMode.TEST
        service = UDLService.STATEVECTOR

        udl_records = [
            map_state_vector_to_udl(sv, self.source, mode, self.classification)
            for sv in state_vectors
        ]

        validation = validate_payload(udl_records, service)
        if not validation.valid:
            pub_logger.error(
                f"State vector validation failed: {validation.errors}"
            )
            return PublishResult(
                success=False,
                service=service,
                records_submitted=len(udl_records),
                errors=validation.errors,
                dry_run=is_dry,
            )

        if is_dry:
            pub_logger.info(
                f"DRY-RUN: Would publish {len(udl_records)} state vectors "
                f"to {service} (dataMode={mode})"
            )
            result = PublishResult(
                success=True,
                service=service,
                records_submitted=len(udl_records),
                records_accepted=len(udl_records),
                dry_run=True,
            )
            self._publish_history.append(result)
            return result

        return self._publish_in_batches(
            service, udl_records, use_filedrop
        )

    def publish_element_sets(
        self,
        element_sets: List[Dict[str, Any]],
        data_mode: Optional[str] = None,
        dry_run: Optional[bool] = None,
        use_filedrop: bool = False,
    ) -> PublishResult:
        """
        Publish element set (TLE) records to UDL elset service.

        Args:
            element_sets: List of element set dicts with line1, line2, epoch
            data_mode: Override dataMode
            dry_run: Override instance dry_run setting
            use_filedrop: Use /filedrop/ endpoint instead of /createBulk

        Returns:
            PublishResult with operation outcome
        """
        is_dry = dry_run if dry_run is not None else self._dry_run
        mode = data_mode or DataMode.TEST
        service = UDLService.ELSET

        udl_records = [
            map_element_set_to_udl(es, self.source, mode, self.classification)
            for es in element_sets
        ]

        validation = validate_payload(udl_records, service)
        if not validation.valid:
            pub_logger.error(
                f"Element set validation failed: {validation.errors}"
            )
            return PublishResult(
                success=False,
                service=service,
                records_submitted=len(udl_records),
                errors=validation.errors,
                dry_run=is_dry,
            )

        if is_dry:
            pub_logger.info(
                f"DRY-RUN: Would publish {len(udl_records)} element sets "
                f"to {service} (dataMode={mode})"
            )
            result = PublishResult(
                success=True,
                service=service,
                records_submitted=len(udl_records),
                records_accepted=len(udl_records),
                dry_run=True,
            )
            self._publish_history.append(result)
            return result

        return self._publish_in_batches(
            service, udl_records, use_filedrop
        )

    def publish_dataset(
        self,
        dataset_json: Union[str, Path, Dict[str, Any]],
        dry_run: Optional[bool] = None,
        use_filedrop: bool = False,
    ) -> Dict[str, PublishResult]:
        """
        Publish an entire benchmark dataset to UDL.

        Reads the dataset JSON (matching export_dataset_to_json format),
        determines the appropriate dataMode from the tier, and publishes
        observations, state vectors, and element sets to their respective
        UDL services.

        Args:
            dataset_json: Path to dataset JSON file, or pre-loaded dict
            dry_run: Override instance dry_run setting
            use_filedrop: Use /filedrop/ endpoints instead of /createBulk

        Returns:
            Dict mapping service name to PublishResult
        """
        # Load dataset
        if isinstance(dataset_json, (str, Path)):
            path = Path(dataset_json)
            if not path.exists():
                raise FileNotFoundError(f"Dataset file not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            dataset = dataset_json

        metadata = dataset.get("metadata", {})
        tier = metadata.get("tier", "T2")
        dataset_name = metadata.get("name", "unknown")
        data_mode = TIER_DATA_MODE_MAP.get(tier, DataMode.TEST).value

        pub_logger.info(
            f"Publishing dataset '{dataset_name}' (tier={tier}, dataMode={data_mode})"
        )

        results: Dict[str, PublishResult] = {}

        # Publish observations
        observations = dataset.get("observations", [])
        if observations:
            results["observations"] = self.publish_observations(
                observations, data_mode=data_mode, dry_run=dry_run,
                use_filedrop=use_filedrop,
            )

        # Publish reference data (state vectors and element sets)
        references = dataset.get("references", [])
        state_vectors = []
        element_sets = []

        for ref in references:
            sat_no = ref.get("sat_no")

            sv_data = ref.get("state_vector")
            if sv_data:
                sv_data["sat_no"] = sat_no
                state_vectors.append(sv_data)

            tle_data = ref.get("tle")
            if tle_data:
                tle_data["sat_no"] = sat_no
                element_sets.append(tle_data)

        if state_vectors:
            results["state_vectors"] = self.publish_state_vectors(
                state_vectors, data_mode=data_mode, dry_run=dry_run,
                use_filedrop=use_filedrop,
            )

        if element_sets:
            results["element_sets"] = self.publish_element_sets(
                element_sets, data_mode=data_mode, dry_run=dry_run,
                use_filedrop=use_filedrop,
            )

        # Log summary
        total_submitted = sum(r.records_submitted for r in results.values())
        total_accepted = sum(r.records_accepted for r in results.values())
        all_success = all(r.success for r in results.values())
        mode_label = "DRY-RUN" if (dry_run if dry_run is not None else self._dry_run) else "LIVE"

        pub_logger.info(
            f"{mode_label} publish of '{dataset_name}': "
            f"{total_submitted} submitted, {total_accepted} accepted, "
            f"{'ALL OK' if all_success else 'ERRORS OCCURRED'}"
        )

        return results

    def dry_run(
        self,
        dataset_json: Union[str, Path, Dict[str, Any]],
        sample_count: int = 3,
    ) -> DryRunReport:
        """
        Perform a comprehensive dry-run validation of a dataset.

        Validates all records, generates sample payloads, and produces
        a detailed report suitable for mentor review.

        Args:
            dataset_json: Path to dataset JSON file, or pre-loaded dict
            sample_count: Number of sample payloads to include per service

        Returns:
            DryRunReport with validation results and sample payloads
        """
        # Load dataset
        if isinstance(dataset_json, (str, Path)):
            path = Path(dataset_json)
            if not path.exists():
                raise FileNotFoundError(f"Dataset file not found: {path}")
            with open(path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            dataset = dataset_json

        metadata = dataset.get("metadata", {})
        tier = metadata.get("tier", "T2")
        dataset_name = metadata.get("name")
        data_mode = TIER_DATA_MODE_MAP.get(tier, DataMode.TEST).value

        report = DryRunReport(
            dataset_name=dataset_name,
            tier=tier,
            data_mode=data_mode,
            source=self.source,
        )

        # Validate observations
        observations = dataset.get("observations", [])
        if observations:
            udl_obs = [
                map_observation_to_udl(
                    obs, self.source, data_mode, self.classification
                )
                for obs in observations
            ]
            report.observation_validation = validate_payload(
                udl_obs, UDLService.EOOBSERVATION
            )
            report.sample_payloads["eoobservation"] = udl_obs[:sample_count]

        # Validate state vectors and element sets from references
        references = dataset.get("references", [])
        sv_records = []
        elset_records = []

        for ref in references:
            sat_no = ref.get("sat_no")

            sv_data = ref.get("state_vector")
            if sv_data:
                sv_data_copy = dict(sv_data)
                sv_data_copy["sat_no"] = sat_no
                udl_sv = map_state_vector_to_udl(
                    sv_data_copy, self.source, data_mode, self.classification
                )
                sv_records.append(udl_sv)

            tle_data = ref.get("tle")
            if tle_data:
                tle_data_copy = dict(tle_data)
                tle_data_copy["sat_no"] = sat_no
                udl_elset = map_element_set_to_udl(
                    tle_data_copy, self.source, data_mode, self.classification
                )
                elset_records.append(udl_elset)

        if sv_records:
            report.state_vector_validation = validate_payload(
                sv_records, UDLService.STATEVECTOR
            )
            report.sample_payloads["statevector"] = sv_records[:sample_count]

        if elset_records:
            report.element_set_validation = validate_payload(
                elset_records, UDLService.ELSET
            )
            report.sample_payloads["elset"] = elset_records[:sample_count]

        # Build summary
        parts = []
        parts.append(
            f"Dataset: {dataset_name} | Tier: {tier} | "
            f"dataMode: {data_mode} | source: {self.source}"
        )

        if report.observation_validation:
            v = report.observation_validation
            status = "PASS" if v.valid else "FAIL"
            parts.append(
                f"  Observations: {v.record_count} records - {status}"
            )
            for e in v.errors[:5]:
                parts.append(f"    ERROR: {e}")
            for w in v.warnings[:5]:
                parts.append(f"    WARNING: {w}")

        if report.state_vector_validation:
            v = report.state_vector_validation
            status = "PASS" if v.valid else "FAIL"
            parts.append(
                f"  State Vectors: {v.record_count} records - {status}"
            )
            for e in v.errors[:5]:
                parts.append(f"    ERROR: {e}")

        if report.element_set_validation:
            v = report.element_set_validation
            status = "PASS" if v.valid else "FAIL"
            parts.append(
                f"  Element Sets: {v.record_count} records - {status}"
            )
            for e in v.errors[:5]:
                parts.append(f"    ERROR: {e}")

        report.summary = "\n".join(parts)
        pub_logger.info(f"Dry-run validation complete:\n{report.summary}")

        return report

    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------

    def _publish_in_batches(
        self,
        service: str,
        records: List[Dict[str, Any]],
        use_filedrop: bool = False,
    ) -> PublishResult:
        """
        Publish records in batches with rate limiting.

        Args:
            service: UDL service name
            records: List of UDL-formatted records
            use_filedrop: Use filedrop endpoint

        Returns:
            Aggregated PublishResult
        """
        total_submitted = 0
        total_accepted = 0
        all_errors: List[str] = []
        start_time = time.perf_counter()

        # Split into batches
        for i in range(0, len(records), self.batch_size):
            batch = records[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(records) + self.batch_size - 1) // self.batch_size

            pub_logger.debug(
                f"Publishing batch {batch_num}/{total_batches} "
                f"({len(batch)} records) to {service}"
            )

            if use_filedrop:
                result = self._post_filedrop(service, batch)
            else:
                result = self._post_bulk(service, batch)

            total_submitted += result.records_submitted
            total_accepted += result.records_accepted
            all_errors.extend(result.errors)

            # Don't continue if a batch failed
            if not result.success:
                pub_logger.error(
                    f"Batch {batch_num} failed, stopping publish to {service}"
                )
                break

            # Rate limit between batches
            if i + self.batch_size < len(records):
                time.sleep(self.rate_limit_sec)

        elapsed = time.perf_counter() - start_time
        return PublishResult(
            success=total_accepted > 0 and len(all_errors) == 0,
            service=service,
            records_submitted=total_submitted,
            records_accepted=total_accepted,
            errors=all_errors,
            dry_run=False,
            elapsed_seconds=elapsed,
        )

    def get_publish_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all publish operations in this session.

        Returns:
            Dict with publish statistics
        """
        if not self._publish_history:
            return {"total_operations": 0}

        return {
            "total_operations": len(self._publish_history),
            "total_submitted": sum(
                r.records_submitted for r in self._publish_history
            ),
            "total_accepted": sum(
                r.records_accepted for r in self._publish_history
            ),
            "total_errors": sum(
                len(r.errors) for r in self._publish_history
            ),
            "dry_run_count": sum(
                1 for r in self._publish_history if r.dry_run
            ),
            "live_count": sum(
                1 for r in self._publish_history if not r.dry_run
            ),
            "operations": [
                {
                    "service": r.service,
                    "submitted": r.records_submitted,
                    "accepted": r.records_accepted,
                    "success": r.success,
                    "dry_run": r.dry_run,
                    "errors": r.errors,
                }
                for r in self._publish_history
            ],
        }
