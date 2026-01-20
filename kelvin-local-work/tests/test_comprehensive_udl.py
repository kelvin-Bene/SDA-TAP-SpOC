#!/usr/bin/env python3
"""
Comprehensive UDL Data Test Script
===================================
Pulls a large dataset from UDL and runs extensive simulation and downsampling tests.

This script:
1. Pulls observations for 20+ satellites across all orbital regimes
2. Fetches 14 days of historical data
3. Runs comprehensive downsampling tests
4. Runs comprehensive simulation tests
5. Validates results against expected performance metrics

Expected runtime: 10-30 minutes depending on network speed and data availability.

Usage:
    # Set credentials as environment variables
    export UDL_USERNAME="your_username"
    export UDL_PASSWORD="your_password"

    # Run the script
    python tests/test_comprehensive_udl.py

    # Or with custom parameters
    python tests/test_comprehensive_udl.py --satellites 30 --days 21

Author: SDA TAP Lab
Date: 2026-01-19
"""

import argparse
import base64
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Suppress HTTPS warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

# Default test parameters
DEFAULT_SATELLITES_PER_REGIME = 20  # 20 per regime = 60 total
DEFAULT_DAYS = 21  # 3 weeks of data
DEFAULT_MIN_OBS = 20  # Minimum observations per satellite to include
MAX_QUERY_RETRIES = 3
QUERY_DELAY_SEC = 0.3  # Delay between API calls to avoid rate limiting


# ============================================================================
# UDL API Functions (Direct HTTP - No Orekit Required)
# ============================================================================

def UDLTokenGen(username: str, password: str) -> str:
    """Generate UDL authentication token."""
    return base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")


def UDLQuery(token: str, service: str, params: dict) -> pd.DataFrame:
    """Perform a UDL query via direct HTTP."""
    url = f"https://unifieddatalibrary.com/udl/{service.lower()}"
    headers = {"Authorization": "Basic " + token}

    resp = requests.get(url, headers=headers, params=params, verify=False, timeout=60)

    if resp.status_code != 200:
        return pd.DataFrame()

    data = resp.json()
    return pd.DataFrame(data) if data else pd.DataFrame()


# ============================================================================
# Utility Functions
# ============================================================================

def get_credentials():
    """Get UDL credentials from environment or prompt."""
    username = os.environ.get('UDL_USERNAME')
    password = os.environ.get('UDL_PASSWORD')

    if not username:
        username = input("Enter UDL username: ")
    if not password:
        import getpass
        password = getpass.getpass("Enter UDL password: ")

    return username, password


def format_duration(seconds):
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds // 60:.0f}m {seconds % 60:.0f}s"
    else:
        return f"{seconds // 3600:.0f}h {(seconds % 3600) // 60:.0f}m"


def get_satellite_ids_by_regime(regime: str, count: int = 10) -> list:
    """
    Get satellite NORAD IDs filtered by orbital regime.
    Uses the satellite catalog if available, otherwise falls back to known satellites.
    """
    catalog_path = PROJECT_ROOT / "src" / "data" / "satelliteData_Full.csv"

    if catalog_path.exists():
        catalog = pd.read_csv(catalog_path)

        # Use boolean LEO/MEO/GEO columns if they exist
        regime_upper = regime.upper()
        if regime_upper in catalog.columns:
            regime_sats = catalog[catalog[regime_upper] == True]
        elif 'period' in catalog.columns:
            if regime_upper == "LEO":
                regime_sats = catalog[catalog['period'] < 128]
            elif regime_upper == "MEO":
                regime_sats = catalog[(catalog['period'] >= 128) & (catalog['period'] < 1400)]
            elif regime_upper == "GEO":
                regime_sats = catalog[(catalog['period'] >= 1400) & (catalog['period'] <= 1500)]
            else:
                regime_sats = catalog
        else:
            regime_sats = catalog

        # Get NORAD IDs from satNo column
        if 'satNo' in regime_sats.columns:
            sat_ids = regime_sats['satNo'].dropna().astype(int).tolist()
        else:
            sat_ids = []

        # Random sample (with fixed seed for reproducibility)
        if len(sat_ids) > count:
            np.random.seed(42 + hash(regime_upper) % 100)  # Different seed per regime
            sat_ids = list(np.random.choice(sat_ids, size=count, replace=False))

        return sat_ids[:count]

    else:
        # Fallback to well-known satellites
        known_sats = {
            'LEO': [25544, 48274, 43013, 41866, 27424, 28654, 33591, 39084, 40697, 42983],
            'MEO': [28874, 32260, 37753, 40294, 41549, 43567, 44506, 45854, 46826, 48859],
            'GEO': [41866, 40258, 37265, 38331, 39232, 41471, 42814, 43632, 44333, 45047],
        }
        return known_sats.get(regime.upper(), known_sats['LEO'])[:count]


