import csv
import logging
from pathlib import Path
from typing import Any, List, Optional

import pendulum as pdlm
from app.features.common.ManageCandle.Handler import ManageCandleHandler
from app.features.state.TrackHoldings.Schema import HoldingsRow

logger = logging.getLogger(__name__)


class Rachet:
    def __init__(self, data_dir: str = "data", **O_SETG: Any) -> None:
        self.strategy = O_SETG["strategy"]
        self._data_dir = data_dir
        self._paper = bool(O_SETG.get("paper", 0))
        self._removable = False
        self._tradingsymbol = O_SETG.get("tradingsymbol", "")
        self._exchange = O_SETG.get("exchange", "NSE")
        self._token = O_SETG.get("instrument_token")
        self._x = O_SETG.get("quantity", 33)
        self._multiplier: List[int] = O_SETG.get("multiplier", [1])
        self._perc: float = O_SETG.get("perc", 0.05)
        self._start_time = O_SETG.get("start_time", "09:00")
        self._stop_time = O_SETG.get("stop_time", "15:30")
        self._candle = ManageCandleHandler(
            minute=O_SETG["candle"],
            start=self._start_time,
            stop=self._stop_time,
        )
        self._holdings: List[HoldingsRow] = []
        self._total_qty: int = 0
        self._avg_price: float = 0.0
        self._last_buy_price: float = 0.0
        self._last_buy_qty: int = self._x
        self._last_sell_date: str | None = None
        self._win_qty: int = self._x
        self._loss_qty: int = self._x
        holdings_file = self._holdings_path()
        if holdings_file.exists():
            self._read_holdings(holdings_file)
        else:
            trades_file = self._trades_path()
            if trades_file.exists():
                with open(trades_file) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["tradingsymbol"] == self._tradingsymbol and row["side"] == "BUY":
                            self._last_buy_price = float(row["avg_price"])
                            self._last_buy_qty = int(row["quantity"])
            if self._last_buy_price > 0:
                ratio = self._last_buy_qty / self._x
                closest = min(self._multiplier, key=lambda m: abs(m - ratio))
                last_idx = self._multiplier.index(closest)
                self._win_qty = self._x * self._multiplier[max(0, last_idx - 1)]
                self._loss_qty = self._x * self._multiplier[min(len(self._multiplier) - 1, last_idx + 1)]

    def _holdings_path(self) -> Path:
        base = Path(self._data_dir)
        if self._paper:
            return base / "paper" / "holdings.csv"
        return base / "holdings.csv"

    def _trades_path(self) -> Path:
        base = Path(self._data_dir)
        if self._paper:
            return base / "paper" / "trades.csv"
        return base / "trades.csv"

    def _read_holdings(self, holdings_file: Path) -> None:
        self._holdings = []
        self._total_qty = 0
        self._avg_price = 0.0
        if not holdings_file.exists():
            return
        with open(holdings_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["tradingsymbol"] == self._tradingsymbol:
                    self._holdings.append(HoldingsRow(**row))
        if self._holdings:
            total_value = sum(h.avg_price * h.quantity for h in self._holdings)
            self._total_qty = sum(h.quantity for h in self._holdings)
            self._avg_price = total_value / self._total_qty if self._total_qty > 0 else 0.0

    def run(self, trades: Any, quotes: dict, positions: Any) -> Optional[dict]:
        cmp = quotes.get(self._tradingsymbol)
        if not cmp:
            return None

        self._read_holdings(self._holdings_path())

        now_raw = quotes.get("_time")
        now_str: str | None = str(now_raw) if now_raw else None
        if now_str is None:
            close_event = self._candle.check_close()
            if close_event is None:
                return None
            now_str = close_event["close_time"]

        try:
            dt = pdlm.from_format(now_str, "YYYY-MM-DD HH:mm:ss")
        except ValueError:
            dt = pdlm.from_format(now_str, "DD-MM-YYYY HH:mm:ss")
        now_str = dt.format("YYYY-MM-DD HH:mm:ss")

        if now_str[11:16] < self._start_time or now_str[11:16] > self._stop_time:
            return None

        trade_date = now_str[:10]

        if not self._holdings:
            if trade_date == self._last_sell_date:
                return None
            qty = self._last_buy_qty
            self._x = qty
            return {
                "action": "BUY",
                "tradingsymbol": self._tradingsymbol,
                "exchange": self._exchange,
                "quantity": qty,
                "price": cmp,
                "time": now_str,
                "multiplier": 1,
            }

        sell_target = self._avg_price * (1.0 + self._perc)
        if cmp > sell_target:
            self._last_sell_date = trade_date
            return {
                "action": "SELL",
                "tradingsymbol": self._tradingsymbol,
                "exchange": self._exchange,
                "quantity": self._total_qty,
                "price": cmp,
                "time": now_str,
                "multiplier": 0,
            }

        if trade_date == self._last_sell_date:
            return None

        last_price = self._holdings[-1].avg_price
        buy_lower = last_price * (1.0 - self._perc)
        buy_upper = last_price * (1.0 + self._perc)
        if cmp <= buy_lower or cmp >= buy_upper:
            last_qty = self._holdings[-1].quantity
            ratio = last_qty / self._x
            closest = min(self._multiplier, key=lambda m: abs(m - ratio))
            current_idx = self._multiplier.index(closest)
            if cmp >= buy_upper:
                next_idx = max(0, current_idx - 1)
            else:
                next_idx = min(len(self._multiplier) - 1, current_idx + 1)
            qty = self._x * self._multiplier[next_idx]
            self._last_buy_qty = qty
            return {
                "action": "BUY",
                "tradingsymbol": self._tradingsymbol,
                "exchange": self._exchange,
                "quantity": qty,
                "price": cmp,
                "time": now_str,
                "multiplier": self._multiplier[next_idx],
            }

        return None
