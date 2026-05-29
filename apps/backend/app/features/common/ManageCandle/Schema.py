from typing import List

from pydantic import BaseModel


class ManageCandleSchema(BaseModel):
    minute: int = 1
    start_time: str
    stop_time: str
    close_times: List[str] = []
