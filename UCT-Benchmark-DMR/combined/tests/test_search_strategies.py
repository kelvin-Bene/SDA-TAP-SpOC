"""
Comprehensive tests for the three search strategies: FAST, HYBRID, WINDOWED.

These tests verify:
1. SearchStrategy enum and model validation
2. Each strategy function works correctly with mocked UDL queries
3. generateDataset correctly routes to each strategy
4. Edge cases and error handling

Run with: uv run pytest tests/test_search_strategies.py -v

Note: API endpoint tests are in backend_api/tests/test_search_strategies_api.py
"""

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend_api.models import DatasetCreate, SearchStrategy

# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_udl_response():
    """Create a mock UDL API response DataFrame."""
    return pd.DataFrame(
        {
            "id": ["obs-1", "obs-2", "obs-3", "obs-4", "obs-5"],
            "satNo": [25544, 25544, 25544, 28654, 28654],
            "obTime": [
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:05:00Z",
                "2025-01-01T00:10:00Z",
                "2025-01-01T00:02:00Z",
                "2025-01-01T00:07:00Z",
            ],
            "ra": [123.45, 123.50, 123.55, 200.00, 200.10],
            "declination": [45.0, 45.1, 45.2, -30.0, -30.1],
        }
    )


@pytest.fixture
def mock_empty_response():
    """Create an empty DataFrame for testing edge cases."""
    return pd.DataFrame()


# ============================================================
# TEST CLASS: SearchStrategy Enum
# ============================================================


class TestSearchStrategyEnum:
    """Tests for the SearchStrategy enum."""

    def test_enum_values(self):
        """Test that all three strategy values exist."""
        assert SearchStrategy.FAST.value == "fast"
        assert SearchStrategy.HYBRID.value == "hybrid"
        assert SearchStrategy.WINDOWED.value == "windowed"

    def test_enum_from_string(self):
        """Test creating enum from string values."""
        assert SearchStrategy("fast") == SearchStrategy.FAST
        assert SearchStrategy("hybrid") == SearchStrategy.HYBRID
        assert SearchStrategy("windowed") == SearchStrategy.WINDOWED

    def test_invalid_enum_value(self):
        """Test that invalid values raise an error."""
        with pytest.raises(ValueError):
            SearchStrategy("invalid_strategy")

    def test_enum_is_string_subclass(self):
        """Test that SearchStrategy is a string subclass for JSON serialization."""
        assert isinstance(SearchStrategy.FAST, str)
        assert SearchStrategy.FAST == "fast"


# ============================================================
# TEST CLASS: DatasetCreate Model Validation
# ============================================================


class TestDatasetCreateModel:
    """Tests for the DatasetCreate model with search_strategy field."""

    def test_default_search_strategy(self):
        """Test that default search_strategy is HYBRID."""
        dataset = DatasetCreate(
            name="Test Dataset",
            regime="LEO",
        )
        assert dataset.search_strategy == SearchStrategy.HYBRID

    def test_explicit_search_strategy_fast(self):
        """Test setting search_strategy to FAST."""
        dataset = DatasetCreate(
            name="Test Dataset",
            regime="LEO",
            search_strategy=SearchStrategy.FAST,
        )
        assert dataset.search_strategy == SearchStrategy.FAST

    def test_explicit_search_strategy_windowed(self):
        """Test setting search_strategy to WINDOWED with window_size."""
        dataset = DatasetCreate(
            name="Test Dataset",
            regime="LEO",
            search_strategy=SearchStrategy.WINDOWED,
            window_size_minutes=15,
        )
        assert dataset.search_strategy == SearchStrategy.WINDOWED
        assert dataset.window_size_minutes == 15

    def test_default_window_size(self):
        """Test default window_size_minutes is 10."""
        dataset = DatasetCreate(
            name="Test Dataset",
            regime="LEO",
        )
        assert dataset.window_size_minutes == 10

    def test_window_size_validation_min(self):
        """Test window_size_minutes minimum validation (1 min)."""
        with pytest.raises(ValueError):
            DatasetCreate(
                name="Test Dataset",
                regime="LEO",
                window_size_minutes=0,
            )

    def test_window_size_validation_max(self):
        """Test window_size_minutes maximum validation (60 min)."""
        with pytest.raises(ValueError):
            DatasetCreate(
                name="Test Dataset",
                regime="LEO",
                window_size_minutes=61,
            )

    def test_search_strategy_string_coercion(self):
        """Test that string values are coerced to enum."""
        dataset = DatasetCreate(
            name="Test Dataset",
            regime="LEO",
            search_strategy="fast",
        )
        assert dataset.search_strategy == SearchStrategy.FAST

    def test_all_strategies_valid(self):
        """Test that all three strategies are valid inputs."""
        for strategy in ["fast", "hybrid", "windowed"]:
            dataset = DatasetCreate(
                name="Test Dataset",
                regime="LEO",
                search_strategy=strategy,
            )
            assert dataset.search_strategy.value == strategy


