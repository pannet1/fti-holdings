import csv
import logging
from pathlib import Path

from .Schema import HoldingsRow

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy"]


class JournalTradesHandler:

    def __init__(self, data_dir: str = "data") -> None:
        self._filepath = Path(data_dir) / "trades.csv"

    def journal_trade(self, row: HoldingsRow) -> None:
        write_header = not self._filepath.exists()
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row.model_dump())
