import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Rachet:
    def __init__(self, **O_SETG: Any) -> None:
        self.strategy = O_SETG["strategy"]
        self.stop_time = O_SETG["stop_time"]
        self._removable = False
        self._tradingsymbol = O_SETG.get("tradingsymbol", "")
        self._exchange = O_SETG.get("exchange", "NSE")
        self._token = O_SETG.get("instrument_token")
        self._rest = O_SETG.get("rest")
        self._x = O_SETG.get("quantity", 33)

    def run(self, trades: Any, quotes: dict, positions: Any) -> Optional[dict]:
        cmp = quotes.get(self._tradingsymbol, 0)
        logger.info(f"{self._tradingsymbol} LTP: {cmp}")

        if cmp <= 0:
            return None

        return None
