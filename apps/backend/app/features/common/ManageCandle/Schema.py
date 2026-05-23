from pydantic import BaseModel
from typing import List


class ManageCandleSchema(BaseModel):
    minute: int = 1
    start: str = "09:00"
    stop: str = "15:30"
    close_times: List[str] = []
