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


class TestSmearSeeingSampler:
    """Tests for the calibrated atmospheric seeing sampler from the
    Smear Explanation reference (518,092 real observations from
    Muztagh-ata II + Lijiang)."""

    def test_smear_seeing_deterministic_default(self):
        """rng=None returns the median percentile (0.375 arcsec)."""
        from uct_benchmark.simulation.noiseModels import sample_smear_seeing_arcsec

        assert sample_smear_seeing_arcsec(rng=None) == 0.375

    def test_smear_seeing_bias_lookup(self):
        """All named percentiles are accessible via the bias parameter."""
        from uct_benchmark.simulation.noiseModels import (
            SMEAR_SEEING_PERCENTILES_ARCSEC,
            sample_smear_seeing_arcsec,
        )

        for level in ["best", "good_day", "median", "bad_day", "really_bad", "worst"]:
            assert sample_smear_seeing_arcsec(rng=None, bias=level) == \
                SMEAR_SEEING_PERCENTILES_ARCSEC[level]

    def test_smear_seeing_within_chart_range(self):
        """Sampled values stay inside [0.25, 1.32] arcsec — the full
        observed range from the Smear doc."""
        from uct_benchmark.simulation.noiseModels import sample_smear_seeing_arcsec

        rng = np.random.default_rng(42)
        samples = [sample_smear_seeing_arcsec(rng=rng) for _ in range(200)]
        assert all(0.25 <= s <= 1.32 for s in samples)
        # Verify the distribution is right-skewed: median should be at or
        # below 0.4875 (worse than the bad_day percentile is rare).
        median_sample = sorted(samples)[len(samples) // 2]
        assert median_sample <= 0.4875


class TestObserverVelocityECI:
    """Tests for the LST-rotated observer velocity in ECI frame.

    The observer at (lat=0, lon=0) at LST=0 has a tangent velocity pointing
    along the +Y ECI axis. As LST rotates 90°, the tangent rotates to -X.
    """

    def test_observer_velocity_magnitude_at_equator(self):
        """At the equator, |v| should be ~0.465 km/s (Earth rotation)."""
        from datetime import datetime, timezone

        from uct_benchmark.simulation.atmospheric import compute_observer_velocity

        v = compute_observer_velocity(
            observer_lat=0.0,
            observer_lon=0.0,
            observer_alt_km=0.0,
            obs_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        speed = np.linalg.norm(v)
        # ω·R_eq ≈ 7.292e-5 · 6378.137 ≈ 0.465 km/s
        assert 0.45 < speed < 0.48
        # Z-component must be zero — the tangent vector lies in the equatorial plane
        assert abs(v[2]) < 1e-10

    def test_observer_velocity_obs_time_none_legacy(self):
        """obs_time=None preserves the legacy [0, v_mag, 0] return for the
        existing test_observer_velocity test (backward compat)."""
        from uct_benchmark.simulation.atmospheric import compute_observer_velocity

        v = compute_observer_velocity(0.0, 0.0, 0.0, None)
        # Legacy path: x and z are zero, y is positive
        assert v[0] == 0.0
        assert v[2] == 0.0
        assert v[1] > 0.0


class TestPhysicalNoisePipelineUnit:
    """Unit tests for the physical-noise pieces wired into simulateObs.

    These tests do NOT exercise the Orekit propagator (which requires the JVM
    to be started before import). Instead they invoke the inner physics
    helpers directly with synthetic ECI inputs. The end-to-end propagator
    integration is exercised in production by the dataset generation worker
    (combined/backend_api/jobs/workers.py) and in the dataset_completeness
    test suite.
    """

    def test_aberration_then_refraction_pipeline(self):
        """The two systematic shifts can be chained without loss of precision
        and produce shifts in the expected arcsecond range for a LEO geometry."""
        from datetime import datetime, timezone

        from uct_benchmark.simulation.atmospheric import (
            compute_observer_velocity,
            compute_velocity_aberration,
            refraction_correction_for_ra_dec,
        )

        # Observer at Maui (GEODSS Haleakala), midnight UTC
        sen_lat, sen_lon, sen_alt_km = 20.7, -156.43, 3.052
        obs_time = datetime(2026, 1, 1, 6, 0, 0, tzinfo=timezone.utc)

        # Synthetic LEO-target geometry
        ra_true, dec_true = 180.0, 30.0
        sat_vel_km_s = np.array([0.0, 7.5, 0.0])  # tangential velocity

        obs_vel = compute_observer_velocity(sen_lat, sen_lon, sen_alt_km, obs_time)
        ra_aberr, dec_aberr = compute_velocity_aberration(
            ra_true, dec_true, obs_vel, target_velocity=sat_vel_km_s
        )

        # Aberration shift should be small (sub-arcminute) for a non-relativistic
        # target. v/c ≈ 7.5/299792 ≈ 2.5e-5 rad ≈ 5 arcsec maximum.
        assert abs(ra_aberr - ra_true) < 1.0 / 60.0  # < 1 arcmin
        assert abs(dec_aberr - dec_true) < 1.0 / 60.0

        # Refraction is a no-op for the input frame because we don't have a
        # below-6° elevation here, but the call must not crash and must
        # return finite floats.
        ra_refr, dec_refr = refraction_correction_for_ra_dec(
            ra_aberr, dec_aberr, sen_lat, sen_lon, sen_alt_km, obs_time
        )
        assert np.isfinite(ra_refr) and np.isfinite(dec_refr)

    def test_apply_physical_noise_uses_smear_seeing(self):
        """A higher seeing percentile must produce a wider noise distribution
        than a lower percentile, holding sensor and elevation fixed."""
        from uct_benchmark.simulation.noiseModels import (
            AtmosphericConditions,
            apply_physical_noise,
            get_sensor_profile,
            sample_smear_seeing_arcsec,
        )

        sensor = get_sensor_profile("GEODSS")
        rng = np.random.default_rng(0)

        # Median day → narrow distribution; really_bad day → wide
        good_atm = AtmosphericConditions(
            seeing_arcsec=sample_smear_seeing_arcsec(rng=None, bias="best")
        )
        bad_atm = AtmosphericConditions(
            seeing_arcsec=sample_smear_seeing_arcsec(rng=None, bias="really_bad")
        )

        _, _, good_model = apply_physical_noise(
            180.0, 30.0, 60.0, sensor=sensor, atmosphere=good_atm, rng=rng
        )
        _, _, bad_model = apply_physical_noise(
            180.0, 30.0, 60.0, sensor=sensor, atmosphere=bad_atm, rng=rng
        )

        # Bad seeing → larger angular noise sigma
        assert bad_model.angular_noise_ra_arcsec > good_model.angular_noise_ra_arcsec

    def test_apply_physical_noise_airmass_scaling(self):
        """At the same atmospheric condition, lower elevation must produce a
        larger noise sigma (Fried's law: σ ∝ airmass^0.6)."""
        from uct_benchmark.simulation.noiseModels import (
            AtmosphericConditions,
            apply_physical_noise,
            get_sensor_profile,
        )

        sensor = get_sensor_profile("GEODSS")
        atmosphere = AtmosphericConditions(seeing_arcsec=0.375)
        rng = np.random.default_rng(0)

        _, _, zenith_model = apply_physical_noise(
            180.0, 60.0, 80.0, sensor=sensor, atmosphere=atmosphere, rng=rng
        )
        _, _, low_model = apply_physical_noise(
            180.0, 60.0, 15.0, sensor=sensor, atmosphere=atmosphere, rng=rng
        )

        assert low_model.angular_noise_ra_arcsec > zenith_model.angular_noise_ra_arcsec

    def test_to_obs_schema_handles_per_row_sigma(self):
        """toObsSchema must accept both the legacy 10-tuple shape and the
        post-physical-noise 11-tuple shape with per-row sigma."""
        from uct_benchmark.simulation.simulateObservations import toObsSchema

        # Legacy 10-tuple — sensorStDev should fall back to scalar
        legacy_results = [
            (
                "2026-01-01T00:00:00",  # ts
                180.0, 30.0,            # ra, dec
                "MUI123",               # sensorID (must be parseable as MUI<digits>)
                20.7, -156.43, 3.052,   # senLat, senLon, senAlt
                90.0, 60.0,             # az, el
                7078e3,                 # rangeVal in meters
            )
        ]
        df_legacy = toObsSchema(legacy_results, satNo=12345, noiseCharacteristics=1.0 / 3600.0)
        assert len(df_legacy) == 1
        assert abs(df_legacy["sensorStDev"].iloc[0] - 1.0 / 3600.0) < 1e-12

        # New 11-tuple with per-row sigma — sensorStDev should use the row value
        new_results = [
            (
                "2026-01-01T00:00:00",
                180.0, 30.0,
                "MUI123",
                20.7, -156.43, 3.052,
                90.0, 60.0,
                7078e3,
                0.5 / 3600.0,  # 0.5 arcsec in degrees
            )
        ]
        df_new = toObsSchema(new_results, satNo=12345, noiseCharacteristics=1.0 / 3600.0)
        assert abs(df_new["sensorStDev"].iloc[0] - 0.5 / 3600.0) < 1e-12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
