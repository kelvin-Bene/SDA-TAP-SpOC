# -*- coding: utf-8 -*-
"""
Tests for simulation enhancements.

Tests:
- Atmospheric refraction
- Velocity aberration
- Sensor noise models
- Photometric simulation
"""

import numpy as np
import pytest


class TestAtmosphericRefraction:
    """Tests for atmospheric refraction model."""

    def test_refraction_at_zenith(self):
        """Test refraction at zenith (90 deg elevation)."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(90.0)
        assert result is not None
        # Refraction at zenith should be very small
        assert abs(result - 90.0) < 0.1

    def test_refraction_at_45_deg(self):
        """Test refraction at 45 degrees elevation."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(45.0)
        assert result is not None
        # Should be slightly higher than true elevation
        assert result > 45.0
        assert result < 46.0

    def test_refraction_at_low_elevation(self):
        """Test refraction at low elevation (near horizon)."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(10.0)
        assert result is not None
        # Large refraction at low elevations
        assert result > 10.0

    def test_refraction_below_threshold(self):
        """Test that very low elevations return None."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(3.0)
        assert result is None

    def test_refraction_negative_elevation(self):
        """Test that negative elevations return None."""
        from uct_benchmark.simulation.atmospheric import apply_atmospheric_refraction

        result = apply_atmospheric_refraction(-5.0)
        assert result is None

    def test_get_refraction_at_elevation(self):
        """Test quick refraction lookup."""
        from uct_benchmark.simulation.atmospheric import get_refraction_at_elevation

        r_45 = get_refraction_at_elevation(45.0)
        r_20 = get_refraction_at_elevation(20.0)

        # Lower elevation should have more refraction
        assert r_20 > r_45


class TestVelocityAberration:
    """Tests for velocity aberration model."""

    def test_aberration_magnitude(self):
        """Test aberration magnitude calculation."""
        from uct_benchmark.simulation.atmospheric import aberration_magnitude_arcsec

        # Earth rotation velocity at equator ~0.46 km/s
        aberration = aberration_magnitude_arcsec(0.46)
        # Should be around 0.3 arcsec
        assert 0.1 < aberration < 1.0

    def test_compute_velocity_aberration(self):
        """Test velocity aberration correction."""
        from uct_benchmark.simulation.atmospheric import compute_velocity_aberration

        ra = 180.0
        dec = 45.0
        observer_vel = np.array([0, 0.46, 0])  # ~equatorial velocity

        ra_corr, dec_corr = compute_velocity_aberration(ra, dec, observer_vel)

        # Corrections should be small (< 1 arcmin)
        assert abs(ra_corr - ra) < 1 / 60
        assert abs(dec_corr - dec) < 1 / 60

    def test_observer_velocity(self):
        """Test observer velocity calculation."""
        from uct_benchmark.simulation.atmospheric import compute_observer_velocity

        vel = compute_observer_velocity(0.0, 0.0, 0.0, None)

        # Should be non-zero
        assert np.linalg.norm(vel) > 0
        # Should be less than 1 km/s
        assert np.linalg.norm(vel) < 1.0


