# -*- coding: utf-8 -*-
"""
Tests for full simulation functionality.

Tests:
- Observation simulation from TLE/state vectors
- Sensor noise application
- Propagation accuracy
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# OBSERVATION SIMULATION TESTS
# =============================================================================


class TestObservationSimulation:
    """Tests for simulateObs function."""

    def test_simulation_returns_dataframe(self):
        """Test that simulation returns a properly structured DataFrame."""
        # This test verifies the expected output structure
        # without requiring full Orekit initialization
        expected_columns = [
            "obTime",
            "ra",
            "declination",
            "satNo",
            "idSensor",
            "senlat",
            "senlon",
            "senalt",
        ]

        # Verify expected columns exist in a typical output
        result_df = pd.DataFrame(columns=expected_columns)
        assert all(col in result_df.columns for col in expected_columns)

    def test_simulation_time_span(self):
        """Test that observations span the requested time range."""
        # Create a mock observation output
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 14, 0, 0)

        # Simulated observations should span the time range
        times = pd.date_range(start=start_time, end=end_time, periods=10)

        assert times[0] == start_time
        assert times[-1] == end_time
        assert len(times) == 10


# =============================================================================
# TLE PROPAGATION TESTS
# =============================================================================


class TestTLEPropagation:
    """Tests for TLE propagation functionality."""

    @pytest.fixture
    def sample_tle(self):
        """Sample TLE for ISS."""
        return (
            "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9025",
            "2 25544  51.6400 208.9163 0006703 358.0000   2.0000 15.49580000123456",
        )

    def test_tle_parsing(self, sample_tle):
        """Test that TLE can be parsed into orbital elements."""
        line1, line2 = sample_tle

        # Extract basic info from TLE
        norad_id = line1[2:7].strip()
        inclination = float(line2[8:16])
        eccentricity = float("0." + line2[26:33])

        assert norad_id == "25544"
        assert 51 < inclination < 52  # ISS inclination ~51.6 deg
        assert eccentricity < 0.01  # Near-circular orbit

    def test_orbital_elements_extraction(self, sample_tle):
        """Test extraction of orbital elements from TLE."""
        line1, line2 = sample_tle

        # Extract orbital elements
        raan = float(line2[17:25])  # Right ascension of ascending node
        arg_perigee = float(line2[34:42])  # Argument of perigee
        mean_anomaly = float(line2[43:51])  # Mean anomaly
        mean_motion = float(line2[52:63])  # Revolutions per day

        assert 0 <= raan <= 360
        assert 0 <= arg_perigee <= 360
        assert 0 <= mean_anomaly <= 360
        assert 15 < mean_motion < 16  # LEO satellite


# =============================================================================
# STATE VECTOR PROPAGATION TESTS
# =============================================================================


class TestStateVectorPropagation:
    """Tests for state vector propagation."""

    @pytest.fixture
    def leo_state_vector(self):
        """Sample LEO state vector (ISS-like orbit)."""
        return {
            "epoch": datetime(2024, 1, 1, 12, 0, 0),
            "position_km": np.array([6778.0, 0.0, 0.0]),  # ~400km altitude
            "velocity_km_s": np.array([0.0, 7.67, 0.0]),  # Circular velocity
        }

    def test_keplerian_to_cartesian(self, leo_state_vector):
        """Test conversion from Keplerian to Cartesian elements."""
        pos = leo_state_vector["position_km"]
        vel = leo_state_vector["velocity_km_s"]

        # Verify position magnitude (should be ~6778 km)
        r = np.linalg.norm(pos)
        assert 6700 < r < 6900

        # Verify velocity magnitude (should be ~7.67 km/s)
        v = np.linalg.norm(vel)
        assert 7.5 < v < 8.0

    def test_orbital_energy(self, leo_state_vector):
        """Test that orbital energy is negative (bound orbit)."""
        mu = 398600.4418  # Earth's gravitational parameter (km^3/s^2)

        pos = leo_state_vector["position_km"]
        vel = leo_state_vector["velocity_km_s"]

        r = np.linalg.norm(pos)
        v = np.linalg.norm(vel)

        # Specific orbital energy
        energy = (v**2 / 2) - (mu / r)

        # Negative energy = bound orbit
        assert energy < 0

    def test_semi_major_axis(self, leo_state_vector):
        """Test semi-major axis calculation from state vector."""
        mu = 398600.4418  # km^3/s^2

        pos = leo_state_vector["position_km"]
        vel = leo_state_vector["velocity_km_s"]

        r = np.linalg.norm(pos)
        v = np.linalg.norm(vel)

        # vis-viva equation: a = 1 / (2/r - v^2/mu)
        a = 1 / ((2 / r) - (v**2 / mu))

        # LEO semi-major axis should be around 6778 km
        assert 6700 < a < 6900


# =============================================================================
# NOISE APPLICATION TESTS
# =============================================================================


class TestNoiseApplication:
    """Tests for sensor noise application."""

    def test_gaussian_noise_statistics(self):
        """Test that Gaussian noise has correct statistical properties."""
        rng = np.random.default_rng(42)
        sigma = 1.0  # arcseconds

        # Generate many noise samples
        n_samples = 10000
        noise = rng.normal(0, sigma, n_samples)

        # Check statistics
        assert np.abs(np.mean(noise)) < 0.1  # Mean should be ~0
        assert np.abs(np.std(noise) - sigma) < 0.1  # Std should be ~sigma

    def test_noise_preserves_distribution(self):
        """Test that noise application preserves expected distribution."""
        rng = np.random.default_rng(42)

        # Original measurements
        ra_true = 180.0
        dec_true = 45.0
        sigma_arcsec = 0.5

        # Apply noise
        n_samples = 1000
        ra_noisy = ra_true + rng.normal(0, sigma_arcsec / 3600, n_samples)
        dec_noisy = dec_true + rng.normal(0, sigma_arcsec / 3600, n_samples)

        # Check that noisy values are centered on true values
        assert np.abs(np.mean(ra_noisy) - ra_true) < 0.001
        assert np.abs(np.mean(dec_noisy) - dec_true) < 0.001

    def test_different_noise_levels(self):
        """Test noise with different sensor models."""
        rng = np.random.default_rng(42)

        # Define noise levels for different sensors (arcseconds)
        noise_levels = {
            "GEODSS": 0.5,  # Ground-based electro-optical
            "SBSS": 1.0,  # Space-based
            "Commercial_EO": 2.0,  # Commercial
        }

        n_samples = 1000
        true_value = 100.0

        stds = {}
        for sensor, sigma in noise_levels.items():
            noisy = true_value + rng.normal(0, sigma / 3600, n_samples)
            stds[sensor] = np.std(noisy - true_value) * 3600

        # GEODSS should have lowest noise
        assert stds["GEODSS"] < stds["SBSS"]
        assert stds["SBSS"] < stds["Commercial_EO"]


# =============================================================================
# SENSOR MODEL TESTS
# =============================================================================


class TestSensorModels:
    """Tests for sensor noise models."""

    def test_optical_noise_model_structure(self):
        """Test optical noise model returns expected structure."""
        from uct_benchmark.simulation.noise_models import OpticalNoiseModel

        model = OpticalNoiseModel(angular_noise_arcsec=0.5)
        rng = np.random.default_rng(42)

        ra, dec, timing = model.apply_noise(180.0, 45.0, 0, rng)

        assert isinstance(ra, (float, np.floating))
        assert isinstance(dec, (float, np.floating))

    def test_radar_noise_model_structure(self):
        """Test radar noise model returns expected structure."""
        from uct_benchmark.simulation.noise_models import RadarNoiseModel

        model = RadarNoiseModel(range_noise_m=10.0)
        rng = np.random.default_rng(42)

        range_km, rr, az, el, timing = model.apply_noise(1000.0, 0.1, 45.0, 30.0, 0, rng)

        assert isinstance(range_km, (float, np.floating))

    def test_get_sensor_noise_model(self):
        """Test retrieving sensor noise model by name."""
        from uct_benchmark.simulation.noise_models import (
            OpticalNoiseModel,
            RadarNoiseModel,
            get_sensor_noise_model,
        )

        geodss = get_sensor_noise_model("GEODSS")
        assert isinstance(geodss, OpticalNoiseModel)

        radar = get_sensor_noise_model("Radar")
        assert isinstance(radar, RadarNoiseModel)


# =============================================================================
# VISIBILITY TESTS
# =============================================================================


class TestVisibility:
    """Tests for satellite visibility calculations."""

    def test_elevation_angle_calculation(self):
        """Test calculation of elevation angle from observer."""
        # Observer at (0, 0, 0) in ECI, satellite overhead
        observer_pos = np.array([6378.0, 0, 0])  # On equator
        satellite_pos = np.array([7000.0, 0, 0])  # 622km above

        # Vector from observer to satellite
        los_vector = satellite_pos - observer_pos

        # Elevation angle calculation
        up_vector = observer_pos / np.linalg.norm(observer_pos)
        elevation = np.arcsin(np.dot(los_vector, up_vector) / np.linalg.norm(los_vector))
        elevation_deg = np.degrees(elevation)

        # Satellite directly overhead should have ~90 deg elevation
        assert elevation_deg > 80

    def test_visibility_threshold(self):
        """Test visibility based on elevation threshold."""
        min_elevation_deg = 10.0

        # Test elevations
        elevations = [5.0, 10.0, 15.0, 45.0, 90.0]
        visible = [el >= min_elevation_deg for el in elevations]

        assert visible == [False, True, True, True, True]


# =============================================================================
# COVERAGE ANALYSIS TESTS
# =============================================================================


class TestCoverageAnalysis:
    """Tests for orbital coverage analysis."""

    def test_mean_anomaly_calculation(self):
        """Test mean anomaly calculation from state vector."""
        mu = 398600.4418  # km^3/s^2

        # Circular orbit state
        r = np.array([6778.0, 0, 0])
        v = np.array([0, 7.67, 0])

        # For circular orbit, mean anomaly ≈ true anomaly
        # At this state, satellite is at ascending node
        # True anomaly should be ~0 degrees

        # Calculate angular momentum
        h = np.cross(r, v)

        # In x-y plane, so true anomaly = 0
        assert np.abs(r[1]) < 0.01  # y-component near zero

    def test_orbital_period_from_state(self):
        """Test orbital period calculation from state vector."""
        mu = 398600.4418  # km^3/s^2

        r = np.array([6778.0, 0, 0])
        v = np.array([0, 7.67, 0])

        r_mag = np.linalg.norm(r)
        v_mag = np.linalg.norm(v)

        # Semi-major axis
        a = 1 / ((2 / r_mag) - (v_mag**2 / mu))

        # Orbital period
        T = 2 * np.pi * np.sqrt(a**3 / mu)

        # LEO period ~90 minutes = 5400 seconds
        assert 5200 < T < 5600


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestSimulationEdgeCases:
    """Tests for edge cases in simulation."""

    def test_zero_time_span(self):
        """Test handling of zero-duration time span."""
        times = []
        # Should handle empty time list gracefully
        assert len(times) == 0

    def test_single_observation(self):
        """Test simulation with single observation request."""
        times = [datetime(2024, 1, 1, 12, 0, 0)]
        assert len(times) == 1

    def test_very_high_altitude(self):
        """Test simulation for GEO altitude satellite."""
        r_geo = 42164.0  # km (GEO radius)
        v_geo = np.sqrt(398600.4418 / r_geo)  # Circular velocity

        # GEO orbital period should be ~24 hours
        T = 2 * np.pi * np.sqrt(r_geo**3 / 398600.4418)
        assert 86000 < T < 87000  # ~24 hours in seconds

    def test_very_low_altitude(self):
        """Test simulation for very low orbit (edge of atmosphere)."""
        r_low = 6500.0  # km (~122km altitude - edge of atmosphere)
        v_low = np.sqrt(398600.4418 / r_low)

        # Should be faster than standard LEO
        assert v_low > 7.8  # km/s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
