"""
Demo data seeder for the SDA-TAP-SpOC symposium demo.

Populates the database with realistic satellites, datasets, observations,
submissions, and results so the UI is not empty for attendees.

Usage:
    Called automatically during app startup via main.py lifespan.
    Only seeds if the datasets table is empty (idempotent).
"""

import json
import random
import uuid
from datetime import datetime, timedelta

from loguru import logger

# ---------------------------------------------------------------------------
# Demo satellite catalog (real NORAD IDs)
# ---------------------------------------------------------------------------
DEMO_SATELLITES = {
    "LEO": [
        (25544, "ISS (ZARYA)", "LEO", "PAYLOAD"),
        (20580, "HST", "LEO", "PAYLOAD"),
        (39084, "LANDSAT 8", "LEO", "PAYLOAD"),
        (43013, "NOAA 20", "LEO", "PAYLOAD"),
        (27424, "ENVISAT", "LEO", "DEBRIS"),
    ],
    "MEO": [
        (28874, "NAVSTAR 60 (GPS IIR-12)", "MEO", "PAYLOAD"),
        (32260, "NAVSTAR 62 (GPS IIR-20)", "MEO", "PAYLOAD"),
        (36585, "NAVSTAR 65 (GPS IIF-1)", "MEO", "PAYLOAD"),
        (41019, "GALILEO-FOC FM3", "MEO", "PAYLOAD"),
    ],
    "GEO": [
        (36868, "AEHF 1", "GEO", "PAYLOAD"),
        (39222, "WGS 6", "GEO", "PAYLOAD"),
        (40733, "MUOS 4", "GEO", "PAYLOAD"),
    ],
    "HEO": [
        (28884, "MOLNIYA 3-53", "HEO", "PAYLOAD"),
        (25744, "MOLNIYA 3-50", "HEO", "PAYLOAD"),
    ],
}

# ---------------------------------------------------------------------------
# Dataset definitions
# ---------------------------------------------------------------------------
DEMO_DATASETS = [
    {
        "name": "LEO-ISS-Corridor",
        "regime": "LEO",
        "tier": "T1",
        "sensor": "optical",
        "regime_key": "LEO",
    },
    {
        "name": "MEO-GPS-Constellation",
        "regime": "MEO",
        "tier": "T2",
        "sensor": "radar",
        "regime_key": "MEO",
    },
    {
        "name": "GEO-Belt-Survey",
        "regime": "GEO",
        "tier": "T1",
        "sensor": "optical",
        "regime_key": "GEO",
    },
    {
        "name": "HEO-Molniya-Track",
        "regime": "HEO",
        "tier": "T2",
        "sensor": "optical",
        "regime_key": "HEO",
    },
]

# ---------------------------------------------------------------------------
# Submission / result definitions
# ---------------------------------------------------------------------------
DEMO_SUBMISSIONS = [
    {
        "team": "Alpha Team",
        "algorithm": "Alpha-OrbTrack v2.1",
        "version": "2.1.0",
        "dataset_idx": 0,
        "f1": 0.921,
    },
    {
        "team": "Bravo Squad",
        "algorithm": "Bravo-CorrelateX v1.4",
        "version": "1.4.0",
        "dataset_idx": 1,
        "f1": 0.887,
    },
    {
        "team": "Charlie Unit",
        "algorithm": "Charlie-DeepAssoc v3.0",
        "version": "3.0.2",
        "dataset_idx": 2,
        "f1": 0.856,
    },
    {
        "team": "Delta Force",
        "algorithm": "Delta-HEOTracker v1.0",
        "version": "1.0.1",
        "dataset_idx": 3,
        "f1": 0.903,
    },
]

SENSOR_NAMES = ["GEODSS-Maui", "GEODSS-Diego-Garcia", "Eglin-AN/FPS-85", "SBSS"]

# Observation window
OBS_START = datetime(2026, 3, 1, 0, 0, 0)
OBS_WINDOW_DAYS = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_clustered(center: float, spread: float, lo: float, hi: float) -> float:
    """Return a random value clustered around *center* within [lo, hi]."""
    val = random.gauss(center, spread)
    return max(lo, min(hi, val))