# ============================================================
# TEST CLASS: Fast Strategy Function
# ============================================================


class TestFastStrategy:
    """Tests for the _fetch_observations_fast function."""

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_strategy_single_query_per_satellite(self, mock_batch_query, mock_udl_response):
        """Test that FAST strategy makes one query per satellite."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = mock_udl_response
        sat_ids = [25544, 28654]
        sweep_time = ">now-7 days"

        result = _fetch_observations_fast(
            token="test_token",
            sat_ids=sat_ids,
            sweep_time=sweep_time,
            max_datapoints=0,
            dt=0.1,
        )

        # Should call asyncUDLBatchQuery once with params for both satellites
        mock_batch_query.assert_called_once()
        call_args = mock_batch_query.call_args

        # Verify params_list contains both satellites
        params_list = call_args[0][2]  # Third positional arg
        assert len(params_list) == 2
        assert params_list[0]["satNo"] == "25544"
        assert params_list[1]["satNo"] == "28654"

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_strategy_returns_dataframe(self, mock_batch_query, mock_udl_response):
        """Test that FAST strategy returns a valid DataFrame."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = mock_udl_response

        result = _fetch_observations_fast(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            max_datapoints=0,
            dt=0.1,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert "satNo" in result.columns
        assert "obTime" in result.columns

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_strategy_with_max_datapoints(self, mock_batch_query, mock_udl_response):
        """Test that FAST strategy respects max_datapoints parameter."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = mock_udl_response

        _fetch_observations_fast(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            max_datapoints=100,
            dt=0.1,
        )

        # Verify maxResults is included in params
        params_list = mock_batch_query.call_args[0][2]
        assert params_list[0]["maxResults"] == 100

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_strategy_no_max_datapoints(self, mock_batch_query, mock_udl_response):
        """Test that FAST strategy excludes maxResults when max_datapoints <= 0."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = mock_udl_response

        _fetch_observations_fast(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            max_datapoints=0,
            dt=0.1,
        )

        params_list = mock_batch_query.call_args[0][2]
        assert "maxResults" not in params_list[0]

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_strategy_correct_service(self, mock_batch_query, mock_udl_response):
        """Test that FAST strategy queries the correct UDL service."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = mock_udl_response

        _fetch_observations_fast(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            max_datapoints=0,
            dt=0.1,
        )

        # Verify service is "eoobservation"
        service = mock_batch_query.call_args[0][1]
        assert service == "eoobservation"


# ============================================================
# TEST CLASS: Windowed Strategy Function
# ============================================================


class TestWindowedStrategy:
    """Tests for the _fetch_observations_windowed function."""

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_creates_time_windows(self, mock_batch_query, mock_udl_response):
        """Test that WINDOWED strategy creates correct time windows."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)  # 30 minutes

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544, 28654],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        # Should call asyncUDLBatchQuery once per window (3 windows: 0-10, 10-20, 20-30)
        assert mock_batch_query.call_count == 3

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_uses_satno_filter(self, mock_batch_query, mock_udl_response):
        """Test that each window query uses satNo filter (not range)."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 10, 0)

        _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544, 28654],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        # Get the params_list from the call
        call_args = mock_batch_query.call_args
        params_list = call_args[0][2]  # Third positional arg

        # Should have one params dict per satellite
        assert len(params_list) == 2
        assert params_list[0]["satNo"] == "25544"
        assert params_list[1]["satNo"] == "28654"

        # Should NOT use range filter
        for params in params_list:
            assert "range" not in params
            assert "satNo" in params

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_concatenates_results(self, mock_batch_query):
        """Test that WINDOWED strategy concatenates results from all windows."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        # Return different data for each window
        window1_data = pd.DataFrame(
            {
                "id": ["obs-1", "obs-2"],
                "satNo": [25544, 25544],
                "obTime": ["2025-01-01T00:00:00Z", "2025-01-01T00:05:00Z"],
            }
        )
        window2_data = pd.DataFrame(
            {
                "id": ["obs-3", "obs-4"],
                "satNo": [25544, 28654],
                "obTime": ["2025-01-01T00:10:00Z", "2025-01-01T00:15:00Z"],
            }
        )

        mock_batch_query.side_effect = [window1_data, window2_data]

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 20, 0)

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544, 28654],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        # Should have 4 observations total
        assert len(result) == 4
        assert "obs-1" in result["id"].values
        assert "obs-4" in result["id"].values

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_handles_empty_windows(self, mock_batch_query, mock_udl_response):
        """Test that WINDOWED strategy handles windows with no data."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        # First window has data, second is empty
        mock_batch_query.side_effect = [mock_udl_response, pd.DataFrame()]

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 20, 0)

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544, 28654],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        # Should only have data from first window
        assert len(result) == 5

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_respects_rate_limiting(self, mock_batch_query, mock_udl_response):
        """Test that WINDOWED strategy passes dt to asyncUDLBatchQuery."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.5,
        )

        # dt should be passed to each asyncUDLBatchQuery call
        assert mock_batch_query.call_count == 3
        for call in mock_batch_query.call_args_list:
            assert call[0][3] == 0.5  # dt is 4th positional arg

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_progress_callback(self, mock_batch_query, mock_udl_response):
        """Test that WINDOWED strategy reports progress via callback."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.return_value = mock_udl_response
        progress_callback = MagicMock()

        # Create a mock DatasetStage
        class MockDatasetStage:
            COLLECTING_OBSERVATIONS = "collecting_observations"

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544, 28654],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
            progress_callback=progress_callback,
            DatasetStage=MockDatasetStage,
        )

        # Should report progress for each window (3 times)
        assert progress_callback.call_count == 3

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_different_window_sizes(self, mock_batch_query, mock_udl_response):
        """Test WINDOWED strategy with different window sizes."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 1, 0, 0)  # 60 minutes

        # 15 minute windows should make 4 queries
        _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=15,
            dt=0.1,
        )

        assert mock_batch_query.call_count == 4

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_strategy_empty_sat_ids(self, mock_batch_query):
        """Test WINDOWED strategy returns empty DataFrame when sat_ids is empty."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        assert result.empty
        mock_batch_query.assert_not_called()


# ============================================================
# TEST CLASS: Hybrid Strategy Function
# ============================================================


class TestHybridStrategy:
    """Tests for the _fetch_observations_hybrid function."""

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_strategy_uses_smart_query(
        self, mock_sleep, mock_smart_query, mock_udl_response
    ):
        """Test that HYBRID strategy uses smart_query for each satellite."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        mock_smart_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        result = _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544, 28654],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=0,
            dt=0.1,
        )

        # Should call smart_query once per satellite
        assert mock_smart_query.call_count == 2

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_strategy_concatenates_satellite_results(self, mock_sleep, mock_smart_query):
        """Test that HYBRID strategy concatenates results from all satellites."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        sat1_data = pd.DataFrame(
            {
                "id": ["obs-1", "obs-2"],
                "satNo": [25544, 25544],
                "obTime": ["2025-01-01T00:00:00Z", "2025-01-01T00:05:00Z"],
            }
        )
        sat2_data = pd.DataFrame(
            {
                "id": ["obs-3"],
                "satNo": [28654],
                "obTime": ["2025-01-01T00:02:00Z"],
            }
        )

        mock_smart_query.side_effect = [sat1_data, sat2_data]

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        result = _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544, 28654],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=0,
            dt=0.1,
        )

        assert len(result) == 3
        assert set(result["satNo"].unique()) == {25544, 28654}

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_strategy_handles_failed_queries(
        self, mock_sleep, mock_smart_query, mock_udl_response
    ):
        """Test that HYBRID strategy continues if one satellite query fails."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        # First satellite fails, second succeeds
        mock_smart_query.side_effect = [Exception("API Error"), mock_udl_response]

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        result = _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544, 28654],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=0,
            dt=0.1,
        )

        # Should still return data from successful query
        assert len(result) == 5

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_strategy_progress_callback(
        self, mock_sleep, mock_smart_query, mock_udl_response
    ):
        """Test that HYBRID strategy reports progress per satellite."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        mock_smart_query.return_value = mock_udl_response
        progress_callback = MagicMock()

        class MockDatasetStage:
            COLLECTING_OBSERVATIONS = "collecting_observations"

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544, 28654, 40000],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=0,
            dt=0.1,
            progress_callback=progress_callback,
            DatasetStage=MockDatasetStage,
        )

        # Should report progress for each satellite (3 times)
        assert progress_callback.call_count == 3

        # Check progress values increase
        calls = progress_callback.call_args_list
        progress_values = [call[0][1] for call in calls]
        assert progress_values == [pytest.approx(1 / 3), pytest.approx(2 / 3), pytest.approx(1.0)]

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_strategy_with_max_datapoints(
        self, mock_sleep, mock_smart_query, mock_udl_response
    ):
        """Test that HYBRID strategy passes max_datapoints to smart_query."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        mock_smart_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=500,
            dt=0.1,
        )

        # Check that maxResults was passed in params
        call_args = mock_smart_query.call_args
        params = call_args[0][2]  # Third positional arg
        assert params.get("maxResults") == 500


