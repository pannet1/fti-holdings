import pytest
from unittest.mock import Mock

from .Handler import RatchetStrategyRunHandler
from .Rachet import Rachet


class TestRatchetStrategyRunHandler:

    def test_execute_accepts_empty_strategies(self):
        handler = RatchetStrategyRunHandler()
        with pytest.raises(ValueError, match="Authenticated broker session required"):
            handler.execute(config={})

    def test_execute_returns_strategy_info(self):
        handler = RatchetStrategyRunHandler()
        result = handler.execute(
            config={
                "strategy": "ratchet",
                "base": "ITBEES",
                "tradingsymbol": "ITBEES",
                "exchange": "BSE",
                "quantity": 33,
                "start_time": "09:30",
                "stop_time": "15:00",
            },
            broker_session=Mock(),
        )
        assert result["status"] == "ok"
        assert result["strategy"] == "ratchet"
        assert result["tradingsymbol"] == "ITBEES"

    def test_load_strategies_returns_empty_on_bad_config(self):
        handler = RatchetStrategyRunHandler()
        instances = handler.load_strategies([{}])
        assert instances == []

    def test_schema_validates_config(self):
        from .Schema import RatchetStrategyRunSchema
        schema = RatchetStrategyRunSchema(
            start="09:15",
            stop="15:30",
            strategies=[
                {
                    "strategy": "ratchet",
                    "base": "NIFTY",
                    "symbol": "NIFTYBEES",
                    "exchange": "NSE",
                    "quantity": 33,
                    "start_time": "09:30",
                    "stop_time": "15:00",
                }
            ],
        )
        assert schema.start == "09:15"
        assert len(schema.strategies) == 1


class TestRachetStrategy:

    def test_ratchet_object_is_created(self):
        inst = Rachet(
            strategy="ratchet",
            base="ITBEES",
            symbol="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
        )
        assert inst.strategy == "ratchet"
        assert inst._tradingsymbol == "ITBEES"
        assert inst._x == 33

    def test_run_accepts_bse_ws_quotes(self):
        inst = Rachet(
            strategy="ratchet",
            base="ITBEES",
            symbol="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
        )
        quotes = {"ITBEES": 245.50, "MOTHERSON": 180.75}
        inst.run(trades=None, quotes=quotes, positions=None)
        assert inst._tradingsymbol == "ITBEES"
