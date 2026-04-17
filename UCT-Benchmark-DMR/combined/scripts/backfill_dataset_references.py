"""One-off backfill: populate `dataset_references` for a dataset that has
observations but no truth-link rows.

Why this exists
---------------
QA_PROD_RUN_2026-04-17 C1: some post-Apr-9 datasets (e.g. 158) passed through
dataset generation successfully but never got rows written to
`dataset_references`, so every evaluation against them fails with
"Dataset N has no reference state vectors persisted." This script mirrors the
reference-linking step from run_dataset_generation
(backend_api/jobs/workers.py:1063-1098) so such a dataset can be repaired
without a full re-generation.

What this script does
---------------------
1. Loads the dataset row.
2. Enumerates the distinct satellites in the dataset via
   `dataset_observations -> observations`.
3. For each satellite, looks up the best-match `state_vectors` row (most
   recent UDL-sourced epoch for that sat_no) and `element_sets` row
   (most recent for that sat_no).
4. Calls `db.datasets.add_references_to_dataset(...)` — the same UPSERT the
   generation worker uses — to persist the link.
5. Prints a summary and exits.

Reference state vectors come from UDL data fetched at generation time. If
the `state_vectors` table has no row for a satellite, that sat is
unrecoverable here; the dataset needs full regeneration to re-fetch UDL
data. Unrecoverable sats are logged and skipped; the script still writes
whatever is recoverable so partial progress is kept.

Usage
-----
    cd combined
    .venv/Scripts/python.exe scripts/backfill_dataset_references.py --dataset-id 158
    .venv/Scripts/python.exe scripts/backfill_dataset_references.py --dataset-id 158 --dry-run

Reads DATABASE_URL (or DATABASE_PATH) from .env via python-dotenv.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

load_dotenv(_PROJECT_ROOT / ".env")

from backend_api.database import get_db, init_database  # noqa: E402


def _collect_sat_observations(db, dataset_id: int) -> Dict[int, List[str]]:
    """Return {sat_no: [observation_id, ...]} for observations in the dataset."""
    df = db.adapter.fetchdf(
        "SELECT o.id AS obs_id, o.sat_no AS sat_no "
        "FROM observations o "
        "JOIN dataset_observations do_ ON do_.observation_id = o.id "
        "WHERE do_.dataset_id = ?",
        (dataset_id,),
    )
    if df.empty:
        return {}
    grouped: Dict[int, List[str]] = {}
    for _, row in df.iterrows():
        sat_no = int(row["sat_no"])
        grouped.setdefault(sat_no, []).append(str(row["obs_id"]))
    return grouped


def _lookup_state_vector_id(db, sat_no: int) -> Optional[int]:
    """Most-recent UDL state_vectors id for this satellite."""
    df = db.adapter.fetchdf(
        "SELECT id FROM state_vectors "
        "WHERE sat_no = ? AND source = 'UDL' "
        "ORDER BY epoch DESC LIMIT 1",
        (sat_no,),
    )
    if df.empty:
        # Fall back to any source if UDL-specific lookup misses.
        df = db.adapter.fetchdf(
            "SELECT id FROM state_vectors WHERE sat_no = ? "
            "ORDER BY epoch DESC LIMIT 1",
            (sat_no,),
        )
    if df.empty:
        return None
    return int(df.iloc[0]["id"])


def _lookup_element_set_id(db, sat_no: int) -> Optional[int]:
    """Most-recent element_sets id for this satellite."""
    df = db.adapter.fetchdf(
        "SELECT id FROM element_sets WHERE sat_no = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (sat_no,),
    )
    if df.empty:
        return None
    return int(df.iloc[0]["id"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill dataset_references rows.")
    parser.add_argument("--dataset-id", type=int, required=True,
                        help="Dataset id to repair.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan without writing.")
    args = parser.parse_args()
    dataset_id: int = args.dataset_id

    init_database()
    db = get_db()

    ds_row = db.adapter.fetchdf(
        "SELECT id, name, status FROM datasets WHERE id = ?",
        (dataset_id,),
    )
    if ds_row.empty:
        print(f"ERROR: dataset {dataset_id} not found", file=sys.stderr)
        return 2
    print(f"Dataset: id={dataset_id} name={ds_row.iloc[0]['name']} "
          f"status={ds_row.iloc[0]['status']}")

    existing_refs = db.adapter.fetchdf(
        "SELECT COUNT(*) AS n FROM dataset_references WHERE dataset_id = ?",
        (dataset_id,),
    )
    existing_count = int(existing_refs.iloc[0]["n"]) if not existing_refs.empty else 0
    print(f"Existing dataset_references rows: {existing_count}")

    obs_by_sat = _collect_sat_observations(db, dataset_id)
    if not obs_by_sat:
        print(f"ERROR: no observations found for dataset {dataset_id}; "
              f"cannot backfill. Dataset likely needs re-generation.",
              file=sys.stderr)
        return 2
    print(f"Satellites observed in dataset: {len(obs_by_sat)}")

    planned: List[Tuple[int, int, Optional[int], int]] = []
    unrecoverable: List[int] = []
    for sat_no, obs_ids in obs_by_sat.items():
        sv_id = _lookup_state_vector_id(db, sat_no)
        es_id = _lookup_element_set_id(db, sat_no)
        if sv_id is None:
            unrecoverable.append(sat_no)
            continue
        planned.append((sat_no, sv_id, es_id, len(obs_ids)))

    print("\nPlan:")
    for sat_no, sv_id, es_id, obs_count in planned:
        print(f"  sat_no={sat_no:>7}  state_vector_id={sv_id}  "
              f"element_set_id={es_id}  obs_count={obs_count}")
    if unrecoverable:
        preview = unrecoverable[:10]
        suffix = "..." if len(unrecoverable) > 10 else ""
        print(f"\nWARNING: {len(unrecoverable)} satellites have no "
              f"state_vectors row and will be SKIPPED: {preview}{suffix}")
        print("         These sats require full dataset regeneration to "
              "re-fetch UDL data.")

    if args.dry_run:
        print("\n--dry-run: no writes performed.")
        return 0

    if not planned:
        print("\nNothing writable (all satellites unrecoverable). "
              "Regenerate the dataset.")
        return 1

    print(f"\nWriting {len(planned)} dataset_references rows...")
    for sat_no, sv_id, es_id, _obs_count in planned:
        db.datasets.add_references_to_dataset(
            dataset_id=dataset_id,
            sat_no=sat_no,
            state_vector_id=sv_id,
            element_set_id=es_id,
            grouped_obs_ids=obs_by_sat.get(sat_no),
        )

    after = db.adapter.fetchdf(
        "SELECT COUNT(*) AS n FROM dataset_references WHERE dataset_id = ?",
        (dataset_id,),
    )
    after_count = int(after.iloc[0]["n"]) if not after.empty else 0
    print(f"Done. dataset_references rows for {dataset_id}: "
          f"{existing_count} -> {after_count} "
          f"(wrote {len(planned)}, skipped {len(unrecoverable)} unrecoverable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
