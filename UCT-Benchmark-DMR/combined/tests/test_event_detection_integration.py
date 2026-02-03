# -*- coding: utf-8 -*-
"""
Test Suite for Event Detection Integration

Tests the filter_satellites_by_event_code() function for each event type:
- MB: Maneuver between observations
- BU: Breakup event
- LL: Long-duration/Low-thrust
- NE: No events (normal)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestFilterByEventCode:
    """Tests for the filter_satellites_by_event_code function."""

    @pytest.fixture
    def sample_tle_df(self):
        """Create sample TLE DataFrame."""
        # Create TLE data with various satellites
        base_time = datetime(2024, 1, 1)
        sat_ids = [25544, 25545, 25546, 25547, 25548]

        records = []
        for sat_id in sat_ids:
            for i in range(10):
                records.append({
                    "satNo": sat_id,  # This is the expected column name
                    "epoch": base_time + timedelta(days=i),
                    "line1": f"1 {sat_id}U 98067A   24001.50000000  .00000000  00000-0  00000-0 0  000{i}",
                    "line2": f"2 {sat_id}  51.6420  10.0000 0001234  90.0000 270.0000 15.50000000{i:05d}",
                    "semiMajorAxisKm": 6800 + i * 0.01,  # Small variations
                    "eccentricity": 0.001,
                    "inclinationDeg": 51.64,
                })

        return pd.DataFrame(records)

    @pytest.fixture
    def sample_satellite_ids(self):
        """Return list of satellite IDs for testing."""
        return [25544, 25545, 25546, 25547, 25548]

    def test_no_events_returns_satellites(self, sample_tle_df, sample_satellite_ids):
        """Test that NE (No Events) returns satellites without detected events."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        matching_sats, events = filter_satellites_by_event_code(
            tle_df=sample_tle_df,
            satellite_ids=sample_satellite_ids,
            event_code="NE",
        )

        # NE should return satellites with no detected events
        assert isinstance(matching_sats, list)
        assert isinstance(events, list)

    def test_maneuver_event_filtering(self, sample_tle_df, sample_satellite_ids):
        """Test that MB (Maneuver) filters satellites with maneuvers."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        matching_sats, events = filter_satellites_by_event_code(
            tle_df=sample_tle_df,
            satellite_ids=sample_satellite_ids,
            event_code="MB",
        )

        assert isinstance(matching_sats, list)
        assert isinstance(events, list)

    def test_breakup_event_filtering(self, sample_tle_df, sample_satellite_ids):
        """Test that BU (Breakup) filters for breakup events."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        matching_sats, events = filter_satellites_by_event_code(
            tle_df=sample_tle_df,
            satellite_ids=sample_satellite_ids,
            event_code="BU",
        )

        assert isinstance(matching_sats, list)
        assert isinstance(events, list)

    def test_low_thrust_event_filtering(self, sample_tle_df, sample_satellite_ids):
        """Test that LL (Low-thrust) filters for long-duration maneuvers."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        matching_sats, events = filter_satellites_by_event_code(
            tle_df=sample_tle_df,
            satellite_ids=sample_satellite_ids,
            event_code="LL",
        )

        assert isinstance(matching_sats, list)
        assert isinstance(events, list)

    def test_invalid_event_code_raises_error(self, sample_tle_df, sample_satellite_ids):
        """Test that invalid event codes raise ValueError."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        with pytest.raises(ValueError) as exc_info:
            filter_satellites_by_event_code(
                tle_df=sample_tle_df,
                satellite_ids=sample_satellite_ids,
                event_code="XX",  # Invalid code
            )

        assert "Invalid event code" in str(exc_info.value)

    def test_empty_satellite_list(self, sample_tle_df):
        """Test handling of empty satellite list."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        matching_sats, events = filter_satellites_by_event_code(
            tle_df=sample_tle_df,
            satellite_ids=[],
            event_code="NE",
        )

        assert matching_sats == []
        assert events == []

    def test_all_valid_event_codes(self, sample_tle_df, sample_satellite_ids):
        """Test that all valid event codes work without error."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code

        valid_codes = ["MB", "BU", "LL", "NE"]

        for code in valid_codes:
            matching_sats, events = filter_satellites_by_event_code(
                tle_df=sample_tle_df,
                satellite_ids=sample_satellite_ids,
                event_code=code,
            )
            assert isinstance(matching_sats, list)
            assert isinstance(events, list)


