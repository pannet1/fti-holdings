from pathlib import Path

import pytest

from .Handler import GenerateReportHandler


def _write_csv(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy,multiplier\n")
        for line in lines:
            f.write(line + "\n")


class TestGenerateReportHandler:

    def test_returns_error_when_file_not_found(self, tmp_path: Path) -> None:
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "No trades file found" in result

    def test_returns_error_when_file_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "trades.csv"
        path.write_text("datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy,multiplier\n")
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "empty" in result

    def test_single_buy_sell_cycle(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-28 14:15,NSE,MOTHERSON,SELL,110.00,50,ratchet,0",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "Cycle 1" in result
        assert "+500" in result
        assert "Win rate: 100%" in result

    def test_multi_buy_accumulate_then_sell(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-29 10:15,NSE,MOTHERSON,BUY,95.00,100,ratchet,2",
            "2026-05-30 10:15,NSE,MOTHERSON,SELL,105.00,150,ratchet,0",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "Cycle 1" in result
        expected = str(int(150 * 105.00 - (50 * 100.00 + 100 * 95.00)))
        assert expected in result.replace(",", "")

    def test_multiple_cycles(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-28 14:15,NSE,MOTHERSON,SELL,110.00,50,ratchet,0",
            "2026-05-29 10:15,NSE,MOTHERSON,BUY,105.00,50,ratchet,1",
            "2026-05-29 14:15,NSE,MOTHERSON,SELL,115.00,50,ratchet,0",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "Cycle 1" in result
        assert "Cycle 2" in result
        assert "Total realized P&L:" in result
        assert "1000" in result.replace(",", "")

    def test_uses_paper_path(self, tmp_path: Path) -> None:
        (tmp_path / "paper").mkdir()
        _write_csv(tmp_path / "paper" / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-28 14:15,NSE,MOTHERSON,SELL,110.00,50,ratchet,0",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=True)
        result = handler.generate_report()
        assert "Cycle 1" in result
        assert "+500" in result

    def test_open_position_reported(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-28 14:15,NSE,MOTHERSON,SELL,110.00,50,ratchet,0",
            "2026-05-29 10:15,NSE,MOTHERSON,BUY,120.00,100,ratchet,1",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        result = handler.generate_report()
        assert "Cycle 1" in result
        assert "Open position" in result
        assert "100" in result
        assert "120" in result

    def test_structured_output(self, tmp_path: Path) -> None:
        _write_csv(tmp_path / "trades.csv", [
            "2026-05-28 10:15,NSE,MOTHERSON,BUY,100.00,50,ratchet,1",
            "2026-05-28 14:15,NSE,MOTHERSON,SELL,110.00,50,ratchet,0",
        ])
        handler = GenerateReportHandler(data_dir=str(tmp_path), paper=False)
        report = handler.generate_structured()
        assert report.summary.total_cycles == 1
        assert report.summary.total_pnl == 500.00
        assert report.cycles[0].pnl == 500.00
        assert report.open_position is None

    def test_real_backtest_data(self, tmp_path: Path) -> None:
        real_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent.parent / "data" / "paper" / "trades.csv"
        if not real_path.exists():
            pytest.skip("No real backtest data found")
        handler = GenerateReportHandler(data_dir=str(real_path.parent.parent), paper=True)
        result = handler.generate_report()
        assert "Total realized P&L:" in result
        assert "Cycle 1" in result
