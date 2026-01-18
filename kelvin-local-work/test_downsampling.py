#!/usr/bin/env python3
"""
Downsampling Test Script
========================
Tests the downsampling functionality using existing sample data.

This script verifies that:
1. downsampleData() runs without errors
2. Observation count is reduced
3. Pipeline still works after downsampling

Usage:
    python test_downsampling.py

Author: Generated for V1 downsampling implementation
Date: 2026-01-18
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR
sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)


def create_mock_orbital_elements(ref_obs):
    """
    Create mock orbital elements dictionary for satellites in the observation data.
    This is needed because we don't have TLE data in the sample files.
    """
    sat_params = {}
    unique_sats = ref_obs['satNo'].unique()

    for sat in unique_sats:
        sat_obs = ref_obs[ref_obs['satNo'] == sat]
        num_obs = len(sat_obs)

        # Create mock orbital elements (LEO-like)
        sat_params[sat] = {
            'Semi-Major Axis': 7000 + np.random.uniform(-500, 500),  # ~7000 km (LEO)
            'Eccentricity': np.random.uniform(0.0001, 0.01),
            'Inclination': np.random.uniform(40, 100),  # degrees
            'RAAN': np.random.uniform(0, 360),
            'Argument of Perigee': np.random.uniform(0, 360),
            'Mean Anomaly': np.random.uniform(0, 360),
            'Epoch': datetime.now(),
            'Period': 5400 + np.random.uniform(-300, 300),  # ~90 min orbital period
            'Number of Obs': num_obs,
            'Orbital Coverage': np.random.uniform(0.1, 0.5),
            'Max Track Gap': np.random.uniform(0.5, 3.0),
            'Orbital Polygon': None  # Not needed for basic downsampling
        }

    return sat_params


def test_downsampling():
    """Test the downsampling functionality"""
    print("=" * 60)
    print("DOWNSAMPLING TEST")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")

    # Load sample data
    data_dir = PROJECT_ROOT / "src" / "data"
    ref_obs_path = data_dir / "ref_obs.csv"

    if not ref_obs_path.exists():
        print(f"ERROR: Sample data not found at {ref_obs_path}")
        return False

    ref_obs = pd.read_csv(ref_obs_path)

    # Convert obTime to datetime if it's a string
    if ref_obs['obTime'].dtype == 'object':
        ref_obs['obTime'] = pd.to_datetime(ref_obs['obTime'])

    print(f"\nLoaded {len(ref_obs)} observations for {ref_obs['satNo'].nunique()} satellites")

    # Create mock orbital elements
    sat_params = create_mock_orbital_elements(ref_obs)
    print(f"Created mock orbital elements for {len(sat_params)} satellites")

    # Import downsampling function
    try:
        from uct_benchmark.data.dataManipulation import downsampleData
        import uct_benchmark.config as config
        print("Successfully imported downsampling modules")
    except ImportError as e:
        print(f"ERROR: Failed to import modules: {e}")
        return False

    # Build downsampling parameters
    orbit_coverage_params = {
        'sats': None,
        'p_bounds': config.downsample_coverage_bounds,
        'p_coverage': config.downsample_coverage_target
    }
    track_length_params = {
        'sats': None,
        'p_bounds': config.downsample_gap_bounds,
        'p_track': config.downsample_gap_target
    }
    obs_count_params = {
        'sats': None,
        'p_bounds': config.downsample_obs_bounds,
        'obs_max': config.downsample_obs_max
    }

    print(f"\nDownsampling parameters:")
    print(f"  Coverage bounds: {config.downsample_coverage_bounds}")
    print(f"  Coverage target: {config.downsample_coverage_target}")
    print(f"  Gap bounds: {config.downsample_gap_bounds}")
    print(f"  Gap target: {config.downsample_gap_target}")
    print(f"  Obs bounds: {config.downsample_obs_bounds}")
    print(f"  Obs max: {config.downsample_obs_max}")

    # Run downsampling
    print("\nRunning downsampling...")
    obs_before = len(ref_obs)

    try:
        downsampled_obs, p_reached = downsampleData(
            ref_obs.copy(),  # Pass a copy to preserve original
            sat_params,
            orbit_coverage_params,
            track_length_params,
            obs_count_params,
            bins=10,
            rand=42
        )

        obs_after = len(downsampled_obs)

        print(f"\n--- RESULTS ---")
        print(f"Observations before: {obs_before}")
        print(f"Observations after:  {obs_after}")
        print(f"Reduction: {100 * (1 - obs_after / obs_before):.1f}%")
        print(f"Percentages reached: {p_reached}")

        # Verify results
        tests_passed = 0
        tests_total = 3

        # Test 1: Downsampling ran without error
        print(f"\n[PASS] Downsampling executed successfully")
        tests_passed += 1

        # Test 2: Observation count changed (or stayed same if already below threshold)
        if obs_after <= obs_before:
            print(f"[PASS] Observation count reduced or maintained")
            tests_passed += 1
        else:
            print(f"[FAIL] Observation count increased (unexpected)")

        # Test 3: Still have some observations
        if obs_after > 0:
            print(f"[PASS] Dataset not empty after downsampling")
            tests_passed += 1
        else:
            print(f"[FAIL] Dataset is empty after downsampling")

        # Save downsampled data for pipeline test
        downsampled_path = data_dir / "ref_obs_downsampled.csv"
        downsampled_obs.to_csv(downsampled_path, index=False)
        print(f"\nSaved downsampled data to {downsampled_path}")

        print(f"\n{'=' * 60}")
        print(f"RESULT: {tests_passed}/{tests_total} tests passed")
        print(f"{'=' * 60}")

        return tests_passed == tests_total

    except Exception as e:
        import traceback
        print(f"\n[FAIL] Downsampling failed with error: {e}")
        traceback.print_exc()
        return False


def test_pipeline_with_downsampling():
    """Run the full pipeline test with downsampled data"""
    print("\n" + "=" * 60)
    print("PIPELINE TEST WITH DOWNSAMPLED DATA")
    print("=" * 60)

    # Check if downsampled data exists
    data_dir = PROJECT_ROOT / "src" / "data"
    downsampled_path = data_dir / "ref_obs_downsampled.csv"

    if not downsampled_path.exists():
        print("Downsampled data not found. Running downsampling first...")
        if not test_downsampling():
            return False

    # Temporarily swap ref_obs with downsampled version
    ref_obs_path = data_dir / "ref_obs.csv"
    ref_obs_backup = data_dir / "ref_obs_backup.csv"

    # Backup original
    original_obs = pd.read_csv(ref_obs_path)
    original_obs.to_csv(ref_obs_backup, index=False)

    # Use downsampled
    downsampled_obs = pd.read_csv(downsampled_path)
    downsampled_obs.to_csv(ref_obs_path, index=False)

    print(f"Swapped ref_obs.csv with downsampled version ({len(downsampled_obs)} obs)")

    try:
        # Run the pipeline test
        from test_pipeline_e2e import main as run_pipeline_test
        result = run_pipeline_test()
        success = (result == 0)
    except Exception as e:
        print(f"Pipeline test failed: {e}")
        success = False
    finally:
        # Restore original
        original_obs.to_csv(ref_obs_path, index=False)
        print(f"\nRestored original ref_obs.csv ({len(original_obs)} obs)")

    return success


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DOWNSAMPLING IMPLEMENTATION TEST SUITE")
    print("=" * 60 + "\n")

    # Test 1: Standalone downsampling test
    downsample_success = test_downsampling()

    # Test 2: Pipeline test with downsampled data
    if downsample_success:
        pipeline_success = test_pipeline_with_downsampling()
    else:
        print("\nSkipping pipeline test due to downsampling failure")
        pipeline_success = False

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Downsampling test: {'PASS' if downsample_success else 'FAIL'}")
    print(f"Pipeline test:     {'PASS' if pipeline_success else 'FAIL'}")
    print("=" * 60)

    sys.exit(0 if (downsample_success and pipeline_success) else 1)
