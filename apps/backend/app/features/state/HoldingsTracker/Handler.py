import csv
import logging
from pathlib import Path
from typing import List

from .Schema import HoldingsRow

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy"]


class HoldingsTrackerHandler:

    def __init__(self, data_dir: str = "data") -> None:
        self._filepath = Path(data_dir) / "holdings.csv"

    def read_all(self) -> List[HoldingsRow]:
        if not self._filepath.exists():
            return []
        with open(self._filepath) as f:
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

    def remove_holding(self, tradingsymbol: str, quantity: int) -> None:
        if not self._filepath.exists():
            return
        rows = self.read_all()
        remaining = quantity
        updated: List[HoldingsRow] = []
        for row in rows:
            if row.tradingsymbol == tradingsymbol and remaining > 0:
                if row.quantity <= remaining:
                    remaining -= row.quantity
                    continue
                else:
                    row.quantity -= remaining
                    remaining = 0
                    updated.append(row)
            else:
                updated.append(row)
        with open(self._filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in updated:
                writer.writerow(row.model_dump())