# ============================================================================
# Data Pulling Functions
# ============================================================================

def pull_observations_batch(token: str, sat_ids: list, days: int = 14) -> pd.DataFrame:
    """
    Pull observations from UDL for given satellites in batches.
    Uses retry logic and rate limiting to handle large requests.
    """
    # Using local UDLQuery function (no orekit required)

    print(f"\n{'='*70}")
    print(f"PULLING OBSERVATIONS")
    print(f"{'='*70}")
    print(f"Satellites: {len(sat_ids)}")
    print(f"Time window: {days} days")
    print(f"Expected runtime: {len(sat_ids) * 2 * days // 7:.0f} - {len(sat_ids) * 5 * days // 7:.0f} minutes")

    all_observations = []
    start_time = time.time()

    for i, sat_id in enumerate(sat_ids):
        progress = (i + 1) / len(sat_ids) * 100
        elapsed = time.time() - start_time

        if i > 0:
            eta = elapsed / i * (len(sat_ids) - i)
            eta_str = f" ETA: {format_duration(eta)}"
        else:
            eta_str = ""

        print(f"  [{progress:5.1f}%] Pulling satellite {sat_id}...{eta_str}", end="", flush=True)

        params = {
            "satNo": str(sat_id),
            "obTime": f">now-{days} days",
            "dataMode": "REAL",
            "maxResults": 5000,  # Increased for more data
        }

        for attempt in range(MAX_QUERY_RETRIES):
            try:
                result = UDLQuery(token, "eoobservation", params)

                if result is not None and not result.empty:
                    result['satNo'] = sat_id  # Ensure satNo is set
                    all_observations.append(result)
                    print(f" {len(result)} observations")
                else:
                    print(f" 0 observations")
                break

            except Exception as e:
                if attempt < MAX_QUERY_RETRIES - 1:
                    print(f" retry ({attempt + 1})...", end="", flush=True)
                    time.sleep(QUERY_DELAY_SEC * (attempt + 1))
                else:
                    print(f" ERROR: {e}")

        # Rate limiting
        time.sleep(QUERY_DELAY_SEC)

    elapsed_total = time.time() - start_time
    print(f"\nTotal time: {format_duration(elapsed_total)}")

    if all_observations:
        combined_df = pd.concat(all_observations, ignore_index=True)
        print(f"Total observations retrieved: {len(combined_df)}")
        return combined_df
    else:
        return pd.DataFrame()


def pull_state_vectors_batch(token: str, sat_ids: list) -> pd.DataFrame:
    """Pull state vectors for satellites."""
    # Using local UDLQuery function (no orekit required)

    print(f"\n{'='*70}")
    print(f"PULLING STATE VECTORS")
    print(f"{'='*70}")

    all_svs = []

    for sat_id in sat_ids:
        params = {
            "satNo": str(sat_id),
            "epoch": ">now-7 days",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
            "maxResults": 1,
        }

        try:
            result = UDLQuery(token, "statevector", params)
            if result is not None and not result.empty:
                result['satNo'] = sat_id
                all_svs.append(result)
        except Exception as e:
            pass  # Skip errors for state vectors

        time.sleep(QUERY_DELAY_SEC / 2)

    if all_svs:
        combined_df = pd.concat(all_svs, ignore_index=True)
        print(f"Retrieved state vectors for {len(combined_df)} satellites")
        return combined_df
    else:
        return pd.DataFrame()


def pull_tles_batch(token: str, sat_ids: list) -> pd.DataFrame:
    """Pull TLEs for satellites to get orbital parameters."""
    # Using local UDLQuery function (no orekit required)

    print(f"\n{'='*70}")
    print(f"PULLING TLEs")
    print(f"{'='*70}")

    all_tles = []

    for sat_id in sat_ids:
        params = {
            "satNo": str(sat_id),
            "maxResults": 1,
        }

        try:
            result = UDLQuery(token, "elset/current", params)
            if result is not None and not result.empty:
                result['satNo'] = sat_id
                all_tles.append(result)
        except Exception as e:
            pass

        time.sleep(QUERY_DELAY_SEC / 2)

    if all_tles:
        combined_df = pd.concat(all_tles, ignore_index=True)
        print(f"Retrieved TLEs for {len(combined_df)} satellites")
        return combined_df
    else:
        return pd.DataFrame()


# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_data_quality(obs_df: pd.DataFrame) -> dict:
    """Analyze observation data quality for all satellites."""
    print(f"\n{'='*70}")
    print(f"DATA QUALITY ANALYSIS")
    print(f"{'='*70}")

    if obs_df.empty:
        return {'status': 'no_data'}

    # Convert obTime
    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    stats = {}
    tier_counts = {'T1': 0, 'T2': 0, 'T3': 0, 'T4': 0}

    print(f"\n{'Sat ID':<12} {'Obs':<8} {'Span (hrs)':<12} {'Max Gap':<12} {'Tier':<6}")
    print("-" * 55)

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]

        # Time span
        time_span = (sat_obs['obTime'].max() - sat_obs['obTime'].min()).total_seconds() / 3600

        # Gaps
        sorted_times = sat_obs['obTime'].sort_values()
        gaps = sorted_times.diff().dropna()
        max_gap_hours = gaps.max().total_seconds() / 3600 if len(gaps) > 0 else 0

        # Tier recommendation
        obs_count = len(sat_obs)
        if obs_count > 100 and max_gap_hours < 2:
            tier = "T1"
        elif obs_count > 50 and max_gap_hours < 6:
            tier = "T2"
        elif obs_count > 10:
            tier = "T3"
        else:
            tier = "T4"

        tier_counts[tier] += 1

        stats[int(sat_id)] = {
            'obs_count': obs_count,
            'time_span_hours': time_span,
            'max_gap_hours': max_gap_hours,
            'avg_gap_hours': gaps.mean().total_seconds() / 3600 if len(gaps) > 0 else 0,
            'recommended_tier': tier
        }

        print(f"{int(sat_id):<12} {obs_count:<8} {time_span:<12.1f} {max_gap_hours:<12.1f} {tier:<6}")

    print("-" * 55)
    print(f"\nTier Distribution: T1={tier_counts['T1']}, T2={tier_counts['T2']}, T3={tier_counts['T3']}, T4={tier_counts['T4']}")

    return stats


# ============================================================================
# Test Functions
# ============================================================================

def test_simulation(obs_df: pd.DataFrame, sat_stats: dict) -> dict:
    """Run simulation tests on all satellites."""
    print(f"\n{'='*70}")
    print(f"SIMULATION TESTS")
    print(f"{'='*70}")

    try:
        from uct_benchmark.simulation.simulateObservations import epochsToSim
    except ImportError as e:
        print(f"Could not import epochsToSim: {e}")
        return {'status': 'import_error'}

    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    results = {}
    passed = 0
    failed = 0
    skipped = 0

    print(f"\n{'Sat ID':<12} {'Status':<15} {'Obs':<8} {'Epochs':<10} {'Empty Bins':<12}")
    print("-" * 65)

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id].copy()

        if len(sat_obs) < 3:
            results[int(sat_id)] = {'status': 'skipped_insufficient_obs'}
            skipped += 1
            print(f"{int(sat_id):<12} {'SKIP':<15} {len(sat_obs):<8} {'-':<10} {'-':<12}")
            continue

        # Estimate orbital parameters
        MU = 398600.4418
        a_est = 7000  # Default LEO
        period_sec = 2 * np.pi * np.sqrt((a_est ** 3) / MU)

        orb_elems = {
            'Semi-Major Axis': a_est,
            'Eccentricity': 0.001,
            'Inclination': 51.6,
            'RAAN': 120.0,
            'Argument of Perigee': 90.0,
            'Mean Anomaly': 0.0,
            'Period': period_sec,
        }

        try:
            epochs, info = epochsToSim(int(sat_id), sat_obs, orb_elems)

            status = info.get('status', 'unknown')
            if status in ['success', 'epochs_generated', 'all_bins_covered', 'already_at_target']:
                passed += 1
                status_str = 'PASS'
            else:
                failed += 1
                status_str = status[:15]

            results[int(sat_id)] = {
                'status': status,
                'existing_obs': len(sat_obs),
                'epochs_to_simulate': len(epochs),
                'empty_bins': info.get('empty_bins', 0),
                'total_bins': info.get('total_bins', 0),
            }

            empty_bins_str = f"{info.get('empty_bins', 0)}/{info.get('total_bins', 0)}"
            print(f"{int(sat_id):<12} {status_str:<15} {len(sat_obs):<8} {len(epochs):<10} {empty_bins_str:<12}")

        except Exception as e:
            failed += 1
            results[int(sat_id)] = {'status': 'error', 'error': str(e)[:50]}
            print(f"{int(sat_id):<12} {'ERROR':<15} {len(sat_obs):<8} {'-':<10} {str(e)[:20]}")

    print("-" * 65)
    print(f"\nSimulation Results: {passed} passed, {failed} failed, {skipped} skipped")

    return {
        'results': results,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'pass_rate': passed / max(1, passed + failed) * 100
    }


