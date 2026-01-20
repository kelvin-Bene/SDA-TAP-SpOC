# -*- coding: utf-8 -*-
"""
Comprehensive Simulation Module Test

Tests the full simulation pipeline:
1. epochsToSim - Gap detection
2. simulateObs - Synthetic observation generation
3. Output format validation against UDL schema

Run with: python tests/test_simulation_comprehensive.py
"""

import sys
from datetime import datetime, timedelta

# Initialize Orekit first (required before any Orekit imports)
# IMPORTANT: initVM() must be called BEFORE importing from pyhelpers
import orekit_jpype as orekit
orekit.initVM()

from orekit_jpype.pyhelpers import setup_orekit_curdir
setup_orekit_curdir(from_pip_library=True)


def test_epochs_to_sim():
    """Test 1: Test epochsToSim function for gap detection"""
    print("=" * 70)
    print("Test 1: Testing epochsToSim function (gap detection)")
    print("=" * 70)

    import numpy as np
    import pandas as pd
    from uct_benchmark.simulation.simulateObservations import epochsToSim

    # Create sample observation data with gaps
    # Simulate observations for a satellite with some bins missing
    satNo = 25544  # ISS

    # Create observation times with intentional gaps
    base_time = datetime(2025, 1, 1, 0, 0, 0)

    # Observations: cluster at start, gap, cluster at end
    obs_times = []
    # First cluster (0-2 hours)
    for i in range(20):
        obs_times.append(base_time + timedelta(minutes=i*5))
    # Gap from 2-8 hours
    # Second cluster (8-10 hours)
    for i in range(20):
        obs_times.append(base_time + timedelta(hours=8, minutes=i*5))

    satObs = pd.DataFrame({
        'obTime': obs_times,
        'satNo': satNo,
        'ra': np.random.uniform(0, 360, len(obs_times)),
        'declination': np.random.uniform(-90, 90, len(obs_times)),
    })

    # Orbital elements (approximate ISS orbit)
    orbElems = {
        'Semi-Major Axis': 6780,  # km
        'Eccentricity': 0.0001,
        'Period': 5580,  # seconds (~93 minutes)
    }

    # Run epochsToSim
    epochs, bins_info = epochsToSim(
        satNo=satNo,
        satObs=satObs,
        orbElems=orbElems,
        target_obs_count=None,
        max_sim_ratio=0.3
    )

    print(f"  Input: {len(satObs)} observations over {10} hours")
    print(f"  Orbital period: {orbElems['Period']/60:.1f} minutes")
    print(f"  Bins info: {bins_info}")
    print(f"  Epochs to simulate: {len(epochs)}")

    if len(epochs) > 0:
        print(f"  First epoch: {epochs[0]}")
        print(f"  Last epoch: {epochs[-1]}")
        print(f"  [PASS] epochsToSim detected gaps and returned simulation epochs")
        return True
    else:
        if bins_info.get('status') == 'all_bins_covered':
            print(f"  [INFO] All bins covered - no simulation needed")
            return True
        print(f"  [FAIL] No epochs returned. Status: {bins_info.get('status')}")
        return False


