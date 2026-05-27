import yaml
from pathlib import Path

import pytest

from .Handler import RunRatchetStrategyHandler
from .Ratchet import Rachet


def _candle_from_settings() -> int:
    path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent / "data" / "settings.yml"
    with open(path) as f:
        raw = yaml.safe_load(f)
    return raw["candle"]


class TestRunRatchetStrategyHandler:

    def test_execute_requires_strategy_in_config(self):
        handler = RunRatchetStrategyHandler()
        with pytest.raises(KeyError):
            handler.execute(config={})

    def test_execute_returns_strategy_info(self):
        handler = RunRatchetStrategyHandler()
        result = handler.execute(
            config={
                "strategy": "ratchet",
                "base": "ITBEES",
                "tradingsymbol": "ITBEES",
                "exchange": "BSE",
                "quantity": 33,
                "start_time": "09:30",
                "stop_time": "15:00",
                "multiplier": [1, 2, 3, 5, 8, 13, 21, 33, 55],
                "perc": 0.05,
                "candle": _candle_from_settings(),
            },
        )
        assert result["status"] == "ok"
        assert result["strategy"] == "ratchet"
        assert result["tradingsymbol"] == "ITBEES"

    def test_execute_tick_returns_buy_signal_when_no_holdings(self):
        handler = RunRatchetStrategyHandler()
        strategy = Rachet(
            strategy="ratchet",
            base="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        strategy._candle.force_index(0)
        signal = handler.execute_tick(strategy=strategy, quotes={"ITBEES": 245.50})
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["quantity"] == 33

    def test_load_strategies_returns_empty_on_bad_config(self):
        handler = RunRatchetStrategyHandler()
        instances = handler.load_strategies([{}])
        assert instances == []

    def test_schema_validates_config(self):
        from .Schema import RunRatchetStrategySchema
        schema = RunRatchetStrategySchema(
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
                    "multiplier": [1, 2, 3],
                    "perc": 0.05,
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
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        assert inst.strategy == "ratchet"
        assert inst._tradingsymbol == "ITBEES"
        assert inst._x == 33
        assert inst._multiplier == [1, 2, 3, 5, 8, 13, 21, 33, 55]
        assert inst._perc == 0.05
        assert inst._total_qty == 0
        assert inst._avg_price == 0.0
        assert inst._last_buy_price == 0.0
        assert inst._last_buy_qty == 33

    def test_uses_trades_csv_when_no_holdings(self, tmp_path):
        trades_csv = tmp_path / "trades.csv"
        trades_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 09:30,BSE,ITBEES,BUY,245.00,66,ratchet\n"
            "2026-05-22 10:15,BSE,ITBEES,BUY,244.50,99,ratchet\n"
        )
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        assert inst._total_qty == 0
        assert inst._holdings == []
        assert inst._last_buy_price == 244.50
        assert inst._last_buy_qty == 99

    def test_init_buy_when_no_holdings(self):
        inst = Rachet(
            strategy="ratchet",
            base="ITBEES",
            symbol="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        quotes = {"ITBEES": 245.50}
        inst._candle.force_index(0)
        signal = inst.run(trades=None, quotes=quotes, positions=None)
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["tradingsymbol"] == "ITBEES"
        assert signal["exchange"] == "BSE"
        assert signal["quantity"] == 33
        assert signal["price"] == 245.50

    def test_reentry_uses_configured_x_when_no_trades_csv(self, tmp_path):
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        signal = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["quantity"] == 33

    def test_reentry_uses_last_buy_qty_from_trades_csv(self, tmp_path):
        trades_csv = tmp_path / "trades.csv"
        trades_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 10:15,BSE,ITBEES,BUY,244.50,99,ratchet\n"
        )
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        signal = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["quantity"] == 99

    def test_candle_timing_skips_second_call(self):
        inst = Rachet(
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        signal1 = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal1 is not None
        signal2 = inst.run(trades=None, quotes={"ITBEES": 251.00}, positions=None)
        assert signal2 is None

    def test_refreshes_holdings_between_candles(self, tmp_path):
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        signal1 = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal1 is not None
        holdings_csv = tmp_path / "holdings.csv"
        holdings_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 09:30,BSE,ITBEES,BUY,250.00,33,ratchet\n"
        )
        inst._candle.force_index(1)
        signal2 = inst.run(trades=None, quotes={"ITBEES": 251.00}, positions=None)
        assert signal2 is None

    def test_returns_none_when_holdings_exist(self, tmp_path):
        holdings_csv = tmp_path / "holdings.csv"
        holdings_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 09:30,BSE,ITBEES,BUY,245.00,33,ratchet\n"
        )
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        signal = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal is None

    def test_sells_when_holdings_reach_target_profit(self, tmp_path):
        holdings_csv = tmp_path / "holdings.csv"
        holdings_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 09:30,BSE,ITBEES,BUY,245.00,33,ratchet\n"
        )
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        target = 245.00 * 1.05
        signal = inst.run(trades=None, quotes={"ITBEES": target + 0.01}, positions=None)
        assert signal is not None
        assert signal["action"] == "SELL"
        assert signal["quantity"] == 33
        assert signal["price"] == target + 0.01

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
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        quotes = {"ITBEES": 0}
        signal = inst.run(trades=None, quotes=quotes, positions=None)
        assert signal is None

    def test_suppresses_buy_on_same_day_as_sell_no_holdings(self):
        inst = Rachet(
            strategy="ratchet",
            base="ITBEES",
            symbol="ITBEES",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._candle.force_index(0)
        signal1 = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal1 is not None
        assert signal1["action"] == "BUY"
        inst._last_sell_date = signal1["time"][:10]
        inst._candle.force_index(1)
        signal2 = inst.run(trades=None, quotes={"ITBEES": 250.00}, positions=None)
        assert signal2 is None

    def test_suppresses_ladder_buy_on_same_day_as_sell(self, tmp_path):
        holdings_csv = tmp_path / "holdings.csv"
        holdings_csv.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2026-05-22 09:30,BSE,ITBEES,BUY,245.00,33,ratchet\n"
        )
        inst = Rachet(
            data_dir=str(tmp_path),
            strategy="ratchet",
            tradingsymbol="ITBEES",
            exchange="BSE",
            quantity=33,
            start_time="09:30",
            stop_time="15:00",
            multiplier=[1, 2, 3, 5, 8, 13, 21, 33, 55],
            perc=0.05,
            candle=_candle_from_settings(),
        )
        inst._last_sell_date = "2026-05-22"
        signal = inst.run(trades=None, quotes={"ITBEES": 232.00}, positions=None)
        assert signal is None
