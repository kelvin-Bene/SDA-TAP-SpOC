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
    # Always ensure profiles table exists (not in base schema, managed by Supabase in prod)
    _ensure_profiles_table(db)

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
    _seed_demo_profile(db)
    _seed_feedback(db)

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
                generation_params, actual_satellite_ids, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                "demo-user",
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

    # Vary processing times for realism
    processing_minutes = [47, 128, 35, 195, 82, 210, 55, 150]

    # Spread submissions across ~4 months for meaningful leaderboard trend lines
    day_offsets = [120, 105, 90, 75, 60, 45, 30, 10]

    # Vary time-of-day so timestamps are not identical
    hour_offsets = [9, 14, 7, 16, 11, 20, 8, 15]
    minute_offsets = [23, 47, 12, 35, 58, 5, 41, 19]

    for i, sub in enumerate(MOCK_SUBMISSIONS):
        dataset_id = dataset_ids[sub["dataset_idx"]]
        base_date = now - timedelta(days=day_offsets[i])
        created_dt = base_date.replace(
            hour=hour_offsets[i % len(hour_offsets)],
            minute=minute_offsets[i % len(minute_offsets)],
            second=0, microsecond=0,
        )
        created_at = created_dt.isoformat()
        proc_time = processing_minutes[i % len(processing_minutes)]
        completed_at = (created_dt + timedelta(minutes=proc_time)).isoformat()

        db.execute(
            """
            INSERT INTO submissions (
                dataset_id, algorithm_name, version, classification_marking,
                status, created_at, completed_at, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                sub["algorithm_name"],
                sub["version"],
                sub["classification_marking"],
                "completed",
                created_at,
                completed_at,
                "demo-user",
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
                position_rms_km, velocity_rms_km_s,
                ra_residual_rms_arcsec, dec_residual_rms_arcsec,
                mahalanobis_distance, raw_results
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                results["ra_residual_rms_arcsec"],
                results["dec_residual_rms_arcsec"],
                results["mahalanobis_distance"],
                json.dumps(results["raw_results"]),
            ),
        )

    logger.info(f"DEMO MODE: Seeded {len(submission_ids)} submission results")


def _ensure_profiles_table(db) -> None:
    """Create the profiles table if it doesn't exist (managed by Supabase in prod)."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id VARCHAR PRIMARY KEY,
            email VARCHAR,
            role VARCHAR DEFAULT 'authenticated',
            display_name VARCHAR,
            organization VARCHAR,
            udl_token VARCHAR,
            esa_token VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _seed_demo_profile(db) -> None:
    """Insert a demo user profile."""
    db.execute("""
        INSERT INTO profiles (id, email, role, display_name, organization, created_at, updated_at)
        VALUES ('dev-user', 'dev@localhost', 'admin', 'Demo User', 'SpOC Demo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
    """)
    logger.info("DEMO MODE: Seeded demo user profile")


def _seed_feedback(db) -> None:
    """Insert sample feedback entries so the demo has data to display."""
    import uuid

    now = datetime.now(timezone.utc)
    feedback_entries = [
        {
            "id": str(uuid.uuid4()),
            "description": "The dataset generation wizard is intuitive and easy to use. Would be great to have a template library for common orbital regimes.",
            "severity": "suggestion",
            "page_url": "/datasets/generate",
            "reporter_email": "researcher@mit.edu",
            "status": "open",
            "created_at": (now - timedelta(days=3, hours=7)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "description": "Leaderboard F1 scores don't update immediately after submission completes. Had to refresh the page manually to see new results.",
            "severity": "bug",
            "page_url": "/leaderboard",
            "reporter_email": "dev@aerospace-corp.com",
            "status": "open",
            "created_at": (now - timedelta(days=2, hours=14)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "description": "Is there a way to export dataset observations to CSV or FITS format? Our pipeline needs raw observation data for offline analysis.",
            "severity": "question",
            "page_url": "/datasets",
            "reporter_email": "analyst@esa.int",
            "status": "open",
            "created_at": (now - timedelta(days=1, hours=22)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "description": "The submission upload flow could benefit from drag-and-drop support. Currently only the file picker button works.",
            "severity": "suggestion",
            "page_url": "/submissions/new",
            "reporter_email": "anonymous",
            "status": "resolved",
            "created_at": (now - timedelta(days=5, hours=3)).isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "description": "Getting a 500 error when trying to generate a dataset with more than 50 satellites in the GEO regime. Works fine with fewer objects.",
            "severity": "bug",
            "page_url": "/datasets/generate",
            "reporter_email": "ops@spaceforce.mil",
            "status": "in_progress",
            "created_at": (now - timedelta(days=1, hours=5)).isoformat(),
        },
    ]

    for fb in feedback_entries:
        try:
            db.execute(
                """
                INSERT INTO feedback (
                    id, description, severity, page_url,
                    reporter_email, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fb["id"],
                    fb["description"],
                    fb["severity"],
                    fb["page_url"],
                    fb["reporter_email"],
                    fb["status"],
                    fb["created_at"],
                ),
            )
        except Exception as e:
            logger.warning(f"DEMO MODE: Failed to seed feedback: {e}")

    logger.info(f"DEMO MODE: Seeded {len(feedback_entries)} feedback entries")
