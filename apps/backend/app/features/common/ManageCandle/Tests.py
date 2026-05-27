import pendulum as pdlm

import pytest

from .Handler import ManageCandleHandler


class TestManageCandleHandler:

    def test_returns_negative_one_when_forced(self):
        mgr = ManageCandleHandler(minute=1, start="23:00", stop="23:55")
        mgr.force_index(-1)
        assert mgr.current_index == -1

    def test_returns_correct_index_when_forced(self):
        mgr = ManageCandleHandler(minute=1, start="09:00", stop="09:02")
        mgr.force_index(0)
        assert mgr.current_index == 0

    def test_index_increments_with_candles(self):
        mgr = ManageCandleHandler(minute=1, start="09:00", stop="09:05")
        mgr.force_index(0)
        assert mgr.current_index == 0
        mgr.force_index(1)
        assert mgr.current_index == 1

    def test_check_close_returns_none_before_first_candle(self):
        mgr = ManageCandleHandler(minute=1, start="09:00", stop="09:02")
        mgr.force_index(-1)
        assert mgr.check_close() is None

    def test_check_close_announces_candle_close_once(self):
        mgr = ManageCandleHandler(minute=1, start="09:00", stop="09:02")
        mgr.force_index(0)
        event = mgr.check_close()
        assert event is not None
        assert event["index"] == 0
        assert "close_time" in event
        assert event["is_truncated"] is False
        assert mgr.check_close() is None

    def test_check_close_announces_each_candle_once(self):
        mgr = ManageCandleHandler(minute=1, start="09:00", stop="09:02")
        mgr.force_index(0)
        e1 = mgr.check_close()
        assert e1 is not None
        assert e1["index"] == 0
        assert mgr.check_close() is None
        mgr.force_index(1)
        e2 = mgr.check_close()
        assert e2 is not None
        assert e2["index"] == 1
        assert mgr.check_close() is None

    def test_is_truncated_last_candle(self):
        mgr = ManageCandleHandler(minute=240, start="09:15", stop="15:30")
        mgr.force_index(0)
        e0 = mgr.check_close()
        assert e0["is_truncated"] is False
        mgr.force_index(1)
        e1 = mgr.check_close()
        assert e1["is_truncated"] is True
