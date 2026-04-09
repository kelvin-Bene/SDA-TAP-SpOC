"""Tests for the Timer utility class."""

import time
from io import StringIO
from unittest.mock import patch

import pytest

from uct_benchmark.utils.timerClass import Timer


class TestTimer:
    """Tests for Timer class functionality."""

    def test_timer_initialization(self):
        """Test that Timer initializes with start time and empty checkpoints."""
        timer = Timer()
        assert timer.start is not None
        assert isinstance(timer.start, float)
        assert timer.checkpoints == []
        assert timer.labels == []

    def test_mark_adds_checkpoint(self):
        """Test that mark() adds a checkpoint with the correct label."""
        timer = Timer()
        timer.mark("test_checkpoint")

        assert len(timer.checkpoints) == 1
        assert len(timer.labels) == 1
        assert timer.labels[0] == "test_checkpoint"

    def test_mark_multiple_checkpoints(self):
        """Test adding multiple checkpoints in sequence."""
        timer = Timer()

        timer.mark("first")
        time.sleep(0.01)  # Small delay to ensure measurable time difference
        timer.mark("second")
        timer.mark("third")

        assert len(timer.checkpoints) == 3
        assert timer.labels == ["first", "second", "third"]
        # Checkpoints should be in increasing order
        assert timer.checkpoints[0] <= timer.checkpoints[1] <= timer.checkpoints[2]

    def test_checkpoint_times_are_after_start(self):
        """Test that all checkpoint times are after the start time."""
        timer = Timer()
        time.sleep(0.01)  # 10ms — more reliable than 1ms under load
        timer.mark("checkpoint")

        assert timer.checkpoints[0] >= timer.start

    @pytest.mark.asyncio
    async def test_mark_async(self):
        """Test that mark_async() works the same as mark()."""
        timer = Timer()
        await timer.mark_async("async_checkpoint")

        assert len(timer.checkpoints) == 1
        assert timer.labels[0] == "async_checkpoint"

    def test_report_output(self):
        """Test that report() outputs correctly formatted timing information."""
        timer = Timer()
        timer.mark("step1")
        timer.mark("step2")

        # Capture stdout
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            timer.report()
            output = mock_stdout.getvalue()

        # Check output format
        assert "step1:" in output
        assert "step2:" in output
        assert "Total:" in output
        assert "s" in output  # seconds unit

    def test_report_with_no_checkpoints(self):
        """Test report() with no checkpoints (edge case)."""
        timer = Timer()

        # Should not raise an error
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            timer.report()
            output = mock_stdout.getvalue()

        # Should still show total time
        assert "Total:" in output

    def test_elapsed_time_accuracy(self):
        """Test that elapsed time measurement is reasonably accurate."""
        timer = Timer()
        sleep_duration = 0.1  # 100ms — generous to avoid flakiness under load
        time.sleep(sleep_duration)
        timer.mark("after_sleep")

        elapsed = timer.checkpoints[0] - timer.start
        # Wide tolerance: system load can cause sleep to overshoot significantly
        assert elapsed >= sleep_duration * 0.3
        assert elapsed < sleep_duration * 5
