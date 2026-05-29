import pytest
import tempfile
from pathlib import Path
from .Handler import TrackHoldingsHandler
from .Schema import HoldingsRow


class TestTrackHoldingsHandler:

    @pytest.fixture
    def temp_data_dir(self) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_read_all_returns_empty_list_when_no_file(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=False)
        assert handler.read_all() == []

    def test_add_holding_and_read_all(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=False)
        handler.ensure()
        row = HoldingsRow(
            datetime="2023-01-01",
            exchange="NSE",
            tradingsymbol="ABC",
            side="BUY",
            avg_price=100.0,
            quantity=10,
            strategy="test",
        )
        handler.add_holding(row)
        rows = handler.read_all()
        assert len(rows) == 1
        assert rows[0] == row

    def test_read_by_symbol(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=False)
        handler.ensure()
        row1 = HoldingsRow(
            datetime="2023-01-01",
            exchange="NSE",
            tradingsymbol="ABC",
            side="BUY",
            avg_price=100.0,
            quantity=10,
            strategy="test",
        )
        row2 = HoldingsRow(
            datetime="2023-01-02",
            exchange="NSE",
            tradingsymbol="XYZ",
            side="SELL",
            avg_price=200.0,
            quantity=5,
            strategy="test",
        )
        handler.add_holding(row1)
        handler.add_holding(row2)
        result = handler.read_by_symbol("ABC")
        assert len(result) == 1
        assert result[0] == row1

    def test_read_by_symbol_returns_empty_list_when_no_match(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=False)
        result = handler.read_by_symbol("NONEXISTENT")
        assert result == []

    def test_paper_mode_uses_different_path(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=True)
        handler.ensure()
        row = HoldingsRow(
            datetime="2023-01-01",
            exchange="NSE",
            tradingsymbol="ABC",
            side="BUY",
            avg_price=100.0,
            quantity=10,
            strategy="test",
        )
        handler.add_holding(row)
        assert Path(temp_data_dir, "paper", "holdings.csv").exists()
        rows = handler.read_all()
        assert len(rows) == 1

    def test_write_all_overwrites_file(self, temp_data_dir):
        handler = TrackHoldingsHandler(data_dir=temp_data_dir, paper=False)
        handler.ensure()
        row1 = HoldingsRow(
            datetime="2023-01-01",
            exchange="NSE",
            tradingsymbol="ABC",
            side="BUY",
            avg_price=100.0,
            quantity=10,
            strategy="test",
        )
        handler.add_holding(row1)
        row2 = HoldingsRow(
            datetime="2023-01-02",
            exchange="BSE",
            tradingsymbol="XYZ",
            side="SELL",
            avg_price=200.0,
            quantity=5,
            strategy="test2",
        )
        handler.write_all([row2])
        rows = handler.read_all()
        assert len(rows) == 1
        assert rows[0] == row2
