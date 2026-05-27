from __future__ import annotations

from NorenRestApiPy.NorenApi import FeedType

from .api_helper import ShoonyaApiPy


class Wsocket:
    def __init__(self, api: ShoonyaApiPy):
        self._api = api
        self._ltp: dict[str, float] = {}
        self._connected: bool = False

        self.on_connect = lambda: None
        self.on_ticks = lambda ltp: None
        self.on_order = lambda msg: None
        self.on_close = lambda: None
        self.on_error = lambda err: None

    @property
    def ltp(self) -> dict:
        return self._ltp

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._api.start_websocket(
            subscribe_callback=self._on_ticks,
            order_update_callback=self._on_order,
            socket_open_callback=self._on_open,
            socket_close_callback=self._on_close,
            socket_error_callback=self._on_error,
        )

    def disconnect(self) -> None:
        self._api.close_websocket()
        self._connected = False

    def subscribe(self, tokens: list[str]) -> None:
        token_str = "#".join(tokens)
        self._api.subscribe(token_str, feed_type=FeedType.SNAPQUOTE)

    def unsubscribe(self, tokens: list[str]) -> None:
        token_str = "#".join(tokens)
        self._api.unsubscribe(token_str, feed_type=FeedType.SNAPQUOTE)

    def _on_open(self) -> None:
        self._connected = True
        self.on_connect()

    def _on_close(self) -> None:
        self._connected = False
        self.on_close()

    def _on_error(self, error) -> None:
        self.on_error(str(error))

    def _on_ticks(self, data: dict | list) -> None:
        print(f"WSOCKET RAW: {type(data).__name__} {data}")
        if isinstance(data, dict):
            if data.get("lp") is not None and data["lp"] != "":
                ws_token = f'{data.get("e")}|{data.get("tk")}'
                self._ltp[ws_token] = float(data["lp"])
                self.on_ticks(self._ltp)
        elif isinstance(data, list):
            for tick in data:
                if tick.get("lp") is not None and tick["lp"] != "":
                    ws_token = f'{tick.get("e")}|{tick.get("tk")}'
                    self._ltp[ws_token] = float(tick["lp"])
            if data:
                self.on_ticks(self._ltp)

    def _on_order(self, message: dict) -> None:
        self.on_order(message)
