import pytest
from pathlib import Path

from .Handler import TrackHoldingsHandler
from .Schema import HoldingsRow


class TestTrackHoldingsHandler:

    def test_read_all_returns_empty_when_file_missing(self, tmp_path):
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        result = handler.read_all()
        assert result == []

    def test_read_all_returns_all_rows(self, tmp_path):
        csv_path = tmp_path / "holdings.csv"
        csv_path.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2024-01-15 10:30:00,BSE,ITBEES,BUY,245.50,33,ratchet\n"
            "2024-01-15 11:00:00,BSE,SYM_B,BUY,180.75,33,ratchet\n"
        )
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        result = handler.read_all()
        assert len(result) == 2
        assert result[0].tradingsymbol == "ITBEES"
        assert result[1].tradingsymbol == "SYM_B"

    def test_read_by_symbol_filters_correctly(self, tmp_path):
        csv_path = tmp_path / "holdings.csv"
        csv_path.write_text(
            "datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy\n"
            "2024-01-15 10:30:00,BSE,ITBEES,BUY,245.50,33,ratchet\n"
            "2024-01-15 10:31:00,BSE,ITBEES,BUY,246.00,33,ratchet\n"
            "2024-01-15 11:00:00,BSE,SYM_B,BUY,180.75,33,ratchet\n"
        )
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        itbees = handler.read_by_symbol("ITBEES")
        sym_b = handler.read_by_symbol("SYM_B")
        assert len(itbees) == 2
        assert len(sym_b) == 1
        assert all(r.tradingsymbol == "ITBEES" for r in itbees)
        assert all(r.tradingsymbol == "SYM_B" for r in sym_b)

    def test_add_holding_appends_row(self, tmp_path):
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        row = HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="BUY",
            avg_price=245.50,
            quantity=33,
            strategy="ratchet",
        )
        handler.add_holding(row)
        rows = handler.read_all()
        assert len(rows) == 1
        assert rows[0].tradingsymbol == "ITBEES"
        assert rows[0].quantity == 33

    def test_remove_holding_reduces_quantity(self, tmp_path):
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        handler.add_holding(HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="BUY",
            avg_price=245.50,
            quantity=33,
            strategy="ratchet",
        ))
        handler.add_holding(HoldingsRow(
            datetime="2024-01-15 10:31:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="BUY",
            avg_price=246.00,
            quantity=33,
            strategy="ratchet",
        ))
        handler.remove_holding("ITBEES", 33)
        rows = handler.read_all()
        assert len(rows) == 1
        assert rows[0].quantity == 33

    def test_remove_holding_removes_full_row_when_quantity_reaches_zero(self, tmp_path):
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        handler.add_holding(HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="BUY",
            avg_price=245.50,
            quantity=33,
            strategy="ratchet",
        ))
        handler.remove_holding("ITBEES", 33)
        rows = handler.read_all()
        assert len(rows) == 0

    def test_remove_holding_does_nothing_for_nonexistent_symbol(self, tmp_path):
        handler = TrackHoldingsHandler(data_dir=str(tmp_path))
        handler.add_holding(HoldingsRow(
            datetime="2024-01-15 10:30:00",
            exchange="BSE",
            tradingsymbol="ITBEES",
            side="BUY",
            avg_price=245.50,
            quantity=33,
            strategy="ratchet",
        ))
        handler.remove_holding("SYM_B", 33)
        rows = handler.read_all()
        assert len(rows) == 1
        assert rows[0].tradingsymbol == "ITBEES"
