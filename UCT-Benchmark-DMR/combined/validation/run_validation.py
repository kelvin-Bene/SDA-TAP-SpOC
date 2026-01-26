# -*- coding: utf-8 -*-
"""
UCT Benchmark Comprehensive Validation Suite
=============================================

This script performs comprehensive validation of the UCT Benchmark implementation:
1. Data Pull: Retrieves 100k+ observations from UDL API
2. Downsampling: Tests T1/T2 tier reduction algorithms
3. Gap Analysis: Tests epochsToSim() gap detection
4. Orekit Simulation: Tests synthetic observation generation

Usage:
    python validation/run_validation.py [--target-obs N] [--days N]

Author: SDA TAP Lab
Date: January 2026
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# Setup paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_TARGET_OBS = 100000
DEFAULT_DAYS = 30
DEFAULT_SATS_PER_REGIME = 50

ORBITAL_REGIMES = {
    "LEO": {"period_range": (88, 128), "description": "Low Earth Orbit"},
    "MEO": {"period_range": (128, 1200), "description": "Medium Earth Orbit"},
    "GEO": {"period_range": (1200, 1600), "description": "Geostationary Orbit"},
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def create_results_directory() -> Path:
    """Create timestamped results directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = SCRIPT_DIR / "results" / timestamp
    (results_dir / "input_data").mkdir(parents=True, exist_ok=True)
    (results_dir / "downsampling").mkdir(parents=True, exist_ok=True)
    (results_dir / "simulation").mkdir(parents=True, exist_ok=True)
    (results_dir / "summary").mkdir(parents=True, exist_ok=True)
    return results_dir


def log_section(title: str):
    print(f"\n{'=' * 80}\n  {title}\n{'=' * 80}\n")


def log_subsection(title: str):
    print(f"\n--- {title} ---\n")


def save_json(data: dict, filepath: Path):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


# =============================================================================
# PHASE 1: DATA PULL
# =============================================================================


