"""
Field name normalization for UCTP submissions.

Different UCT processors may use different naming conventions for the same fields.
For example: 'xvel' vs 'vx' vs 'VX' vs 'x_vel' for x-velocity.

This module provides a canonical name mapping so the evaluation pipeline
can accept any of these aliases without crashing.

Per Feb 19, 2026 mentor meeting:
  "Different field names (VX vs XVEL) currently cause errors.
   Future: add flexible field name mapping."
"""

from typing import Any, Dict, List, Optional

import pandas as pd

# Canonical field names -> accepted aliases (case-insensitive matching applied separately)
FIELD_ALIASES: Dict[str, List[str]] = {
    # Position fields (km, J2000 ECI)
    "xpos": ["xpos", "x_pos", "X", "x", "pos_x", "position_x"],
    "ypos": ["ypos", "y_pos", "Y", "y", "pos_y", "position_y"],
    "zpos": ["zpos", "z_pos", "Z", "z", "pos_z", "position_z"],
    # Velocity fields (km/s, J2000 ECI)
    "xvel": ["xvel", "x_vel", "vx", "VX", "Vx", "vel_x", "velocity_x", "xdot", "x_dot"],
    "yvel": ["yvel", "y_vel", "vy", "VY", "Vy", "vel_y", "velocity_y", "ydot", "y_dot"],
    "zvel": ["zvel", "z_vel", "vz", "VZ", "Vz", "vel_z", "velocity_z", "zdot", "z_dot"],
    # Observation fields
    "grouped_ops": ["grouped_ops", "sourcedData", "sourced_data", "grouped_observations",
                     "obs_ids", "observation_ids"],
    "source_data_types": ["source_data_types", "sourcedDataTypes", "sourced_data_types",
                          "data_types", "obs_types"],
    # Epoch
    "epoch": ["epoch", "Epoch", "time", "datetime", "timestamp"],
    # Satellite number
    "satNo": ["satNo", "sat_no", "norad_id", "NORAD_ID", "noradId", "satellite_number",
              "sat_num", "catalog_number"],
    # Covariance
    "cov": ["cov", "covariance", "cov_matrix", "covarianceMatrix"],
    # Classification marking
    "classificationMarking": ["classificationMarking", "classification_marking",
                              "classification", "class_marking"],
    # Reference frame
    "referenceFrame": ["referenceFrame", "reference_frame", "ref_frame", "frame"],
    # Observation metadata fields
    "obTime": ["obTime", "ob_time", "obs_time", "observation_time"],
    "idOnOrbit": ["idOnOrbit", "id_on_orbit"],
    "idSensor": ["idSensor", "id_sensor", "sensor_id"],
    "taskId": ["taskId", "task_id"],
    "origObjectId": ["origObjectId", "orig_object_id"],
    "origSensorId": ["origSensorId", "orig_sensor_id"],
    "senlat": ["senlat", "send_lat", "senderLatitude", "sensor_lat"],
    "senlon": ["senlon", "send_long", "senderLongitude", "sensor_lon"],
    "senalt": ["senalt", "send_alt", "senderAltitude", "sensor_alt"],
    "senx": ["senx", "sen_x"],
    "seny": ["seny", "sen_y"],
    "senz": ["senz", "sen_z"],
    "senvelx": ["senvelx", "sen_vel_x"],
    "senvely": ["senvely", "sen_vel_y"],
    "senvelz": ["senvelz", "sen_vel_z"],
    "expDuration": ["expDuration", "exp_duration", "exposure_duration"],
    "zeroptd": ["zeroptd"],
    "netObjSig": ["netObjSig", "net_obj_sig"],
    "netObjSigUnc": ["netObjSigUnc", "net_obj_sig_unc"],
    "mag": ["mag", "magnitude"],
    "magUnc": ["magUnc", "mag_unc", "magnitude_uncertainty"],
    "geolat": ["geolat", "geo_lat"],
    "geolon": ["geolon", "geo_lon"],
    "geoalt": ["geoalt", "geo_alt"],
    "georange": ["georange", "geo_range"],
    "solarPhaseAngle": ["solarPhaseAngle", "solar_phase_angle"],
    "solarEqPhaseAngle": ["solarEqPhaseAngle", "solar_eq_phase_angle"],
    "solarDecAngle": ["solarDecAngle", "solar_dec_angle"],
    "shutterDelay": ["shutterDelay", "shutter_delay"],
    "rawFileURI": ["rawFileURI", "raw_file_uri"],
    "losUnc": ["losUnc", "los_unc"],
    "createdBy": ["createdBy", "created_by"],
    "origNetwork": ["origNetwork", "orig_network"],
    "dataMode": ["dataMode", "data_mode"],
    "source": ["source"],
    "type": ["type", "obs_type", "observation_type"],
}

# Build reverse lookup: alias -> canonical name (case-insensitive)
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in FIELD_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias.lower()] = canonical


def get_canonical_name(field_name: str) -> str:
    """
    Map a field name to its canonical form.

    Args:
        field_name: The field name from a UCTP submission

    Returns:
        The canonical field name, or the original name if no mapping exists
    """
    return _ALIAS_TO_CANONICAL.get(field_name.lower(), field_name)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename DataFrame columns to their canonical forms.

    Only renames columns that have a known mapping; unknown columns pass through unchanged.

    Args:
        df: DataFrame with potentially non-canonical column names

    Returns:
        DataFrame with canonical column names
    """
    rename_map = {}
    for col in df.columns:
        canonical = get_canonical_name(col)
        if canonical != col:
            rename_map[col] = canonical
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize field names in a single dictionary record.

    Args:
        record: A dictionary (e.g., one entry from a UCTP JSON submission)

    Returns:
        New dictionary with canonical field names
    """
    return {get_canonical_name(k): v for k, v in record.items()}


def normalize_submission(submission_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize field names across an entire UCTP submission (list of records).

    Args:
        submission_data: List of dictionaries from a UCTP JSON output

    Returns:
        List of dictionaries with canonical field names
    """
    return [normalize_record(record) for record in submission_data]


def validate_required_fields(
    record: Dict[str, Any],
    required: Optional[List[str]] = None,
) -> List[str]:
    """
    Check if a record has all required fields (after normalization).

    Args:
        record: A normalized record dictionary
        required: List of canonical field names required. Defaults to core UCTP output fields.

    Returns:
        List of missing field names (empty if all present)
    """
    if required is None:
        required = ["grouped_ops", "epoch", "xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
    return [f for f in required if f not in record]
