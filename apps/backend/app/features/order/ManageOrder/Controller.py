import logging

from .Schema import ManageOrderSchema
from .Handler import ManageOrderHandler

logger = logging.getLogger(__name__)


class ManageOrderController:

    def handle(self, request: dict) -> dict:
        schema = ManageOrderSchema(**request)
        handler = ManageOrderHandler()
        extra = {k: v for k, v in request.items() if k not in schema.model_dump()}
        return handler.execute(
            tradingsymbol=schema.tradingsymbol,
            exchange=schema.exchange,
            transaction_type=schema.transaction_type,
            quantity=schema.quantity,
            price=schema.price,
            **extra,
        )
