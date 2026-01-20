# -*- coding: utf-8 -*-
"""
Orekit Installation Test Script

Run this script to verify that Orekit is properly installed and configured.
Usage: python tests/test_orekit_installation.py

Requirements:
- Java JDK 11+ installed and in PATH
- orekit-jpype package installed
- orekitdata package installed (for bundled data files)
"""

import sys


def test_java_installation():
    """Test 1: Check Java is available"""
    print("=" * 60)
    print("Test 1: Checking Java installation...")

    import subprocess
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            # Java version is usually in stderr
            version_info = result.stderr if result.stderr else result.stdout
            print(f"  [PASS] Java is installed")
            print(f"  Version info: {version_info.split(chr(10))[0]}")
            return True
        else:
            print(f"  [FAIL] Java returned error code {result.returncode}")
            return False
    except FileNotFoundError:
        print("  [FAIL] Java not found in PATH")
        print("  Please install Java JDK 11+ from https://adoptium.net/")
        return False


def test_orekit_jpype_import():
    """Test 2: Check orekit-jpype package can be imported"""
    print("=" * 60)
    print("Test 2: Testing orekit-jpype import...")

    try:
        import orekit_jpype as orekit
        print(f"  [PASS] orekit_jpype imported successfully")
        return True
    except ImportError as e:
        print(f"  [FAIL] Cannot import orekit_jpype: {e}")
        print("  Run: pip install orekit-jpype")
        return False


def test_jvm_initialization():
    """Test 3: Initialize the JVM"""
    print("=" * 60)
    print("Test 3: Testing JVM initialization...")

    try:
        import orekit_jpype as orekit
        vm_started = orekit.initVM()
        print(f"  [PASS] JVM initialized (started={vm_started})")
        return True
    except Exception as e:
        print(f"  [FAIL] JVM initialization failed: {e}")
        print("  Check JAVA_HOME environment variable")
        return False


def test_orekit_data():
    """Test 4: Load Orekit data files"""
    print("=" * 60)
    print("Test 4: Testing Orekit data loading...")

    try:
        import orekit_jpype as orekit
        from orekit_jpype.pyhelpers import setup_orekit_curdir

        orekit.initVM()
        setup_orekit_curdir(from_pip_library=True)
        print(f"  [PASS] Orekit data loaded from pip library")
        return True
    except Exception as e:
        print(f"  [FAIL] Cannot load Orekit data: {e}")
        print("  Run: pip install orekitdata")
        return False


def test_orekit_basic_functionality():
    """Test 5: Test basic Orekit functionality"""
    print("=" * 60)
    print("Test 5: Testing basic Orekit functionality...")

    try:
        import orekit_jpype as orekit
        from orekit_jpype.pyhelpers import setup_orekit_curdir

        orekit.initVM()
        setup_orekit_curdir(from_pip_library=True)

        # Test time scales
        from org.orekit.time import TimeScalesFactory, AbsoluteDate
        utc = TimeScalesFactory.getUTC()
        date = AbsoluteDate(2025, 1, 1, 0, 0, 0.0, utc)
        print(f"  [PASS] TimeScalesFactory works - Created date: {date}")

        # Test frames
        from org.orekit.frames import FramesFactory
        eme2000 = FramesFactory.getEME2000()
        print(f"  [PASS] FramesFactory works - EME2000 frame: {eme2000.getName()}")

        # Test constants
        from org.orekit.utils import Constants
        mu = Constants.WGS84_EARTH_MU
        print(f"  [PASS] Constants available - Earth GM: {mu:.4e} m^3/s^2")

        return True
    except Exception as e:
        print(f"  [FAIL] Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tle_propagation():
    """Test 6: Test TLE propagation"""
    print("=" * 60)
    print("Test 6: Testing TLE propagation...")

    try:
        import orekit_jpype as orekit
        from orekit_jpype.pyhelpers import setup_orekit_curdir
        import numpy as np

        orekit.initVM()
        setup_orekit_curdir(from_pip_library=True)

        from org.orekit.propagation.analytical.tle import TLE, TLEPropagator

        # ISS TLE (sample)
        line1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
        line2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"

        tle = TLE(line1, line2)
        propagator = TLEPropagator.selectExtrapolator(tle)

        # Get state at TLE epoch
        date = tle.getDate()
        pv = propagator.getPVCoordinates(date)

        pos = np.array(pv.getPosition().toArray()) / 1000  # Convert to km
        print(f"  [PASS] TLE propagation works")
        print(f"  Position (km): [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")

        return True
    except Exception as e:
        print(f"  [FAIL] TLE propagation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulation_module_import():
    """Test 7: Test simulation module imports"""
    print("=" * 60)
    print("Test 7: Testing simulation module import...")

    try:
        # Initialize Orekit first (needed for module-level imports)
        import orekit_jpype as orekit
        from orekit_jpype.pyhelpers import setup_orekit_curdir
        orekit.initVM()
        setup_orekit_curdir(from_pip_library=True)

        # Now import the simulation module
        from uct_benchmark.simulation import simulateObservations
        print(f"  [PASS] simulateObservations module imported")

        # Check for key functions
        assert hasattr(simulateObservations, 'simulateObs'), "Missing simulateObs function"
        assert hasattr(simulateObservations, 'epochsToSim'), "Missing epochsToSim function"
        print(f"  [PASS] Key functions available: simulateObs, epochsToSim")

        return True
    except ImportError as e:
        print(f"  [FAIL] Cannot import simulation module: {e}")
        return False
    except AssertionError as e:
        print(f"  [FAIL] Missing function: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_propagator_module():
    """Test 8: Test propagator module"""
    print("=" * 60)
    print("Test 8: Testing propagator module...")

    try:
        from datetime import datetime
        import numpy as np

        # Initialize Orekit first
        import orekit_jpype as orekit
        from orekit_jpype.pyhelpers import setup_orekit_curdir
        orekit.initVM()
        setup_orekit_curdir(from_pip_library=True)

        # Import propagator functions
        from uct_benchmark.simulation.propagator import TLEpropagator

        # Test with ISS TLE
        line1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
        line2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"

        # Propagate 1 hour ahead
        final_epochs = [datetime(2021, 10, 2, 14, 8, 57, 360000)]  # Roughly TLE epoch + 1hr

        tles1, tles2, states = TLEpropagator(line1, line2, final_epochs)

        print(f"  [PASS] TLEpropagator works")
        print(f"  Propagated state position (km): [{states[0][0]:.1f}, {states[0][1]:.1f}, {states[0][2]:.1f}]")

        return True
    except Exception as e:
        print(f"  [FAIL] Propagator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("    OREKIT INSTALLATION TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests in order
    results.append(("Java Installation", test_java_installation()))
    results.append(("orekit-jpype Import", test_orekit_jpype_import()))

    # Only continue if basic imports work
    if results[-1][1]:
        results.append(("JVM Initialization", test_jvm_initialization()))

    if all(r[1] for r in results):
        results.append(("Orekit Data Loading", test_orekit_data()))

    if all(r[1] for r in results):
        results.append(("Basic Functionality", test_orekit_basic_functionality()))
        results.append(("TLE Propagation", test_tle_propagation()))
        results.append(("Simulation Module Import", test_simulation_module_import()))
        results.append(("Propagator Module", test_propagator_module()))

    # Summary
    print("\n" + "=" * 60)
    print("    TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print("-" * 60)
    print(f"  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  SUCCESS! Orekit is properly installed and configured.")
        print("  You can now run the simulation module.")
    else:
        print("\n  INCOMPLETE: Some tests failed. Please fix the issues above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
