"""
Mock data constants for SpOC demo mode.

All data uses realistic satellite names, NORAD IDs, and plausible metrics
to demonstrate the full platform capabilities without requiring real API keys.
"""

from datetime import datetime, timedelta, timezone
import math
import random

# ============================================================
# MOCK SATELLITES
# ============================================================

MOCK_SATELLITES: list[dict] = [
    # LEO
    {"sat_no": 25544, "name": "ISS (ZARYA)", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    {"sat_no": 22314, "name": "SPOT 3", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    {"sat_no": 43873, "name": "STARLINK-1007", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    {"sat_no": 39504, "name": "YAOGAN-20A", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    {"sat_no": 27944, "name": "COSMOS 2251 DEB", "orbital_regime": "LEO", "object_type": "DEBRIS"},
    {"sat_no": 39070, "name": "COSMOS 2251 DEB", "orbital_regime": "LEO", "object_type": "DEBRIS"},
    {"sat_no": 46826, "name": "STARLINK-2305", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    {"sat_no": 48859, "name": "ONEWEB-0350", "orbital_regime": "LEO", "object_type": "PAYLOAD"},
    # MEO
    {"sat_no": 20026, "name": "NAVSTAR 22 (USA 66)", "orbital_regime": "MEO", "object_type": "PAYLOAD"},
    {"sat_no": 22824, "name": "NAVSTAR 29 (USA 91)", "orbital_regime": "MEO", "object_type": "PAYLOAD"},
    {"sat_no": 43476, "name": "BEIDOU-3 M13", "orbital_regime": "MEO", "object_type": "PAYLOAD"},
    {"sat_no": 43477, "name": "BEIDOU-3 M14", "orbital_regime": "MEO", "object_type": "PAYLOAD"},
    # GEO
    {"sat_no": 36508, "name": "SDO (SOLAR DYNAMICS OBSERVATORY)", "orbital_regime": "GEO", "object_type": "PAYLOAD"},
    {"sat_no": 26360, "name": "GOES 11", "orbital_regime": "GEO", "object_type": "PAYLOAD"},
    {"sat_no": 27566, "name": "ASTRA 1KR", "orbital_regime": "GEO", "object_type": "PAYLOAD"},
    {"sat_no": 28358, "name": "INTELSAT 10-02", "orbital_regime": "GEO", "object_type": "PAYLOAD"},
]

# Satellite lookup by regime
SATS_BY_REGIME: dict[str, list[int]] = {}
for _s in MOCK_SATELLITES:
    SATS_BY_REGIME.setdefault(_s["orbital_regime"], []).append(_s["sat_no"])


# ============================================================
# MOCK DATASETS
# ============================================================

_NOW = datetime.now(timezone.utc)

MOCK_DATASETS: list[dict] = [
    {
        "name": "LEO-Calibration-T1-Optical",
        "orbital_regime": "LEO",
        "tier": "T1",
        "observation_count": 2450,
        "satellite_count": 10,
        "avg_coverage": 0.85,
        "status": "available",
        "created_at": _NOW - timedelta(days=28),
    },
    {
        "name": "LEO-Standard-T2-Downsampled",
        "orbital_regime": "LEO",
        "tier": "T2",
        "observation_count": 1820,
        "satellite_count": 10,
        "avg_coverage": 0.42,
        "status": "available",
        "created_at": _NOW - timedelta(days=25),
    },
    {
        "name": "MEO-Navigation-T1-Radar",
        "orbital_regime": "MEO",
        "tier": "T1",
        "observation_count": 980,
        "satellite_count": 8,
        "avg_coverage": 0.78,
        "status": "available",
        "created_at": _NOW - timedelta(days=21),
    },
    {
        "name": "GEO-Comms-T2-Optical",
        "orbital_regime": "GEO",
        "tier": "T2",
        "observation_count": 640,
        "satellite_count": 5,
        "avg_coverage": 0.55,
        "status": "available",
        "created_at": _NOW - timedelta(days=17),
    },
    {
        "name": "LEO-Mixed-T3-Fusion",
        "orbital_regime": "LEO",
        "tier": "T3",
        "observation_count": 3100,
        "satellite_count": 15,
        "avg_coverage": 0.30,
        "status": "available",
        "created_at": _NOW - timedelta(days=14),
    },
    {
        "name": "GEO-HAMR-T2-Optical",
        "orbital_regime": "GEO",
        "tier": "T2",
        "observation_count": 420,
        "satellite_count": 6,
        "avg_coverage": 0.48,
        "status": "available",
        "created_at": _NOW - timedelta(days=10),
    },
    {
        "name": "MEO-Standard-T2-Radar",
        "orbital_regime": "MEO",
        "tier": "T2",
        "observation_count": 1250,
        "satellite_count": 10,
        "avg_coverage": 0.60,
        "status": "available",
        "created_at": _NOW - timedelta(days=6),
    },
    {
        "name": "LEO-Maneuver-T2-Optical",
        "orbital_regime": "LEO",
        "tier": "T2",
        "observation_count": 1650,
        "satellite_count": 8,
        "avg_coverage": 0.38,
        "status": "available",
        "created_at": _NOW - timedelta(days=2),
    },
]


# ============================================================
# MOCK SUBMISSIONS
# ============================================================

MOCK_SUBMISSIONS: list[dict] = [
    {
        "dataset_idx": 0,
        "algorithm_name": "OrbitGuard ML",
        "version": "2.1",
        "classification_marking": "SpaceML Lab",
        "f1": 0.942, "precision": 0.955, "recall": 0.929,
        "position_rms_km": 1.24, "velocity_rms_km_s": 0.082,
    },
    {
        "dataset_idx": 0,
        "algorithm_name": "TrackForge",
        "version": "1.0",
        "classification_marking": "DARPA UCT Team",
        "f1": 0.881, "precision": 0.897, "recall": 0.866,
        "position_rms_km": 2.87, "velocity_rms_km_s": 0.195,
    },
    {
        "dataset_idx": 1,
        "algorithm_name": "OrbitGuard ML",
        "version": "2.1",
        "classification_marking": "SpaceML Lab",
        "f1": 0.872, "precision": 0.889, "recall": 0.855,
        "position_rms_km": 3.15, "velocity_rms_km_s": 0.210,
    },
    {
        "dataset_idx": 2,
        "algorithm_name": "AstroIOD",
        "version": "3.2",
        "classification_marking": "NavLab",
        "f1": 0.786, "precision": 0.810, "recall": 0.764,
        "position_rms_km": 5.42, "velocity_rms_km_s": 0.350,
    },
    {
        "dataset_idx": 3,
        "algorithm_name": "DeepOrbit",
        "version": "1.5",
        "classification_marking": "StarNet AI",
        "f1": 0.725, "precision": 0.748, "recall": 0.703,
        "position_rms_km": 8.71, "velocity_rms_km_s": 0.570,
    },
    {
        "dataset_idx": 4,
        "algorithm_name": "OrbitGuard ML",
        "version": "2.1",
        "classification_marking": "SpaceML Lab",
        "f1": 0.658, "precision": 0.691, "recall": 0.627,
        "position_rms_km": 12.30, "velocity_rms_km_s": 0.810,
    },
    {
        "dataset_idx": 6,
        "algorithm_name": "TrackForge",
        "version": "1.1",
        "classification_marking": "DARPA UCT Team",
        "f1": 0.908, "precision": 0.920, "recall": 0.897,
        "position_rms_km": 1.82, "velocity_rms_km_s": 0.120,
    },
    {
        "dataset_idx": 7,
        "algorithm_name": "AstroIOD",
        "version": "3.2",
        "classification_marking": "NavLab",
        "f1": 0.834, "precision": 0.851, "recall": 0.817,
        "position_rms_km": 4.05, "velocity_rms_km_s": 0.265,
    },
]


# ============================================================
# SENSORS
# ============================================================

MOCK_SENSORS: list[dict] = [
    {"id": "GEODSS-MAUI", "name": "GEODSS Maui", "lat": 20.71, "lon": -156.26, "alt": 3.06},
    {"id": "GEODSS-DG", "name": "GEODSS Diego Garcia", "lat": -7.41, "lon": 72.45, "alt": 0.01},
    {"id": "EGLIN-RADAR", "name": "Eglin Radar", "lat": 30.57, "lon": -86.21, "alt": 0.05},
    {"id": "SBSS", "name": "SBSS (Space-Based)", "lat": 0.0, "lon": 0.0, "alt": 600.0},
]


# ============================================================
# OBSERVATION GENERATOR
# ============================================================

def generate_observations_for_dataset(
    dataset_id: int,
    regime: str,
    observation_count: int,
    satellite_count: int,
    seed: int = 42,
) -> list[dict]:
    """
    Generate synthetic observations for a dataset.

    Produces realistic RA/Dec values per regime, grouped into tracks
    with proper temporal spacing.
    """
    rng = random.Random(seed + dataset_id)

    # Pick satellites for this regime
    regime_sats = SATS_BY_REGIME.get(regime, SATS_BY_REGIME["LEO"])
    selected_sats = regime_sats[:satellite_count] if satellite_count <= len(regime_sats) else regime_sats

    # If we need more sats than available in the regime, add from other regimes
    if len(selected_sats) < satellite_count:
        all_sats = [s["sat_no"] for s in MOCK_SATELLITES if s["sat_no"] not in selected_sats]
        rng.shuffle(all_sats)
        selected_sats += all_sats[: satellite_count - len(selected_sats)]

    # Distribute observations across satellites
    obs_per_sat = max(15, observation_count // len(selected_sats))
    observations: list[dict] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    # RA/Dec ranges by regime
    dec_range = {"LEO": (-60, 60), "MEO": (-45, 45), "GEO": (-10, 10)}
    dec_min, dec_max = dec_range.get(regime, (-60, 60))

    for sat_no in selected_sats:
        # Generate 3-8 tracks per satellite
        num_tracks = rng.randint(3, 8)
        track_start = base_time

        for track_idx in range(num_tracks):
            # 3-5 observations per track, 30s apart
            obs_in_track = rng.randint(3, 5)
            sensor = rng.choice(MOCK_SENSORS)

            # Base RA/Dec for this track
            base_ra = rng.uniform(0, 360)
            base_dec = rng.uniform(dec_min, dec_max)

            for obs_idx in range(obs_in_track):
                obs_time = track_start + timedelta(seconds=30 * obs_idx)
                obs_id = f"demo-{dataset_id}-{sat_no}-{len(observations):04d}"

                # Small perturbation within track
                ra = base_ra + rng.gauss(0, 0.01)
                dec = base_dec + rng.gauss(0, 0.005)

                observations.append({
                    "id": obs_id,
                    "sat_no": sat_no,
                    "ob_time": obs_time.isoformat(),
                    "ra": round(ra % 360, 8),
                    "declination": round(max(-90, min(90, dec)), 8),
                    "sensor_id": sensor["id"],
                    "sensor_name": sensor["name"],
                    "send_lat": sensor["lat"],
                    "send_long": sensor["lon"],
                    "send_alt": sensor["alt"],
                    "data_mode": "SIMULATED",
                    "track_id": f"track-{dataset_id}-{sat_no}-{track_idx}",
                })

                if len(observations) >= observation_count:
                    return observations

            # Gap between tracks: 2-12 hours
            track_start += timedelta(hours=rng.uniform(2, 12))

    return observations[:observation_count]


# ============================================================
# SUBMISSION RESULTS GENERATOR
# ============================================================

def generate_submission_results(
    submission_id: int,
    f1: float,
    precision_val: float,
    recall_val: float,
    position_rms_km: float,
    velocity_rms_km_s: float,
    observation_count: int,
    satellite_count: int,
    seed: int = 42,
) -> dict:
    """Generate plausible detailed results for a submission."""
    rng = random.Random(seed + submission_id)

    # Derive binary metrics from F1/precision/recall
    total = observation_count
    tp = int(total * recall_val * 0.6)
    fp = int(tp * (1 - precision_val) / max(precision_val, 0.01))
    fn = int(tp * (1 - recall_val) / max(recall_val, 0.01))
    tn = max(0, total - tp - fp - fn)

    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)
    specificity = tn / max(tn + fp, 1)

    # Per-satellite breakdown (list format expected by results endpoint)
    # Pick real NORAD IDs for satellite names
    all_sat_nos = [s["sat_no"] for s in MOCK_SATELLITES]
    per_satellite: list[dict] = []
    for i in range(satellite_count):
        sat_no = all_sat_nos[i % len(all_sat_nos)]
        sat_f1 = f1 + rng.gauss(0, 0.05)
        sat_f1 = max(0.1, min(1.0, sat_f1))
        pe = position_rms_km * rng.uniform(0.5, 1.5)
        total_obs = rng.randint(15, 40)
        used_obs = int(total_obs * min(1.0, recall_val + rng.gauss(0, 0.05)))
        status = "TP" if rng.random() < precision_val else rng.choice(["FP", "FN"])
        per_satellite.append({
            "satellite_id": str(sat_no),
            "status": status,
            "observations_used": used_obs,
            "total_observations": total_obs,
            "position_error_km": round(pe, 3),
            "velocity_error_km_s": round(pe * rng.uniform(0.05, 0.08), 4),
            "confidence": round(sat_f1, 4),
            "f1_score": round(sat_f1, 4),
            "ra_residual_arcsec": round(rng.gauss(0, 2.0), 4),
            "dec_residual_arcsec": round(rng.gauss(0, 1.5), 4),
        })

    # Position error histogram: bins [0-1, 1-2, 2-3, 3-4, 4-5, 5+] km
    pe_counts = [0] * 6
    for sat_data in per_satellite:
        pe = sat_data["position_error_km"]
        bin_idx = min(5, int(pe))
        pe_counts[bin_idx] += 1

    # Residual histograms in sigma units
    def _make_residual_hist(key: str) -> dict:
        vals = [sat_data[key] for sat_data in per_satellite]
        if not vals:
            return {"labels": ["-3", "-2", "-1", "0", "1", "2", "3"], "counts": [0]*7}
        rms = math.sqrt(sum(v**2 for v in vals) / len(vals)) or 1.0
        sigma_vals = [v / rms for v in vals]
        bins = [0] * 7
        for sv in sigma_vals:
            if sv < -2.5: idx = 0
            elif sv < -1.5: idx = 1
            elif sv < -0.5: idx = 2
            elif sv < 0.5: idx = 3
            elif sv < 1.5: idx = 4
            elif sv < 2.5: idx = 5
            else: idx = 6
            bins[idx] += 1
        return {"labels": ["-3", "-2", "-1", "0", "1", "2", "3"], "counts": bins}

    ra_rms = round(math.sqrt(sum(s["ra_residual_arcsec"]**2 for s in per_satellite) / len(per_satellite)), 4) if per_satellite else 0.0
    dec_rms = round(math.sqrt(sum(s["dec_residual_arcsec"]**2 for s in per_satellite) / len(per_satellite)), 4) if per_satellite else 0.0
    mahalanobis = round(rng.uniform(0.8, 2.5), 2)

    raw_results = {
        "binary": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision_val,
            "recall": recall_val,
            "f1_score": f1,
            "accuracy": round(accuracy, 4),
            "specificity": round(specificity, 4),
        },
        "state": {
            "position_rms_km": position_rms_km,
            "velocity_rms_km_s": velocity_rms_km_s,
            "ra_residual_rms_arcsec": ra_rms,
            "dec_residual_rms_arcsec": dec_rms,
            "mahalanobis_distance": mahalanobis,
        },
        "per_satellite": per_satellite,
        "position_error_histogram": {
            "labels": ["0-1", "1-2", "2-3", "3-4", "4-5", "5+"],
            "counts": pe_counts,
        },
        "ra_residual_histogram": _make_residual_hist("ra_residual_arcsec"),
        "dec_residual_histogram": _make_residual_hist("dec_residual_arcsec"),
    }

    return {
        "submission_id": submission_id,
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision_val,
        "recall": recall_val,
        "f1_score": f1,
        "specificity": round(specificity, 4),
        "accuracy": round(accuracy, 4),
        "position_rms_km": position_rms_km,
        "velocity_rms_km_s": velocity_rms_km_s,
        "ra_residual_rms_arcsec": ra_rms,
        "dec_residual_rms_arcsec": dec_rms,
        "mahalanobis_distance": mahalanobis,
        "raw_results": raw_results,
    }
