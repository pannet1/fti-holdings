import csv
import logging
from pathlib import Path
from typing import List

from .Schema import HoldingsRow

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy", "multiplier"]


class TrackHoldingsHandler:

    def __init__(self, data_dir: str = "data", paper: bool = False) -> None:
        base = Path(data_dir)
        if paper:
            self._filepath = base / "paper" / "holdings.csv"
        else:
            self._filepath = base / "holdings.csv"

    def ensure(self) -> None:
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self._filepath.exists():
            with open(self._filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()

    def read_all(self) -> List[HoldingsRow]:
        if not self._filepath.exists():
            return []
        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            return [HoldingsRow(**row) for row in reader]

    def read_by_symbol(self, tradingsymbol: str) -> List[HoldingsRow]:
        return [row for row in self.read_all() if row.tradingsymbol == tradingsymbol]

    def add_holding(self, row: HoldingsRow) -> None:
        with open(self._filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writerow(row.model_dump())

    def write_all(self, rows: List[HoldingsRow]) -> None:
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row.model_dump())

    def remove_holding(self, tradingsymbol: str, quantity: int) -> List[HoldingsRow]:
        if not self._filepath.exists():
            return []
        rows = self.read_all()
        remaining = quantity
        removed: List[HoldingsRow] = []
        updated: List[HoldingsRow] = []
        for row in rows:
            if row.tradingsymbol == tradingsymbol and remaining > 0:
                remove_qty = min(row.quantity, remaining)
                removed.append(HoldingsRow(
                    datetime=row.datetime,
                    exchange=row.exchange,
                    tradingsymbol=row.tradingsymbol,
                    side=row.side,
                    avg_price=row.avg_price,
                    quantity=remove_qty,
                    strategy=row.strategy,
                    multiplier=row.multiplier,
                ))
                remaining -= remove_qty
                if row.quantity > remove_qty:
                    updated.append(HoldingsRow(
                        datetime=row.datetime,
                        exchange=row.exchange,
                        tradingsymbol=row.tradingsymbol,
                        side=row.side,
                        avg_price=row.avg_price,
                        quantity=row.quantity - remove_qty,
                        strategy=row.strategy,
                        multiplier=row.multiplier,
                    ))
            else:
                updated.append(row)
        self.write_all(updated)
        return removed
