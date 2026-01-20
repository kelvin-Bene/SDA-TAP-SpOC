#!/usr/bin/env python3
"""
UDL Test Data Pull Script
=========================
Pull real observation data from UDL to test simulation and downsampling
with real-world observation patterns.

Prerequisites:
    - UDL account credentials
    - Network access to UDL

Usage:
    # Set credentials as environment variables or pass directly
    export UDL_USERNAME="your_username"
    export UDL_PASSWORD="your_password"

    # Run the script
    python pull_udl_test_data.py

    # Or with arguments
    python pull_udl_test_data.py --regime LEO --satellites 5 --days 7

Author: SDA TAP Lab
Date: 2026-01-18
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


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


def get_satellite_ids_by_regime(regime: str, count: int = 10) -> list:
    """
    Get a list of satellite NORAD IDs for testing, filtered by orbital regime.

    Uses the satelliteData_Full.csv catalog to find suitable satellites.
    """
    catalog_path = PROJECT_ROOT / "src" / "data" / "satelliteData_Full.csv"

    if catalog_path.exists():
        catalog = pd.read_csv(catalog_path)

        # Filter by regime
        if regime.upper() == "LEO":
            # LEO: Period < 128 minutes (roughly)
            if 'PERIOD' in catalog.columns:
                regime_sats = catalog[catalog['PERIOD'] < 128]
            elif 'APOGEE' in catalog.columns:
                regime_sats = catalog[catalog['APOGEE'] < 2000]
            else:
                # Fallback: use common LEO satellites
                regime_sats = catalog[catalog['NORAD_CAT_ID'].isin([25544, 48274, 43013])]

        elif regime.upper() == "MEO":
            # MEO: Period 128-1440 minutes
            if 'PERIOD' in catalog.columns:
                regime_sats = catalog[(catalog['PERIOD'] >= 128) & (catalog['PERIOD'] < 1440)]
            elif 'APOGEE' in catalog.columns:
                regime_sats = catalog[(catalog['APOGEE'] >= 2000) & (catalog['APOGEE'] < 35000)]
            else:
                regime_sats = catalog.head(count)

        elif regime.upper() == "GEO":
            # GEO: Period ~1440 minutes
            if 'PERIOD' in catalog.columns:
                regime_sats = catalog[(catalog['PERIOD'] >= 1400) & (catalog['PERIOD'] <= 1480)]
            elif 'APOGEE' in catalog.columns:
                regime_sats = catalog[(catalog['APOGEE'] >= 35000) & (catalog['APOGEE'] <= 36500)]
            else:
                regime_sats = catalog.head(count)

        else:
            regime_sats = catalog

        # Get NORAD IDs
        if 'NORAD_CAT_ID' in regime_sats.columns:
            sat_ids = regime_sats['NORAD_CAT_ID'].dropna().astype(int).tolist()
        elif 'satNo' in regime_sats.columns:
            sat_ids = regime_sats['satNo'].dropna().astype(int).tolist()
        else:
            sat_ids = []

        # Take random sample
        if len(sat_ids) > count:
            np.random.seed(42)  # Reproducible
            sat_ids = list(np.random.choice(sat_ids, size=count, replace=False))

        return sat_ids[:count]

    else:
        # Fallback to well-known satellites
        known_sats = {
            'LEO': [25544, 48274, 43013, 41866, 27424],  # ISS, Starlink, etc.
            'MEO': [28874, 32260, 37753],  # GPS satellites
            'GEO': [41866, 40258, 37265],  # GEO comms sats
        }
        return known_sats.get(regime.upper(), known_sats['LEO'])[:count]


def pull_observations(token: str, sat_ids: list, days: int = 7) -> pd.DataFrame:
    """Pull observations from UDL for given satellites."""
    from uct_benchmark.api.apiIntegration import asyncUDLBatchQuery

    print(f"\nPulling observations for {len(sat_ids)} satellites over {days} days...")

    # Build query parameters
    params_list = [
        {
            "satNo": str(sat_id),
            "obTime": f">now-{days} days",
            "dataMode": "REAL",
            "maxResults": 1000,
        }
        for sat_id in sat_ids
    ]

    try:
        obs_data = asyncUDLBatchQuery(token, "eoobservation", params_list, dt=0.2)
        print(f"Retrieved {len(obs_data)} observations")
        return obs_data
    except Exception as e:
        print(f"Error pulling observations: {e}")
        return pd.DataFrame()


def pull_state_vectors(token: str, sat_ids: list, days: int = 7) -> pd.DataFrame:
    """Pull state vectors from UDL for given satellites."""
    from uct_benchmark.api.apiIntegration import asyncUDLBatchQuery

    print(f"\nPulling state vectors for {len(sat_ids)} satellites...")

    params_list = [
        {
            "satNo": str(sat_id),
            "epoch": f">now-{days} days",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
            "maxResults": 1,
        }
        for sat_id in sat_ids
    ]

    try:
        sv_data = asyncUDLBatchQuery(token, "statevector", params_list, dt=0.2)
        print(f"Retrieved {len(sv_data)} state vectors")
        return sv_data
    except Exception as e:
        print(f"Error pulling state vectors: {e}")
        return pd.DataFrame()


def analyze_data_quality(obs_df: pd.DataFrame) -> dict:
    """Analyze observation data quality to determine tier suitability."""
    if obs_df.empty:
        return {'status': 'no_data'}

    # Convert obTime to datetime
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    stats = {}

    # Per-satellite statistics
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]

        # Time span
        time_span = (sat_obs['obTime'].max() - sat_obs['obTime'].min()).total_seconds() / 3600

        # Calculate gaps
        sorted_times = sat_obs['obTime'].sort_values()
        gaps = sorted_times.diff().dropna()
        max_gap_hours = gaps.max().total_seconds() / 3600 if len(gaps) > 0 else 0

        # Determine tier recommendation
        obs_count = len(sat_obs)
        if obs_count > 100 and max_gap_hours < 2:
            tier = "T1"  # High quality, may need downsampling
        elif obs_count > 50 and max_gap_hours < 6:
            tier = "T2"  # Medium quality, needs downsampling
        elif obs_count > 10:
            tier = "T3"  # Low quality, needs simulation
        else:
            tier = "T4"  # Very low, needs object simulation

        stats[sat_id] = {
            'obs_count': obs_count,
            'time_span_hours': time_span,
            'max_gap_hours': max_gap_hours,
            'avg_gap_hours': gaps.mean().total_seconds() / 3600 if len(gaps) > 0 else 0,
            'recommended_tier': tier
        }

    return stats


def test_simulation_with_data(obs_df: pd.DataFrame, sv_df: pd.DataFrame) -> dict:
    """Test simulation with pulled data."""
    from uct_benchmark.simulation.simulateObservations import epochsToSim
    from uct_benchmark.api.apiIntegration import parseTLE

    results = {}

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id].copy()

        if len(sat_obs) < 5:
            results[sat_id] = {'status': 'insufficient_obs', 'count': len(sat_obs)}
            continue

        # Create orbital elements (simplified - use TLE if available)
        # For now, estimate from observation spread
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
            epochs, info = epochsToSim(sat_id, sat_obs, orb_elems)
            results[sat_id] = {
                'status': info.get('status', 'unknown'),
                'existing_obs': len(sat_obs),
                'epochs_to_simulate': len(epochs),
                'empty_bins': info.get('empty_bins', 0),
                'total_bins': info.get('total_bins', 0),
            }
        except Exception as e:
            results[sat_id] = {'status': 'error', 'error': str(e)}

    return results


def test_downsampling_with_data(obs_df: pd.DataFrame) -> dict:
    """Test downsampling with pulled data."""
    from uct_benchmark.data.dataManipulation import downsampleData

    # Convert obTime to datetime
    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    # Create sat_params
    sat_params = {}
    MU = 398600.4418
    a_est = 7000
    period_sec = 2 * np.pi * np.sqrt((a_est ** 3) / MU)

    for sat_id in obs_df['satNo'].unique():
        sat_params[sat_id] = {
            'Semi-Major Axis': a_est,
            'Eccentricity': 0.001,
            'Inclination': 51.6,
            'RAAN': 120.0,
            'Argument of Perigee': 90.0,
            'Mean Anomaly': 0.0,
            'Period': period_sec,
        }

    # Downsampling parameters
    orbit_coverage = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.5, 0.3)}
    track_length = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.5}
    obs_count = {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'obs_max': 100}

    try:
        result, p_reached = downsampleData(
            obs_df, sat_params, orbit_coverage, track_length, obs_count
        )

        return {
            'status': 'success',
            'initial_count': len(obs_df),
            'final_count': len(result),
            'reduction_pct': 100 * (1 - len(result) / len(obs_df)),
            'p_reached': p_reached
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description="Pull UDL data for testing")
    parser.add_argument('--regime', default='LEO', choices=['LEO', 'MEO', 'GEO'],
                        help='Orbital regime to test')
    parser.add_argument('--satellites', type=int, default=5,
                        help='Number of satellites to pull')
    parser.add_argument('--days', type=int, default=7,
                        help='Days of historical data to pull')
    parser.add_argument('--save', action='store_true',
                        help='Save pulled data to CSV files')
    args = parser.parse_args()

    print("=" * 70)
    print("UDL TEST DATA PULL")
    print("=" * 70)
    print(f"Regime: {args.regime}")
    print(f"Satellites: {args.satellites}")
    print(f"Days: {args.days}")
    print("=" * 70)

    # Get credentials and generate token
    from uct_benchmark.api.apiIntegration import UDLTokenGen

    username, password = get_credentials()
    token = UDLTokenGen(username, password)
    print("\nToken generated successfully")

    # Get satellite IDs
    sat_ids = get_satellite_ids_by_regime(args.regime, args.satellites)
    print(f"\nSelected satellites: {sat_ids}")

    # Pull observations
    obs_df = pull_observations(token, sat_ids, args.days)

    if obs_df.empty:
        print("\nNo observations retrieved. Check credentials and satellite availability.")
        return

    # Pull state vectors
    sv_df = pull_state_vectors(token, sat_ids, args.days)

    # Analyze data quality
    print("\n" + "=" * 70)
    print("DATA QUALITY ANALYSIS")
    print("=" * 70)

    quality_stats = analyze_data_quality(obs_df)
    for sat_id, stats in quality_stats.items():
        if isinstance(stats, dict) and 'obs_count' in stats:
            print(f"\nSatellite {sat_id}:")
            print(f"  Observations: {stats['obs_count']}")
            print(f"  Time span: {stats['time_span_hours']:.1f} hours")
            print(f"  Max gap: {stats['max_gap_hours']:.1f} hours")
            print(f"  Recommended tier: {stats['recommended_tier']}")

    # Test simulation
    print("\n" + "=" * 70)
    print("SIMULATION TEST")
    print("=" * 70)

    sim_results = test_simulation_with_data(obs_df, sv_df)
    for sat_id, result in sim_results.items():
        print(f"\nSatellite {sat_id}: {result.get('status', 'unknown')}")
        if result.get('status') == 'success':
            print(f"  Existing obs: {result.get('existing_obs', 0)}")
            print(f"  Epochs to simulate: {result.get('epochs_to_simulate', 0)}")
            print(f"  Empty bins: {result.get('empty_bins', 0)}/{result.get('total_bins', 0)}")

    # Test downsampling
    print("\n" + "=" * 70)
    print("DOWNSAMPLING TEST")
    print("=" * 70)

    ds_result = test_downsampling_with_data(obs_df)
    print(f"\nStatus: {ds_result.get('status', 'unknown')}")
    if ds_result.get('status') == 'success':
        print(f"Initial observations: {ds_result.get('initial_count', 0)}")
        print(f"Final observations: {ds_result.get('final_count', 0)}")
        print(f"Reduction: {ds_result.get('reduction_pct', 0):.1f}%")

    # Save data if requested
    if args.save:
        output_dir = PROJECT_ROOT / "tests" / "data" / "udl_test_data"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        obs_path = output_dir / f"obs_{args.regime}_{timestamp}.csv"
        sv_path = output_dir / f"sv_{args.regime}_{timestamp}.csv"

        obs_df.to_csv(obs_path, index=False)
        if not sv_df.empty:
            sv_df.to_csv(sv_path, index=False)

        print(f"\nData saved to:")
        print(f"  Observations: {obs_path}")
        print(f"  State vectors: {sv_path}")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
