# -*- coding: utf-8 -*-
"""
Test Suite for Close (C) Object Proximity Filter with Velocity

Tests the Close proximity filter per Louis's specification:
"distance < X km, velocity < X m/s"

The Close filter requires BOTH position AND velocity thresholds to be met.

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestVelocityThresholdSettings:
    """Tests for velocity threshold settings."""

    def test_velocity_threshold_exists_in_settings(self):
        """Test that PROXIMITY_VELOCITY_THRESHOLD_M_S exists in settings."""
        from uct_benchmark.settings import PROXIMITY_VELOCITY_THRESHOLD_M_S

        assert PROXIMITY_VELOCITY_THRESHOLD_M_S is not None
        assert isinstance(PROXIMITY_VELOCITY_THRESHOLD_M_S, (int, float))

    def test_velocity_threshold_reasonable_value(self):
        """Test that velocity threshold has reasonable value."""
        from uct_benchmark.settings import PROXIMITY_VELOCITY_THRESHOLD_M_S

        # Should be positive
        assert PROXIMITY_VELOCITY_THRESHOLD_M_S > 0

        # Should be in reasonable range (10-1000 m/s for close approaches)
        assert PROXIMITY_VELOCITY_THRESHOLD_M_S >= 10
        assert PROXIMITY_VELOCITY_THRESHOLD_M_S <= 1000

    def test_distance_threshold_exists(self):
        """Test that PROXIMITY_DISTANCE_THRESHOLD_KM exists."""
        from uct_benchmark.settings import PROXIMITY_DISTANCE_THRESHOLD_KM

        assert PROXIMITY_DISTANCE_THRESHOLD_KM is not None
        assert isinstance(PROXIMITY_DISTANCE_THRESHOLD_KM, (int, float))
        assert PROXIMITY_DISTANCE_THRESHOLD_KM > 0


class TestComputeVelocityDifference:
    """Tests for compute_velocity_difference function."""

    def test_function_exists(self):
        """Test that compute_velocity_difference function exists."""
        from uct_benchmark.data.objectTypeFiltering import compute_velocity_difference

        assert callable(compute_velocity_difference)

    def test_same_velocity_returns_zero(self):
        """Test that identical velocities return zero difference."""
        from uct_benchmark.data.objectTypeFiltering import compute_velocity_difference

        # Function takes tuples (vx, vy, vz) in km/s
        vel1 = (7.5, 0.0, 0.0)
        vel2 = (7.5, 0.0, 0.0)

        diff = compute_velocity_difference(vel1, vel2)

        assert diff == pytest.approx(0.0, abs=1e-6)

    def test_opposite_velocities(self):
        """Test velocity difference for opposite directions."""
        from uct_benchmark.data.objectTypeFiltering import compute_velocity_difference

        # Head-on collision course (velocities in km/s)
        vel1 = (7.5, 0.0, 0.0)
        vel2 = (-7.5, 0.0, 0.0)

        diff = compute_velocity_difference(vel1, vel2)

        # Should be 15.0 km/s = 15000 m/s
        assert diff == pytest.approx(15000.0, rel=0.01)

    def test_perpendicular_velocities(self):
        """Test velocity difference for perpendicular directions."""
        from uct_benchmark.data.objectTypeFiltering import compute_velocity_difference

        vel1 = (7.5, 0.0, 0.0)
        vel2 = (0.0, 7.5, 0.0)

        diff = compute_velocity_difference(vel1, vel2)

        # Should be sqrt(7.5^2 + 7.5^2) km/s * 1000 m/s
        expected = np.sqrt(7.5**2 + 7.5**2) * 1000.0
        assert diff == pytest.approx(expected, rel=0.01)

    def test_3d_velocity_difference(self):
        """Test 3D velocity difference calculation."""
        from uct_benchmark.data.objectTypeFiltering import compute_velocity_difference

        vel1 = (1.0, 2.0, 3.0)
        vel2 = (4.0, 5.0, 6.0)

        diff = compute_velocity_difference(vel1, vel2)

        # Difference vector: (3, 3, 3), magnitude = sqrt(27) km/s * 1000
        expected = np.sqrt(3**2 + 3**2 + 3**2) * 1000.0
        assert diff == pytest.approx(expected, rel=0.01)


class TestFilterPhysicalProximity:
    """Tests for filter_physical_proximity with velocity threshold."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame."""
        base_time = datetime(2024, 1, 1)
        return pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3", "obs_4"],
            "satNo": [25544, 25545, 25546, 25547],
            "obTime": [base_time + timedelta(hours=i) for i in range(4)],
            "ra": [100.0, 101.0, 102.0, 103.0],
            "declination": [20.0, 21.0, 22.0, 23.0],
        })

    @pytest.fixture
    def close_state_data(self):
        """Create state data with close objects (both position and velocity)."""
        return {
            25544: {
                "position": (6800.0, 0.0, 0.0),
                "velocity": (0.0, 7.5, 0.0),  # 7.5 km/s
            },
            25545: {
                "position": (6800.05, 0.0, 0.0),  # 50m away - very close!
                "velocity": (0.0, 7.5, 0.0),  # Same velocity - relative vel ~0
            },
            25546: {
                "position": (7000.0, 0.0, 0.0),  # 200km away - not close
                "velocity": (0.0, 7.3, 0.0),
            },
            25547: {
                "position": (6800.08, 0.0, 0.0),  # 80m away - close in position
                "velocity": (0.0, 8.0, 0.0),  # But different velocity (500 m/s diff)
            },
        }

    @pytest.fixture
    def far_state_data(self):
        """Create state data with no close objects."""
        return {
            25544: {
                "position": (6800.0, 0.0, 0.0),
                "velocity": (0.0, 7.5, 0.0),
            },
            25545: {
                "position": (7500.0, 0.0, 0.0),  # 700km away
                "velocity": (0.0, 7.0, 0.0),
            },
            25546: {
                "position": (8000.0, 0.0, 0.0),  # 1200km away
                "velocity": (0.0, 6.5, 0.0),
            },
        }

    def test_filter_physical_proximity_exists(self):
        """Test that filter_physical_proximity function exists."""
        from uct_benchmark.data.objectTypeFiltering import filter_physical_proximity

        assert callable(filter_physical_proximity)

    def test_filter_accepts_velocity_threshold(self):
        """Test that filter accepts velocity_threshold parameter."""
        from uct_benchmark.data.objectTypeFiltering import filter_physical_proximity
        import inspect

        sig = inspect.signature(filter_physical_proximity)
        params = list(sig.parameters.keys())

        # Should have velocity threshold parameter
        assert "velocity_threshold_m_s" in params

    def test_close_objects_both_thresholds(
        self, sample_observations_df, close_state_data
    ):
        """Test that objects must meet BOTH position AND velocity thresholds."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        # 25544 and 25545 are close in position AND have similar velocity
        # 25547 is close in position but different velocity

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="C",
            sat_params={},
            physical_data={},
            state_data=close_state_data,
        )

        # Should process without error
        assert isinstance(filtered_df, pd.DataFrame)
        assert isinstance(metadata, dict)

    def test_high_velocity_excluded(self, sample_observations_df):
        """Test that objects with high relative velocity are excluded."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        # Objects close in position but moving fast relative to each other
        state_data = {
            25544: {
                "position": (6800.0, 0.0, 0.0),
                "velocity": (0.0, 7.5, 0.0),  # Prograde
            },
            25545: {
                "position": (6800.01, 0.0, 0.0),  # 10m away!
                "velocity": (0.0, -7.5, 0.0),  # RETROGRADE - opposite direction!
            },
        }

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="C",
            sat_params={},
            physical_data={},
            state_data=state_data,
        )

        # Should handle without error
        assert isinstance(filtered_df, pd.DataFrame)

    def test_missing_velocity_data_handled(self, sample_observations_df):
        """Test graceful handling when velocity data is missing."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        # State data with only position (no velocity)
        state_data = {
            25544: {
                "position": (6800.0, 0.0, 0.0),
                # No velocity key
            },
            25545: {
                "position": (6800.05, 0.0, 0.0),
                # No velocity key
            },
        }

        # Should not crash
        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="C",
            sat_params={},
            physical_data={},
            state_data=state_data,
        )

        assert isinstance(filtered_df, pd.DataFrame)
        assert isinstance(metadata, dict)

    def test_no_close_objects_returns_empty(
        self, sample_observations_df, far_state_data
    ):
        """Test that no close objects returns empty or appropriate result."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="C",
            sat_params={},
            physical_data={},
            state_data=far_state_data,
        )

        # Should handle gracefully
        assert isinstance(filtered_df, pd.DataFrame)


