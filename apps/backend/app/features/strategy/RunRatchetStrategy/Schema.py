from pydantic import BaseModel
from typing import List


class StrategyConfig(BaseModel):
    strategy: str
    base: str
    symbol: str
    exchange: str
    quantity: int
    start_time: str
    stop_time: str
    multiplier: List[int]
    perc: float


class RunRatchetStrategySchema(BaseModel):
    start: str
    stop: str
    strategies: List[StrategyConfig]