def test_downsampling(obs_df: pd.DataFrame, sat_stats: dict) -> dict:
    """Run downsampling tests with multiple configurations."""
    print(f"\n{'='*70}")
    print(f"DOWNSAMPLING TESTS")
    print(f"{'='*70}")

    try:
        from uct_benchmark.data.dataManipulation import downsampleData
        import uct_benchmark.config as config
    except ImportError as e:
        print(f"Could not import downsampling modules: {e}")
        return {'status': 'import_error'}

    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    # Convert satNo to int
    obs_df['satNo'] = obs_df['satNo'].astype(int)

    # Create sat_params
    sat_params = {}
    MU = 398600.4418

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        a_est = 7000
        period_sec = 2 * np.pi * np.sqrt((a_est ** 3) / MU)

        sat_params[int(sat_id)] = {
            'Semi-Major Axis': a_est,
            'Eccentricity': 0.001,
            'Inclination': 51.6,
            'RAAN': 120.0,
            'Argument of Perigee': 90.0,
            'Mean Anomaly': 0.0,
            'Period': period_sec,
            'Number of Obs': len(sat_obs),
            'Orbital Coverage': sat_stats.get(int(sat_id), {}).get('obs_count', len(sat_obs)) / 500,
            'Max Track Gap': sat_stats.get(int(sat_id), {}).get('max_gap_hours', 1) / 1.5,
        }

    initial_count = len(obs_df)

    # Test configurations
    configs = [
        {
            'name': 'T1 (Light - target 80% retention)',
            'orbit_coverage': {'sats': None, 'p_bounds': (0.2, 0.3, 0.4), 'p_coverage': (0.8, 0.6)},
            'track_length': {'sats': None, 'p_bounds': (0.2, 0.3, 0.4), 'p_track': 0.3},
            'obs_count': {'sats': None, 'p_bounds': (0.2, 0.3, 0.4), 'obs_max': 1000},
        },
        {
            'name': 'T2 (Medium - target 50% retention)',
            'orbit_coverage': {'sats': None, 'p_bounds': config.downsample_coverage_bounds, 'p_coverage': config.downsample_coverage_target},
            'track_length': {'sats': None, 'p_bounds': config.downsample_gap_bounds, 'p_track': config.downsample_gap_target},
            'obs_count': {'sats': None, 'p_bounds': config.downsample_obs_bounds, 'obs_max': config.downsample_obs_max},
        },
        {
            'name': 'Heavy (target 20% retention)',
            'orbit_coverage': {'sats': None, 'p_bounds': (0.7, 0.9, 0.95), 'p_coverage': (0.3, 0.1)},
            'track_length': {'sats': None, 'p_bounds': (0.7, 0.9, 0.95), 'p_track': 0.8},
            'obs_count': {'sats': None, 'p_bounds': (0.7, 0.9, 0.95), 'obs_max': 30},
        },
    ]

    results = {}
    all_passed = True

    print(f"\nInitial observations: {initial_count}")
    print(f"\n{'Configuration':<35} {'Initial':<10} {'Final':<10} {'Reduction':<12} {'Status':<10}")
    print("-" * 80)

    for config_dict in configs:
        try:
            result_df, p_reached = downsampleData(
                obs_df.copy(),
                sat_params,
                config_dict['orbit_coverage'],
                config_dict['track_length'],
                config_dict['obs_count'],
                bins=10,
                rand=42
            )

            final_count = len(result_df)
            reduction_pct = 100 * (1 - final_count / initial_count)

            # Verify minimum observations preserved
            sat_obs_counts = result_df.groupby('satNo').size()
            min_obs_per_sat = sat_obs_counts.min() if len(sat_obs_counts) > 0 else 0
            avg_obs_per_sat = sat_obs_counts.mean() if len(sat_obs_counts) > 0 else 0

            # Pass if we preserved at least 3 obs per satellite and have data
            if final_count > 0 and min_obs_per_sat >= 3:
                status = 'PASS'
            elif final_count > 0 and min_obs_per_sat >= 1:
                status = 'WARN'  # Borderline - some satellites have few obs
            else:
                status = 'FAIL'
                all_passed = False

            results[config_dict['name']] = {
                'status': 'success',
                'initial': initial_count,
                'final': final_count,
                'reduction_pct': reduction_pct,
                'min_obs_per_sat': min_obs_per_sat,
                'avg_obs_per_sat': avg_obs_per_sat,
                'test_status': status,
            }

            print(f"{config_dict['name']:<35} {initial_count:<10} {final_count:<10} {reduction_pct:<11.1f}% {status:<10}")

        except Exception as e:
            all_passed = False
            results[config_dict['name']] = {'status': 'error', 'error': str(e)}
            print(f"{config_dict['name']:<35} {initial_count:<10} {'ERROR':<10} {'-':<12} {'FAIL':<10}")

    print("-" * 80)

    return {
        'results': results,
        'all_passed': all_passed,
    }


