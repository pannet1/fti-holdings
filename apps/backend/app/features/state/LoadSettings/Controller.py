import logging
from .Handler import LoadSettingsHandler

logger = logging.getLogger(__name__)


class LoadSettingsController:

    def handle(self, request: dict = None) -> dict:
        handler = LoadSettingsHandler()
        result = handler.execute()
        logger.info("Settings loaded successfully")
        return {
            "status": "ok",
            "data": result,
        }
