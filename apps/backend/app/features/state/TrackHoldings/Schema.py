from pydantic import BaseModel


class HoldingsRow(BaseModel):
    datetime: str
    exchange: str
    tradingsymbol: str
    side: str
    avg_price: float
    quantity: int
    strategy: str
