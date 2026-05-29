import csv
import logging
from pathlib import Path

from .Schema import HoldingsRow

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy", "multiplier"]


class JournalTradesHandler:

    def __init__(self, data_dir: str = "data", paper: bool = False) -> None:
        base = Path(data_dir)
        if paper:
            self._filepath = base / "paper" / "trades.csv"
        else:
            self._filepath = base / "trades.csv"

    def ensure(self) -> None:
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self._filepath.exists():
            with open(self._filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def journal_trade(self, row: HoldingsRow) -> None:
        with open(self._filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(row.model_dump())
