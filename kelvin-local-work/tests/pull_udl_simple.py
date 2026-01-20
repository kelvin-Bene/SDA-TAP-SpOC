#!/usr/bin/env python3
"""
Simple UDL Data Pull Script (No Orekit Required)
=================================================
Standalone script to pull observation data from UDL without orekit dependency.

Usage:
    python tests/pull_udl_simple.py
"""

import base64
import getpass
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Suppress HTTPS warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def udl_token_gen(username: str, password: str) -> str:
    """Generate UDL authentication token."""
    return base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")


def udl_query(token: str, service: str, params: dict) -> pd.DataFrame:
    """Perform a UDL query."""
    url = f"https://unifieddatalibrary.com/udl/{service.lower()}"
    headers = {"Authorization": "Basic " + token}

    print(f"  Querying {service} with params: {params}")
    resp = requests.get(url, headers=headers, params=params, verify=False)

    if resp.status_code != 200:
        print(f"  Error: {resp.status_code} - {resp.text[:200]}")
        return pd.DataFrame()

    data = resp.json()
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_credentials():
    """Get UDL credentials from environment or prompt."""
    username = os.environ.get('UDL_USERNAME')
    password = os.environ.get('UDL_PASSWORD')

    if not username:
        username = input("Enter UDL username: ")
    if not password:
        password = getpass.getpass("Enter UDL password: ")

    return username, password


def pull_observations_for_satellite(token: str, sat_id: int, days: int = 7) -> pd.DataFrame:
    """Pull observations for a single satellite."""
    params = {
        "satNo": str(sat_id),
        "obTime": f">now-{days} days",
        "dataMode": "REAL",
        "maxResults": "1000",
    }
    return udl_query(token, "eoobservation", params)


def analyze_observations(obs_df: pd.DataFrame) -> dict:
    """Analyze observation data quality."""
    if obs_df.empty:
        return {'status': 'no_data'}

    # Convert obTime to datetime
    obs_df = obs_df.copy()
    obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    stats = {}
    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id]

        # Time span
        time_span = (sat_obs['obTime'].max() - sat_obs['obTime'].min()).total_seconds() / 3600

        # Calculate gaps
        sorted_times = sat_obs['obTime'].sort_values()
        gaps = sorted_times.diff().dropna()
        max_gap_hours = gaps.max().total_seconds() / 3600 if len(gaps) > 0 else 0
        avg_gap_hours = gaps.mean().total_seconds() / 3600 if len(gaps) > 0 else 0

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

        stats[sat_id] = {
            'obs_count': obs_count,
            'time_span_hours': round(time_span, 1),
            'max_gap_hours': round(max_gap_hours, 1),
            'avg_gap_hours': round(avg_gap_hours, 2),
            'recommended_tier': tier
        }

    return stats


def test_simulation_logic(obs_df: pd.DataFrame) -> dict:
    """Test simulation epoch selection logic (without orekit)."""
    results = {}

    obs_df = obs_df.copy()
    obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    for sat_id in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_id].sort_values('obTime')

        if len(sat_obs) < 5:
            results[sat_id] = {'status': 'insufficient_obs', 'count': len(sat_obs)}
            continue

        # Estimate orbital period (assume LEO ~90 min)
        period_sec = 5400  # 90 minutes

        # Get time window
        start_time = sat_obs['obTime'].min()
        end_time = sat_obs['obTime'].max()
        window_sec = (end_time - start_time).total_seconds()

        # Calculate bins (10 bins per period)
        bins_per_period = 10
        bin_size_sec = period_sec / bins_per_period
        total_bins = int(np.ceil(window_sec / bin_size_sec))

        # Count observations per bin
        bin_counts = np.zeros(total_bins, dtype=int)
        for obs_time in sat_obs['obTime']:
            bin_idx = int((obs_time - start_time).total_seconds() / bin_size_sec)
            if 0 <= bin_idx < total_bins:
                bin_counts[bin_idx] += 1

        # Find empty bins
        empty_bins = np.sum(bin_counts == 0)

        # Estimate epochs to simulate
        current_count = len(sat_obs)
        target_count = int(current_count * 1.5)
        epochs_needed = min(target_count - current_count, empty_bins * 3)

        results[sat_id] = {
            'status': 'success',
            'existing_obs': current_count,
            'total_bins': total_bins,
            'empty_bins': int(empty_bins),
            'coverage_pct': round(100 * (total_bins - empty_bins) / total_bins, 1),
            'epochs_to_simulate': max(0, epochs_needed),
        }

    return results


