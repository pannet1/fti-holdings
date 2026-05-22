import logging

from .Schema import OrderManagerSchema
from .Handler import OrderManagerHandler

logger = logging.getLogger(__name__)


class OrderManagerController:

    def handle(self, request: dict) -> dict:
        schema = OrderManagerSchema(**request)
        handler = OrderManagerHandler()
        extra = {k: v for k, v in request.items() if k not in schema.model_dump()}
        return handler.execute(
            tradingsymbol=schema.tradingsymbol,
            exchange=schema.exchange,
            transaction_type=schema.transaction_type,
            quantity=schema.quantity,
            price=schema.price,
            **extra,
        )
