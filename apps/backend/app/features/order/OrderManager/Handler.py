import logging
from typing import Any

logger = logging.getLogger(__name__)


class OrderManagerHandler:

    def execute(self, tradingsymbol: str, exchange: str, transaction_type: str, quantity: int, price: float, broker_session: Any = None) -> dict:
        if broker_session is None:
            raise ValueError("Authenticated broker session required. Run AuthenticateBroker first.")

        if not all([tradingsymbol, exchange, transaction_type]):
            raise ValueError("Missing required order fields: tradingsymbol, exchange, transaction_type")

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if price <= 0:
            raise ValueError("Price must be positive")

        try:
            order_id = broker_session.order_place(
                tradingsymbol=tradingsymbol,
                exchange=exchange,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type="LIMIT",
                product="C",
                variety="regular",
                price=price,
            )
            if order_id is None:
                return {"status": "error", "message": "Broker returned no order ID"}
            return {"status": "ok", "order_id": order_id}
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return {"status": "error", "message": str(e)}