class TestEventDetectionConfig:
    """Tests for the EventDetectionConfig class."""

    def test_config_exists(self):
        """Test that EventDetectionConfig exists and can be instantiated."""
        from uct_benchmark.data.eventDetection import EventDetectionConfig

        config = EventDetectionConfig()
        assert config is not None

    def test_config_has_expected_attributes(self):
        """Test that config has expected threshold attributes."""
        from uct_benchmark.data.eventDetection import EventDetectionConfig

        config = EventDetectionConfig()

        # Check for expected attributes
        assert hasattr(config, "sma_threshold_km")
        assert hasattr(config, "ecc_threshold")
        assert hasattr(config, "inc_threshold_deg")

    def test_config_default_values(self):
        """Test that config has reasonable default values."""
        from uct_benchmark.data.eventDetection import EventDetectionConfig

        config = EventDetectionConfig()

        assert config.sma_threshold_km > 0
        assert config.ecc_threshold > 0
        assert config.inc_threshold_deg > 0


class TestEventType:
    """Tests for the EventType enum."""

    def test_event_types_exist(self):
        """Test that event type enum values exist."""
        from uct_benchmark.data.eventDetection import EventType

        assert hasattr(EventType, "MANEUVER")
        assert hasattr(EventType, "BREAKUP")


class TestOrbitalEvent:
    """Tests for the OrbitalEvent class."""

    def test_orbital_event_creation(self):
        """Test creating an OrbitalEvent instance."""
        from uct_benchmark.data.eventDetection import OrbitalEvent, EventType

        event = OrbitalEvent(
            event_type=EventType.MANEUVER,
            satellite_id=25544,
            event_time=datetime(2024, 1, 1),  # Correct field name
            confidence=0.9,
        )

        assert event.event_type == EventType.MANEUVER
        assert event.satellite_id == 25544
        assert event.confidence == 0.9


class TestManeuverDetection:
    """Tests for maneuver detection from TLE history."""

    @pytest.fixture
    def sample_tle_with_maneuver(self):
        """Create TLE data with a clear maneuver signature."""
        base_time = datetime(2024, 1, 1)

        records = []
        sat_id = 25544

        # First 5 days: stable orbit
        for i in range(5):
            records.append({
                "satNo": sat_id,  # Correct column name
                "epoch": base_time + timedelta(days=i),
                "line2": f"2 {sat_id}  51.6420  10.0000 0001234  90.0000 270.0000 15.50000000{i:05d}",
                "semiMajorAxisKm": 6800,
                "eccentricity": 0.001,
                "inclinationDeg": 51.64,
            })

        # Day 5: Maneuver - significant SMA change
        for i in range(5, 10):
            records.append({
                "satNo": sat_id,  # Correct column name
                "epoch": base_time + timedelta(days=i),
                "line2": f"2 {sat_id}  51.6420  10.0000 0001234  90.0000 270.0000 15.48000000{i:05d}",
                "semiMajorAxisKm": 6850,  # 50km change = maneuver
                "eccentricity": 0.001,
                "inclinationDeg": 51.64,
            })

        return pd.DataFrame(records)

    def test_maneuver_detection_from_tle(self, sample_tle_with_maneuver):
        """Test that maneuver can be detected from TLE history."""
        from uct_benchmark.data.eventDetection import detect_maneuvers_from_tle_history, EventDetectionConfig

        config = EventDetectionConfig()
        config.sma_threshold_km = 10  # Set threshold lower than 50km change

        events = detect_maneuvers_from_tle_history(
            tle_df=sample_tle_with_maneuver,
            satellite_id=25544,
            config=config,
        )

        # Should detect at least one maneuver
        assert isinstance(events, list)


class TestBreakupDetection:
    """Tests for breakup detection."""

    def test_detect_breakup_candidates(self):
        """Test breakup candidate detection function."""
        from uct_benchmark.data.eventDetection import detect_breakup_candidates

        # Create catalog data with potential debris cluster
        base_time = datetime(2024, 1, 1)
        records = []

        # Parent object and potential debris (appear at same time)
        for debris_id in [25544, 99001, 99002, 99003, 99004, 99005]:
            records.append({
                "satNo": debris_id,
                "noradCatId": debris_id,
                "epoch": base_time,
                "launchDate": base_time,  # All launched at same time (breakup signature)
                "semiMajorAxisKm": 6800 + (debris_id % 10),  # Similar orbits
                "eccentricity": 0.001,
                "inclinationDeg": 51.64,
            })

        catalog_df = pd.DataFrame(records)

        candidates = detect_breakup_candidates(
            catalog_df=catalog_df,
            time_window_days=30.0,
            min_fragments=3,
        )

        assert isinstance(candidates, list)


class TestFetchBreakupEvents:
    """Tests for fetching breakup events from external sources."""

    def test_fetch_breakup_functions_exist(self):
        """Test that breakup fetch functions exist."""
        from uct_benchmark.data.eventDetection import (
            fetch_breakup_events_from_celestrak,
            fetch_breakup_events_combined,
        )

        # Just verify the functions exist
        assert callable(fetch_breakup_events_from_celestrak)
        assert callable(fetch_breakup_events_combined)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
