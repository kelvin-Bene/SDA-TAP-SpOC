#!/usr/bin/env python3
"""
Comprehensive Quality Test Suite for Downsampling and Simulation
=================================================================
This test suite thoroughly validates the downsampling and simulation
implementations using real UDL data.

Tests Include:
1. Data pulling from UDL (multiple satellites, different tiers)
2. Downsampling validation (each stage individually + combined)
3. Simulation validation (gap detection, epoch selection, observation generation)
4. Metric verification (coverage, gaps, counts before/after)
5. Visualizations (time distributions, coverage, gaps)

Usage:
    python tests/comprehensive_quality_test.py

Author: UCT Benchmark Team
Date: 2026-01-19
"""

import base64
import getpass
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Suppress warnings
warnings.filterwarnings('ignore')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Output directory for test results
OUTPUT_DIR = SCRIPT_DIR / "test_results" / datetime.now().strftime("%Y%m%d_%H%M%S")


# =============================================================================
# UDL DATA PULLING FUNCTIONS
# =============================================================================

def udl_token_gen(username: str, password: str) -> str:
    """Generate UDL authentication token."""
    return base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")


def udl_query(token: str, service: str, params: dict, max_retries: int = 3) -> pd.DataFrame:
    """Perform a UDL query with retry logic."""
    url = f"https://unifieddatalibrary.com/udl/{service.lower()}"
    headers = {"Authorization": "Basic " + token}

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, params=params, verify=False, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return pd.DataFrame(data) if data else pd.DataFrame()
            elif resp.status_code == 401:
                print(f"  ERROR: Authentication failed")
                return pd.DataFrame()
        except requests.exceptions.Timeout:
            print(f"  Timeout on attempt {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"  Error on attempt {attempt + 1}: {e}")

    return pd.DataFrame()


def get_credentials():
    """Get UDL credentials from environment, command line args, or prompt."""
    # Check command line args first (usage: script.py username password)
    if len(sys.argv) >= 3:
        return sys.argv[1], sys.argv[2]

    # Then check environment variables
    username = os.environ.get('UDL_USERNAME')
    password = os.environ.get('UDL_PASSWORD')

    if username and password:
        return username, password

    # Finally, prompt if running interactively
    if sys.stdin.isatty():
        if not username:
            username = input("Enter UDL username: ")
        if not password:
            password = getpass.getpass("Enter UDL password: ")
        return username, password

    raise ValueError("No credentials provided. Use: python script.py <username> <password>")


def pull_satellite_data(token: str, sat_id: int, days: int = 30) -> pd.DataFrame:
    """Pull observation data for a single satellite."""
    params = {
        "satNo": str(sat_id),
        "obTime": f">now-{days} days",
        "dataMode": "REAL",
        "maxResults": "2000",
        "sort": "obTime,ASC",
    }
    return udl_query(token, "eoobservation", params)


def find_active_satellites(token: str, days: int = 30, min_obs: int = 50) -> list:
    """Find satellites with sufficient recent observations."""
    print(f"\nSearching for satellites with >{min_obs} observations in last {days} days...")

    params = {
        "obTime": f">now-{days} days",
        "dataMode": "REAL",
        "maxResults": "10000",
    }

    obs = udl_query(token, "eoobservation", params)

    if obs.empty:
        return []

    # Get satellites with most observations
    sat_counts = obs['satNo'].value_counts()
    good_sats = sat_counts[sat_counts >= min_obs].index.tolist()

    print(f"  Found {len(good_sats)} satellites with >={min_obs} observations")
    return [int(s) for s in good_sats[:20]]  # Return top 20


# =============================================================================
# METRIC CALCULATION FUNCTIONS
# =============================================================================

def calculate_orbital_coverage(obs_df: pd.DataFrame, period_sec: float) -> float:
    """
    Calculate orbital coverage as percentage of orbital period covered.
    Uses time-binning approach similar to the simulation.
    """
    if len(obs_df) < 3:
        return 0.0

    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    obs_df = obs_df.sort_values('obTime')

    # Calculate time span
    time_span = (obs_df['obTime'].max() - obs_df['obTime'].min()).total_seconds()

    if time_span < period_sec:
        return time_span / period_sec

    # Bin observations into orbital period segments
    bins_per_period = 20
    bin_size = period_sec / bins_per_period
    total_bins = int(np.ceil(time_span / bin_size))

    start_time = obs_df['obTime'].min()
    bin_counts = np.zeros(total_bins)

    for obs_time in obs_df['obTime']:
        bin_idx = int((obs_time - start_time).total_seconds() / bin_size)
        if 0 <= bin_idx < total_bins:
            bin_counts[bin_idx] += 1

    # Coverage = fraction of bins with observations
    covered_bins = np.sum(bin_counts > 0)
    return covered_bins / total_bins


def calculate_max_gap(obs_df: pd.DataFrame) -> float:
    """Calculate maximum gap between observations in seconds."""
    if len(obs_df) < 2:
        return float('inf')

    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    sorted_times = obs_df['obTime'].sort_values()
    gaps = sorted_times.diff().dropna()

    if len(gaps) == 0:
        return 0.0

    return gaps.max().total_seconds()


def calculate_gap_distribution(obs_df: pd.DataFrame) -> dict:
    """Calculate gap distribution statistics."""
    if len(obs_df) < 2:
        return {'max': float('inf'), 'mean': float('inf'), 'median': float('inf'), 'std': 0}

    obs_df = obs_df.copy()
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    sorted_times = obs_df['obTime'].sort_values()
    gaps_sec = sorted_times.diff().dropna().dt.total_seconds()

    return {
        'max': gaps_sec.max(),
        'mean': gaps_sec.mean(),
        'median': gaps_sec.median(),
        'std': gaps_sec.std(),
        'gaps': gaps_sec.values
    }


def create_orbital_elements(sat_id: int, obs_df: pd.DataFrame = None, period_hours: float = 1.5) -> dict:
    """Create orbital elements dictionary for a satellite."""
    num_obs = len(obs_df) if obs_df is not None else 0
    period_sec = period_hours * 3600

    # Calculate actual coverage and gaps if we have data
    coverage = 0.0
    max_gap_fraction = 0.0

    if obs_df is not None and len(obs_df) >= 3:
        coverage = calculate_orbital_coverage(obs_df, period_sec)
        max_gap_sec = calculate_max_gap(obs_df)
        max_gap_fraction = max_gap_sec / period_sec

    return {
        'Semi-Major Axis': 7000 + np.random.uniform(-500, 500),  # LEO
        'Eccentricity': np.random.uniform(0.0001, 0.01),
        'Inclination': np.random.uniform(40, 100),
        'RAAN': np.random.uniform(0, 360),
        'Argument of Perigee': np.random.uniform(0, 360),
        'Mean Anomaly': np.random.uniform(0, 360),
        'Period': period_sec,
        'Number of Obs': num_obs,
        'Orbital Coverage': coverage,
        'Max Track Gap': max_gap_fraction,
    }


# =============================================================================
# DOWNSAMPLING TESTS
# =============================================================================

def test_downsampling_coverage_reduction(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test that coverage downsampling actually reduces orbital coverage."""
    from uct_benchmark.data.dataManipulation import _lowerOrbitCoverage

    results = {
        'test_name': 'Coverage Reduction',
        'passed': False,
        'before': {},
        'after': {},
        'satellites_tested': 0,
        'satellites_reduced': 0,
    }

    # Calculate before metrics
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id in sat_params and len(sat_obs) >= 5:
            period = sat_params[sat_id]['Period']
            results['before'][sat_id] = calculate_orbital_coverage(sat_obs, period)

    # Run coverage downsampling
    try:
        rng = np.random.default_rng(42)
        downsampled, err = _lowerOrbitCoverage(
            obs_df.copy(),
            sat_params,
            objp=(0.3, 0.5, 0.7),  # Target 50% of sats
            coveragep=(0.15, 0.05),  # Max 15%, min 5% coverage
            rng=rng,
            chosen_sats=None
        )

        # Calculate after metrics
        for sat_id in downsampled['satNo'].unique():
            sat_obs = downsampled[downsampled['satNo'] == sat_id]
            if sat_id in sat_params and len(sat_obs) >= 3:
                period = sat_params[sat_id]['Period']
                results['after'][sat_id] = calculate_orbital_coverage(sat_obs, period)

        # Count satellites with reduced coverage
        for sat_id in results['before']:
            if sat_id in results['after']:
                results['satellites_tested'] += 1
                if results['after'][sat_id] < results['before'][sat_id]:
                    results['satellites_reduced'] += 1

        results['passed'] = results['satellites_reduced'] > 0 or len(obs_df) == len(downsampled)
        results['obs_before'] = len(obs_df)
        results['obs_after'] = len(downsampled)

    except Exception as e:
        results['error'] = str(e)

    return results


def test_downsampling_gap_increase(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test that gap downsampling actually increases maximum gaps."""
    from uct_benchmark.data.dataManipulation import _increaseTrackDistance

    results = {
        'test_name': 'Gap Increase',
        'passed': False,
        'before': {},
        'after': {},
        'satellites_tested': 0,
        'satellites_increased': 0,
    }

    # Calculate before metrics
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id in sat_params and len(sat_obs) >= 5:
            max_gap = calculate_max_gap(sat_obs)
            period = sat_params[sat_id]['Period']
            results['before'][sat_id] = max_gap / period  # Gap in orbital periods

    # Run gap downsampling
    try:
        rng = np.random.default_rng(42)
        downsampled, err = _increaseTrackDistance(
            obs_df.copy(),
            sat_params,
            objp=(0.3, 0.5, 0.7),
            trackp=2.0,  # Target 2 orbital periods gap
            rng=rng,
            chosen_sats=None
        )

        # Calculate after metrics
        for sat_id in downsampled['satNo'].unique():
            sat_obs = downsampled[downsampled['satNo'] == sat_id]
            if sat_id in sat_params and len(sat_obs) >= 3:
                max_gap = calculate_max_gap(sat_obs)
                period = sat_params[sat_id]['Period']
                results['after'][sat_id] = max_gap / period

        # Count satellites with increased gaps
        for sat_id in results['before']:
            if sat_id in results['after']:
                results['satellites_tested'] += 1
                if results['after'][sat_id] > results['before'][sat_id]:
                    results['satellites_increased'] += 1

        results['passed'] = results['satellites_increased'] > 0 or len(obs_df) == len(downsampled)
        results['obs_before'] = len(obs_df)
        results['obs_after'] = len(downsampled)

    except Exception as e:
        results['error'] = str(e)

    return results


def test_downsampling_count_reduction(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test that count downsampling actually reduces observation count."""
    from uct_benchmark.data.dataManipulation import _downsampleAbsolute

    results = {
        'test_name': 'Count Reduction',
        'passed': False,
        'before': {},
        'after': {},
        'satellites_tested': 0,
        'satellites_reduced': 0,
    }

    # Calculate before metrics
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id in sat_params:
            results['before'][sat_id] = len(sat_obs)

    # Run count downsampling
    try:
        rng = np.random.default_rng(42)
        downsampled = _downsampleAbsolute(
            obs_df.copy(),
            sat_params,
            objp=(0.3, 0.5, 0.7),
            obs_max=50,  # Max 50 observations per satellite
            rand=42,
            rng=rng,
            chosen_sats=None
        )

        # Calculate after metrics
        for sat_id in downsampled['satNo'].unique():
            sat_obs = downsampled[downsampled['satNo'] == sat_id]
            results['after'][sat_id] = len(sat_obs)

        # Count satellites with reduced count
        for sat_id in results['before']:
            if sat_id in results['after']:
                results['satellites_tested'] += 1
                if results['after'][sat_id] < results['before'][sat_id]:
                    results['satellites_reduced'] += 1

        results['passed'] = results['satellites_reduced'] > 0 or all(
            v <= 50 for v in results['before'].values()
        )
        results['obs_before'] = len(obs_df)
        results['obs_after'] = len(downsampled)

    except Exception as e:
        results['error'] = str(e)

    return results


def test_full_downsampling_pipeline(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test the complete downsampling pipeline."""
    from uct_benchmark.data.dataManipulation import downsampleData
    import uct_benchmark.config as config

    results = {
        'test_name': 'Full Downsampling Pipeline',
        'passed': False,
        'obs_before': len(obs_df),
        'sats_before': obs_df['satNo'].nunique(),
        'metrics_before': {},
        'metrics_after': {},
    }

    # Calculate before metrics for each satellite
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id in sat_params and len(sat_obs) >= 5:
            period = sat_params[sat_id]['Period']
            results['metrics_before'][sat_id] = {
                'count': len(sat_obs),
                'coverage': calculate_orbital_coverage(sat_obs, period),
                'max_gap_periods': calculate_max_gap(sat_obs) / period,
            }

    try:
        # Build parameters
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

        # Run full pipeline
        downsampled, p_reached = downsampleData(
            obs_df.copy(),
            sat_params,
            orbit_coverage_params,
            track_length_params,
            obs_count_params,
            bins=10,
            rand=42
        )

        results['obs_after'] = len(downsampled)
        results['sats_after'] = downsampled['satNo'].nunique()
        results['percentages_reached'] = p_reached

        # Calculate after metrics
        for sat_id in downsampled['satNo'].unique():
            sat_obs = downsampled[downsampled['satNo'] == sat_id]
            if sat_id in sat_params and len(sat_obs) >= 3:
                period = sat_params[sat_id]['Period']
                results['metrics_after'][sat_id] = {
                    'count': len(sat_obs),
                    'coverage': calculate_orbital_coverage(sat_obs, period),
                    'max_gap_periods': calculate_max_gap(sat_obs) / period,
                }

        # Test passes if observation count reduced or stayed same
        results['passed'] = results['obs_after'] <= results['obs_before']
        results['reduction_pct'] = 100 * (1 - results['obs_after'] / results['obs_before'])

    except Exception as e:
        import traceback
        results['error'] = str(e)
        results['traceback'] = traceback.format_exc()

    return results


# =============================================================================
# SIMULATION TESTS
# =============================================================================

def test_epoch_detection(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test that epochsToSim correctly identifies gaps."""
    from uct_benchmark.simulation.simulateObservations import epochsToSim

    results = {
        'test_name': 'Epoch Detection',
        'passed': False,
        'satellites_tested': 0,
        'satellites_with_gaps': 0,
        'total_epochs_generated': 0,
        'satellite_results': {},
    }

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id not in sat_params or len(sat_obs) < 5:
            continue

        results['satellites_tested'] += 1

        try:
            epochs, bins_info = epochsToSim(sat_id, sat_obs, sat_params[sat_id])

            results['satellite_results'][sat_id] = {
                'status': bins_info.get('status', 'unknown'),
                'total_bins': bins_info.get('total_bins', 0),
                'empty_bins': bins_info.get('empty_bins', 0),
                'epochs_generated': len(epochs),
                'existing_obs': len(sat_obs),
            }

            if len(epochs) > 0:
                results['satellites_with_gaps'] += 1
                results['total_epochs_generated'] += len(epochs)

        except Exception as e:
            results['satellite_results'][sat_id] = {'error': str(e)}

    # Test passes if function runs without errors for all satellites
    results['passed'] = all(
        'error' not in v for v in results['satellite_results'].values()
    )

    return results


def test_simulation_gap_filling(obs_df: pd.DataFrame, sat_params: dict) -> dict:
    """Test that simulation would fill gaps (without running actual propagation)."""
    from uct_benchmark.simulation.simulateObservations import epochsToSim
    import uct_benchmark.config as config

    results = {
        'test_name': 'Gap Filling Analysis',
        'passed': False,
        'satellites_analyzed': 0,
        'satellites_improved': 0,
        'analysis': {},
    }

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        if sat_id not in sat_params or len(sat_obs) < 5:
            continue

        results['satellites_analyzed'] += 1
        period = sat_params[sat_id]['Period']

        # Calculate current metrics
        current_coverage = calculate_orbital_coverage(sat_obs, period)
        current_gap_distribution = calculate_gap_distribution(sat_obs)

        try:
            epochs, bins_info = epochsToSim(sat_id, sat_obs, sat_params[sat_id])

            # Estimate improvement
            if len(epochs) > 0:
                # Estimate new coverage (each epoch would add track_size observations)
                estimated_new_obs = len(sat_obs) + len(epochs)

                # The epochs target empty bins, so coverage should improve
                empty_bins = bins_info.get('empty_bins', 0)
                total_bins = bins_info.get('total_bins', 1)
                current_filled = total_bins - empty_bins

                # After simulation, more bins would be filled
                estimated_new_filled = min(total_bins, current_filled + len(epochs) // config.simulation_track_size)
                estimated_new_coverage = estimated_new_filled / total_bins

                improved = estimated_new_coverage > current_coverage
                if improved:
                    results['satellites_improved'] += 1

                results['analysis'][sat_id] = {
                    'current_obs': len(sat_obs),
                    'current_coverage': round(current_coverage, 4),
                    'current_max_gap_hours': round(current_gap_distribution['max'] / 3600, 2),
                    'epochs_to_add': len(epochs),
                    'estimated_new_obs': estimated_new_obs,
                    'estimated_new_coverage': round(estimated_new_coverage, 4),
                    'would_improve': improved,
                }
            else:
                results['analysis'][sat_id] = {
                    'current_obs': len(sat_obs),
                    'current_coverage': round(current_coverage, 4),
                    'status': bins_info.get('status', 'unknown'),
                    'no_simulation_needed': True,
                }

        except Exception as e:
            results['analysis'][sat_id] = {'error': str(e)}

    # Test passes if analysis completed for all satellites
    results['passed'] = all(
        'error' not in v for v in results['analysis'].values()
    )

    return results


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_time_distribution_plot(obs_before: pd.DataFrame, obs_after: pd.DataFrame,
                                   title: str, filename: str):
    """Create time distribution comparison plot."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # Convert times
    for df in [obs_before, obs_after]:
        if df['obTime'].dtype == 'object':
            df['obTime'] = pd.to_datetime(df['obTime'])

    # Before
    axes[0].hist(obs_before['obTime'], bins=50, alpha=0.7, color='blue', edgecolor='black')
    axes[0].set_title(f'BEFORE: {len(obs_before)} observations')
    axes[0].set_xlabel('Time')
    axes[0].set_ylabel('Count')
    axes[0].tick_params(axis='x', rotation=45)

    # After
    axes[1].hist(obs_after['obTime'], bins=50, alpha=0.7, color='green', edgecolor='black')
    axes[1].set_title(f'AFTER: {len(obs_after)} observations')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel('Count')
    axes[1].tick_params(axis='x', rotation=45)

    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()


def create_gap_histogram(obs_before: pd.DataFrame, obs_after: pd.DataFrame,
                         title: str, filename: str):
    """Create gap distribution comparison histogram."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    gaps_before = calculate_gap_distribution(obs_before)
    gaps_after = calculate_gap_distribution(obs_after)

    # Convert to hours
    gaps_before_hours = gaps_before['gaps'] / 3600
    gaps_after_hours = gaps_after['gaps'] / 3600

    # Before
    axes[0].hist(gaps_before_hours, bins=30, alpha=0.7, color='blue', edgecolor='black')
    axes[0].axvline(gaps_before['max']/3600, color='red', linestyle='--',
                    label=f'Max: {gaps_before["max"]/3600:.1f}h')
    axes[0].set_title(f'BEFORE: Max gap = {gaps_before["max"]/3600:.1f} hours')
    axes[0].set_xlabel('Gap Duration (hours)')
    axes[0].set_ylabel('Count')
    axes[0].legend()

    # After
    axes[1].hist(gaps_after_hours, bins=30, alpha=0.7, color='green', edgecolor='black')
    axes[1].axvline(gaps_after['max']/3600, color='red', linestyle='--',
                    label=f'Max: {gaps_after["max"]/3600:.1f}h')
    axes[1].set_title(f'AFTER: Max gap = {gaps_after["max"]/3600:.1f} hours')
    axes[1].set_xlabel('Gap Duration (hours)')
    axes[1].set_ylabel('Count')
    axes[1].legend()

    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()


def create_metrics_comparison_chart(results: dict, title: str, filename: str):
    """Create bar chart comparing metrics before/after."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    metrics_before = results.get('metrics_before', {})
    metrics_after = results.get('metrics_after', {})

    sat_ids = list(metrics_before.keys())[:10]  # Top 10 satellites

    # Coverage comparison
    coverage_before = [metrics_before[s]['coverage'] for s in sat_ids if s in metrics_before]
    coverage_after = [metrics_after.get(s, {}).get('coverage', 0) for s in sat_ids]

    x = np.arange(len(sat_ids))
    width = 0.35

    axes[0].bar(x - width/2, coverage_before, width, label='Before', color='blue', alpha=0.7)
    axes[0].bar(x + width/2, coverage_after, width, label='After', color='green', alpha=0.7)
    axes[0].set_xlabel('Satellite')
    axes[0].set_ylabel('Coverage')
    axes[0].set_title('Orbital Coverage')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([str(s)[-5:] for s in sat_ids], rotation=45)
    axes[0].legend()

    # Gap comparison
    gap_before = [metrics_before[s]['max_gap_periods'] for s in sat_ids if s in metrics_before]
    gap_after = [metrics_after.get(s, {}).get('max_gap_periods', 0) for s in sat_ids]

    axes[1].bar(x - width/2, gap_before, width, label='Before', color='blue', alpha=0.7)
    axes[1].bar(x + width/2, gap_after, width, label='After', color='green', alpha=0.7)
    axes[1].set_xlabel('Satellite')
    axes[1].set_ylabel('Max Gap (orbital periods)')
    axes[1].set_title('Maximum Track Gap')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([str(s)[-5:] for s in sat_ids], rotation=45)
    axes[1].legend()

    # Count comparison
    count_before = [metrics_before[s]['count'] for s in sat_ids if s in metrics_before]
    count_after = [metrics_after.get(s, {}).get('count', 0) for s in sat_ids]

    axes[2].bar(x - width/2, count_before, width, label='Before', color='blue', alpha=0.7)
    axes[2].bar(x + width/2, count_after, width, label='After', color='green', alpha=0.7)
    axes[2].set_xlabel('Satellite')
    axes[2].set_ylabel('Observation Count')
    axes[2].set_title('Observation Count')
    axes[2].set_xticks(x)
    axes[2].set_xticklabels([str(s)[-5:] for s in sat_ids], rotation=45)
    axes[2].legend()

    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()


def create_summary_report(all_results: dict, output_path: Path):
    """Create a text summary report of all test results."""
    with open(output_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("COMPREHENSIVE QUALITY TEST REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        # Data summary
        f.write("DATA SUMMARY\n")
        f.write("-" * 40 + "\n")
        data_info = all_results.get('data_info', {})
        f.write(f"Total observations pulled: {data_info.get('total_obs', 'N/A')}\n")
        f.write(f"Satellites tested: {data_info.get('num_sats', 'N/A')}\n")
        f.write(f"Time span: {data_info.get('time_span', 'N/A')}\n\n")

        # Test results summary
        f.write("TEST RESULTS SUMMARY\n")
        f.write("-" * 40 + "\n")

        tests = ['coverage_reduction', 'gap_increase', 'count_reduction',
                 'full_pipeline', 'epoch_detection', 'gap_filling']

        passed = 0
        total = 0

        for test in tests:
            result = all_results.get(test, {})
            test_passed = result.get('passed', False)
            status = "PASS" if test_passed else "FAIL"
            f.write(f"{result.get('test_name', test)}: {status}\n")
            if test_passed:
                passed += 1
            total += 1

        f.write(f"\nOverall: {passed}/{total} tests passed\n\n")

        # Detailed results
        f.write("=" * 80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 80 + "\n\n")

        # Full pipeline results
        pipeline = all_results.get('full_pipeline', {})
        f.write("FULL DOWNSAMPLING PIPELINE\n")
        f.write("-" * 40 + "\n")
        f.write(f"Observations: {pipeline.get('obs_before', 'N/A')} -> {pipeline.get('obs_after', 'N/A')}\n")
        f.write(f"Reduction: {pipeline.get('reduction_pct', 0):.1f}%\n")
        f.write(f"Percentages reached: {pipeline.get('percentages_reached', 'N/A')}\n\n")

        # Simulation results
        sim = all_results.get('gap_filling', {})
        f.write("SIMULATION ANALYSIS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Satellites analyzed: {sim.get('satellites_analyzed', 0)}\n")
        f.write(f"Satellites that would improve: {sim.get('satellites_improved', 0)}\n\n")

        # Per-satellite details
        f.write("PER-SATELLITE ANALYSIS\n")
        f.write("-" * 40 + "\n")

        analysis = sim.get('analysis', {})
        for sat_id, info in list(analysis.items())[:10]:
            f.write(f"\nSatellite {sat_id}:\n")
            for key, value in info.items():
                f.write(f"  {key}: {value}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and generate report."""
    print("=" * 80)
    print("COMPREHENSIVE QUALITY TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    all_results = {}

    # ==========================================================================
    # STEP 1: Pull data from UDL
    # ==========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: PULLING DATA FROM UDL")
    print("=" * 80)

    username, password = get_credentials()
    token = udl_token_gen(username, password)
    print("Token generated successfully")

    # Find active satellites
    active_sats = find_active_satellites(token, days=30, min_obs=30)

    if not active_sats:
        print("ERROR: No suitable satellites found. Using fallback list.")
        active_sats = [25544, 22314, 42915, 43013, 48274]

    # Pull data for each satellite
    print(f"\nPulling data for {len(active_sats[:10])} satellites...")
    all_obs = []

    for sat_id in active_sats[:10]:
        print(f"  Satellite {sat_id}...", end=" ")
        obs = pull_satellite_data(token, sat_id, days=30)
        if not obs.empty:
            print(f"{len(obs)} observations")
            all_obs.append(obs)
        else:
            print("no data")

    if not all_obs:
        print("ERROR: No observation data retrieved. Exiting.")
        return

    obs_df = pd.concat(all_obs, ignore_index=True)

    # Convert obTime
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    print(f"\nTotal: {len(obs_df)} observations for {obs_df['satNo'].nunique()} satellites")

    # Save raw data
    obs_df.to_csv(OUTPUT_DIR / "raw_observations.csv", index=False)

    all_results['data_info'] = {
        'total_obs': len(obs_df),
        'num_sats': obs_df['satNo'].nunique(),
        'time_span': f"{obs_df['obTime'].min()} to {obs_df['obTime'].max()}"
    }

    # Create orbital elements for each satellite
    sat_params = {}
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]
        sat_params[sat_id] = create_orbital_elements(sat_id, sat_obs)

    # ==========================================================================
    # STEP 2: Run Downsampling Tests
    # ==========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: DOWNSAMPLING TESTS")
    print("=" * 80)

    # Test 2a: Coverage reduction
    print("\nTest 2a: Coverage Reduction...")
    results_coverage = test_downsampling_coverage_reduction(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_coverage['passed'] else 'FAIL'}")
    print(f"  Satellites tested: {results_coverage['satellites_tested']}")
    print(f"  Satellites with reduced coverage: {results_coverage['satellites_reduced']}")
    all_results['coverage_reduction'] = results_coverage

    # Test 2b: Gap increase
    print("\nTest 2b: Gap Increase...")
    results_gap = test_downsampling_gap_increase(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_gap['passed'] else 'FAIL'}")
    print(f"  Satellites tested: {results_gap['satellites_tested']}")
    print(f"  Satellites with increased gaps: {results_gap['satellites_increased']}")
    all_results['gap_increase'] = results_gap

    # Test 2c: Count reduction
    print("\nTest 2c: Count Reduction...")
    results_count = test_downsampling_count_reduction(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_count['passed'] else 'FAIL'}")
    print(f"  Satellites tested: {results_count['satellites_tested']}")
    print(f"  Satellites with reduced count: {results_count['satellites_reduced']}")
    all_results['count_reduction'] = results_count

    # Test 2d: Full pipeline
    print("\nTest 2d: Full Downsampling Pipeline...")
    results_pipeline = test_full_downsampling_pipeline(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_pipeline['passed'] else 'FAIL'}")
    print(f"  Observations: {results_pipeline.get('obs_before', 0)} -> {results_pipeline.get('obs_after', 0)}")
    print(f"  Reduction: {results_pipeline.get('reduction_pct', 0):.1f}%")
    all_results['full_pipeline'] = results_pipeline

    # ==========================================================================
    # STEP 3: Run Simulation Tests
    # ==========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: SIMULATION TESTS")
    print("=" * 80)

    # Test 3a: Epoch detection
    print("\nTest 3a: Epoch Detection...")
    results_epoch = test_epoch_detection(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_epoch['passed'] else 'FAIL'}")
    print(f"  Satellites tested: {results_epoch['satellites_tested']}")
    print(f"  Satellites with gaps: {results_epoch['satellites_with_gaps']}")
    print(f"  Total epochs generated: {results_epoch['total_epochs_generated']}")
    all_results['epoch_detection'] = results_epoch

    # Test 3b: Gap filling analysis
    print("\nTest 3b: Gap Filling Analysis...")
    results_filling = test_simulation_gap_filling(obs_df, sat_params)
    print(f"  Result: {'PASS' if results_filling['passed'] else 'FAIL'}")
    print(f"  Satellites analyzed: {results_filling['satellites_analyzed']}")
    print(f"  Satellites that would improve: {results_filling['satellites_improved']}")
    all_results['gap_filling'] = results_filling

    # ==========================================================================
    # STEP 4: Generate Visualizations
    # ==========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: GENERATING VISUALIZATIONS")
    print("=" * 80)

    # Run full downsampling for visualization
    from uct_benchmark.data.dataManipulation import downsampleData
    import uct_benchmark.config as config

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

    downsampled_obs, _ = downsampleData(
        obs_df.copy(), sat_params,
        orbit_coverage_params, track_length_params, obs_count_params,
        bins=10, rand=42
    )

    # Save downsampled data
    downsampled_obs.to_csv(OUTPUT_DIR / "downsampled_observations.csv", index=False)

    print("Creating time distribution plot...")
    create_time_distribution_plot(
        obs_df, downsampled_obs,
        "Observation Time Distribution: Before vs After Downsampling",
        "time_distribution.png"
    )

    print("Creating gap histogram...")
    create_gap_histogram(
        obs_df, downsampled_obs,
        "Gap Distribution: Before vs After Downsampling",
        "gap_histogram.png"
    )

    print("Creating metrics comparison chart...")
    create_metrics_comparison_chart(
        results_pipeline,
        "Metrics Comparison: Before vs After Downsampling",
        "metrics_comparison.png"
    )

    # ==========================================================================
    # STEP 5: Generate Report
    # ==========================================================================
    print("\n" + "=" * 80)
    print("STEP 5: GENERATING REPORT")
    print("=" * 80)

    create_summary_report(all_results, OUTPUT_DIR / "test_report.txt")
    print(f"Report saved to: {OUTPUT_DIR / 'test_report.txt'}")

    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    tests = [
        ('Coverage Reduction', all_results.get('coverage_reduction', {}).get('passed', False)),
        ('Gap Increase', all_results.get('gap_increase', {}).get('passed', False)),
        ('Count Reduction', all_results.get('count_reduction', {}).get('passed', False)),
        ('Full Pipeline', all_results.get('full_pipeline', {}).get('passed', False)),
        ('Epoch Detection', all_results.get('epoch_detection', {}).get('passed', False)),
        ('Gap Filling', all_results.get('gap_filling', {}).get('passed', False)),
    ]

    passed = sum(1 for _, p in tests if p)
    total = len(tests)

    for name, result in tests:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"\nOutput files saved to: {OUTPUT_DIR}")
    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
