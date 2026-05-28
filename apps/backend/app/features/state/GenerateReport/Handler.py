import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

from .Schema import CycleReport, OpenPosition, ReportSummary, TradeReport
from shared.logger import logging_func
logger = logging_func(__name__)

CSV_FIELDS = ["datetime", "exchange", "tradingsymbol", "side", "avg_price", "quantity", "strategy", "multiplier"]
RISK_FREE_RATE = 0.07


class GenerateReportHandler:

    def __init__(self, data_dir: str = "data", paper: bool = False) -> None:
        base = Path(data_dir)
        self._base = base
        self._paper = paper
        if paper:
            self._filepath = base / "paper" / "trades.csv"
        else:
            self._filepath = base / "trades.csv"

    def _ltp_path(self) -> Path:
        if self._paper:
            return self._base / "paper" / "ltp.json"
        return self._base / "ltp.json"

    def _read_ltp(self) -> Optional[float]:
        path = self._ltp_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            prices = data.get("prices", {})
            if not prices:
                return None
            vals = [v for v in prices.values() if v is not None]
            return float(vals[0]) if vals else None
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None

    def _compute_advanced_metrics(self, cycles: list[CycleReport], days: int) -> dict:
        result: dict = {}

        if not cycles:
            return result

        total_pnl = sum(c.pnl for c in cycles)
        winning = [c for c in cycles if c.pnl > 0]
        losing = [c for c in cycles if c.pnl <= 0]
        result["winning_cycles"] = len(winning)
        result["losing_cycles"] = len(losing)

        result["total_gross_profit"] = round(sum(c.pnl for c in winning), 2)
        result["total_gross_loss"] = round(abs(sum(c.pnl for c in losing)), 2)

        gp = result["total_gross_profit"]
        gl = result["total_gross_loss"]
        result["profit_factor"] = round(gp / gl, 2) if gl else None

        result["avg_win_pct"] = round(sum(c.pnl_pct for c in winning) / len(winning), 2) if winning else None
        result["avg_loss_pct"] = round(sum(c.pnl_pct for c in losing) / len(losing), 2) if losing else None

        result["expectancy"] = round(total_pnl / len(cycles), 2)

        returns = [c.pnl / c.buy_total for c in cycles]
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        n = 365.0 / days * len(cycles) if days > 0 else 0
        sample_ok = len(cycles) >= 30 and days >= 60
        if std_dev > 0 and n > 0 and sample_ok:
            annual_return = (1 + avg_return) ** n - 1
            annual_vol = std_dev * math.sqrt(n)
            result["sharpe_ratio"] = round((annual_return - RISK_FREE_RATE) / annual_vol, 2)
        else:
            result["sharpe_ratio"] = None

        downside = [r for r in returns if r < 0]
        if downside and len(downside) > 0 and sample_ok:
            down_var = sum(d ** 2 for d in downside) / len(returns)
            down_std = math.sqrt(down_var)
            if down_std > 0 and n > 0:
                annual_return = (1 + avg_return) ** n - 1
                annual_down_vol = down_std * math.sqrt(n)
                result["sortino_ratio"] = round((annual_return - RISK_FREE_RATE) / annual_down_vol, 2)
            else:
                result["sortino_ratio"] = None
        else:
            result["sortino_ratio"] = None

        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        max_dd_value = 0.0
        for c in cycles:
            equity += c.pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            if dd_pct > max_dd:
                max_dd = dd_pct
                max_dd_value = round(dd, 2)

        result["max_drawdown_pct"] = round(max_dd, 2)
        result["max_drawdown_value"] = max_dd_value

        result["calmar_ratio"] = round((total_pnl / (cycles[0].buy_total if cycles else 1) * 100) / max_dd, 2) if max_dd > 0 else None

        return result

    def _parse_rows(self, rows: list[dict]) -> tuple[list[CycleReport], OpenPosition | None, str, str, float]:
        cycles: list[CycleReport] = []
        buy_stack: list[tuple[int, float]] = []
        peak_capital: float = 0.0
        open_position: OpenPosition | None = None
        first_date = rows[0]["datetime"][:10]
        last_date = rows[-1]["datetime"][:10]

        for row in rows:
            qty = int(row["quantity"])
            price = float(row["avg_price"])
            if row["side"] == "BUY":
                buy_stack.append((qty, price))
            else:
                buy_qty = sum(bq for bq, _ in buy_stack)
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

        return cycles, open_position, first_date, last_date, peak_capital

    def generate_report(self) -> str:
        if not self._filepath.exists():
            return f"No trades file found at {self._filepath}"
        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return "Trades file is empty"
        cycles, open_position, first_date, last_date, peak_capital = self._parse_rows(rows)
        return self._build_report(cycles, open_position, first_date, last_date, peak_capital)

    def generate_structured(self) -> TradeReport:
        if not self._filepath.exists():
            raise FileNotFoundError(f"No trades file found at {self._filepath}")
        with open(self._filepath, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            raise ValueError("Trades file is empty")
        cycles, open_position, first_date, last_date, peak_capital = self._parse_rows(rows)
        return self._build_structured(cycles, open_position, first_date, last_date, peak_capital)

    def _build_report(self, cycles: list[CycleReport], open_position: OpenPosition | None,
                      first_date: str, last_date: str, peak_capital: float) -> str:
        total_pnl = sum(c.pnl for c in cycles)
        total_cycles = len(cycles)
        win_rate = 100.0 if total_cycles > 0 and all(c.pnl > 0 for c in cycles) else (sum(1 for c in cycles if c.pnl > 0) / total_cycles * 100) if total_cycles > 0 else 0.0
        initial_stake = cycles[0].buy_total if cycles else 0.0
        return_on_stake_pct = (total_pnl / initial_stake * 100) if initial_stake else 0.0
        return_on_peak_pct = (total_pnl / peak_capital * 100) if peak_capital else 0.0
        days = (datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date != last_date else 0

        lines: list[str] = []
        lines.append("=" * 64)
        lines.append("  PROFESSIONAL BACKTEST REPORT")
        lines.append("=" * 64)

        lines.append("")
        lines.append("--- PERIOD ---")
        lines.append(f"  Start:           {first_date}")
        lines.append(f"  End:             {last_date}")
        lines.append(f"  Calendar days:   {days}")

        lines.append("")
        lines.append("--- SUMMARY ---")
        lines.append(f"  Complete cycles: {total_cycles}")
        lines.append(f"  Winning cycles:  {sum(1 for c in cycles if c.pnl > 0)}")
        lines.append(f"  Losing cycles:   {sum(1 for c in cycles if c.pnl <= 0)}")
        lines.append(f"  Win rate:        {win_rate:.1f}%")

        lines.append("")
        lines.append("--- CAPITAL ---")
        lines.append(f"  Initial stake:   \u20b9{initial_stake:,.0f}")
        lines.append(f"  Peak capital:    \u20b9{peak_capital:,.0f}")
        lines.append(f"  Return on stake: {return_on_stake_pct:.1f}%")
        lines.append(f"  Return on peak:  {return_on_peak_pct:.1f}%")

        metrics = self._compute_advanced_metrics(cycles, days)

        lines.append("")
        lines.append("--- RISK METRICS ---")
        sharpe = metrics.get("sharpe_ratio")
        if sharpe is not None:
            lines.append(f"  Sharpe ratio:    {sharpe:.2f}")
            if sharpe < 0.5:
                lines.append(f"    Explanation: Below 0.5 — suboptimal risk-adjusted return.")
            elif sharpe < 1.0:
                lines.append(f"    Explanation: 0.5-1.0 — acceptable but room for improvement.")
            elif sharpe < 2.0:
                lines.append(f"    Explanation: 1.0-2.0 — good risk-adjusted return.")
            else:
                lines.append(f"    Explanation: >2.0 — excellent risk-adjusted return.")

        sortino = metrics.get("sortino_ratio")
        if sortino is not None:
            lines.append(f"  Sortino ratio:   {sortino:.2f}")
            lines.append(f"    Explanation: Like Sharpe but penalises only downside volatility. Higher is better.")

        dd_pct = metrics.get("max_drawdown_pct")
        dd_val = metrics.get("max_drawdown_value")
        if dd_pct is not None:
            lines.append(f"  Max drawdown:    {dd_pct:.2f}%  (\u20b9{dd_val:,.0f})")
            lines.append(f"    Explanation: Largest peak-to-trough decline in equity. Lower is better.")

        calmar = metrics.get("calmar_ratio")
        if calmar is not None:
            lines.append(f"  Calmar ratio:    {calmar:.2f}")
            lines.append(f"    Explanation: Return on stake divided by max drawdown. Higher is better.")

        lines.append("")
        lines.append("--- TRADE STATISTICS ---")
        pf = metrics.get("profit_factor")
        if pf is not None:
            lines.append(f"  Profit factor:   {pf:.2f}")
            lines.append(f"    Explanation: Gross profit \u00f7 gross loss. >1.5 is healthy, >2.0 is excellent.")

        aw = metrics.get("avg_win_pct")
        al = metrics.get("avg_loss_pct")
        if aw is not None:
            lines.append(f"  Avg win:         {aw:+.2f}%")
        if al is not None:
            lines.append(f"  Avg loss:        {al:+.2f}%")

        exp_val = metrics.get("expectancy")
        if exp_val is not None:
            lines.append(f"  Expectancy:      \u20b9{exp_val:+,.2f}")
            lines.append(f"    Explanation: Average P&L per completed cycle. Positive means the strategy makes money on average.")

        lines.append("")
        lines.append("--- PER-CYCLE BREAKDOWN ---")
        for c in cycles:
            lines.append(f"  #{c.cycle:2d}: Buy {c.buy_quantity:4d}@\u20b9{c.buy_avg_price:>7.2f} (\u20b9{c.buy_total:>8,.0f}) \u2192 Sell @ \u20b9{c.sell_price:>7.2f} = \u20b9{c.pnl:>+8,.0f} ({c.pnl_pct:+.2f}%)")

        lines.append("")
        lines.append("--- P&L ---")
        lines.append(f"  Realized P&L:    \u20b9{total_pnl:+,.0f}")
        if open_position:
            o = open_position
            ltp = self._read_ltp()
            lines.append(f"  Open position:   {o.quantity} @ \u20b9{o.avg_price} (\u20b9{o.invested:,.0f})")
            if ltp:
                mv = o.quantity * ltp
                upnl = round(mv - o.invested, 2)
                upnl_pct = round(upnl / o.invested * 100, 2)
                lines.append(f"  LTP:             \u20b9{ltp}")
                lines.append(f"  Market value:    \u20b9{mv:,.0f}")
                lines.append(f"  Unrealized P&L:  \u20b9{upnl:+,.0f} ({upnl_pct:+.2f}%)")
                lines.append(f"  Total P&L:       \u20b9{total_pnl + upnl:+,.0f}")

        lines.append("")
        lines.append("=" * 64)
        lines.append("  End of Report")
        lines.append("=" * 64)

        return "\n".join(lines)

    def _build_structured(self, cycles: list[CycleReport], open_position: OpenPosition | None,
                          first_date: str, last_date: str, peak_capital: float) -> TradeReport:
        total_pnl = sum(c.pnl for c in cycles)
        total_cycles = len(cycles)
        win_rate = 100.0 if total_cycles > 0 and all(c.pnl > 0 for c in cycles) else (sum(1 for c in cycles if c.pnl > 0) / total_cycles * 100) if total_cycles > 0 else 0.0
        initial_stake = cycles[0].buy_total if cycles else 0.0
        return_on_stake_pct = (total_pnl / initial_stake * 100) if initial_stake else 0.0
        return_on_peak_pct = (total_pnl / peak_capital * 100) if peak_capital else 0.0
        days = (datetime.strptime(last_date, "%Y-%m-%d") - datetime.strptime(first_date, "%Y-%m-%d")).days if first_date != last_date else 0
        metrics = self._compute_advanced_metrics(cycles, days)

        return TradeReport(
            summary=ReportSummary(
                total_cycles=total_cycles,
                win_rate=round(win_rate, 1),
                total_pnl=round(total_pnl, 2),
                initial_stake=round(initial_stake, 2),
                peak_capital=round(peak_capital, 2),
                return_on_peak_pct=round(return_on_peak_pct, 2),
                return_on_stake_pct=round(return_on_stake_pct, 2),
                first_trade_date=first_date,
                last_trade_date=last_date,
                calendar_days=days,
                **metrics,
            ),
            cycles=cycles,
            open_position=open_position,
        )