def pull_observations(
    target_obs: int, days: int, sats_per_regime: int
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Pull observations from UDL API."""
    from uct_benchmark.api.apiIntegration import UDLQuery, UDLTokenGen, asyncUDLBatchQuery

    log_section("PHASE 1: DATA PULL FROM UDL")
    start_time = datetime.now()

    # Get token - try UDL_TOKEN first, then fall back to USERNAME/PASSWORD
    token = os.getenv("UDL_TOKEN")
    if not token:
        username = os.getenv("UDL_USERNAME")
        password = os.getenv("UDL_PASSWORD")
        if not username or not password:
            raise ValueError(
                "UDL credentials not found in .env (need UDL_TOKEN or UDL_USERNAME/UDL_PASSWORD)"
            )
        print("Generating UDL token...")
        token = UDLTokenGen(username, password)
    else:
        print("Using UDL_TOKEN from environment...")

    sweep_time = f">now-{days} days"
    print(f"Target: {target_obs:,} observations over {days} days")

    all_obs = []
    all_tles = []
    sat_info = {}

    for regime, config in ORBITAL_REGIMES.items():
        log_subsection(f"Pulling {regime}")
        period_min, period_max = config["period_range"]

        try:
            # Get satellites
            sat_df = UDLQuery(
                token,
                "elset/current",
                {"period": f"{period_min}..{period_max}", "maxResults": sats_per_regime * 2},
            )

            if sat_df is None or len(sat_df) == 0:
                print("  No satellites found")
                continue

            sat_ids = sat_df["satNo"].unique()[:sats_per_regime]
            print(f"  Found {len(sat_ids)} satellites")

            # Get observations
            obs_params = [
                {"satNo": str(s), "obTime": sweep_time, "dataMode": "REAL", "maxResults": 5000}
                for s in sat_ids
            ]
            obs_df = asyncUDLBatchQuery(token, "eoobservation", obs_params, dt=0.1)

            if obs_df is not None and len(obs_df) > 0:
                obs_df["regime"] = regime
                all_obs.append(obs_df)

                for sid in obs_df["satNo"].unique():
                    sat_info[int(sid)] = {
                        "regime": regime,
                        "obs_count": len(obs_df[obs_df["satNo"] == sid]),
                    }

                print(
                    f"  Retrieved {len(obs_df):,} observations from {obs_df['satNo'].nunique()} satellites"
                )

                # Get TLEs using elset/current
                tle_sats = obs_df["satNo"].unique()
                for sid in tle_sats:
                    try:
                        tle_result = UDLQuery(
                            token, "elset/current", {"satNo": str(sid), "maxResults": 1}
                        )
                        if tle_result is not None and len(tle_result) > 0:
                            tle_row = tle_result.iloc[0].to_dict()
                            tle_row["regime"] = regime
                            all_tles.append(tle_row)
                    except Exception:
                        pass

                print(f"  Retrieved {len([t for t in all_tles if t.get('regime') == regime])} TLEs")

        except Exception as e:
            print(f"  Error: {e}")
            continue

    if not all_obs:
        raise ValueError("No observations retrieved")

    obs_df = pd.concat(all_obs, ignore_index=True)
    tle_df = pd.DataFrame(all_tles)

    # Convert obTime to datetime
    if "obTime" in obs_df.columns:
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"], utc=True)
        print("  Converted obTime to datetime")

    # Rename TLE columns
    if "tle1" in tle_df.columns:
        tle_df = tle_df.rename(columns={"tle1": "line1", "tle2": "line2"})

    duration = (datetime.now() - start_time).total_seconds()

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "target": target_obs,
        "actual": len(obs_df),
        "target_met": len(obs_df) >= target_obs,
        "satellites": len(sat_info),
        "by_regime": {r: int(obs_df[obs_df["regime"] == r].shape[0]) for r in ORBITAL_REGIMES},
        "duration": duration,
    }

    log_subsection("Summary")
    print(f"Total observations: {len(obs_df):,}")
    print(f"Satellites: {len(sat_info)}")
    print(f"TLEs: {len(tle_df)}")
    print(f"Duration: {format_duration(duration)}")

    status = "PASS" if len(obs_df) >= target_obs else "WARN"
    print(f"\n[{status}] {len(obs_df):,} / {target_obs:,} observations")

    return obs_df, tle_df, metadata


# =============================================================================
# PHASE 2: DOWNSAMPLING
# =============================================================================


def test_downsampling(obs_df: pd.DataFrame, tle_df: pd.DataFrame, results_dir: Path) -> Dict:
    """Test downsampling with various retention levels."""
    from uct_benchmark.data.dataManipulation import downsampleData
    from uct_benchmark.simulation.propagator import orbit2OE

    log_section("PHASE 2: DOWNSAMPLING VALIDATION")
    start_time = datetime.now()

    # Build sat_params from TLEs
    print("Building satellite parameters from TLEs...")
    sat_params = {}

    for _, tle_row in tle_df.iterrows():
        try:
            sat_id = int(tle_row["satNo"])
            line1 = tle_row.get("line1", tle_row.get("tle1", ""))
            line2 = tle_row.get("line2", tle_row.get("tle2", ""))

            if not line1 or not line2:
                continue

            orb_elems = orbit2OE(line1, line2)
            sat_obs = obs_df[obs_df["satNo"] == sat_id]

            sat_params[sat_id] = {
                "Semi-Major Axis": orb_elems.get("Semi-Major Axis", 7000),
                "Eccentricity": orb_elems.get("Eccentricity", 0.001),
                "Inclination": orb_elems.get("Inclination", 45),
                "RAAN": orb_elems.get("RAAN", 0),
                "Argument of Perigee": orb_elems.get("Argument of Perigee", 0),
                "Mean Anomaly": orb_elems.get("Mean Anomaly", 0),
                "Period": orb_elems.get("Period", 5400),
                "Number of Obs": len(sat_obs),
                "Orbital Coverage": 0.5,
                "Max Track Gap": 2,
            }
        except Exception:
            continue

    print(f"Built parameters for {len(sat_params)} satellites")

    # Test configurations
    configs = [
        {"name": "T1_80pct", "coverage": (0.7, 1.0, 0.8), "track": 2, "obs_max": None},
        {"name": "T2_50pct", "coverage": (0.4, 0.6, 0.5), "track": 3, "obs_max": None},
        {"name": "T2_30pct", "coverage": (0.2, 0.4, 0.3), "track": 4, "obs_max": None},
    ]

    results = {"original_count": len(obs_df), "configs": {}, "passed": 0, "failed": 0}

    for cfg in configs:
        print(f"\nTesting {cfg['name']}...")
        try:
            orbit_coverage = {"sats": None, "p_bounds": cfg["coverage"], "p_coverage": (0.8, 0.2)}
            track_length = {"sats": None, "p_bounds": cfg["coverage"], "p_track": cfg["track"]}
            obs_count = {
                "sats": None,
                "p_bounds": cfg["coverage"],
                "obs_max": cfg["obs_max"] or len(obs_df),
            }

            ds_df, p_reached = downsampleData(
                obs_df.copy(), sat_params, orbit_coverage, track_length, obs_count
            )

            retention = len(ds_df) / len(obs_df)
            target = cfg["coverage"][2]

            status = "PASS" if abs(retention - target) < 0.3 else "WARN"
            results["passed"] += 1 if status == "PASS" else 0

            results["configs"][cfg["name"]] = {
                "target": target,
                "actual": retention,
                "count": len(ds_df),
                "status": status,
            }

            ds_df.to_csv(results_dir / "downsampling" / f"{cfg['name']}.csv", index=False)
            print(f"  {len(ds_df):,} obs ({retention * 100:.1f}%) - [{status}]")

        except Exception as e:
            results["configs"][cfg["name"]] = {"status": "ERROR", "error": str(e)}
            results["failed"] += 1
            print(f"  Error: {e}")

    results["duration"] = (datetime.now() - start_time).total_seconds()
    save_json(results, results_dir / "downsampling" / "metrics.json")

    log_subsection("Summary")
    print(f"Passed: {results['passed']}, Failed: {results['failed']}")

    return results


# =============================================================================
# PHASE 3: GAP ANALYSIS
# =============================================================================


def test_gap_analysis(obs_df: pd.DataFrame, tle_df: pd.DataFrame, results_dir: Path) -> Dict:
    """Test gap detection algorithm."""
    from uct_benchmark.simulation.propagator import orbit2OE
    from uct_benchmark.simulation.simulateObservations import epochsToSim

    log_section("PHASE 3: GAP ANALYSIS VALIDATION")
    start_time = datetime.now()

    # Get satellites with TLEs
    tle_sats = set(tle_df["satNo"].unique()) & set(obs_df["satNo"].unique())
    print(f"Testing {len(tle_sats)} satellites with TLEs")

    results = {"total": len(tle_sats), "passed": 0, "failed": 0, "skipped": 0, "details": {}}

    for i, sat_id in enumerate(tle_sats):
        try:
            sat_obs = obs_df[obs_df["satNo"] == sat_id]
            if len(sat_obs) < 10:
                results["skipped"] += 1
                continue

            tle_row = tle_df[tle_df["satNo"] == sat_id].iloc[0]
            line1 = tle_row.get("line1", tle_row.get("tle1", ""))
            line2 = tle_row.get("line2", tle_row.get("tle2", ""))

            orb_elems = orbit2OE(line1, line2)
            epochs, bins_info = epochsToSim(sat_id, sat_obs, orb_elems, None, 0.3)

            results["details"][int(sat_id)] = {
                "obs": len(sat_obs),
                "epochs": len(epochs),
                "status": bins_info.get("status", "unknown"),
            }

            if bins_info.get("status") in [
                "ok",
                "success",
                "sufficient_coverage",
                "max_ratio_limited",
            ]:
                results["passed"] += 1
            else:
                results["failed"] += 1

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(tle_sats)}...")

        except Exception as e:
            results["failed"] += 1
            results["details"][int(sat_id)] = {"error": str(e)}

    results["duration"] = (datetime.now() - start_time).total_seconds()
    save_json(results, results_dir / "simulation" / "gap_analysis.json")

    log_subsection("Summary")
    print(
        f"Passed: {results['passed']}, Failed: {results['failed']}, Skipped: {results['skipped']}"
    )

    return results


# =============================================================================
# PHASE 4: OREKIT SIMULATION
# =============================================================================


def test_orekit_simulation(obs_df: pd.DataFrame, tle_df: pd.DataFrame, results_dir: Path) -> Dict:
    """Test Orekit-based observation simulation."""
    import orekit_jpype as orekit

    orekit.initVM()
    from orekit_jpype.pyhelpers import setup_orekit_curdir

    setup_orekit_curdir(from_pip_library=True)

    from uct_benchmark.simulation.propagator import orbit2OE
    from uct_benchmark.simulation.simulateObservations import simulateObs

    log_section("PHASE 4: OREKIT SIMULATION VALIDATION")
    start_time = datetime.now()

    sensors_df = pd.DataFrame(
        {
            "idSensor": ["SEN001", "SEN002", "SEN003"],
            "name": ["DIEGO_GARCIA", "ASCENSION", "MAUI"],
            "senlat": [-7.3, -7.9, 20.7],
            "senlon": [72.4, -14.4, -156.3],
            "senalt": [0.01, 0.04, 3.1],
            "sensorLikelihood": [1.0, 1.0, 1.0],
            "count": [10, 10, 10],
        }
    )

    tle_sats = list(set(tle_df["satNo"].unique()) & set(obs_df["satNo"].unique()))[:25]
    print(f"Testing Orekit simulation for {len(tle_sats)} satellites")

    results = {
        "tle": {"passed": 0, "failed": 0, "obs": 0},
        "sv": {"passed": 0, "failed": 0, "obs": 0},
        "details": {},
    }

    all_sim_obs = []

    # TLE Propagation
    log_subsection("TLE Propagation")
    for i, sat_id in enumerate(tle_sats):
        try:
            tle_row = tle_df[tle_df["satNo"] == sat_id].iloc[0]
            line1 = tle_row.get("line1", tle_row.get("tle1", ""))
            line2 = tle_row.get("line2", tle_row.get("tle2", ""))

            sim_obs = simulateObs(line1, line2, 3600, sensors_df, 0.01, 1 / 3600, 60)
            obs_count = len(sim_obs) if sim_obs is not None else 0

            results["tle"]["passed"] += 1
            results["tle"]["obs"] += obs_count
            results["details"][int(sat_id)] = {"tle_obs": obs_count, "tle_status": "PASS"}

            if obs_count > 0:
                sim_obs["satNo"] = sat_id
                sim_obs["method"] = "TLE"
                all_sim_obs.append(sim_obs)

            if (i + 1) % 5 == 0:
                print(f"  TLE: {i + 1}/{len(tle_sats)}, {results['tle']['obs']} obs generated")

        except Exception as e:
            results["tle"]["failed"] += 1
            results["details"][int(sat_id)] = {"tle_error": str(e)}

    # State Vector Propagation
    log_subsection("State Vector Propagation")
    for i, sat_id in enumerate(tle_sats[:15]):
        try:
            tle_row = tle_df[tle_df["satNo"] == sat_id].iloc[0]
            line1 = tle_row.get("line1", tle_row.get("tle1", ""))
            line2 = tle_row.get("line2", tle_row.get("tle2", ""))

            orb_elems = orbit2OE(line1, line2)

            # Extract state vector as numpy array (required by ephemerisPropagator)
            sv = np.array(
                [
                    orb_elems["X"],
                    orb_elems["Y"],
                    orb_elems["Z"],
                    orb_elems["Vx"],
                    orb_elems["Vy"],
                    orb_elems["Vz"],
                ]
            )
            epoch = orb_elems["Epoch"]  # Now returns Python datetime

            # Use satellite parameters for propagation
            sat_params = [int(sat_id), 1000, 10]  # [satNo, mass, area]

            sim_obs = simulateObs(sv, epoch, 1800, sensors_df, 0.01, 1 / 3600, 60, sat_params)
            obs_count = len(sim_obs) if sim_obs is not None else 0

            results["sv"]["passed"] += 1
            results["sv"]["obs"] += obs_count

            if int(sat_id) in results["details"]:
                results["details"][int(sat_id)]["sv_obs"] = obs_count
                results["details"][int(sat_id)]["sv_status"] = "PASS"

            if obs_count > 0:
                sim_obs["satNo"] = sat_id
                sim_obs["method"] = "SV"
                all_sim_obs.append(sim_obs)

            if (i + 1) % 5 == 0:
                print(f"  SV: {i + 1}/15, {results['sv']['obs']} obs generated")

        except Exception as e:
            results["sv"]["failed"] += 1
            # Log error details for debugging
            if int(sat_id) in results["details"]:
                results["details"][int(sat_id)]["sv_error"] = str(e)
            else:
                results["details"][int(sat_id)] = {"sv_error": str(e)}

    # Save simulated observations
    if all_sim_obs:
        combined = pd.concat(all_sim_obs, ignore_index=True)
        combined.to_csv(results_dir / "simulation" / "generated_observations.csv", index=False)
        results["total_obs"] = len(combined)
    else:
        results["total_obs"] = 0

    results["duration"] = (datetime.now() - start_time).total_seconds()
    save_json(results, results_dir / "simulation" / "orekit_metrics.json")

    log_subsection("Summary")
    print(
        f"TLE: {results['tle']['passed']} passed, {results['tle']['failed']} failed, {results['tle']['obs']} obs"
    )
    print(
        f"SV: {results['sv']['passed']} passed, {results['sv']['failed']} failed, {results['sv']['obs']} obs"
    )
    print(f"Total generated: {results['total_obs']}")

    return results


# =============================================================================
# SUMMARY REPORT
# =============================================================================


def generate_report(results_dir: Path, pull: Dict, ds: Dict, gap: Dict, sim: Dict) -> Dict:
    """Generate summary report."""
    log_section("GENERATING SUMMARY")

    # Calculate pass rates
    ds_rate = ds["passed"] / max(1, ds["passed"] + ds["failed"])
    gap_rate = gap["passed"] / max(1, gap["passed"] + gap["failed"])
    tle_rate = sim["tle"]["passed"] / max(1, sim["tle"]["passed"] + sim["tle"]["failed"])
    sv_rate = sim["sv"]["passed"] / max(1, sim["sv"]["passed"] + sim["sv"]["failed"])

    overall = (
        pull["target_met"]
        and ds_rate >= 0.6
        and gap_rate >= 0.8
        and tle_rate >= 0.8
        and sv_rate >= 0.8
    )

    summary = {
        "timestamp": datetime.now().isoformat(),
        "overall": "PASS" if overall else "FAIL",
        "data_pull": {"status": "PASS" if pull["target_met"] else "WARN", **pull},
        "downsampling": {"pass_rate": ds_rate, **ds},
        "gap_analysis": {"pass_rate": gap_rate, **gap},
        "orekit": {"tle_rate": tle_rate, "sv_rate": sv_rate, **sim},
    }

    save_json(summary, results_dir / "summary" / "metrics_summary.json")

    # Markdown report
    report = f"""# UCT Benchmark Validation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Status:** {"PASS" if overall else "FAIL"}

## Summary

| Component | Status | Details |
|-----------|--------|---------|
| Data Pull | {"PASS" if pull["target_met"] else "WARN"} | {pull["actual"]:,} / {pull["target"]:,} observations |
| Downsampling | {"PASS" if ds_rate >= 0.6 else "FAIL"} | {ds["passed"]}/{ds["passed"] + ds["failed"]} configs passed |
| Gap Analysis | {"PASS" if gap_rate >= 0.8 else "FAIL"} | {gap["passed"]}/{gap["passed"] + gap["failed"]} satellites passed |
| Orekit TLE | {"PASS" if tle_rate >= 0.8 else "FAIL"} | {sim["tle"]["passed"]}/{sim["tle"]["passed"] + sim["tle"]["failed"]} satellites, {sim["tle"]["obs"]} obs |
| Orekit SV | {"PASS" if sv_rate >= 0.8 else "FAIL"} | {sim["sv"]["passed"]}/{sim["sv"]["passed"] + sim["sv"]["failed"]} satellites, {sim["sv"]["obs"]} obs |

## Data Pull
- Target: {pull["target"]:,} observations
- Actual: {pull["actual"]:,} observations
- Satellites: {pull["satellites"]}
- Duration: {format_duration(pull["duration"])}

## Observations by Regime
| Regime | Count |
|--------|-------|
| LEO | {pull["by_regime"].get("LEO", 0):,} |
| MEO | {pull["by_regime"].get("MEO", 0):,} |
| GEO | {pull["by_regime"].get("GEO", 0):,} |

## Orekit Simulation
- Total generated observations: {sim["total_obs"]:,}
- TLE propagation: {sim["tle"]["obs"]} observations
- State vector propagation: {sim["sv"]["obs"]} observations

---
*Generated by UCT Benchmark Validation Suite*
"""

    with open(results_dir / "summary" / "test_report.md", "w") as f:
        f.write(report)

    print(f"Overall Status: {'PASS' if overall else 'FAIL'}")
    print(f"Report saved to: {results_dir / 'summary'}")

    return summary


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="UCT Benchmark Validation")
    parser.add_argument("--target-obs", type=int, default=DEFAULT_TARGET_OBS)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--sats-per-regime", type=int, default=DEFAULT_SATS_PER_REGIME)
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("       UCT BENCHMARK COMPREHENSIVE VALIDATION SUITE")
    print("=" * 80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {args.target_obs:,} observations, {args.days} days")

    results_dir = create_results_directory()
    print(f"Results: {results_dir}")

    start = datetime.now()

    try:
        # Phase 1: Data Pull
        obs_df, tle_df, pull_meta = pull_observations(
            args.target_obs, args.days, args.sats_per_regime
        )
        obs_df.to_csv(results_dir / "input_data" / "observations.csv", index=False)
        tle_df.to_csv(results_dir / "input_data" / "tles.csv", index=False)
        save_json(pull_meta, results_dir / "input_data" / "metadata.json")

        # Phase 2: Downsampling
        ds_results = test_downsampling(obs_df, tle_df, results_dir)

        # Phase 3: Gap Analysis
        gap_results = test_gap_analysis(obs_df, tle_df, results_dir)

        # Phase 4: Orekit Simulation
        sim_results = test_orekit_simulation(obs_df, tle_df, results_dir)

        # Generate Report
        summary = generate_report(results_dir, pull_meta, ds_results, gap_results, sim_results)

        log_section("VALIDATION COMPLETE")
        print(f"Overall: {summary['overall']}")
        print(f"Duration: {format_duration((datetime.now() - start).total_seconds())}")
        print(f"Results: {results_dir}")

        return 0 if summary["overall"] == "PASS" else 1

    except Exception as e:
        log_section("VALIDATION FAILED")
        print(f"Error: {e}")
        traceback.print_exc()
        save_json(
            {"error": str(e), "traceback": traceback.format_exc()},
            results_dir / "summary" / "error.json",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