# ============================================================
# TEST CLASS: generateDataset Integration
# ============================================================


class TestGenerateDatasetStrategyIntegration:
    """Tests for generateDataset function using different strategies."""

    @patch("uct_benchmark.api.apiIntegration._fetch_observations_fast")
    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    @patch("uct_benchmark.api.apiIntegration.UDLQuery")
    @patch("uct_benchmark.api.apiIntegration.discoswebQuery")
    def test_generate_dataset_uses_fast_strategy(
        self,
        mock_discos,
        mock_udl_query,
        mock_batch_query,
        mock_fast,
        mock_udl_response,
    ):
        """Test that generateDataset calls _fetch_observations_fast for 'fast' strategy."""
        from uct_benchmark.api.apiIntegration import generateDataset

        # Setup mock returns
        mock_fast.return_value = mock_udl_response
        mock_batch_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "epoch": ["2025-01-01T00:00:00Z"],
                "x": [6800],
                "y": [0],
                "z": [0],
                "xDot": [0],
                "yDot": [7.5],
                "zDot": [0],
            }
        )
        mock_udl_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "line1": ["1 25544U 98067A   25001.00000000  .00000000  00000-0  00000-0 0  9991"],
                "line2": ["2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000000000"],
            }
        )
        mock_discos.return_value = {
            "attributes": [{"satno": 25544, "mass": 400000, "xSectAvg": 100}]
        }

        try:
            generateDataset(
                UDL_token="test",
                ESA_token="test",
                satIDs=[25544],
                timeframe=1,
                timeunit="days",
                search_strategy="fast",
            )
        except Exception:
            pass  # We're just checking the strategy was called

        mock_fast.assert_called_once()

    @patch("uct_benchmark.api.apiIntegration._fetch_observations_windowed")
    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    @patch("uct_benchmark.api.apiIntegration.UDLQuery")
    @patch("uct_benchmark.api.apiIntegration.discoswebQuery")
    def test_generate_dataset_uses_windowed_strategy(
        self,
        mock_discos,
        mock_udl_query,
        mock_batch_query,
        mock_windowed,
        mock_udl_response,
    ):
        """Test that generateDataset calls _fetch_observations_windowed for 'windowed' strategy."""
        from uct_benchmark.api.apiIntegration import generateDataset

        mock_windowed.return_value = mock_udl_response
        mock_batch_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "epoch": ["2025-01-01T00:00:00Z"],
                "x": [6800],
                "y": [0],
                "z": [0],
                "xDot": [0],
                "yDot": [7.5],
                "zDot": [0],
            }
        )
        mock_udl_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "line1": ["1 25544U 98067A   25001.00000000  .00000000  00000-0  00000-0 0  9991"],
                "line2": ["2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000000000"],
            }
        )
        mock_discos.return_value = {
            "attributes": [{"satno": 25544, "mass": 400000, "xSectAvg": 100}]
        }

        try:
            generateDataset(
                UDL_token="test",
                ESA_token="test",
                satIDs=[25544],
                timeframe=1,
                timeunit="days",
                search_strategy="windowed",
                window_size_minutes=15,
            )
        except Exception:
            pass

        mock_windowed.assert_called_once()
        call_args = mock_windowed.call_args
        # 2nd positional arg should be satIDs (not regime string)
        assert call_args[0][1] == [25544]
        # window_size_minutes is 5th positional arg
        assert call_args[0][4] == 15

    @patch("uct_benchmark.api.apiIntegration._fetch_observations_hybrid")
    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    @patch("uct_benchmark.api.apiIntegration.UDLQuery")
    @patch("uct_benchmark.api.apiIntegration.discoswebQuery")
    def test_generate_dataset_uses_hybrid_by_default(
        self,
        mock_discos,
        mock_udl_query,
        mock_batch_query,
        mock_hybrid,
        mock_udl_response,
    ):
        """Test that generateDataset uses _fetch_observations_hybrid by default."""
        from uct_benchmark.api.apiIntegration import generateDataset

        mock_hybrid.return_value = mock_udl_response
        mock_batch_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "epoch": ["2025-01-01T00:00:00Z"],
                "x": [6800],
                "y": [0],
                "z": [0],
                "xDot": [0],
                "yDot": [7.5],
                "zDot": [0],
            }
        )
        mock_udl_query.return_value = pd.DataFrame(
            {
                "satNo": [25544],
                "line1": ["1 25544U 98067A   25001.00000000  .00000000  00000-0  00000-0 0  9991"],
                "line2": ["2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000000000"],
            }
        )
        mock_discos.return_value = {
            "attributes": [{"satno": 25544, "mass": 400000, "xSectAvg": 100}]
        }

        try:
            generateDataset(
                UDL_token="test",
                ESA_token="test",
                satIDs=[25544],
                timeframe=1,
                timeunit="days",
                # No search_strategy specified, should default to hybrid
            )
        except Exception:
            pass

        mock_hybrid.assert_called_once()

    @patch("uct_benchmark.api.apiIntegration._fetch_observations_fast")
    @patch("uct_benchmark.api.apiIntegration._fetch_observations_windowed")
    @patch("uct_benchmark.api.apiIntegration._fetch_observations_hybrid")
    def test_generate_dataset_strategy_routing(
        self,
        mock_hybrid,
        mock_windowed,
        mock_fast,
        mock_udl_response,
    ):
        """Test that generateDataset routes to the correct strategy based on parameter."""
        from uct_benchmark.api.apiIntegration import generateDataset

        # Setup all mocks to return valid data
        mock_fast.return_value = mock_udl_response
        mock_windowed.return_value = mock_udl_response
        mock_hybrid.return_value = mock_udl_response

        # Test fast - should only call fast
        with (
            patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery"),
            patch("uct_benchmark.api.apiIntegration.UDLQuery"),
            patch("uct_benchmark.api.apiIntegration.discoswebQuery"),
        ):
            try:
                generateDataset("t", "t", [25544], 1, "days", search_strategy="fast")
            except Exception:
                pass

        assert mock_fast.called
        assert not mock_windowed.called
        assert not mock_hybrid.called

        # Reset mocks
        mock_fast.reset_mock()
        mock_windowed.reset_mock()
        mock_hybrid.reset_mock()

        # Test windowed
        with (
            patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery"),
            patch("uct_benchmark.api.apiIntegration.UDLQuery"),
            patch("uct_benchmark.api.apiIntegration.discoswebQuery"),
        ):
            try:
                generateDataset("t", "t", [25544], 1, "days", search_strategy="windowed")
            except Exception:
                pass

        assert not mock_fast.called
        assert mock_windowed.called
        assert not mock_hybrid.called


