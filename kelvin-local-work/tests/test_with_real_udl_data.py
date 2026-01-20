#!/usr/bin/env python3
"""
Test Simulation and Downsampling with Real UDL Data
====================================================
Uses the saved UDL observation data to validate the simulation and
downsampling algorithms with real-world observation patterns.

Usage:
    python tests/test_with_real_udl_data.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def find_latest_udl_data():
    """Find the most recent UDL test data file."""
    data_dir = SCRIPT_DIR / "data" / "udl_test_data"
    if not data_dir.exists():
        return None

    csv_files = list(data_dir.glob("obs_*.csv"))
    if not csv_files:
        return None

    # Return most recent
    return max(csv_files, key=lambda f: f.stat().st_mtime)


def test_simulation_with_real_data(obs_df: pd.DataFrame):
    """Test epochsToSim with real UDL observation data."""
    print("\n" + "=" * 70)
    print("TESTING SIMULATION (epochsToSim) WITH REAL DATA")
    print("=" * 70)

    # Import the actual simulation function
    try:
        from uct_benchmark.simulation.simulateObservations import epochsToSim
    except ImportError as e:
        print(f"Could not import epochsToSim: {e}")
        print("Running simplified simulation test instead...")
        return test_simulation_simplified(obs_df)

    results = {}

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id].copy()

        # Create orbital elements (estimate for LEO)
        MU = 398600.4418
        a_est = 7000  # LEO altitude estimate
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

            results[sat_id] = {
                'status': info.get('status', 'unknown'),
                'existing_obs': len(sat_obs),
                'epochs_generated': len(epochs),
                'empty_bins': info.get('empty_bins', 0),
                'total_bins': info.get('total_bins', 0),
            }

            print(f"\nSatellite {int(sat_id)}:")
            print(f"  Status: {info.get('status', 'unknown')}")
            print(f"  Existing observations: {len(sat_obs)}")
            print(f"  Empty bins: {info.get('empty_bins', 0)}/{info.get('total_bins', 0)}")
            print(f"  Epochs to simulate: {len(epochs)}")

            if epochs:
                print(f"  First epoch: {epochs[0]}")
                print(f"  Last epoch: {epochs[-1]}")

        except Exception as e:
            print(f"\nSatellite {int(sat_id)}: ERROR - {e}")
            results[sat_id] = {'status': 'error', 'error': str(e)}

    return results


def test_simulation_simplified(obs_df: pd.DataFrame):
    """Simplified simulation test without orekit."""
    print("\nRunning simplified simulation analysis...")

    results = {}
    obs_df = obs_df.copy()
    obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id].sort_values('obTime')

        # Estimate orbital period (LEO ~90 min)
        period_sec = 5400

        # Time window
        start_time = sat_obs['obTime'].min()
        end_time = sat_obs['obTime'].max()
        window_sec = (end_time - start_time).total_seconds()

        # Calculate bins
        bins_per_period = 10
        bin_size_sec = period_sec / bins_per_period
        total_bins = int(np.ceil(window_sec / bin_size_sec))

        # Count observations per bin
        bin_counts = np.zeros(max(1, total_bins), dtype=int)
        for obs_time in sat_obs['obTime']:
            bin_idx = int((obs_time - start_time).total_seconds() / bin_size_sec)
            if 0 <= bin_idx < len(bin_counts):
                bin_counts[bin_idx] += 1

        empty_bins = np.sum(bin_counts == 0)

        results[sat_id] = {
            'status': 'success',
            'existing_obs': len(sat_obs),
            'total_bins': total_bins,
            'empty_bins': int(empty_bins),
            'coverage_pct': round(100 * (total_bins - empty_bins) / max(1, total_bins), 1),
        }

        print(f"\nSatellite {int(sat_id)}:")
        print(f"  Observations: {len(sat_obs)}")
        print(f"  Coverage: {results[sat_id]['coverage_pct']}%")
        print(f"  Empty bins: {empty_bins}/{total_bins}")

    return results


def test_downsampling_with_real_data(obs_df: pd.DataFrame):
    """Test downsampleData with real UDL observation data."""
    print("\n" + "=" * 70)
    print("TESTING DOWNSAMPLING WITH REAL DATA")
    print("=" * 70)

    # Import the actual downsampling function
    try:
        from uct_benchmark.data.dataManipulation import downsampleData
    except ImportError as e:
        print(f"Could not import downsampleData: {e}")
        print("Skipping downsampling test.")
        return None

    # Prepare data
    obs_df = obs_df.copy()
    obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    # Create sat_params for all satellites
    sat_params = {}
    MU = 398600.4418
    a_est = 7000
    period_sec = 2 * np.pi * np.sqrt((a_est ** 3) / MU)

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        sat_params[int(sat_id)] = {
            'Semi-Major Axis': a_est,
            'Eccentricity': 0.001,
            'Inclination': 51.6,
            'RAAN': 120.0,
            'Argument of Perigee': 90.0,
            'Mean Anomaly': 0.0,
            'Period': period_sec,
            'Number of Obs': len(sat_obs),
            'Orbital Coverage': 0.5,
            'Max Track Gap': 0.3,
        }

    # Convert satNo to int
    obs_df['satNo'] = obs_df['satNo'].astype(int)

    initial_count = len(obs_df)
    initial_per_sat = obs_df.groupby('satNo').size().to_dict()

    print(f"\nInitial data: {initial_count} observations")
    print(f"Per satellite: {initial_per_sat}")

    # Test different downsampling configurations
    configs = [
        {
            'name': 'Light downsampling (reduce to ~500 per sat)',
            'orbit_coverage': {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_coverage': (0.7, 0.5)},
            'track_length': {'sats': None, 'p_bounds': (0.3, 0.5, 0.4), 'p_track': 0.3},
            'obs_count': {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'obs_max': 500},
        },
        {
            'name': 'Heavy downsampling (reduce to ~100 per sat)',
            'orbit_coverage': {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'p_coverage': (0.5, 0.3)},
            'track_length': {'sats': None, 'p_bounds': (0.5, 0.9, 0.7), 'p_track': 0.5},
            'obs_count': {'sats': None, 'p_bounds': (0.7, 1.0, 0.9), 'obs_max': 100},
        },
    ]

    results = {}

    for config in configs:
        print(f"\n--- {config['name']} ---")

        try:
            result_df, p_reached = downsampleData(
                obs_df.copy(),
                sat_params,
                config['orbit_coverage'],
                config['track_length'],
                config['obs_count'],
            )

            final_count = len(result_df)
            final_per_sat = result_df.groupby('satNo').size().to_dict()

            print(f"  Result: {initial_count} -> {final_count} observations ({100*final_count/initial_count:.1f}%)")
            print(f"  Per satellite: {final_per_sat}")
            print(f"  Metrics reached: {p_reached}")

            results[config['name']] = {
                'status': 'success',
                'initial': initial_count,
                'final': final_count,
                'reduction_pct': round(100 * (1 - final_count/initial_count), 1),
                'per_sat': final_per_sat,
            }

        except Exception as e:
            print(f"  ERROR: {e}")
            results[config['name']] = {'status': 'error', 'error': str(e)}

    return results


def main():
    print("=" * 70)
    print("TESTING WITH REAL UDL DATA")
    print("=" * 70)

    # Find the latest UDL data file
    data_file = find_latest_udl_data()

    if data_file is None:
        print("\nNo UDL test data found!")
        print("Run pull_udl_simple.py first to download data.")
        return

    print(f"\nUsing data file: {data_file}")

    # Load data
    obs_df = pd.read_csv(data_file)
    print(f"Loaded {len(obs_df)} observations for {obs_df['satNo'].nunique()} satellites")

    # Run simulation test
    sim_results = test_simulation_with_real_data(obs_df)

    # Run downsampling test
    ds_results = test_downsampling_with_real_data(obs_df)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nSimulation Results:")
    for sat_id, result in sim_results.items():
        status = result.get('status', 'unknown')
        if status == 'success':
            print(f"  Satellite {int(sat_id)}: {result.get('epochs_generated', result.get('empty_bins', 'N/A'))} epochs/empty bins")
        else:
            print(f"  Satellite {int(sat_id)}: {status}")

    if ds_results:
        print("\nDownsampling Results:")
        for name, result in ds_results.items():
            if result.get('status') == 'success':
                print(f"  {name}: {result['initial']} -> {result['final']} ({result['reduction_pct']}% reduction)")
            else:
                print(f"  {name}: {result.get('status', 'unknown')}")

    print("\nDone!")


if __name__ == "__main__":
    main()
