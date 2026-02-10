"""Tests for the timeSort utility function."""

from datetime import datetime

import pytest

from uct_benchmark.utils.timeSort import timeSort


class TestTimeSort:
    """Tests for timeSort function."""

    def test_cutoff_in_middle_of_list(self):
        """Test splitting when cutoff is between observations."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
            datetime(2025, 7, 1),
        ]
        cutoff = datetime(2025, 4, 1)

        before, after = timeSort(cutoff, dt_list)

        assert before == [datetime(2025, 1, 1), datetime(2025, 3, 1)]
        assert after == [datetime(2025, 5, 1), datetime(2025, 7, 1)]

    def test_cutoff_exactly_on_observation(self):
        """Test when cutoff matches an observation time exactly."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
        ]
        cutoff = datetime(2025, 3, 1)

        before, after = timeSort(cutoff, dt_list)

        # cutoff >= t_ob means exact match goes to 'after'
        assert before == [datetime(2025, 1, 1)]
        assert after == [datetime(2025, 3, 1), datetime(2025, 5, 1)]

    def test_cutoff_before_all_observations(self):
        """Test when cutoff is before all observations."""
        dt_list = [
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
            datetime(2025, 7, 1),
        ]
        cutoff = datetime(2025, 1, 1)

        before, after = timeSort(cutoff, dt_list)

        # Function returns empty lists when cutoff is outside range
        assert before == []
        assert after == []

    def test_cutoff_after_all_observations(self):
        """Test when cutoff is after all observations."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
        ]
        cutoff = datetime(2025, 12, 1)

        before, after = timeSort(cutoff, dt_list)

        # Function returns empty lists when cutoff is outside range
        assert before == []
        assert after == []

    def test_cutoff_close_to_first_observation(self):
        """Test cutoff just after the first observation."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
        ]
        cutoff = datetime(2025, 2, 1)

        before, after = timeSort(cutoff, dt_list)

        assert before == [datetime(2025, 1, 1)]
        assert after == [datetime(2025, 3, 1), datetime(2025, 5, 1)]

    def test_cutoff_close_to_last_observation(self):
        """Test cutoff just before the last observation."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
        ]
        cutoff = datetime(2025, 4, 15)

        before, after = timeSort(cutoff, dt_list)

        assert before == [datetime(2025, 1, 1), datetime(2025, 3, 1)]
        assert after == [datetime(2025, 5, 1)]

    def test_single_observation_cutoff_before(self):
        """Test with single observation when cutoff is before it."""
        dt_list = [datetime(2025, 5, 1)]
        cutoff = datetime(2025, 1, 1)

        before, after = timeSort(cutoff, dt_list)

        # Function expects cutoff between first and last obs
        assert before == []
        assert after == []

    def test_single_observation_cutoff_after(self):
        """Test with single observation when cutoff is after it."""
        dt_list = [datetime(2025, 1, 1)]
        cutoff = datetime(2025, 5, 1)

        before, after = timeSort(cutoff, dt_list)

        assert before == []
        assert after == []

    def test_two_observations_cutoff_between(self):
        """Test with two observations and cutoff between them."""
        dt_list = [
            datetime(2025, 1, 1),
            datetime(2025, 5, 1),
        ]
        cutoff = datetime(2025, 3, 1)

        before, after = timeSort(cutoff, dt_list)

        assert before == [datetime(2025, 1, 1)]
        assert after == [datetime(2025, 5, 1)]

    def test_empty_list(self):
        """Test with empty observation list."""
        dt_list = []
        cutoff = datetime(2025, 3, 1)

        # This will raise IndexError due to t_obs[-1] on empty list
        with pytest.raises(IndexError):
            timeSort(cutoff, dt_list)

    def test_preserves_datetime_objects(self):
        """Test that returned lists contain the same datetime objects."""
        obs1 = datetime(2025, 1, 1, 10, 30)
        obs2 = datetime(2025, 3, 1, 15, 45)
        obs3 = datetime(2025, 5, 1, 20, 0)
        dt_list = [obs1, obs2, obs3]
        cutoff = datetime(2025, 2, 15)

        before, after = timeSort(cutoff, dt_list)

        # Check exact datetime preservation (including time components)
        assert before[0] == obs1
        assert after[0] == obs2
        assert after[1] == obs3
