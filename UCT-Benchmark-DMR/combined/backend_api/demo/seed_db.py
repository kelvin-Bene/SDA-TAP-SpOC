"""
Idempotent database seeding for demo mode.

Seeds the database with mock satellites, datasets, observations,
submissions, and results on startup. Skips if data already exists.
"""

import json
from datetime import datetime, timedelta, timezone

from loguru import logger

from .seed_data import (
    MOCK_DATASETS,
    MOCK_SATELLITES,
    MOCK_SUBMISSIONS,
    generate_observations_for_dataset,
    generate_submission_results,
)


def seed_demo_database(db) -> None:
    """Seed the demo database with mock data. Idempotent - skips if data exists."""
    count = db.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    if count > 0:
        logger.info("DEMO MODE: Database already seeded, skipping")
        return

    logger.info("DEMO MODE: Seeding database with mock data...")

    _seed_satellites(db)
    dataset_ids = _seed_datasets(db)
    _seed_observations_and_links(db, dataset_ids)
    submission_ids = _seed_submissions(db, dataset_ids)
    _seed_submission_results(db, submission_ids)

    logger.info("DEMO MODE: Database seeding complete")


def _seed_satellites(db) -> None:
    """Insert mock satellites."""
    for sat in MOCK_SATELLITES:
        try:
            db.execute(
                """
                INSERT INTO satellites (sat_no, name, orbital_regime, object_type)
                VALUES (?, ?, ?, ?)
                """,
                (sat["sat_no"], sat["name"], sat["orbital_regime"], sat["object_type"]),
            )
        except Exception:
            # Satellite may already exist from a partial seed
            pass
    logger.info(f"DEMO MODE: Seeded {len(MOCK_SATELLITES)} satellites")


def _seed_datasets(db) -> list[int]:
    """Insert mock datasets, return their IDs."""
    dataset_ids: list[int] = []
    now = datetime.now(timezone.utc)

    for i, ds in enumerate(MOCK_DATASETS):
        created_at = ds["created_at"].isoformat() if isinstance(ds["created_at"], datetime) else ds["created_at"]
        time_window_start = (now - timedelta(days=14)).isoformat()
        time_window_end = (now - timedelta(days=7)).isoformat()

        # Build generation_params JSON for sensor type inference
        sensor = "optical" if "Optical" in ds["name"] or "Fusion" in ds["name"] else "radar"
        gen_params = json.dumps({"sensors": [sensor]})

        db.execute(
            """
            INSERT INTO datasets (
                name, orbital_regime, tier, observation_count, satellite_count,
                avg_coverage, status, created_at, updated_at,
                time_window_start, time_window_end,
                generation_params, actual_satellite_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ds["name"],
                ds["orbital_regime"],
                ds["tier"],
                ds["observation_count"],
                ds["satellite_count"],
                ds["avg_coverage"],
                ds["status"],
                created_at,
                created_at,
                time_window_start,
                time_window_end,
                gen_params,
                json.dumps([]),
            ),
        )

        # Get the inserted ID
        row = db.execute(
            "SELECT id FROM datasets WHERE name = ?", (ds["name"],)
        ).fetchone()
        dataset_ids.append(row[0])

    logger.info(f"DEMO MODE: Seeded {len(dataset_ids)} datasets (IDs: {dataset_ids})")
    return dataset_ids


def _seed_observations_and_links(db, dataset_ids: list[int]) -> None:
    """Generate and insert synthetic observations, then link to datasets."""
    total_obs = 0

    for i, ds in enumerate(MOCK_DATASETS):
        dataset_id = dataset_ids[i]
        observations = generate_observations_for_dataset(
            dataset_id=dataset_id,
            regime=ds["orbital_regime"],
            observation_count=ds["observation_count"],
            satellite_count=ds["satellite_count"],
            seed=42,
        )

        # Batch insert observations
        for obs in observations:
            try:
                db.execute(
                    """
                    INSERT INTO observations (
                        id, sat_no, ob_time, ra, declination,
                        sensor_id, sensor_name, send_lat, send_long, send_alt,
                        data_mode, track_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        obs["id"],
                        obs["sat_no"],
                        obs["ob_time"],
                        obs["ra"],
                        obs["declination"],
                        obs["sensor_id"],
                        obs["sensor_name"],
                        obs["send_lat"],
                        obs["send_long"],
                        obs["send_alt"],
                        obs["data_mode"],
                        obs["track_id"],
                    ),
                )
            except Exception:
                pass  # Skip duplicates

        # Link observations to dataset
        for obs in observations:
            try:
                db.execute(
                    """
                    INSERT INTO dataset_observations (dataset_id, observation_id)
                    VALUES (?, ?)
                    """,
                    (dataset_id, obs["id"]),
                )
            except Exception:
                pass

        total_obs += len(observations)

    logger.info(f"DEMO MODE: Seeded {total_obs} observations across {len(dataset_ids)} datasets")


def _seed_submissions(db, dataset_ids: list[int]) -> list[int]:
    """Insert mock submissions, return their IDs."""
    submission_ids: list[int] = []
    now = datetime.now(timezone.utc)

    for i, sub in enumerate(MOCK_SUBMISSIONS):
        dataset_id = dataset_ids[sub["dataset_idx"]]
        created_at = (now - timedelta(days=30 - i * 3)).isoformat()
        completed_at = (now - timedelta(days=30 - i * 3, hours=-1)).isoformat()

        db.execute(
            """
            INSERT INTO submissions (
                dataset_id, algorithm_name, version, classification_marking,
                status, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                sub["algorithm_name"],
                sub["version"],
                sub["classification_marking"],
                "completed",
                created_at,
                completed_at,
            ),
        )

        row = db.execute(
            """
            SELECT id FROM submissions
            WHERE dataset_id = ? AND algorithm_name = ? AND version = ?
            ORDER BY id DESC LIMIT 1
            """,
            (dataset_id, sub["algorithm_name"], sub["version"]),
        ).fetchone()
        submission_ids.append(row[0])

    logger.info(f"DEMO MODE: Seeded {len(submission_ids)} submissions")
    return submission_ids


def _seed_submission_results(db, submission_ids: list[int]) -> None:
    """Generate and insert submission results with detailed metrics."""
    for i, sub in enumerate(MOCK_SUBMISSIONS):
        submission_id = submission_ids[i]
        ds = MOCK_DATASETS[sub["dataset_idx"]]

        results = generate_submission_results(
            submission_id=submission_id,
            f1=sub["f1"],
            precision_val=sub["precision"],
            recall_val=sub["recall"],
            position_rms_km=sub["position_rms_km"],
            velocity_rms_km_s=sub["velocity_rms_km_s"],
            observation_count=ds["observation_count"],
            satellite_count=ds["satellite_count"],
            seed=42,
        )

        db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, true_negatives,
                false_positives, false_negatives,
                precision, recall, f1_score, specificity, accuracy,
                position_rms_km, velocity_rms_km_s, raw_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                results["submission_id"],
                results["true_positives"],
                results["true_negatives"],
                results["false_positives"],
                results["false_negatives"],
                results["precision"],
                results["recall"],
                results["f1_score"],
                results["specificity"],
                results["accuracy"],
                results["position_rms_km"],
                results["velocity_rms_km_s"],
                json.dumps(results["raw_results"]),
            ),
        )

    logger.info(f"DEMO MODE: Seeded {len(submission_ids)} submission results")
