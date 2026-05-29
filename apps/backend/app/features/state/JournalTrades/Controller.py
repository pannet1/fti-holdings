import logging
from pathlib import Path

from .Handler import JournalTradesHandler
from .Schema import HoldingsRow

logger = logging.getLogger(__name__)


class JournalTradesController:

    def __init__(self, base_data_dir: str = "data") -> None:
        self._base_data_dir = base_data_dir

    def handle(self, row: HoldingsRow, paper: bool) -> None:
        if paper:
            data_dir = str(Path(self._base_data_dir) / "paper")
        else:
            data_dir = self._base_data_dir
        handler = JournalTradesHandler(data_dir=data_dir)
        handler.ensure()
        handler.journal_trade(row)