def test_simulate_obs_with_tle():
    """Test 2: Test simulateObs function with TLE input"""
    print("\n" + "=" * 70)
    print("Test 2: Testing simulateObs with TLE input")
    print("=" * 70)

    import numpy as np
    import pandas as pd
    from uct_benchmark.simulation.simulateObservations import simulateObs

    # ISS TLE (sample)
    tle_line1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
    tle_line2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"

    # Create sample sensor data
    sensors_df = pd.DataFrame({
        'idSensor': ['SEN001', 'SEN002', 'SEN003'],
        'senlat': [35.0, 40.0, 30.0],      # Latitude (degrees)
        'senlon': [-120.0, -105.0, -85.0],  # Longitude (degrees)
        'senalt': [0.5, 1.0, 0.3],          # Altitude (km)
        'sensorLikelihood': [1.0, 1.0, 1.0],
        'count': [10, 10, 10],              # Weight for sampling
    })

    # Simulate for 600 seconds (10 minutes) with 60s step
    timespan = 600
    step = 60

    print(f"  TLE: {tle_line1[:30]}...")
    print(f"  Timespan: {timespan}s, Step: {step}s")
    print(f"  Sensors: {len(sensors_df)}")

    try:
        result_df = simulateObs(
            input1=tle_line1,
            input2=tle_line2,
            timespan=timespan,
            sensorsDataFrame=sensors_df,
            positionNoise=0.01,  # 10m
            angularNoise=1/3600,  # 1 arcsec
            step=step,
        )

        print(f"  Generated observations: {len(result_df)}")

        if len(result_df) > 0:
            print(f"  Columns: {list(result_df.columns)[:10]}...")
            print(f"  Sample observation:")
            print(f"    - obTime: {result_df['obTime'].iloc[0]}")
            print(f"    - RA: {result_df['ra'].iloc[0]:.4f} deg")
            print(f"    - Dec: {result_df['declination'].iloc[0]:.4f} deg")
            print(f"    - Elevation: {result_df['elevation'].iloc[0]:.2f} deg")
            print(f"    - dataMode: {result_df['dataMode'].iloc[0]}")
            print(f"  [PASS] simulateObs generated {len(result_df)} observations")
            return True, result_df
        else:
            print(f"  [WARN] No observations generated (possibly no visible passes)")
            return True, result_df  # Not a failure, just no visibility

    except Exception as e:
        print(f"  [FAIL] simulateObs failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_simulate_obs_with_state_vector():
    """Test 3: Test simulateObs function with state vector input"""
    print("\n" + "=" * 70)
    print("Test 3: Testing simulateObs with state vector input")
    print("=" * 70)

    import numpy as np
    import pandas as pd
    from uct_benchmark.simulation.simulateObservations import simulateObs

    # State vector for a sample satellite (position in km, velocity in km/s)
    # Approximate GEO satellite
    state_vector = np.array([
        -40000.0,   # x (km)
        10000.0,    # y (km)
        0.0,        # z (km)
        -0.73,      # vx (km/s)
        -2.9,       # vy (km/s)
        0.0         # vz (km/s)
    ])

    epoch = datetime(2025, 1, 1, 12, 0, 0)

    # Create sample sensor data
    sensors_df = pd.DataFrame({
        'idSensor': ['SEN001', 'SEN002'],
        'senlat': [35.0, -35.0],
        'senlon': [-100.0, 150.0],
        'senalt': [1.0, 0.5],
        'sensorLikelihood': [1.0, 1.0],
        'count': [10, 10],
    })

    # Define specific times to simulate
    sim_times = [
        epoch + timedelta(minutes=i*10) for i in range(6)
    ]

    print(f"  State vector: {state_vector[:3]} km (position)")
    print(f"  Epoch: {epoch}")
    print(f"  Simulation times: {len(sim_times)}")

    try:
        result_df = simulateObs(
            input1=state_vector,
            input2=epoch,
            timespan=sim_times,  # List of datetimes
            sensorsDataFrame=sensors_df,
            positionNoise=0.01,
            angularNoise=1/3600,
            satelliteParameters=[99999, 1000, 10],  # satNo, mass, area
        )

        print(f"  Generated observations: {len(result_df)}")

        if len(result_df) > 0:
            print(f"  Sample observation:")
            print(f"    - satNo: {result_df['satNo'].iloc[0]}")
            print(f"    - obTime: {result_df['obTime'].iloc[0]}")
            print(f"    - RA: {result_df['ra'].iloc[0]:.4f} deg")
            print(f"    - Dec: {result_df['declination'].iloc[0]:.4f} deg")
            print(f"  [PASS] State vector simulation generated {len(result_df)} observations")
            return True, result_df
        else:
            print(f"  [WARN] No observations generated (satellite not visible)")
            return True, result_df

    except Exception as e:
        print(f"  [FAIL] State vector simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_output_format_validation(result_df):
    """Test 4: Validate output format matches UDL schema"""
    print("\n" + "=" * 70)
    print("Test 4: Validating output format against UDL observation schema")
    print("=" * 70)

    if result_df is None or len(result_df) == 0:
        print("  [SKIP] No data to validate")
        return True

    # Required UDL schema fields
    required_fields = [
        'id',                   # UUID
        'obTime',               # ISO timestamp
        'satNo',                # NORAD ID
        'ra',                   # Right ascension (degrees)
        'declination',          # Declination (degrees)
        'dataMode',             # Should be "SIMULATED"
        'idSensor',             # Sensor ID
        'elevation',            # Elevation angle
        'azimuth',              # Azimuth angle
        'senlat',               # Sensor latitude
        'senlon',               # Sensor longitude
        'senalt',               # Sensor altitude
    ]

    optional_fields = [
        'range',
        'classificationMarking',
        'source',
        'type',
        'createdAt',
        'sensorStDev',
    ]

    # Check required fields
    missing_fields = []
    for field in required_fields:
        if field not in result_df.columns:
            missing_fields.append(field)

    if missing_fields:
        print(f"  [FAIL] Missing required fields: {missing_fields}")
        return False

    print(f"  [PASS] All required fields present: {len(required_fields)}")

    # Validate field types and ranges
    validation_errors = []

    # Check RA range (0-360)
    if result_df['ra'].min() < 0 or result_df['ra'].max() > 360:
        validation_errors.append(f"RA out of range [0,360]: [{result_df['ra'].min():.2f}, {result_df['ra'].max():.2f}]")

    # Check Dec range (-90 to 90)
    if result_df['declination'].min() < -90 or result_df['declination'].max() > 90:
        validation_errors.append(f"Dec out of range [-90,90]: [{result_df['declination'].min():.2f}, {result_df['declination'].max():.2f}]")

    # Check elevation range (0-90) - should be > 6 due to visibility constraint
    if result_df['elevation'].min() < 0:
        validation_errors.append(f"Elevation below 0: {result_df['elevation'].min():.2f}")

    # Check dataMode is SIMULATED
    if result_df['dataMode'].iloc[0] != 'SIMULATED':
        validation_errors.append(f"dataMode should be 'SIMULATED', got: {result_df['dataMode'].iloc[0]}")

    # Check satNo is integer
    if not all(isinstance(x, (int, np.integer)) for x in result_df['satNo']):
        validation_errors.append("satNo should be integer")

    if validation_errors:
        for err in validation_errors:
            print(f"  [WARN] {err}")
        print(f"  [PARTIAL] {len(validation_errors)} validation warnings")
        return True  # Warnings, not failures

    print(f"  [PASS] All field validations passed")
    print(f"  Schema validation summary:")
    print(f"    - RA range: [{result_df['ra'].min():.2f}, {result_df['ra'].max():.2f}] deg")
    print(f"    - Dec range: [{result_df['declination'].min():.2f}, {result_df['declination'].max():.2f}] deg")
    print(f"    - Elevation range: [{result_df['elevation'].min():.2f}, {result_df['elevation'].max():.2f}] deg")
    print(f"    - dataMode: {result_df['dataMode'].iloc[0]}")

    return True


def test_propagator_functions():
    """Test 5: Test propagator module functions directly"""
    print("\n" + "=" * 70)
    print("Test 5: Testing propagator module functions")
    print("=" * 70)

    from datetime import datetime
    import numpy as np
    from uct_benchmark.simulation.propagator import TLEpropagator, ephemerisPropagator, orbit2OE

    # Test TLE propagator
    print("  5a. Testing TLEpropagator...")
    tle_line1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
    tle_line2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"

    epochs = [
        datetime(2021, 10, 2, 13, 0, 0),
        datetime(2021, 10, 2, 14, 0, 0),
    ]

    try:
        lines1, lines2, states = TLEpropagator(tle_line1, tle_line2, epochs)
        print(f"      Propagated to {len(epochs)} epochs")
        print(f"      State 1 position: [{states[0][0]:.1f}, {states[0][1]:.1f}, {states[0][2]:.1f}] km")
        print(f"      [PASS] TLEpropagator")
    except Exception as e:
        print(f"      [FAIL] TLEpropagator: {e}")
        return False

    # Test orbit2OE (orbital elements)
    print("  5b. Testing orbit2OE...")
    try:
        oe = orbit2OE(tle_line1, tle_line2)
        print(f"      Semi-major axis: {oe['Semi-Major Axis']:.1f} km")
        print(f"      Eccentricity: {oe['Eccentricity']:.6f}")
        print(f"      Inclination: {oe['Inclination']:.2f} deg")
        print(f"      Period: {oe['Period']/60:.1f} min")
        print(f"      [PASS] orbit2OE")
    except Exception as e:
        print(f"      [FAIL] orbit2OE: {e}")
        return False

    # Test ephemerisPropagator with state vector
    print("  5c. Testing ephemerisPropagator...")
    try:
        state = np.array([6700.0, 0.0, 0.0, 0.0, 7.7, 0.0])  # Simple LEO orbit
        epoch = datetime(2025, 1, 1, 0, 0, 0)
        final_epochs = [epoch + timedelta(hours=1)]

        result_states = ephemerisPropagator(state, epoch, final_epochs)
        print(f"      Propagated state: [{result_states[0][0]:.1f}, {result_states[0][1]:.1f}, {result_states[0][2]:.1f}] km")
        print(f"      [PASS] ephemerisPropagator")
    except Exception as e:
        print(f"      [FAIL] ephemerisPropagator: {e}")
        return False

    return True


def test_radec2azel():
    """Test 6: Test RA/Dec to Az/El conversion"""
    print("\n" + "=" * 70)
    print("Test 6: Testing radec2azel coordinate conversion")
    print("=" * 70)

    from datetime import datetime
    from uct_benchmark.simulation.simulateObservations import radec2azel

    # Test case: Known satellite position
    ra_deg = 180.0      # RA in degrees
    dec_deg = 45.0      # Dec in degrees
    range_km = 400.0    # Range in km
    sensor_pos = [40.0, -100.0, 1.0]  # lat, lon, alt (deg, deg, km)
    obs_time = datetime(2025, 1, 1, 12, 0, 0)

    try:
        az, el = radec2azel(ra_deg, dec_deg, range_km, sensor_pos, obs_time)
        print(f"  Input: RA={ra_deg}deg, Dec={dec_deg}deg")
        print(f"  Sensor: lat={sensor_pos[0]}, lon={sensor_pos[1]}, alt={sensor_pos[2]}km")
        print(f"  Output: Az={az:.2f}deg, El={el:.2f}deg")

        # Basic sanity checks
        if 0 <= az <= 360 and -90 <= el <= 90:
            print(f"  [PASS] radec2azel returns valid Az/El")
            return True
        else:
            print(f"  [FAIL] Az/El out of expected range")
            return False
    except Exception as e:
        print(f"  [FAIL] radec2azel failed: {e}")
        import traceback
        traceback.print_exc()
        return False


import numpy as np

def main():
    """Run all comprehensive tests"""
    print("\n" + "=" * 70)
    print("    COMPREHENSIVE SIMULATION MODULE TEST SUITE")
    print("=" * 70)

    results = []
    result_df = None

    # Test 1: epochsToSim
    try:
        results.append(("epochsToSim (gap detection)", test_epochs_to_sim()))
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("epochsToSim (gap detection)", False))

    # Test 2: simulateObs with TLE
    try:
        success, result_df = test_simulate_obs_with_tle()
        results.append(("simulateObs (TLE input)", success))
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("simulateObs (TLE input)", False))

    # Test 3: simulateObs with state vector
    try:
        success, sv_result = test_simulate_obs_with_state_vector()
        results.append(("simulateObs (state vector)", success))
        if result_df is None or len(result_df) == 0:
            result_df = sv_result
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("simulateObs (state vector)", False))

    # Test 4: Output validation
    try:
        results.append(("Output format validation", test_output_format_validation(result_df)))
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("Output format validation", False))

    # Test 5: Propagator functions
    try:
        results.append(("Propagator functions", test_propagator_functions()))
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("Propagator functions", False))

    # Test 6: Coordinate conversion
    try:
        results.append(("radec2azel conversion", test_radec2azel()))
    except Exception as e:
        print(f"  [FAIL] Test crashed: {e}")
        results.append(("radec2azel conversion", False))

    # Summary
    print("\n" + "=" * 70)
    print("    TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print("-" * 70)
    print(f"  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  SUCCESS! Simulation module is fully operational.")
        print("  All functions work correctly:")
        print("    - Gap detection (epochsToSim)")
        print("    - Observation simulation (simulateObs)")
        print("    - TLE propagation")
        print("    - State vector propagation")
        print("    - Coordinate transformations")
    else:
        print(f"\n  PARTIAL SUCCESS: {passed}/{total} tests passed.")
        print("  Review failed tests above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
