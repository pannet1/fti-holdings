import pytest
from pathlib import Path

from .Handler import TradesJournalHandler
from .Schema import HoldingsRow


class TestTradesJournalHandler:

    def test_journal_trade_creates_file_with_header(self, tmp_path):
        handler = TradesJournalHandler(data_dir=str(tmp_path))
        row = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="SELL",
            avg_price=250.00,
            quantity=33,
            strategy="ratchet",
        )
        handler.journal_trade(row)
        csv_path = tmp_path / "trades.csv"
        assert csv_path.exists()
        content = csv_path.read_text()
        assert content.startswith("datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy")

    def test_journal_trade_appends_subsequent_rows(self, tmp_path):
        handler = TradesJournalHandler(data_dir=str(tmp_path))
        row1 = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="SELL",
            avg_price=250.00,
            quantity=33,
            strategy="ratchet",
        )
        row2 = HoldingsRow(
            datetime="2024-01-15 11:00:00",
            exchange="BSE",
            tradingsymbol="MOTHERSON",
            side="SELL",
            avg_price=185.00,
            quantity=33,
            strategy="ratchet",
        )
        handler.journal_trade(row1)
        handler.journal_trade(row2)
        csv_path = tmp_path / "trades.csv"
        lines = csv_path.read_text().strip().split("\n")
        assert len(lines) == 3
        assert lines[1].endswith("ITBEES,SELL,250.0,33,ratchet")
        assert lines[2].endswith("MOTHERSON,SELL,185.0,33,ratchet")
