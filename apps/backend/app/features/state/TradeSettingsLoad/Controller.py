import logging
from .Handler import TradeSettingsLoadHandler

logger = logging.getLogger(__name__)


class TradeSettingsLoadController:

    def handle(self, request: dict = None) -> dict:
        handler = TradeSettingsLoadHandler()
        result = handler.execute()
        logger.info("Settings loaded successfully")
        return {
            "status": "ok",
            "data": result,
        }
