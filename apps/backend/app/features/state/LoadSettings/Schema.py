from pydantic import BaseModel
from typing import List, Optional


class GlobalSettings(BaseModel):
    log_level: str
    log_show: bool
    start: str
    stop: str
    candle: int


class StrategySettings(BaseModel):
    strategy: str
    base: str
    symbol: str
    exchange: str
    quantity: int
    start_time: str
    stop_time: str
    multiplier: List[int]
    perc: float
