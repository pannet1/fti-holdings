import pytest
from pathlib import Path

from .Handler import JournalTradesHandler
from .Schema import HoldingsRow
from .Controller import JournalTradesController


class TestJournalTradesHandler:

    def test_journal_trade_creates_file_with_header(self, tmp_path):
        handler = JournalTradesHandler(data_dir=str(tmp_path))
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
        assert content.startswith("datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy,multiplier")

    def test_journal_trade_appends_subsequent_rows(self, tmp_path):
        handler = JournalTradesHandler(data_dir=str(tmp_path))
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
            tradingsymbol="ITBEES",
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
        assert lines[1].endswith("ITBEES,SELL,250.0,33,ratchet,1")
        assert lines[2].endswith("ITBEES,SELL,185.0,33,ratchet,1")


class TestJournalTradesController:

    def test_handle_paper_false(self, tmp_path):
        controller = JournalTradesController(base_data_dir=str(tmp_path))
        row = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="SELL",
            avg_price=250.00,
            quantity=33,
            strategy="ratchet",
        )
        controller.handle(row, paper=False)
        csv_path = tmp_path / "trades.csv"
        assert csv_path.exists()
        assert csv_path.read_text().strip().endswith("ITBEES,SELL,250.0,33,ratchet,1")

    def test_handle_paper_true_creates_in_paper_subdir(self, tmp_path):
        controller = JournalTradesController(base_data_dir=str(tmp_path))
        row = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="SELL",
            avg_price=250.00,
            quantity=33,
            strategy="ratchet",
        )
        controller.handle(row, paper=True)
        csv_path = tmp_path / "paper" / "trades.csv"
        assert csv_path.exists()
        assert csv_path.read_text().strip().endswith("ITBEES,SELL,250.0,33,ratchet,1")

    def test_handle_paper_true_creates_directory_if_not_exists(self, tmp_path):
        controller = JournalTradesController(base_data_dir=str(tmp_path))
        row = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="SELL",
            avg_price=250.00,
            quantity=33,
            strategy="ratchet",
        )
        controller.handle(row, paper=True)
        paper_dir = tmp_path / "paper"
        assert paper_dir.exists()
        assert paper_dir.is_dir()
