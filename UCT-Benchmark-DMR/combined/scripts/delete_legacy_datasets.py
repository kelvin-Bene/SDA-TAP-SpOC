"""One-off cleanup script: delete the legacy 31 datasets and their dependent
rows so the schema migration in Phase 1 of the CTF train/val/test split work
can land against a clean production database.

Why this exists
---------------
Before the CTF split work, the production database held 31 datasets that:
  - had no `dataset_references` rows linking truth state vectors (they were
    generated before Phase 1 of the eval-pipeline fix that wired persistence)
  - therefore could not be evaluated end-to-end
  - had only one stale `submission_results` row from 2026-01-29 with f1=0
    (the dummy seed row from before the eval pipeline was even wired)

The user explicitly approved deleting them and starting fresh on the post-split
schema rather than backfilling. See plans/zesty-marinating-bubble.md Phase 0.

What this script touches
------------------------
DELETES (children first to avoid orphans):
  - submission_results  (1 row, the legacy dummy on submission_id=3)
  - submissions          (4 rows, all referencing dataset 72)
  - non_reference_observations (already 0 rows but cleared defensively)
  - dataset_references   (1 row)
  - dataset_observations (33,711 rows)
  - datasets             (31 rows)

KEEPS (intentional — these are reusable reference data):
  - observations         (20,733 rows; orphaned but reduces UDL re-query cost
                          when the next dataset generation runs against an
                          overlapping time window)
  - state_vectors        (33 rows)
  - element_sets         (31 rows)
  - satellites           (22 rows)

Usage
-----
    cd combined
    .venv/Scripts/python.exe scripts/delete_legacy_datasets.py

The script will print before/after row counts and prompt y/N before any
DELETE statements run. Reads DATABASE_URL from .env via python-dotenv.

Safety
------
- Read-only by default until the user types `y`
- Wraps the deletes in a single transaction; rolls back on any error
- Does NOT touch observations, state_vectors, element_sets, or satellites
- Does NOT touch the schema (Phase 1 handles ALTER TABLE separately)
"""

from __future__ import annotations

import os
import sys

import pg8000
from dotenv import load_dotenv


# Tables that store dataset_id (or otherwise depend on dataset state) and
# need to be cleared. Order matters: children before parents.
DELETE_ORDER = [
    "submission_results",  # depends on submissions
    "submissions",         # depends on datasets
    "non_reference_observations",
    "dataset_references",
    "dataset_observations",
    "datasets",
]

# Tables that should be preserved exactly as-is.
PRESERVE = [
    "observations",
    "state_vectors",
    "element_sets",
    "satellites",
]


def _connect():
    """Open a pg8000 connection using DATABASE_URL from the project .env."""
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        sys.exit("ERROR: DATABASE_URL not set in .env")

    # pg8000 wants explicit kwargs rather than a URL. Parse the canonical
    # postgresql://user:pass@host:port/db form by hand to avoid pulling in
    # SQLAlchemy or psycopg just for this.
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        sys.exit(f"ERROR: unexpected DATABASE_URL scheme: {url[:30]}...")
    rest = url.split("://", 1)[1]
    creds, hostpart = rest.split("@", 1)
    user, password = creds.split(":", 1)
    hostport, db = hostpart.split("/", 1)
    host, port = hostport.split(":", 1)
    db = db.split("?", 1)[0]  # strip query string if any
    return pg8000.connect(
        host=host, port=int(port), user=user, password=password, database=db
    )


def _row_counts(cur, tables):
    """Return a dict of {table_name: row_count}."""
    counts = {}
    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        counts[tbl] = cur.fetchone()[0]
    return counts


def _print_counts(label, counts):
    print(f"\n=== {label} ===")
    for tbl, n in counts.items():
        print(f"  {tbl:30s} {n:>10,}")


def main():
    conn = _connect()
    try:
        cur = conn.cursor()

        before_delete = _row_counts(cur, DELETE_ORDER)
        before_preserve = _row_counts(cur, PRESERVE)
        _print_counts("BEFORE — tables to clear", before_delete)
        _print_counts("BEFORE — tables to preserve (untouched)", before_preserve)

        total_to_delete = sum(before_delete.values())
        if total_to_delete == 0:
            print("\nNothing to delete — all tables are already empty.")
            return

        print(
            f"\nThis will DELETE {total_to_delete:,} rows across "
            f"{len([t for t, n in before_delete.items() if n > 0])} tables."
        )
        print(
            f"It will NOT touch {sum(before_preserve.values()):,} rows in "
            f"{len(PRESERVE)} preserved tables."
        )
        print("\nThis is irreversible.")
        confirm = input("Type 'y' to proceed, anything else to abort: ").strip().lower()
        if confirm != "y":
            print("Aborted; no changes made.")
            return

        # Single transaction so a partial failure rolls everything back.
        try:
            for tbl in DELETE_ORDER:
                if before_delete[tbl] == 0:
                    print(f"  skip {tbl} (already empty)")
                    continue
                cur.execute(f"DELETE FROM {tbl}")
                print(f"  cleared {tbl}")
            conn.commit()
        except Exception as e:
            conn.rollback()
            sys.exit(f"\nERROR during DELETE: {e}\nTransaction rolled back.")

        after_delete = _row_counts(cur, DELETE_ORDER)
        after_preserve = _row_counts(cur, PRESERVE)
        _print_counts("AFTER — cleared tables (should all be 0)", after_delete)
        _print_counts("AFTER — preserved tables (should be unchanged)", after_preserve)

        # Sanity check
        if any(n != 0 for n in after_delete.values()):
            sys.exit("ERROR: not all targeted tables ended at zero rows!")
        if after_preserve != before_preserve:
            sys.exit("ERROR: preserved tables changed unexpectedly!")
        print("\nDone — production state is clean for Phase 1 schema migration.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
