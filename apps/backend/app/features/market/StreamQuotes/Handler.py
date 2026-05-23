import logging
import time
from threading import Lock
from typing import Any, Dict, List, Optional

from NorenRestApiPy.NorenApi import FeedType

logger = logging.getLogger(__name__)


class StreamQuotesHandler:

    def __init__(self, broker_session: Any, tokens: List[str], symbol_map: Dict[str, str]) -> None:
        self._api = broker_session
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
        self._api.broker.start_websocket(
            subscribe_callback=self._quote_callback,
            order_update_callback=self._order_callback,
            socket_open_callback=self._open_callback,
            socket_close_callback=self._close_callback,
            socket_error_callback=self._error_callback,
        )

    def _open_callback(self) -> None:
        self._socket_opened = True
        self._api.broker.subscribe(self._tokens, feed_type=FeedType.SNAPQUOTE)
        logger.info(f"Websocket subscribed to {len(self._tokens)} tokens")

    def _close_callback(self) -> None:
        self._socket_opened = False
        logger.warning("Websocket closed")

    def _error_callback(self, error: Any) -> None:
        logger.error(f"Websocket error: {error}")

    def _order_callback(self, message: Any) -> None:
        pass

    def _quote_callback(self, message: Any) -> None:
        lp = message.get("lp")
        if lp is not None:
            key = f"{message['e']}|{message['tk']}"
            with self._lock:
                self._ltp[key] = float(lp)

    def get_quotes(self, symbols: List[str]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        with self._lock:
            for sym in symbols:
                ws_key = self._symbol_map.get(sym)
                if ws_key:
                    val = self._ltp.get(ws_key)
                    if val is not None:
                        result[sym] = val
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
            self._api.broker.close_websocket()
            self._started = False
