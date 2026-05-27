from typing import List, Optional

from .Schema import HoldingsRow
from .Handler import TrackHoldingsHandler


class TrackHoldingsController:

    def __init__(self, paper: Optional[bool] = None, data_dir: str = "data") -> None:
        if paper is None:
            from core.config import O_SETG
            paper = bool(O_SETG.get("paper", 0))
        self._handler = TrackHoldingsHandler(data_dir=data_dir, paper=paper)

    def read_all(self) -> List[HoldingsRow]:
        return self._handler.read_all()

    def read_by_symbol(self, tradingsymbol: str) -> List[HoldingsRow]:
        return self._handler.read_by_symbol(tradingsymbol)

    def add_holding(self, row: HoldingsRow) -> None:
        self._handler.add_holding(row)

    def write_all(self, rows: List[HoldingsRow]) -> None:
        self._handler.write_all(rows)
