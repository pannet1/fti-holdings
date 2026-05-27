import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .Schema import CycleReport, OpenPosition, ReportSummary, TradeReport

logger = logging.getLogger(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy", "multiplier"]


class GenerateReportHandler:

    def __init__(self, data_dir: str = "data", paper: bool = False) -> None:
        base = Path(data_dir)
        if paper:
            self._filepath = base / "paper" / "trades.csv"
        else:
            self._filepath = base / "trades.csv"

    def generate_report(self) -> str:
        if not self._filepath.exists():
            return f"No trades file found at {self._filepath}"

        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return "Trades file is empty"

        cycles: list[CycleReport] = []
        buy_stack: list[tuple[int, float]] = []
        peak_capital: float = 0.0
        open_position: OpenPosition | None = None

        first_date = rows[0]["datetime"][:10]
        last_date = rows[-1]["datetime"][:10]

        for i, row in enumerate(rows):
            qty = int(row["quantity"])
            price = float(row["avg_price"])
            if row["side"] == "BUY":
                buy_stack.append((qty, price))
            else:
                if not buy_stack:
                    return f"Trade data error: SELL at row {i + 1} with no preceding BUYs"
                buy_qty = sum(bq for bq, _ in buy_stack)
                if qty > buy_qty:
                    return f"Trade data error: SELL qty {qty} exceeds BUY stack {buy_qty} at row {i + 1}"
                buy_total = sum(bq * bp for bq, bp in buy_stack)
                buy_avg = buy_total / buy_qty
                sell_total = qty * price
                pnl = sell_total - buy_total
                pnl_pct = (pnl / buy_total) * 100
                peak_capital = max(peak_capital, buy_total)
                cycles.append(CycleReport(
                    cycle=len(cycles) + 1,
                    buy_quantity=buy_qty,
                    buy_avg_price=round(buy_avg, 2),
                    buy_total=round(buy_total, 2),
                    sell_price=price,
                    sell_total=round(sell_total, 2),
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                ))
                buy_stack = []

        if buy_stack:
            qty = sum(bq for bq, _ in buy_stack)
            avg = sum(bq * bp for bq, bp in buy_stack) / qty
            invested = sum(bq * bp for bq, bp in buy_stack)
            open_position = OpenPosition(quantity=qty, avg_price=round(avg, 2), invested=round(invested, 2))

        total_pnl = sum(c.pnl for c in cycles)
        total_cycles = len(cycles)
        win_rate = 100.0 if total_cycles > 0 and all(c.pnl > 0 for c in cycles) else 0.0
        initial_stake = cycles[0].buy_total if cycles else 0.0
        return_on_stake_pct = (total_pnl / initial_stake * 100) if initial_stake else 0.0
        return_on_peak_pct = (total_pnl / peak_capital * 100) if peak_capital else 0.0
        days = (datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date != last_date else 0

        summary = ReportSummary(
            total_cycles=total_cycles,
            win_rate=win_rate,
            total_pnl=round(total_pnl, 2),
            initial_stake=round(initial_stake, 2),
            peak_capital=round(peak_capital, 2),
            return_on_peak_pct=round(return_on_peak_pct, 2),
            return_on_stake_pct=round(return_on_stake_pct, 2),
            first_trade_date=first_date,
            last_trade_date=last_date,
            calendar_days=days,
        )

        report = TradeReport(summary=summary, cycles=cycles, open_position=open_position)
        return self._format(report)

    def _format(self, report: TradeReport) -> str:
        lines: list[str] = []
        lines.append("=== Trade Report ===")
        lines.append(f"Period: {report.summary.first_trade_date} to {report.summary.last_trade_date} ({report.summary.calendar_days} days)")
        lines.append(f"Complete cycles: {report.summary.total_cycles}  |  Win rate: {report.summary.win_rate:.0f}%")
        lines.append(f"")
        for c in report.cycles:
            lines.append(f"  Cycle {c.cycle}: Buy {c.buy_quantity}@\u20b9{c.buy_avg_price} (\u20b9{c.buy_total:,.0f}) \u2192 Sell @ \u20b9{c.sell_price} = \u20b9{c.pnl:+,.0f} ({c.pnl_pct:+.2f}%)")
        lines.append(f"")
        lines.append(f"Total realized P&L: \u20b9{report.summary.total_pnl:,.0f}")
        lines.append(f"Initial stake: \u20b9{report.summary.initial_stake:,.0f}  |  Peak capital at risk: \u20b9{report.summary.peak_capital:,.0f}")
        lines.append(f"Return on initial stake: {report.summary.return_on_stake_pct:.0f}%")
        lines.append(f"Return on peak capital: {report.summary.return_on_peak_pct:.1f}%")
        if report.open_position:
            o = report.open_position
            lines.append(f"Open position: {o.quantity} @ \u20b9{o.avg_price} (\u20b9{o.invested:,.0f} invested)")
        lines.append(f"=== End ===")
        return "\n".join(lines)

    def generate_structured(self) -> TradeReport:
        if not self._filepath.exists():
            raise FileNotFoundError(f"No trades file found at {self._filepath}")
        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            raise ValueError("Trades file is empty")
        cycles, buy_stack, peak_capital, open_position = [], [], 0.0, None
        first_date, last_date = rows[0]["datetime"][:10], rows[-1]["datetime"][:10]
        for row in rows:
            qty, price = int(row["quantity"]), float(row["avg_price"])
            if row["side"] == "BUY":
                buy_stack.append((qty, price))
            else:
                buy_qty = sum(bq for bq, _ in buy_stack)
                buy_total = sum(bq * bp for bq, bp in buy_stack)
                buy_avg = buy_total / buy_qty
                pnl = qty * price - buy_total
                peak_capital = max(peak_capital, buy_total)
                cycles.append(CycleReport(
                    cycle=len(cycles) + 1, buy_quantity=buy_qty, buy_avg_price=round(buy_avg, 2),
                    buy_total=round(buy_total, 2), sell_price=price,
                    sell_total=round(qty * price, 2), pnl=round(pnl, 2),
                    pnl_pct=round(pnl / buy_total * 100, 2),
                ))
                buy_stack = []
        if buy_stack:
            qty = sum(bq for bq, _ in buy_stack)
            avg = sum(bq * bp for bq, bp in buy_stack) / qty
            open_position = OpenPosition(quantity=qty, avg_price=round(avg, 2), invested=round(sum(bq * bp for bq, bp in buy_stack), 2))
        total_pnl = sum(c.pnl for c in cycles)
        days = (datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date != last_date else 0
        initial_stake = cycles[0].buy_total if cycles else 0.0
        return TradeReport(
            summary=ReportSummary(
                total_cycles=len(cycles), win_rate=100.0 if len(cycles) > 0 and all(c.pnl > 0 for c in cycles) else 0.0,
                total_pnl=round(total_pnl, 2), initial_stake=round(initial_stake, 2),
                peak_capital=round(peak_capital, 2),
                return_on_peak_pct=round(total_pnl / peak_capital * 100, 2) if peak_capital else 0.0,
                return_on_stake_pct=round(total_pnl / initial_stake * 100, 2) if initial_stake else 0.0,
                first_trade_date=first_date, last_trade_date=last_date, calendar_days=days,
            ),
            cycles=cycles, open_position=open_position,
        )
