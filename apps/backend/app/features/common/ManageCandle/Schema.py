from typing import List

from pydantic import BaseModel


class ManageCandleSchema(BaseModel):
    minute: int = 1
    start: str = "09:00"
    stop: str = "15:30"
    close_times: List[str] = []