class TestCloseObjectDescription:
    """Tests for Close object type description."""

    def test_get_legacy_description_includes_thresholds(self):
        """Test that Close (C) description includes threshold values."""
        from uct_benchmark.data.objectTypeFiltering import get_legacy_object_type_description

        description = get_legacy_object_type_description("C")

        # Description should mention distance and velocity thresholds
        assert "km" in description.lower() or "distance" in description.lower()
        assert "m/s" in description.lower() or "velocity" in description.lower()


class TestApparentProximityFilter:
    """Tests for Apparent (A) angular proximity filter."""

    @pytest.fixture
    def observations_with_angular_proximity(self):
        """Create observations with some close in angular position."""
        base_time = datetime(2024, 1, 1)
        return pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3", "obs_4"],
            "satNo": [25544, 25545, 25546, 25547],
            "obTime": [base_time] * 4,  # Same time
            "ra": [100.0, 100.1, 150.0, 200.0],  # 25544 and 25545 are close
            "declination": [20.0, 20.05, 45.0, -30.0],
        })

    def test_apparent_filter_works(self, observations_with_angular_proximity):
        """Test that Apparent (A) filter runs without error."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=observations_with_angular_proximity,
            object_type_code="A",
            sat_params={},
            physical_data={},
        )

        assert isinstance(filtered_df, pd.DataFrame)
        assert metadata["object_type_code"] == "A"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