def _generate_observations_for_satellite(sat_no: int, count: int):
    """
    Generate *count* synthetic observations for one satellite.

    Returns a list of tuples ready for INSERT and a parallel list of
    (obs_id, track_id) pairs for linking.
    """
    # Per-satellite base pointing (gives realistic clustering)
    base_ra = random.uniform(0, 360)
    base_dec = random.uniform(-50, 50)

    # Spread timestamps over the 7-day window
    window_seconds = OBS_WINDOW_DAYS * 86400
    timestamps = sorted(
        OBS_START + timedelta(seconds=random.uniform(0, window_seconds))
        for _ in range(count)
    )

    rows = []
    obs_ids = []

    # Group into tracks (3-6 obs each)
    idx = 0
    while idx < count:
        remaining = count - idx
        track_size = random.randint(min(3, remaining), min(6, remaining))
        track_id = str(uuid.uuid4())
        sensor = random.choice(SENSOR_NAMES)

        for _ in range(track_size):
            if idx >= count:
                break
            obs_id = str(uuid.uuid4())
            ts = timestamps[idx]

            ra = _random_clustered(base_ra, 5.0, 0, 360)
            dec = _random_clustered(base_dec, 3.0, -60, 60)
            ra_rate = round(random.uniform(0.001, 0.01), 6)
            dec_rate = round(random.uniform(0.001, 0.01), 6)
            # Store rates as small strings via the ra_rate / dec_rate columns
            # Schema doesn't have ra_rate / dec_rate columns — store in
            # los_unc (unused) so the data round-trips; safer to just skip
            # non-schema fields.  We'll use only columns that exist.
            ra_unc = round(random.uniform(0.5, 2.0), 4)
            dec_unc = round(random.uniform(0.5, 2.0), 4)

            rows.append((
                obs_id,          # id
                sat_no,          # sat_no
                ts.isoformat(),  # ob_time
                round(ra, 8),    # ra
                round(dec, 8),   # declination
                sensor,          # sensor_name
                track_id,        # track_id
                False,           # is_uct
                False,           # is_simulated
                "SIMULATED",     # data_mode
            ))
            obs_ids.append((obs_id, track_id))
            idx += 1

    return rows, obs_ids


def _derive_metrics(f1: float):
    """Derive precision, recall, and confusion-matrix counts from an F1 score."""
    # Choose precision slightly above F1, recall slightly below (or vice-versa)
    # so that the harmonic mean lands near f1.
    precision = round(min(1.0, f1 + random.uniform(0.01, 0.04)), 6)
    # recall = (f1 * precision) / (2 * precision - f1)
    denom = 2 * precision - f1
    if denom <= 0:
        recall = f1
    else:
        recall = round(min(1.0, (f1 * precision) / denom), 6)

    # Derive integer counts (scale to ~200 total correlated obs)
    total = random.randint(180, 250)
    tp = int(round(recall * total))
    fn = total - tp
    # FP from precision: precision = tp / (tp + fp) => fp = tp/precision - tp
    fp = max(0, int(round(tp / precision - tp))) if precision > 0 else 0
    tn = random.randint(20, 60)

    return {
        "precision": precision,
        "recall": recall,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
    }


