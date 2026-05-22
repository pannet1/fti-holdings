from pydantic import BaseModel
from typing import List


class QuotesFetchSchema(BaseModel):
    symbols: List[str]