class TestSensorNoiseModels:
    """Tests for sensor-specific noise models."""

    def test_optical_noise_model(self):
        """Test optical sensor noise model."""
        from uct_benchmark.simulation.noise_models import OpticalNoiseModel

        model = OpticalNoiseModel(angular_noise_arcsec=0.5)
        rng = np.random.default_rng(42)

        ra, dec, timing = model.apply_noise(180.0, 45.0, 0, rng)

        # Should be close to original but not exact
        assert abs(ra - 180.0) < 1.0
        assert abs(dec - 45.0) < 1.0

    def test_radar_noise_model(self):
        """Test radar sensor noise model."""
        from uct_benchmark.simulation.noise_models import RadarNoiseModel

        model = RadarNoiseModel(range_noise_m=10.0)
        rng = np.random.default_rng(42)

        range_km, rr, az, el, timing = model.apply_noise(1000.0, 0.1, 45.0, 30.0, 0, rng)

        # Range should be close to original
        assert abs(range_km - 1000.0) < 0.1  # 100m tolerance

    def test_get_sensor_noise_model(self):
        """Test getting sensor noise model by name."""
        from uct_benchmark.simulation.noise_models import (
            OpticalNoiseModel,
            RadarNoiseModel,
            get_sensor_noise_model,
        )

        geodss = get_sensor_noise_model("GEODSS")
        assert isinstance(geodss, OpticalNoiseModel)

        radar = get_sensor_noise_model("Radar")
        assert isinstance(radar, RadarNoiseModel)

    def test_apply_realistic_noise(self):
        """Test combined realistic noise application."""
        from uct_benchmark.settings import SimulationConfig
        from uct_benchmark.simulation.noise_models import apply_realistic_noise

        config = SimulationConfig(apply_sensor_noise=True, sensor_model="GEODSS")
        rng = np.random.default_rng(42)

        ra, dec, timing = apply_realistic_noise(180.0, 45.0, None, "GEODSS", config, rng)

        assert isinstance(ra, float)
        assert isinstance(dec, float)


class TestPhotometricSimulation:
    """Tests for photometric (magnitude) simulation."""

    def test_compute_phase_angle(self):
        """Test phase angle computation."""
        from uct_benchmark.simulation.noise_models import compute_phase_angle

        # Sun, satellite, observer positions
        sat_pos = np.array([7000.0, 0, 0])
        sun_pos = np.array([149597870.7, 0, 0])  # 1 AU
        obs_pos = np.array([6378.0, 0, 0])

        phase = compute_phase_angle(sat_pos, sun_pos, obs_pos)

        # Should be a valid angle
        assert 0 <= phase <= np.pi

    def test_lambertian_phase_function(self):
        """Test Lambertian phase function."""
        from uct_benchmark.simulation.noise_models import lambertian_phase_function

        # Full illumination (phase = 0)
        f_full = lambertian_phase_function(0)
        assert f_full > 0.6

        # Quarter phase
        f_quarter = lambertian_phase_function(np.pi / 2)
        assert 0 < f_quarter < f_full

        # Back-illuminated (phase = pi)
        f_back = lambertian_phase_function(np.pi)
        assert f_back >= 0

    def test_simulate_magnitude(self):
        """Test magnitude simulation."""
        from uct_benchmark.simulation.noise_models import simulate_magnitude

        # Set up geometry where satellite is illuminated from observer's perspective
        # Observer on Earth surface, satellite overhead, sun at 90 degrees
        obs_pos = np.array([6378.0, 0, 0])  # Observer on Earth surface
        sat_pos = np.array([7000.0, 0, 0])  # Satellite 622km above
        sun_pos = np.array([0, 149597870.7, 0])  # Sun perpendicular to obs-sat line

        mag = simulate_magnitude(sat_pos, sun_pos, obs_pos, 10.0, 0.2)

        # Should be a reasonable magnitude for LEO satellite
        # Typical LEO satellites are mag 2-8, but can be dimmer depending on phase
        assert -10 < mag < 25

    def test_sun_position_approx(self):
        """Test approximate sun position calculation."""
        from datetime import datetime

        from uct_benchmark.simulation.noise_models import get_sun_position_approx

        sun_pos = get_sun_position_approx(datetime(2025, 6, 21, 12, 0, 0))

        # Should be approximately 1 AU from origin
        dist = np.linalg.norm(sun_pos)
        assert 0.98 * 149597870.7 < dist < 1.02 * 149597870.7

    def test_satellite_illumination(self):
        """Test satellite illumination check."""
        from uct_benchmark.simulation.noise_models import is_satellite_illuminated

        sun_pos = np.array([149597870.7, 0, 0])

        # Satellite on sun side - should be illuminated
        sat_sunside = np.array([7000.0, 0, 0])
        assert is_satellite_illuminated(sat_sunside, sun_pos)

        # Satellite behind Earth (in shadow)
        sat_shadow = np.array([-7000.0, 0, 0])
        assert not is_satellite_illuminated(sat_shadow, sun_pos)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
