from pydantic import BaseModel
from typing import List, Optional


class GlobalSettings(BaseModel):
    log_level: str
    log_show: bool
    start: str
    stop: str


class StrategySettings(BaseModel):
    strategy: str
    base: str
    symbol: str
    exchange: str
    quantity: int
    start_time: str
    stop_time: str
    fibo_seq: Optional[List[int]] = None
    downtrend_thresh: Optional[float] = None
    uptrend_thresh: Optional[float] = None
    ratchet_factor: Optional[float] = None
    sell_profit_thresh: Optional[float] = None
