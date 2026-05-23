from pydantic import BaseModel
from typing import List


class FetchQuotesSchema(BaseModel):
    symbols: List[str]
