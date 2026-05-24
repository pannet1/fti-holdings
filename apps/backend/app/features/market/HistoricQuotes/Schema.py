from pydantic import BaseModel, Field
from datetime import date
import pendulum

class HistoricQuotesConfig(BaseModel):
    symbol: str
    exchange: str
    timeframe: str = Field(default="1Min")
    start_date: date = Field(default_factory=lambda: pendulum.now().subtract(days=30).date())
    end_date: date = Field(default_factory=lambda: pendulum.now().date())
