import csv
import logging
from pathlib import Path
from typing import Any, List, Optional

from app.features.common.ManageCandle.Handler import ManageCandleHandler
from app.features.state.TrackHoldings.Schema import HoldingsRow

logger = logging.getLogger(__name__)


class Rachet:
    def __init__(self, data_dir: str = "data", **O_SETG: Any) -> None:
        self.strategy = O_SETG["strategy"]
        self.stop_time = O_SETG["stop_time"]
        self._data_dir = data_dir
        self._removable = False
        self._tradingsymbol = O_SETG.get("tradingsymbol", "")
        self._exchange = O_SETG.get("exchange", "NSE")
        self._token = O_SETG.get("instrument_token")
        self._x = O_SETG.get("quantity", 33)
        self._multiplier: List[int] = O_SETG.get("multiplier", [1])
        self._perc: float = O_SETG.get("perc", 0.05)
        self._candle = ManageCandleHandler(
            minute=O_SETG["candle"],
            start=O_SETG.get("start_time", "09:00"),
            stop=O_SETG.get("stop_time", "15:30"),
        )
        self._last_candle_idx: int = -1
        self._holdings: List[HoldingsRow] = []
        self._total_qty: int = 0
        self._avg_price: float = 0.0
        self._last_buy_price: float = 0.0
        self._last_buy_qty: int = self._x
        self._win_qty: int = self._x
        self._loss_qty: int = self._x
        holdings_file = Path(data_dir) / "holdings.csv"
        if holdings_file.exists():
            self._read_holdings(holdings_file)
        else:
            trades_file = Path(data_dir) / "trades.csv"
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
        cmp = quotes.get(self._tradingsymbol, 0)
        logger.info(f"{self._tradingsymbol} LTP: {cmp}")

        if cmp <= 0:
            return None

        curr_idx = self._candle.current_index
        if curr_idx <= self._last_candle_idx:
            return None
        self._last_candle_idx = curr_idx

        self._read_holdings(Path(self._data_dir) / "holdings.csv")

        if not self._holdings:
            if self._last_buy_price > 0:
                if cmp > self._last_buy_price:
                    qty = self._win_qty
                else:
                    qty = self._loss_qty
            else:
                qty = self._x

            return {
                "action": "BUY",
                "tradingsymbol": self._tradingsymbol,
                "exchange": self._exchange,
                "quantity": qty,
                "price": cmp,
            }

        target = self._avg_price * (1.0 + self._perc)
        if cmp >= target:
            return {
                "action": "SELL",
                "tradingsymbol": self._tradingsymbol,
                "exchange": self._exchange,
                "quantity": self._x,
                "price": cmp,
            }

        return None
