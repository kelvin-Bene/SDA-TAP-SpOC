"""Seed a realistic, successful demo submission against a specified dataset.

Why this exists
---------------
QA_PROD_RUN_2026-04-17 follow-up: after fixing C1 (missing dataset_references)
and H1 (error_message propagation), every test submission still ended up
status=failed because the CI smoke-test UCTP fixture was months stale vs the
only backfill-repaired dataset, and the downstream orbit-association flow
crashed before producing meaningful scores. This script produces ONE realistic
UCTP tailored to a specific dataset (correct satNo, correct epoch in the obs
window, correct grouped_ops = real observation IDs, realistic covariance)
and submits it so the leaderboard populates for the Louis demo.

What this script does
---------------------
1. Fetches dataset + truth state vector + observation IDs from prod Supabase.
2. Builds a UCTP record at the TRUTH epoch with TRUTH state + small noise.
   This is intentional: the evaluation worker propagates truth -> est epoch
   during association, and keeping epochs aligned makes the propagation delta
   near-zero so we don't depend on local Orekit being available. Prod's
   evaluator DOES have Orekit so it will still propagate to the real obs
   times during state metrics. The truth epoch sits inside the obs window
   ±7 day Path-3 tolerance.
3. Adds small Gaussian noise (1 km position, 1 m/s velocity) to simulate a
   realistic high-quality algorithm output. Fixed seed for reproducibility.
4. Builds a single UCTP record with:
     - grouped_ops = every real observation_id for that dataset (the
       algorithm is declaring "these observations belong to this one orbit")
     - cov = 21-element lower-triangular matching the noise model
     - referenceFrame = "J2000" (skips unitConversion in the worker)
5. POSTs via multipart to /api/v1/submissions/ with a JWT loaded from the
   Playwright auth state file.
6. Polls /api/v1/submissions/{id} until status != queued/in_progress or
   until --timeout-seconds elapses. Prints the final summary and exits 0 on
   completed, 1 on failed/timeout.

Optional: --use-propagator flag invokes ephemerisPropagator to produce a
state at the obs-window midpoint instead of the truth epoch. Requires a
working Orekit/JVM locally — off by default because Windows installs often
lack it.

Usage
-----
    cd UCT-Benchmark-DMR/combined
    .venv/Scripts/python.exe scripts/seed_demo_submission.py \\
        --dataset-id 158 \\
        --algorithm-name DemoAlgo \\
        --version 1.0 \\
        --jwt-file frontend/e2e/.auth/user.json

Reads DATABASE_URL from .env. JWT is sourced from the Playwright auth state
(re-run `npm run e2e:prod:setup` in frontend/ to refresh if expired).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

load_dotenv(_PROJECT_ROOT / ".env")

from backend_api.database import get_db, init_database  # noqa: E402

DEFAULT_BACKEND_URL = "https://backend-production-4b02.up.railway.app"


def _extract_jwt_from_playwright_auth(auth_file: Path) -> str:
    """Parse the Playwright storageState JSON to find the Supabase access
    token. Matches the lookup logic in 91-supplementary.spec.ts:32-45."""
    with auth_file.open("r") as f:
        state = json.load(f)
    for origin in state.get("origins", []):
        for kv in origin.get("localStorage", []):
            name = kv.get("name", "")
            if not name.startswith("sb-") or not name.endswith("-auth-token"):
                continue
            try:
                parsed = json.loads(kv["value"])
                tok = parsed.get("access_token")
                if tok:
                    return tok
            except Exception:
                continue
    raise RuntimeError(
        f"no Supabase auth-token found in {auth_file}; re-run "
        f"`npm run e2e:prod:setup` to refresh"
    )


def _fetch_truth_sv(db, dataset_id: int) -> Dict[str, Any]:
    """Return a dict with the truth state vector + satellite params for the
    (single) reference orbit in this dataset. Mirrors workers.py:1371-1398."""
    df = db.adapter.fetchdf(
        """
        SELECT
            sv.sat_no,
            sv.epoch,
            sv.x_pos,
            sv.y_pos,
            sv.z_pos,
            sv.x_vel,
            sv.y_vel,
            sv.z_vel,
            COALESCE(s.mass_kg,        1000.0) AS mass_kg,
            COALESCE(s.cross_section_m2, 10.0) AS cross_section_m2,
            COALESCE(s.drag_coeff,        2.2) AS drag_coeff,
            COALESCE(s.srp_coeff,         1.3) AS srp_coeff
        FROM state_vectors sv
        JOIN dataset_references dr ON sv.id = dr.state_vector_id
        LEFT JOIN satellites s ON sv.sat_no = s.sat_no
        WHERE dr.dataset_id = ?
        ORDER BY sv.epoch DESC
        LIMIT 1
        """,
        (dataset_id,),
    )
    if df.empty:
        raise RuntimeError(
            f"dataset {dataset_id} has no dataset_references rows; run "
            f"backfill_dataset_references.py first"
        )
    row = df.iloc[0].to_dict()
    return {
        "sat_no": int(row["sat_no"]),
        "epoch": row["epoch"].to_pydatetime()
            if hasattr(row["epoch"], "to_pydatetime") else row["epoch"],
        "state_km": np.array(
            [row["x_pos"], row["y_pos"], row["z_pos"],
             row["x_vel"], row["y_vel"], row["z_vel"]],
            dtype=float,
        ),
        "sat_params": [
            float(row["mass_kg"]), float(row["cross_section_m2"]),
            float(row["drag_coeff"]), float(row["srp_coeff"]),
        ],
    }


def _fetch_obs_ids_and_window(db, dataset_id: int) -> Tuple[List[str], datetime, datetime]:
    df = db.adapter.fetchdf(
        """
        SELECT o.id AS obs_id, o.ob_time
        FROM observations o
        JOIN dataset_observations dso ON dso.observation_id = o.id
        WHERE dso.dataset_id = ?
        ORDER BY o.ob_time ASC
        """,
        (dataset_id,),
    )
    if df.empty:
        raise RuntimeError(f"dataset {dataset_id} has no observations")
    obs_ids = [str(x) for x in df["obs_id"].tolist()]
    t0 = df["ob_time"].min()
    t1 = df["ob_time"].max()
    if hasattr(t0, "to_pydatetime"):
        t0 = t0.to_pydatetime()
    if hasattr(t1, "to_pydatetime"):
        t1 = t1.to_pydatetime()
    return obs_ids, t0, t1


def _lower_triangular_21(diag_pos_km: float, diag_vel_kms: float) -> List[float]:
    """Serialize a 6x6 diagonal covariance (pos/pos/pos/vel/vel/vel) to the
    21-element row-major lower-triangular order expected by generateCov
    (`generateCov.py:50-62`).

    Diagonal only (no off-diag correlations).
    """
    # Full symmetric matrix
    cov = np.diag([
        diag_pos_km, diag_pos_km, diag_pos_km,
        diag_vel_kms, diag_vel_kms, diag_vel_kms,
    ])
    # Row-major lower-triangular unpacking: [C00, C10,C11, C20,C21,C22, ...]
    out: List[float] = []
    for row in range(6):
        for col in range(row + 1):
            out.append(float(cov[row, col]))
    assert len(out) == 21
    return out


def _build_uctp(
    state_at_midpoint_km: np.ndarray,
    midpoint_epoch: datetime,
    obs_ids: List[str],
) -> List[Dict[str, Any]]:
    cov21 = _lower_triangular_21(
        diag_pos_km=1.0,      # 1 km^2 position variance
        diag_vel_kms=1e-6,    # 1 m/s^2 velocity variance
    )
    return [{
        "idStateVector": 0,
        "grouped_ops": obs_ids,
        "source_data_types": ["EO"] * len(obs_ids),
        "classificationMarking": "U",
        "epoch": midpoint_epoch.isoformat(timespec="microseconds"),
        "uct": False,
        "xpos": float(state_at_midpoint_km[0]),
        "ypos": float(state_at_midpoint_km[1]),
        "zpos": float(state_at_midpoint_km[2]),
        "xvel": float(state_at_midpoint_km[3]),
        "yvel": float(state_at_midpoint_km[4]),
        "zvel": float(state_at_midpoint_km[5]),
        "cov": cov21,
        "referenceFrame": "J2000",
        "source": "SeedDemo",
        "dataMode": "NOMINAL",
        "algorithm": "seed_demo_submission.py",
    }]


def _submit(
    backend_url: str, jwt: str, dataset_id: int, algorithm_name: str,
    version: str, uctp_path: Path,
) -> Dict[str, Any]:
    with uctp_path.open("rb") as f:
        res = requests.post(
            f"{backend_url}/api/v1/submissions/",
            headers={"Authorization": f"Bearer {jwt}"},
            data={
                "dataset_id": str(dataset_id),
                "algorithm_name": algorithm_name,
                "version": version,
            },
            files={"file": ("demo_submission.json", f, "application/json")},
            timeout=30,
        )
    if res.status_code != 201:
        raise RuntimeError(
            f"POST /api/v1/submissions/ returned {res.status_code}: "
            f"{res.text[:500]}"
        )
    return res.json()


def _poll_until_terminal(
    backend_url: str, jwt: str, submission_id: str,
    timeout_seconds: int = 90, poll_interval_seconds: float = 2.0,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        r = requests.get(
            f"{backend_url}/api/v1/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"  warning: GET /submissions/{submission_id} "
                  f"returned {r.status_code}: {r.text[:200]}")
            time.sleep(poll_interval_seconds)
            continue
        last = r.json()
        status = last.get("status", "?")
        print(f"  submission {submission_id} status={status} "
              f"score={last.get('score')}")
        if status in ("completed", "failed", "cancelled"):
            return last
        time.sleep(poll_interval_seconds)
    raise TimeoutError(
        f"submission {submission_id} did not reach a terminal status "
        f"within {timeout_seconds}s. Last state: {last}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a demo submission.")
    parser.add_argument("--dataset-id", type=int, required=True,
                        help="Target dataset id (must have dataset_references).")
    parser.add_argument("--algorithm-name", type=str, default="DemoAlgo",
                        help="Algorithm name shown on the leaderboard.")
    parser.add_argument("--version", type=str, default="1.0",
                        help="Algorithm version label.")
    parser.add_argument("--jwt-file", type=Path,
                        default=Path("frontend/e2e/.auth/user.json"),
                        help="Path to Playwright storageState JSON.")
    parser.add_argument("--backend-url", type=str, default=DEFAULT_BACKEND_URL,
                        help="Backend base URL.")
    parser.add_argument("--pos-noise-km", type=float, default=1.0,
                        help="Std-dev of Gaussian position noise (km).")
    parser.add_argument("--vel-noise-km-s", type=float, default=1e-3,
                        help="Std-dev of Gaussian velocity noise (km/s).")
    parser.add_argument("--seed", type=int, default=42,
                        help="PRNG seed for reproducible noise.")
    parser.add_argument("--timeout-seconds", type=int, default=90,
                        help="Max wait for submission to reach terminal status.")
    parser.add_argument("--use-propagator", action="store_true",
                        help="Propagate truth to obs-window midpoint (requires "
                             "Orekit/JVM locally; default: keep truth epoch).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the UCTP that would be submitted; no POST.")
    args = parser.parse_args()

    # ---- 1. DB lookups ---------------------------------------------------
    init_database()
    db = get_db()
    truth = _fetch_truth_sv(db, args.dataset_id)
    obs_ids, obs_t0, obs_t1 = _fetch_obs_ids_and_window(db, args.dataset_id)
    midpoint = obs_t0 + (obs_t1 - obs_t0) / 2

    print(f"Dataset {args.dataset_id}: sat={truth['sat_no']}, "
          f"truth_epoch={truth['epoch']}, obs_window=[{obs_t0} .. {obs_t1}], "
          f"n_obs={len(obs_ids)}")

    # ---- 2. Build base state (either propagated or truth-epoch) ---------
    if args.use_propagator:
        print(f"Propagating truth to obs midpoint: {midpoint}")
        from uct_benchmark.simulation.propagator import ephemerisPropagator

        try:
            propagated = ephemerisPropagator(
                truth["state_km"],
                truth["epoch"],
                [midpoint],
                truth["sat_params"],
            )
        except Exception as e:
            print(f"ERROR: propagator failed: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 2
        base_state_km = np.asarray(propagated[0], dtype=float)
        base_epoch = midpoint
    else:
        # Offset by a small epsilon so prod's evaluator does a non-zero
        # propagation — zero-delta propagations have caused ProcessPoolExecutor
        # subprocess hangs in the Railway Orekit setup.
        print(f"Using truth epoch + 60s offset (propagation skipped locally)")
        base_state_km = np.asarray(truth["state_km"], dtype=float)
        base_epoch = truth["epoch"] + timedelta(seconds=60)
    print(f"Base state (km/km·s): pos=[{base_state_km[0]:.2f}, "
          f"{base_state_km[1]:.2f}, {base_state_km[2]:.2f}] "
          f"vel=[{base_state_km[3]:.4f}, "
          f"{base_state_km[4]:.4f}, {base_state_km[5]:.4f}]")
    print(f"UCTP epoch: {base_epoch}")

    # ---- 3. Noise --------------------------------------------------------
    rng = np.random.default_rng(args.seed)
    noise = rng.normal(
        loc=0.0,
        scale=[args.pos_noise_km]*3 + [args.vel_noise_km_s]*3,
        size=6,
    )
    state_noisy = base_state_km + noise
    print(f"Noise added: pos_rms={np.linalg.norm(noise[:3]):.3f} km, "
          f"vel_rms={np.linalg.norm(noise[3:]):.6f} km/s")

    # ---- 4. Build UCTP ---------------------------------------------------
    uctp = _build_uctp(state_noisy, base_epoch, obs_ids)
    temp_path = _PROJECT_ROOT / f"data/uploads/demo_seed_ds{args.dataset_id}.json"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(uctp, indent=2))
    print(f"Wrote UCTP to {temp_path}")

    if args.dry_run:
        print("\n--dry-run: skipping POST and poll.")
        return 0

    # ---- 5. Submit -------------------------------------------------------
    jwt = _extract_jwt_from_playwright_auth(args.jwt_file)
    print(f"\nPOSTing to {args.backend_url}/api/v1/submissions/ ...")
    sub = _submit(
        args.backend_url, jwt, args.dataset_id,
        args.algorithm_name, args.version, temp_path,
    )
    sub_id = sub.get("id")
    print(f"Created submission id={sub_id}, job_id={sub.get('job_id')}, "
          f"initial_status={sub.get('status')}")

    # ---- 6. Poll ---------------------------------------------------------
    print("\nPolling for completion...")
    final = _poll_until_terminal(
        args.backend_url, jwt, sub_id,
        timeout_seconds=args.timeout_seconds,
    )
    print("\n--- Final submission state ---")
    for k in ("id", "status", "score", "error_message", "dataset_name",
              "algorithm_name", "version", "completed_at"):
        print(f"  {k}: {final.get(k)}")

    status = final.get("status")
    if status != "completed":
        print(f"\nFAIL: submission ended with status={status}", file=sys.stderr)
        return 1
    print(f"\nSUCCESS: composite_score={final.get('score')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
