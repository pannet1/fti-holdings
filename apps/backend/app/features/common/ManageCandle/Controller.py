import logging
from typing import Dict, Optional

from .Handler import ManageCandleHandler

logger = logging.getLogger(__name__)


class ManageCandleController:

    def handle(self, request: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        params = request or {}
        minute = int(params.get("minute", 1))
        start = str(params.get("start", "09:00"))
        stop = str(params.get("stop", "15:30"))
        handler = ManageCandleHandler(minute=minute, start=start, stop=stop)
        idx = handler.current_index
        logger.info("Candle index computed: %s", idx)
        return {
            "status": "ok",
            "data": {
                "current_index": idx,
            },
        }