# ============================================================
# TEST CLASS: Edge Cases and Error Handling
# ============================================================


class TestSearchStrategyEdgeCases:
    """Tests for edge cases and error handling in search strategies."""

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_handles_query_exception(self, mock_batch_query):
        """Test that WINDOWED strategy handles query exceptions gracefully."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        # First window fails, second succeeds
        mock_batch_query.side_effect = [
            Exception("Network error"),
            pd.DataFrame(
                {
                    "id": ["obs-1"],
                    "satNo": [25544],
                    "obTime": ["2025-01-01T00:10:00Z"],
                }
            ),
        ]

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 20, 0)

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        # Should still have data from successful window
        assert len(result) == 1

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_windowed_all_windows_fail(self, mock_batch_query):
        """Test WINDOWED strategy returns empty DataFrame if all windows fail."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_windowed

        mock_batch_query.side_effect = Exception("All queries fail")

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 20, 0)

        result = _fetch_observations_windowed(
            token="test_token",
            sat_ids=[25544],
            start_time=start_time,
            end_time=end_time,
            window_size_minutes=10,
            dt=0.1,
        )

        assert result.empty

    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_hybrid_all_satellites_fail(self, mock_sleep, mock_smart_query):
        """Test HYBRID strategy returns empty DataFrame if all satellites fail."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_hybrid

        mock_smart_query.side_effect = Exception("All queries fail")

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        result = _fetch_observations_hybrid(
            token="test_token",
            sat_ids=[25544, 28654],
            sweep_time=">now-7 days",
            start_time=start_time,
            end_time=end_time,
            max_datapoints=0,
            dt=0.1,
        )

        assert result.empty

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    def test_fast_handles_empty_response(self, mock_batch_query):
        """Test FAST strategy handles empty API response."""
        from uct_benchmark.api.apiIntegration import _fetch_observations_fast

        mock_batch_query.return_value = pd.DataFrame()

        result = _fetch_observations_fast(
            token="test_token",
            sat_ids=[25544],
            sweep_time=">now-7 days",
            max_datapoints=0,
            dt=0.1,
        )

        assert result.empty


# ============================================================
# TEST CLASS: End-to-End Strategy Comparison
# ============================================================


class TestEndToEndStrategyComparison:
    """
    End-to-end tests comparing behavior of all three strategies.

    These tests verify that all strategies produce valid output
    and can be used interchangeably in the pipeline.
    """

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_all_strategies_produce_same_columns(
        self,
        mock_sleep,
        mock_smart_query,
        mock_batch_query,
        mock_udl_response,
    ):
        """Test that all strategies return DataFrames with the same columns."""
        from uct_benchmark.api.apiIntegration import (
            _fetch_observations_fast,
            _fetch_observations_hybrid,
            _fetch_observations_windowed,
        )

        mock_batch_query.return_value = mock_udl_response
        mock_smart_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        fast_result = _fetch_observations_fast("token", [25544], ">now-7 days", 0, 0.1)
        windowed_result = _fetch_observations_windowed(
            "token", [25544], start_time, end_time, 10, 0.1
        )
        hybrid_result = _fetch_observations_hybrid(
            "token", [25544], ">now-7 days", start_time, end_time, 0, 0.1
        )

        # All strategies should return DataFrames with the same columns
        assert set(fast_result.columns) == set(windowed_result.columns)
        assert set(fast_result.columns) == set(hybrid_result.columns)

    @patch("uct_benchmark.api.apiIntegration.asyncUDLBatchQuery")
    @patch("uct_benchmark.api.apiIntegration.smart_query")
    @patch("uct_benchmark.api.apiIntegration.time.sleep")
    def test_all_strategies_return_dataframes(
        self,
        mock_sleep,
        mock_smart_query,
        mock_batch_query,
        mock_udl_response,
    ):
        """Test that all strategies return pandas DataFrames."""
        from uct_benchmark.api.apiIntegration import (
            _fetch_observations_fast,
            _fetch_observations_hybrid,
            _fetch_observations_windowed,
        )

        mock_batch_query.return_value = mock_udl_response
        mock_smart_query.return_value = mock_udl_response

        start_time = datetime.datetime(2025, 1, 1, 0, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 0, 30, 0)

        fast_result = _fetch_observations_fast("token", [25544], ">now-7 days", 0, 0.1)
        windowed_result = _fetch_observations_windowed(
            "token", [25544], start_time, end_time, 10, 0.1
        )
        hybrid_result = _fetch_observations_hybrid(
            "token", [25544], ">now-7 days", start_time, end_time, 0, 0.1
        )

        assert isinstance(fast_result, pd.DataFrame)
        assert isinstance(windowed_result, pd.DataFrame)
        assert isinstance(hybrid_result, pd.DataFrame)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
