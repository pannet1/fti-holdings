import csv
import logging
from pathlib import Path
from typing import Any, List, Optional

from app.features.state.HoldingsTracker.Schema import HoldingsRow

logger = logging.getLogger(__name__)


class Rachet:
    def __init__(self, data_dir: str = "data", **O_SETG: Any) -> None:
        self.strategy = O_SETG["strategy"]
        self.stop_time = O_SETG["stop_time"]
        self._removable = False
        self._tradingsymbol = O_SETG.get("tradingsymbol", "")
        self._exchange = O_SETG.get("exchange", "NSE")
        self._token = O_SETG.get("instrument_token")
        self._rest = O_SETG.get("rest")
        self._x = O_SETG.get("quantity", 33)
        self._holdings: List[HoldingsRow] = []
        self._total_qty: int = 0
        self._avg_price: float = 0.0
        self._last_buy_price: float = 0.0
        holdings_file = Path(data_dir) / "holdings.csv"
        if holdings_file.exists():
            with open(holdings_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["tradingsymbol"] == self._tradingsymbol:
                        self._holdings.append(HoldingsRow(**row))
            if self._holdings:
                total_value = sum(h.avg_price * h.quantity for h in self._holdings)
                self._total_qty = sum(h.quantity for h in self._holdings)
                self._avg_price = total_value / self._total_qty if self._total_qty > 0 else 0.0
        trades_file = Path(data_dir) / "trades.csv"
        if trades_file.exists():
            with open(trades_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["tradingsymbol"] == self._tradingsymbol and row["side"] == "BUY":
                        self._last_buy_price = float(row["avg_price"])

    def run(self, trades: Any, quotes: dict, positions: Any) -> Optional[dict]:
        cmp = quotes.get(self._tradingsymbol, 0)
        logger.info(f"{self._tradingsymbol} LTP: {cmp}")

        if cmp <= 0:
            return None

        return None
