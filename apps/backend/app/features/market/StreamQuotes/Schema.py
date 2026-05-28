from pydantic import BaseModel
from typing import Dict, List


class StreamQuotesInput(BaseModel):
    tokens: List[str]
    symbol_map: Dict[str, str]


class StreamQuotesOutput(BaseModel):
    status: str
    quotes: Dict[str, float]