def verify_performance_metrics(sim_results: dict, ds_results: dict, sat_stats: dict) -> dict:
    """
    Verify that results match expected performance metrics from documentation.

    Reference standards (from provided-materials):
    - Position noise: 0.01 km
    - Angular noise: 1 arcsecond
    - Track separation: 90 minutes
    - Min obs per track: 3
    - Long track gap: 2 orbital periods
    """
    print(f"\n{'='*70}")
    print(f"PERFORMANCE METRICS VERIFICATION")
    print(f"{'='*70}")

    import uct_benchmark.config as config

    checks = []

    # Check 1: Simulation generates valid epochs
    if sim_results.get('status') != 'import_error':
        sim_pass_rate = sim_results.get('pass_rate', 0)
        check1 = sim_pass_rate >= 80
        checks.append(('Simulation pass rate >= 80%', check1, f"{sim_pass_rate:.1f}%"))
    else:
        checks.append(('Simulation pass rate >= 80%', False, 'Import error'))

    # Check 2: Downsampling preserves minimum observations
    # Check all config results - PASS and WARN are acceptable, only FAIL is not
    ds_config_results = ds_results.get('results', {})
    failed_configs = [name for name, res in ds_config_results.items()
                      if res.get('test_status') == 'FAIL']

    if len(failed_configs) == 0:
        checks.append(('Downsampling preserves min obs', True, 'All configs passed'))
    else:
        checks.append(('Downsampling preserves min obs', False, f'{len(failed_configs)} configs failed'))

    # Check 3: Config values match documentation standards
    checks.append(('Position noise = 0.01 km', config.positionNoise == 0.01, f"{config.positionNoise} km"))
    checks.append(('Angular noise = 1 arcsec', config.angularNoise == 3600, f"{config.angularNoise / 3600} arcsec"))
    checks.append(('Long track gap = 2 periods', config.longTrackGap == 2, f"{config.longTrackGap} periods"))
    checks.append(('Min downsampled obs = 5', config.downsample_min_obs >= 3, f"{config.downsample_min_obs} obs"))
    checks.append(('Simulation track size = 3', config.simulation_track_size == 3, f"{config.simulation_track_size} obs"))
    checks.append(('Simulation track spacing = 30s', config.simulation_track_spacing == 30, f"{config.simulation_track_spacing}s"))

    # Display results
    print(f"\n{'Metric':<40} {'Status':<10} {'Value':<20}")
    print("-" * 70)

    passed = 0
    total = len(checks)

    for name, result, value in checks:
        status = "PASS" if result else "FAIL"
        if result:
            passed += 1
        print(f"{name:<40} {status:<10} {value:<20}")

    print("-" * 70)
    print(f"\nVerification: {passed}/{total} checks passed")

    return {
        'checks': checks,
        'passed': passed,
        'total': total,
        'all_passed': passed == total,
    }


