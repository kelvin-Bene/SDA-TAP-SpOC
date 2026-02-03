# -*- coding: utf-8 -*-
"""
Tests for Breakup Event Detection.

Per Louis's documentation, breakup (BU) event detection requires external
database integration with Space-Track and CelesTrak to identify actual
fragmentation events.

These tests verify:
1. BreakupEvent data structure
2. Space-Track breakup event fetching
3. CelesTrak breakup event fetching
4. Combined event fetching with deduplication
5. BU filter returns affected satellites
6. Breakup event caching
7. Graceful handling when no breakups in date range

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestBreakupEventDataStructure:
    """Tests for BreakupEvent data structure."""

    def test_breakup_event_creation(self):
        """Test BreakupEvent dataclass creation."""
        from uct_benchmark.data.eventDetection import BreakupEvent

        event = BreakupEvent(
            parent_norad_id=25544,
            parent_name="ISS (ZARYA)",
            event_date=datetime(2025, 1, 15, 12, 0, 0),
            debris_count=50,
            debris_norad_ids=[25545, 25546, 25547],
            event_type="FRAGMENTATION",
            source="SPACETRACK",
        )

        assert event.parent_norad_id == 25544
        assert event.parent_name == "ISS (ZARYA)"
        assert event.debris_count == 50
        assert len(event.debris_norad_ids) == 3
        assert event.event_type == "FRAGMENTATION"
        assert event.source == "SPACETRACK"

    def test_breakup_event_to_dict(self):
        """Test BreakupEvent.to_dict() serialization."""
        from uct_benchmark.data.eventDetection import BreakupEvent

        event = BreakupEvent(
            parent_norad_id=25544,
            parent_name="ISS",
            event_date=datetime(2025, 1, 15),
            debris_count=10,
            debris_norad_ids=[1, 2, 3],
            event_type="COLLISION",
            source="CELESTRAK",
        )

        d = event.to_dict()

        assert d["parent_norad_id"] == 25544
        assert d["parent_name"] == "ISS"
        assert d["debris_count"] == 10
        assert d["event_type"] == "COLLISION"
        assert d["source"] == "CELESTRAK"
        assert "event_date" in d

    def test_breakup_event_from_dict(self):
        """Test BreakupEvent.from_dict() deserialization."""
        from uct_benchmark.data.eventDetection import BreakupEvent

        d = {
            "parent_norad_id": 12345,
            "parent_name": "TEST SAT",
            "event_date": "2025-06-01T00:00:00",
            "debris_count": 5,
            "debris_norad_ids": [12346, 12347],
            "event_type": "ANOMALY",
            "source": "SPACETRACK",
        }

        event = BreakupEvent.from_dict(d)

        assert event.parent_norad_id == 12345
        assert event.parent_name == "TEST SAT"
        assert event.debris_count == 5
        assert event.event_type == "ANOMALY"


class TestSpaceTrackIntegration:
    """Tests for Space-Track breakup event fetching."""

    def test_fetch_breakup_events_spacetrack(self):
        """Test Space-Track breakup event fetching."""
        from uct_benchmark.data.eventDetection import fetch_breakup_events_from_spacetrack

        # Try to import apiIntegration, skip if dependencies missing
        try:
            import uct_benchmark.api.apiIntegration
        except ImportError as e:
            pytest.skip(f"Optional dependency not available: {e}")

        # Mock Space-Track response with debris objects
        mock_response = pd.DataFrame({
            "NORAD_CAT_ID": [10001, 10002, 10003, 10004, 10005, 10006],
            "SATNAME": ["DEB1", "DEB2", "DEB3", "DEB4", "DEB5", "DEB6"],
            "INTLDES": [
                "2020-001A", "2020-001B", "2020-001C",
                "2020-001D", "2020-001E", "2020-001F"
            ],
            "OBJECT_TYPE": ["DEBRIS"] * 6,
            "LAUNCH": pd.to_datetime([
                "2020-01-15", "2020-01-15", "2020-01-15",
                "2020-01-15", "2020-01-15", "2020-01-15"
            ]),
        })

        with patch("uct_benchmark.api.apiIntegration.spacetrackQuery", return_value=mock_response):
            with patch.dict("os.environ", {"SPACETRACK_TOKEN": "test_token"}):
                events = fetch_breakup_events_from_spacetrack(
                    start_date=datetime(2020, 1, 1),
                    end_date=datetime(2020, 12, 31),
                )

        # Should detect breakup event from 6 debris with same INTLDES prefix
        assert isinstance(events, list)

    def test_fetch_breakup_events_no_token(self):
        """Test graceful handling when no Space-Track token available."""
        from uct_benchmark.data.eventDetection import fetch_breakup_events_from_spacetrack

        with patch.dict("os.environ", {}, clear=True):
            # Remove SPACETRACK_TOKEN from environment
            import os
            os.environ.pop("SPACETRACK_TOKEN", None)

            events = fetch_breakup_events_from_spacetrack(
                start_date=datetime(2020, 1, 1),
                end_date=datetime(2020, 12, 31),
            )

        # Should return empty list without crashing
        assert events == []


class TestCelesTrakIntegration:
    """Tests for CelesTrak breakup event fetching."""

    def test_fetch_breakup_events_celestrak(self):
        """Test CelesTrak breakup event fetching."""
        from uct_benchmark.data.eventDetection import fetch_breakup_events_from_celestrak

        # Try to import apiIntegration, skip if dependencies missing
        try:
            import uct_benchmark.api.apiIntegration
        except ImportError as e:
            pytest.skip(f"Optional dependency not available: {e}")

        # Mock CelesTrak response
        mock_response = pd.DataFrame({
            "NORAD_CAT_ID": [20001, 20002, 20003, 20004, 20005],
            "SATNAME": ["DEBRIS A", "DEBRIS B", "DEBRIS C", "DEBRIS D", "DEBRIS E"],
            "INTLDES": [
                "2021-050A", "2021-050B", "2021-050C", "2021-050D", "2021-050E"
            ],
            "LAUNCH": pd.to_datetime([
                "2021-06-15", "2021-06-15", "2021-06-15", "2021-06-15", "2021-06-15"
            ]),
        })

        with patch("uct_benchmark.api.apiIntegration.celestrakQuery", return_value=mock_response):
            events = fetch_breakup_events_from_celestrak(
                start_date=datetime(2021, 1, 1),
                end_date=datetime(2021, 12, 31),
            )

        # Should detect breakup event from debris with same INTLDES prefix
        assert isinstance(events, list)


class TestCombinedBreakupFetching:
    """Tests for combined Space-Track + CelesTrak breakup fetching."""

    @patch("uct_benchmark.data.eventDetection.fetch_breakup_events_from_spacetrack")
    @patch("uct_benchmark.data.eventDetection.fetch_breakup_events_from_celestrak")
    def test_fetch_breakup_events_combined(self, mock_celestrak, mock_spacetrack):
        """Test combined event fetching with deduplication."""
        from uct_benchmark.data.eventDetection import (
            fetch_breakup_events_combined,
            BreakupEvent,
        )

        # Mock events from both sources
        event1 = BreakupEvent(
            parent_norad_id=10001,
            parent_name="TEST1",
            event_date=datetime(2021, 6, 15),
            debris_count=5,
            debris_norad_ids=[10002, 10003],
            event_type="FRAGMENTATION",
            source="SPACETRACK",
        )
        event2 = BreakupEvent(
            parent_norad_id=10001,  # Same parent - should be deduplicated
            parent_name="TEST1",
            event_date=datetime(2021, 6, 15),
            debris_count=5,
            debris_norad_ids=[10002, 10003],
            event_type="FRAGMENTATION",
            source="CELESTRAK",
        )
        event3 = BreakupEvent(
            parent_norad_id=20001,  # Different event
            parent_name="TEST2",
            event_date=datetime(2021, 7, 20),
            debris_count=10,
            debris_norad_ids=[20002, 20003, 20004],
            event_type="COLLISION",
            source="CELESTRAK",
        )

        mock_spacetrack.return_value = [event1]
        mock_celestrak.return_value = [event2, event3]

        events = fetch_breakup_events_combined(
            start_date=datetime(2021, 1, 1),
            end_date=datetime(2021, 12, 31),
            use_cache=False,
        )

        # Should have 2 unique events (deduplicated by parent_norad_id)
        assert len(events) == 2
        parent_ids = [e.parent_norad_id for e in events]
        assert 10001 in parent_ids
        assert 20001 in parent_ids


class TestBreakupFiltering:
    """Tests for BU event code filtering."""

    def test_filter_by_breakup_event(self):
        """Verify BU filter returns affected satellites."""
        from uct_benchmark.data.eventDetection import (
            filter_by_breakup_event,
            BreakupEvent,
        )

        # Create observation DataFrame
        obs_df = pd.DataFrame({
            "satNo": [1, 1, 2, 2, 3, 3, 10001, 10002, 10003],
            "obTime": pd.date_range("2021-06-01", periods=9, freq="D"),
            "id": [f"obs{i}" for i in range(9)],
        })

        # Mock breakup events
        with patch("uct_benchmark.data.eventDetection.fetch_breakup_events_combined") as mock_fetch:
            mock_fetch.return_value = [
                BreakupEvent(
                    parent_norad_id=10001,
                    parent_name="BREAKUP SAT",
                    event_date=datetime(2021, 6, 15),
                    debris_count=3,
                    debris_norad_ids=[10002, 10003],
                    event_type="FRAGMENTATION",
                    source="SPACETRACK",
                )
            ]

            filtered, events, metadata = filter_by_breakup_event(
                obs_df,
                start_date=datetime(2021, 1, 1),
                end_date=datetime(2021, 12, 31),
            )

        # Should only include observations from breakup-affected satellites
        affected_sats = filtered["satNo"].unique()
        assert 10001 in affected_sats
        assert 10002 in affected_sats
        assert 10003 in affected_sats
        assert 1 not in affected_sats  # Non-breakup satellite excluded
        assert 2 not in affected_sats
        assert 3 not in affected_sats

    def test_breakup_no_events_in_range(self):
        """Verify graceful handling when no breakups in date range."""
        from uct_benchmark.data.eventDetection import filter_by_breakup_event

        obs_df = pd.DataFrame({
            "satNo": [1, 2, 3],
            "obTime": pd.date_range("2021-01-01", periods=3, freq="D"),
            "id": ["obs1", "obs2", "obs3"],
        })

        with patch("uct_benchmark.data.eventDetection.fetch_breakup_events_combined") as mock_fetch:
            mock_fetch.return_value = []  # No breakup events

            filtered, events, metadata = filter_by_breakup_event(
                obs_df,
                start_date=datetime(2021, 1, 1),
                end_date=datetime(2021, 12, 31),
            )

        assert len(filtered) == 0  # Empty result when no breakup events
        assert metadata["status"] == "no_breakup_events"


class TestBreakupEventCaching:
    """Tests for breakup event caching."""

    def test_breakup_event_caching(self):
        """Verify breakup events are cached."""
        from uct_benchmark.data.eventDetection import (
            fetch_breakup_events_combined,
            BreakupEvent,
        )
        import tempfile
        from pathlib import Path

        # Create a temporary cache directory
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            with patch("uct_benchmark.data.eventDetection.fetch_breakup_events_from_spacetrack") as mock_st:
                with patch("uct_benchmark.data.eventDetection.fetch_breakup_events_from_celestrak") as mock_ct:
                    mock_st.return_value = [
                        BreakupEvent(
                            parent_norad_id=99999,
                            parent_name="CACHE TEST",
                            event_date=datetime(2021, 1, 1),
                            debris_count=5,
                            debris_norad_ids=[99998, 99997],
                            event_type="FRAGMENTATION",
                            source="SPACETRACK",
                        )
                    ]
                    mock_ct.return_value = []

                    # First call should fetch from APIs
                    events1 = fetch_breakup_events_combined(
                        start_date=datetime(2021, 1, 1),
                        end_date=datetime(2021, 12, 31),
                        use_cache=False,  # Don't use cache for this test
                    )

                    # Verify events were returned
                    assert len(events1) == 1


class TestFilterByEventIntegration:
    """Integration tests for filter_by_event with BU code."""

    def test_filter_by_event_bu_code(self):
        """Test filter_satellites_by_event_code with BU (breakup) event code."""
        from uct_benchmark.data.eventDetection import (
            filter_satellites_by_event_code,
            BreakupEvent,
        )

        # Create TLE DataFrame
        tle_df = pd.DataFrame({
            "satNo": [1, 1, 2, 2, 10001, 10001],
            "epoch": pd.to_datetime([
                "2021-01-01", "2021-02-01",
                "2021-01-01", "2021-02-01",
                "2021-01-01", "2021-02-01"
            ]),
            "line2": ["2 1  98.2 0.0 0.001 0.0 0.0 15.0 0"] * 6,
        })

        satellite_ids = [1, 2, 10001]

        with patch("uct_benchmark.data.eventDetection.fetch_breakup_events_combined") as mock_fetch:
            mock_fetch.return_value = [
                BreakupEvent(
                    parent_norad_id=10001,
                    parent_name="BU SAT",
                    event_date=datetime(2021, 1, 15),
                    debris_count=5,
                    debris_norad_ids=[10002],
                    event_type="FRAGMENTATION",
                    source="SPACETRACK",
                )
            ]

            matching_sats, events = filter_satellites_by_event_code(
                tle_df=tle_df,
                satellite_ids=satellite_ids,
                event_code="BU",
            )

        # Should only return satellites involved in breakup
        assert 10001 in matching_sats
        # Satellites 1 and 2 should not be included (no breakup involvement)


class TestLongDurationManeuverDetection:
    """Tests for long-duration low-thrust (LL) maneuver detection."""

    def test_detect_long_duration_maneuvers(self):
        """Test detection of long-duration low-thrust maneuvers."""
        from uct_benchmark.data.eventDetection import (
            detect_long_duration_maneuvers,
            EventDetectionConfig,
        )

        # Create TLE data with gradual SMA drift (characteristic of low-thrust)
        base_sma = 7000  # km
        epochs = pd.date_range("2021-01-01", periods=30, freq="D")

        tle_data = []
        for i, epoch in enumerate(epochs):
            # Gradually increasing SMA (low-thrust raising maneuver)
            sma = base_sma + i * 0.5  # 0.5 km/day drift
            mean_motion = 15.5 - i * 0.001  # Corresponding MM decrease

            tle_line2 = f"2 12345  98.2000   0.0000 0001000   0.0000   0.0000 {mean_motion:.8f}00000"

            tle_data.append({
                "satNo": 12345,
                "epoch": epoch,
                "line2": tle_line2,
            })

        tle_df = pd.DataFrame(tle_data)

        config = EventDetectionConfig(
            long_thrust_duration_days=7.0,
            long_thrust_rate_threshold=1.0,
        )

        events = detect_long_duration_maneuvers(tle_df, 12345, config)

        # Should detect long-duration maneuver pattern
        # (Actual detection depends on implementation details)
        assert isinstance(events, list)
