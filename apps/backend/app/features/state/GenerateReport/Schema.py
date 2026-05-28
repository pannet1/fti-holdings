from pydantic import BaseModel
from typing import Optional


class CycleReport(BaseModel):
    cycle: int
    buy_quantity: int
    buy_avg_price: float
    buy_total: float
    sell_price: float
    sell_total: float
    pnl: float
    pnl_pct: float


class OpenPosition(BaseModel):
    quantity: int
    avg_price: float
    invested: float


class ReportSummary(BaseModel):
    total_cycles: int
    win_rate: float
    total_pnl: float
    initial_stake: float
    peak_capital: float
    return_on_peak_pct: float
    return_on_stake_pct: float
    first_trade_date: str
    last_trade_date: str
    calendar_days: int
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_drawdown_value: Optional[float] = None
    calmar_ratio: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_win_pct: Optional[float] = None
    avg_loss_pct: Optional[float] = None
    expectancy: Optional[float] = None
    total_gross_profit: Optional[float] = None
    total_gross_loss: Optional[float] = None
    winning_cycles: Optional[int] = None
    losing_cycles: Optional[int] = None


class TradeReport(BaseModel):
    summary: ReportSummary
    cycles: list[CycleReport]
    open_position: OpenPosition | None = None