def find_satellites_with_observations(token: str, days: int = 30, limit: int = 10) -> list:
    """Query UDL to find satellites that have recent observations."""
    print(f"\nSearching for satellites with observations in last {days} days...")

    # Query for recent observations (any satellite)
    params = {
        "obTime": f">now-{days} days",
        "dataMode": "REAL",
        "maxResults": "5000",
        "sort": "obTime,DESC",
    }

    obs = udl_query(token, "eoobservation", params)

    if obs.empty:
        print("  No observations found in UDL")
        return []

    # Get satellites with most observations
    sat_counts = obs['satNo'].value_counts()
    top_sats = [int(sat_id) for sat_id in sat_counts.head(limit).index.tolist()]

    print(f"  Found {len(obs)} total observations for {obs['satNo'].nunique()} satellites")
    print(f"  Top satellites by obs count: {dict(zip(top_sats, sat_counts.head(limit).values))}")

    return top_sats


def main():
    print("=" * 70)
    print("SIMPLE UDL DATA PULL (No Orekit Required)")
    print("=" * 70)

    # Get credentials
    username, password = get_credentials()
    token = udl_token_gen(username, password)
    print("\nToken generated successfully")

    # First, find satellites that actually have observations
    active_sats = find_satellites_with_observations(token, days=30, limit=10)

    if active_sats:
        test_satellites = active_sats[:5]  # Use top 5
    else:
        # Fallback to known satellites from existing data
        test_satellites = [
            22314,  # From ref_obs.csv
            42915,  # From ref_obs.csv
            25544,  # ISS
            48274,  # Starlink
            43013,  # Starlink
        ]

    print(f"\nPulling detailed data for satellites: {test_satellites}")
    print("-" * 70)

    all_obs = []
    for sat_id in test_satellites:
        print(f"\nSatellite {sat_id}:")
        obs = pull_observations_for_satellite(token, sat_id, days=30)  # 30 days
        if not obs.empty:
            print(f"  Retrieved {len(obs)} observations")
            all_obs.append(obs)
        else:
            print(f"  No observations found")

    if not all_obs:
        print("\nNo observations retrieved. Check credentials and try again.")
        return

    # Combine all observations
    obs_df = pd.concat(all_obs, ignore_index=True)
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {len(obs_df)} observations for {obs_df['satNo'].nunique()} satellites")
    print("=" * 70)

    # Analyze data quality
    print("\nDATA QUALITY ANALYSIS")
    print("-" * 70)

    quality_stats = analyze_observations(obs_df)
    for sat_id, stats in quality_stats.items():
        if isinstance(stats, dict) and 'obs_count' in stats:
            print(f"\nSatellite {sat_id}:")
            print(f"  Observations:      {stats['obs_count']}")
            print(f"  Time span:         {stats['time_span_hours']} hours")
            print(f"  Max gap:           {stats['max_gap_hours']} hours")
            print(f"  Avg gap:           {stats['avg_gap_hours']} hours")
            print(f"  Recommended tier:  {stats['recommended_tier']}")

    # Test simulation logic
    print(f"\n{'=' * 70}")
    print("SIMULATION ANALYSIS")
    print("-" * 70)

    sim_results = test_simulation_logic(obs_df)
    for sat_id, result in sim_results.items():
        print(f"\nSatellite {sat_id}: {result.get('status', 'unknown')}")
        if result.get('status') == 'success':
            print(f"  Existing obs:       {result.get('existing_obs', 0)}")
            print(f"  Bin coverage:       {result.get('coverage_pct', 0)}%")
            print(f"  Empty bins:         {result.get('empty_bins', 0)}/{result.get('total_bins', 0)}")
            print(f"  Epochs to simulate: {result.get('epochs_to_simulate', 0)}")

    # Save data
    output_dir = Path(__file__).parent / "data" / "udl_test_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"obs_LEO_{timestamp}.csv"
    obs_df.to_csv(output_path, index=False)

    print(f"\n{'=' * 70}")
    print(f"Data saved to: {output_path}")
    print("=" * 70)

    # Summary
    print("\nSUMMARY")
    print("-" * 70)
    t1_count = sum(1 for s in quality_stats.values() if isinstance(s, dict) and s.get('recommended_tier') == 'T1')
    t2_count = sum(1 for s in quality_stats.values() if isinstance(s, dict) and s.get('recommended_tier') == 'T2')
    t3_count = sum(1 for s in quality_stats.values() if isinstance(s, dict) and s.get('recommended_tier') == 'T3')
    t4_count = sum(1 for s in quality_stats.values() if isinstance(s, dict) and s.get('recommended_tier') == 'T4')

    print(f"T1 (high quality, may downsample):  {t1_count} satellites")
    print(f"T2 (medium, needs downsampling):    {t2_count} satellites")
    print(f"T3 (sparse, needs simulation):      {t3_count} satellites")
    print(f"T4 (very sparse, needs objects):    {t4_count} satellites")

    print("\nDone!")


if __name__ == "__main__":
    main()