def _build_raw_results(dataset_sats, metrics, f1):
    """Build a JSON-serialisable raw_results dict with per-satellite breakdown."""
    per_sat = {}
    remaining_tp = metrics["tp"]
    sat_list = list(dataset_sats)
    for i, (sat_no, name, *_rest) in enumerate(sat_list):
        if i == len(sat_list) - 1:
            sat_tp = remaining_tp
        else:
            sat_tp = max(1, int(remaining_tp / (len(sat_list) - i) + random.randint(-3, 3)))
            remaining_tp -= sat_tp
        per_sat[str(sat_no)] = {
            "name": name,
            "true_positives": sat_tp,
            "false_positives": random.randint(0, 3),
            "false_negatives": random.randint(0, 4),
        }

    return {
        "per_satellite": per_sat,
        "histogram": {
            "bins": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            "counts": [random.randint(2, 30) for _ in range(8)],
        },
        "summary": {
            "f1_score": f1,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
        },
    }


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def seed_if_empty(db) -> None:
    """
    Seed the database with demo data if the datasets table is empty.

    This is idempotent: if any datasets already exist the function returns
    immediately.

    Args:
        db: DatabaseManager instance (from backend_api.database)
    """
    # Use a deterministic seed so re-runs produce the same data
    random.seed(42)

    # --- Guard: skip if already seeded ---------------------------------
    try:
        row = db.adapter.fetchone(
            db.adapter.convert_placeholders("SELECT COUNT(*) FROM datasets"),
            (),
        )
        if row and row[0] > 0:
            logger.info("Demo data already present, skipping seed")
            return
    except Exception as e:
        logger.warning(f"Could not check datasets table (may not exist yet): {e}")
        return

    logger.info("Seeding demo data for symposium demo...")

    # ------------------------------------------------------------------
    # 1. Satellites
    # ------------------------------------------------------------------
    all_sats = []
    for regime_sats in DEMO_SATELLITES.values():
        for sat_no, name, regime, obj_type in regime_sats:
            all_sats.append((sat_no, name, regime, obj_type))

    sat_query = (
        "INSERT INTO satellites (sat_no, name, orbital_regime, object_type) "
        "VALUES (?, ?, ?, ?) ON CONFLICT (sat_no) DO NOTHING"
    )
    db.executemany(sat_query, all_sats)
    logger.info(f"  Satellites inserted: {len(all_sats)}")

    # ------------------------------------------------------------------
    # 2. Datasets (use sequence-generated IDs via DEFAULT)
    # ------------------------------------------------------------------
    dataset_ids = []

    for ds_def in DEMO_DATASETS:
        regime_sats = DEMO_SATELLITES[ds_def["regime_key"]]
        sat_ids_list = [s[0] for s in regime_sats]
        sat_count = len(sat_ids_list)
        obs_per_sat = random.randint(25, 40)
        total_obs = sat_count * obs_per_sat

        gen_params = json.dumps({
            "regime": ds_def["regime"],
            "tier": ds_def["tier"],
            "sensor_type": ds_def["sensor"],
            "obs_per_satellite": obs_per_sat,
        })
        actual_sat_ids = json.dumps(sat_ids_list)

        time_start = OBS_START.isoformat()
        time_end = (OBS_START + timedelta(days=OBS_WINDOW_DAYS)).isoformat()

        # INSERT and retrieve the sequence-generated id
        db.execute(
            "INSERT INTO datasets "
            "(name, tier, orbital_regime, satellite_count, observation_count, "
            "status, generation_params, actual_satellite_ids, "
            "time_window_start, time_window_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ds_def["name"],
                ds_def["tier"],
                ds_def["regime"],
                sat_count,
                total_obs,
                "available",
                gen_params,
                actual_sat_ids,
                time_start,
                time_end,
            ),
        )

        # Fetch the id that was just generated
        row = db.adapter.fetchone(
            db.adapter.convert_placeholders(
                "SELECT id FROM datasets WHERE name = ?"
            ),
            (ds_def["name"],),
        )
        ds_id = row[0]
        dataset_ids.append(ds_id)
        logger.info(f"  Dataset '{ds_def['name']}' created (id={ds_id}, sats={sat_count}, target_obs={total_obs})")

    # ------------------------------------------------------------------
    # 3. Observations & dataset_observations links
    # ------------------------------------------------------------------
    obs_insert_query = (
        "INSERT INTO observations "
        "(id, sat_no, ob_time, ra, declination, sensor_name, track_id, "
        "is_uct, is_simulated, data_mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (id) DO NOTHING"
    )

    link_insert_query = (
        "INSERT INTO dataset_observations (dataset_id, observation_id) "
        "VALUES (?, ?) "
        "ON CONFLICT (dataset_id, observation_id) DO NOTHING"
    )

    total_obs_inserted = 0

    for ds_idx, ds_def in enumerate(DEMO_DATASETS):
        ds_id = dataset_ids[ds_idx]
        regime_sats = DEMO_SATELLITES[ds_def["regime_key"]]

        all_obs_rows = []
        all_link_rows = []

        for sat_no, _name, _regime, _obj_type in regime_sats:
            count = random.randint(25, 40)
            obs_rows, obs_ids = _generate_observations_for_satellite(sat_no, count)
            all_obs_rows.extend(obs_rows)

            for obs_id, _track_id in obs_ids:
                all_link_rows.append((ds_id, obs_id))

        # Batch insert observations
        db.executemany(obs_insert_query, all_obs_rows)
        # Batch insert links
        db.executemany(link_insert_query, all_link_rows)

        total_obs_inserted += len(all_obs_rows)

        # Update the dataset's actual observation count
        db.execute(
            "UPDATE datasets SET observation_count = ? WHERE id = ?",
            (len(all_obs_rows), ds_id),
        )

    logger.info(f"  Observations inserted: {total_obs_inserted}")

    # ------------------------------------------------------------------
    # 4. Submissions
    # ------------------------------------------------------------------
    submission_ids = []
    now = datetime.utcnow()

    for sub_def in DEMO_SUBMISSIONS:
        ds_id = dataset_ids[sub_def["dataset_idx"]]
        created = now - timedelta(hours=random.randint(12, 72))
        completed = created + timedelta(minutes=random.randint(15, 90))

        db.execute(
            "INSERT INTO submissions "
            "(dataset_id, algorithm_name, version, description, "
            "status, created_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ds_id,
                sub_def["algorithm"],
                sub_def["version"],
                f"{sub_def['team']} submission using {sub_def['algorithm']}",
                "completed",
                created.isoformat(),
                completed.isoformat(),
            ),
        )

        row = db.adapter.fetchone(
            db.adapter.convert_placeholders(
                "SELECT id FROM submissions WHERE algorithm_name = ? AND dataset_id = ?"
            ),
            (sub_def["algorithm"], ds_id),
        )
        sub_id = row[0]
        submission_ids.append(sub_id)
        logger.info(f"  Submission '{sub_def['algorithm']}' created (id={sub_id})")

    # ------------------------------------------------------------------
    # 5. Submission results
    # ------------------------------------------------------------------
    for i, sub_def in enumerate(DEMO_SUBMISSIONS):
        sub_id = submission_ids[i]
        f1 = sub_def["f1"]
        m = _derive_metrics(f1)

        ds_idx = sub_def["dataset_idx"]
        regime_key = DEMO_DATASETS[ds_idx]["regime_key"]
        dataset_sats = DEMO_SATELLITES[regime_key]

        raw = _build_raw_results(dataset_sats, m, f1)

        pos_rms = round(random.uniform(0.5, 3.0), 6)
        vel_rms = round(random.uniform(0.005, 0.03), 9)
        mahal = round(random.uniform(0.8, 2.5), 6)
        ra_res = round(random.uniform(1.0, 4.0), 6)
        dec_res = round(random.uniform(1.0, 4.0), 6)
        proc_time = round(random.uniform(15.0, 60.0), 3)

        # accuracy = (TP+TN) / (TP+TN+FP+FN)
        total = m["tp"] + m["tn"] + m["fp"] + m["fn"]
        accuracy = round((m["tp"] + m["tn"]) / total, 6) if total > 0 else 0
        # specificity = TN / (TN + FP)
        spec_denom = m["tn"] + m["fp"]
        specificity = round(m["tn"] / spec_denom, 6) if spec_denom > 0 else 0

        db.execute(
            "INSERT INTO submission_results "
            "(submission_id, true_positives, true_negatives, false_positives, "
            "false_negatives, precision, recall, f1_score, specificity, accuracy, "
            "position_rms_km, velocity_rms_km_s, mahalanobis_distance, "
            "ra_residual_rms_arcsec, dec_residual_rms_arcsec, "
            "raw_results, processing_time_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sub_id,
                m["tp"],
                m["tn"],
                m["fp"],
                m["fn"],
                m["precision"],
                m["recall"],
                f1,
                specificity,
                accuracy,
                pos_rms,
                vel_rms,
                mahal,
                ra_res,
                dec_res,
                json.dumps(raw),
                proc_time,
            ),
        )
        logger.info(f"  Result for submission {sub_id}: F1={f1}")

    logger.info("Demo data seeding complete.")
