from pydantic import BaseModel


class ManageOrderSchema(BaseModel):
    tradingsymbol: str
    exchange: str
    transaction_type: str
    quantity: int
    price: float
