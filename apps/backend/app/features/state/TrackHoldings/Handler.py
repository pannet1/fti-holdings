import csv
import logging
from pathlib import Path
from typing import List

from .Schema import HoldingsRow

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy"]


class TrackHoldingsHandler:

    def __init__(self, data_dir: str = "data", paper: bool = False) -> None:
        base = Path(data_dir)
        if paper:
            self._filepath = base / "paper" / "holdings.csv"
        else:
            self._filepath = base / "holdings.csv"

    def read_all(self) -> List[HoldingsRow]:
        if not self._filepath.exists():
            return []
        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            return [HoldingsRow(**row) for row in reader]

    def read_by_symbol(self, tradingsymbol: str) -> List[HoldingsRow]:
        return [row for row in self.read_all() if row.tradingsymbol == tradingsymbol]

    def add_holding(self, row: HoldingsRow) -> None:
        write_header = not self._filepath.exists()
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row.model_dump())

    def write_all(self, rows: List[HoldingsRow]) -> None:
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row.model_dump())
