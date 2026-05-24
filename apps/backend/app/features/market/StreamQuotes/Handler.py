import logging
import time
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

from broker_ai.finvasia.wsocket import Wsocket

logger = logging.getLogger(__name__)


class StreamQuotesHandler:

    def __init__(self, broker_session: Any, tokens: List[str], symbol_map: Dict[str, str]) -> None:
        self._ws = Wsocket(broker_session.broker)
        self._tokens = tokens
        self._symbol_map = symbol_map
        self._ltp: Dict[str, float] = {}
        self._lock = Lock()
        self._socket_opened = False
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True

        self._ws.on_connect = self._on_open
        self._ws.on_ticks = self._on_ticks
        self._ws.on_close = self._on_close
        self._ws.on_error = self._on_error

        self._ws.connect()

    def _on_open(self) -> None:
        self._socket_opened = True
        self._ws.subscribe(self._tokens)
        logger.info(f"Websocket subscribed to {len(self._tokens)} tokens")

    def _on_close(self) -> None:
        self._socket_opened = False
        logger.warning("Websocket closed")

    def _on_error(self, error: str) -> None:
        logger.error(f"Websocket error: {error}")

    def _on_ticks(self, ltp: Dict[str, float]) -> None:
        with self._lock:
            self._ltp.update(ltp)

    def get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        result: Dict[str, float] = {}
        with self._lock:
            for sym in symbols:
                ws_key = self._symbol_map.get(sym)
                if ws_key:
                    val = self._ltp.get(ws_key)
                    if val is not None:
                        result[sym] = val
        result["_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return result

    def wait_for_quotes(self, symbols: List[str], timeout: float = 10.0) -> Dict[str, float]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            quotes = self.get_quotes(symbols)
            if len(quotes) == len(symbols):
                return quotes
            time.sleep(0.1)
        return self.get_quotes(symbols)

    def close(self) -> None:
        if self._started:
            self._ws.disconnect()
            self._started = False
