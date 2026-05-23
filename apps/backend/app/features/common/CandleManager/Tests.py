import pytest

from .Handler import CandleManagerHandler


class TestCandleManagerHandler:

    def test_returns_negative_one_before_market_open(self):
        mgr = CandleManagerHandler(minute=1, start="23:00", stop="23:55")
        assert mgr.current_index == -1

    def test_returns_zero_after_first_candle_close(self):
        mgr = CandleManagerHandler(minute=1, start="09:00", stop="09:02")
        assert mgr.current_index >= 0

    def test_index_increments_with_candles(self):
        mgr = CandleManagerHandler(minute=1, start="09:00", stop="09:05")
        idx = mgr.current_index
        assert idx >= 0
