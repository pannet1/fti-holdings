import pytest

from .Handler import RatchetStrategyRunHandler
from .Rachet import Rachet


class TestRatchetStrategyRunHandler:

    def test_execute_requires_strategy_in_config(self):
        handler = RatchetStrategyRunHandler()
        with pytest.raises(KeyError):
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
        )
        assert result["status"] == "ok"
        assert result["strategy"] == "ratchet"
        assert result["tradingsymbol"] == "ITBEES"

    def test_execute_tick_returns_none_for_hold(self):
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
        )
        strategy = Rachet(
            strategy="ratchet",
            base="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
        )
        signal = handler.execute_tick(strategy=strategy, quotes={"ITBEES": 245.50})
        assert signal is None

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

    def test_ratchet_object_is_created(self, tmp_path):
        inst = Rachet(
            data_dir=str(tmp_path),
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
        assert inst._total_qty == 0
        assert inst._avg_price == 0.0

    def test_run_returns_none_for_hold_by_default(self):
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
        signal = inst.run(trades=None, quotes=quotes, positions=None)
        assert signal is None

    def test_run_returns_none_on_zero_quote(self):
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
        quotes = {"ITBEES": 0}
        signal = inst.run(trades=None, quotes=quotes, positions=None)
        assert signal is None
