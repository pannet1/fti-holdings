from typing import Dict, Optional

import pendulum as pdlm

from .Handler import ManageCandleHandler
from .Schema import ManageCandleSchema
from shared.logger import logging_func

logger = logging_func(__name__)


class ManageCandleController:

    def handle(self, request: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        params = request or {}
        schema = ManageCandleSchema.model_validate(params)
        start_time = pdlm.parse(schema.start_time).in_tz("Asia/Kolkata")
        stop_time = pdlm.parse(schema.stop_time).in_tz("Asia/Kolkata")
        handler = ManageCandleHandler(
            start_time=start_time, stop_time=stop_time, minute=schema.minute
        )
        event = handler.check_close()
        logger.info("Candle close event: %s", event)
        return {
            "status": "ok",
            "data": event or {"index": handler.current_index},
        }