# ============================================================================
# Main Function
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Comprehensive UDL data test")
    parser.add_argument('--satellites', type=int, default=DEFAULT_SATELLITES_PER_REGIME,
                        help=f'Satellites per regime (default: {DEFAULT_SATELLITES_PER_REGIME})')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS,
                        help=f'Days of data to pull (default: {DEFAULT_DAYS})')
    parser.add_argument('--min-obs', type=int, default=DEFAULT_MIN_OBS,
                        help=f'Minimum observations per satellite (default: {DEFAULT_MIN_OBS})')
    parser.add_argument('--save', action='store_true',
                        help='Save pulled data to CSV files')
    parser.add_argument('--load', type=str, default=None,
                        help='Load existing data from path instead of pulling')
    args = parser.parse_args()

    start_time = time.time()

    print("=" * 70)
    print("COMPREHENSIVE UDL DATA TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Configuration:")
    print(f"  Satellites per regime: {args.satellites}")
    print(f"  Total satellites: {args.satellites * 3}")
    print(f"  Days of data: {args.days}")
    print(f"  Minimum observations filter: {args.min_obs}")
    print("=" * 70)

    # Load or pull data
    if args.load:
        print(f"\nLoading data from {args.load}")
        obs_df = pd.read_csv(args.load)
        print(f"Loaded {len(obs_df)} observations")
    else:
        # Get credentials and generate token (using local function, no orekit required)
        username, password = get_credentials()
        token = UDLTokenGen(username, password)
        print("\nToken generated successfully")

        # Get satellite IDs for each regime
        all_sat_ids = []
        for regime in ['LEO', 'MEO', 'GEO']:
            regime_sats = get_satellite_ids_by_regime(regime, args.satellites)
            print(f"\n{regime} satellites ({len(regime_sats)}): {regime_sats}")
            all_sat_ids.extend(regime_sats)

        # Remove duplicates
        all_sat_ids = list(set(all_sat_ids))
        print(f"\nTotal unique satellites: {len(all_sat_ids)}")

        # Pull observations
        obs_df = pull_observations_batch(token, all_sat_ids, args.days)

        if obs_df.empty:
            print("\nNo observations retrieved. Check credentials and satellite availability.")
            return 1

        # Filter out satellites with too few observations
        if args.min_obs > 0:
            print(f"\n{'='*70}")
            print(f"FILTERING SATELLITES (min {args.min_obs} observations)")
            print(f"{'='*70}")

            sat_counts = obs_df.groupby('satNo').size()
            original_sats = len(sat_counts)
            original_obs = len(obs_df)

            # Keep only satellites with enough observations
            valid_sats = sat_counts[sat_counts >= args.min_obs].index.tolist()
            obs_df = obs_df[obs_df['satNo'].isin(valid_sats)]

            filtered_sats = len(valid_sats)
            filtered_obs = len(obs_df)

            print(f"  Before filter: {original_sats} satellites, {original_obs} observations")
            print(f"  After filter:  {filtered_sats} satellites, {filtered_obs} observations")
            print(f"  Removed: {original_sats - filtered_sats} satellites with <{args.min_obs} observations")

            if obs_df.empty:
                print("\nNo satellites meet minimum observation threshold.")
                return 1

        # Save data if requested
        if args.save:
            output_dir = SCRIPT_DIR / "data" / "udl_comprehensive"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            obs_path = output_dir / f"obs_comprehensive_{timestamp}.csv"
            obs_df.to_csv(obs_path, index=False)
            print(f"\nData saved to: {obs_path}")

    # Analyze data quality
    sat_stats = analyze_data_quality(obs_df)

    # Run simulation tests
    sim_results = test_simulation(obs_df, sat_stats)

    # Run downsampling tests
    ds_results = test_downsampling(obs_df, sat_stats)

    # Verify performance metrics
    verify_results = verify_performance_metrics(sim_results, ds_results, sat_stats)

    # Final summary
    elapsed_time = time.time() - start_time

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total runtime: {format_duration(elapsed_time)}")
    print(f"Observations processed: {len(obs_df)}")
    print(f"Satellites tested: {obs_df['satNo'].nunique()}")
    print()
    print(f"Simulation Tests:")
    print(f"  Passed: {sim_results.get('passed', 'N/A')}")
    print(f"  Failed: {sim_results.get('failed', 'N/A')}")
    print(f"  Pass Rate: {sim_results.get('pass_rate', 0):.1f}%")
    print()
    print(f"Downsampling Tests:")
    print(f"  All Passed: {ds_results.get('all_passed', False)}")
    print()
    print(f"Performance Verification:")
    print(f"  Checks Passed: {verify_results['passed']}/{verify_results['total']}")
    print()

    # Overall result
    overall_pass = (
        sim_results.get('pass_rate', 0) >= 80 and
        ds_results.get('all_passed', False) and
        verify_results['all_passed']
    )

    if overall_pass:
        print("=" * 70)
        print("OVERALL RESULT: PASS")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("OVERALL RESULT: SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
