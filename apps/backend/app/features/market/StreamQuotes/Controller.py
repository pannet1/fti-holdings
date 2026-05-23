import logging

from .Schema import StreamQuotesInput, StreamQuotesOutput
from .Handler import StreamQuotesHandler

logger = logging.getLogger(__name__)


class StreamQuotesController:

    def __init__(self) -> None:
        self._handler: StreamQuotesHandler | None = None

    def start(self, request: dict) -> dict:
        schema = StreamQuotesInput(**request)
        self._handler = StreamQuotesHandler(
            broker_session=request["broker_session"],
            tokens=schema.tokens,
            symbol_map=schema.symbol_map,
        )
        self._handler.start()
        return {"status": "started"}

    def get_quotes(self, symbols: list[str]) -> dict:
        if not self._handler:
            return {"status": "error", "quotes": {}, "message": "Stream not started"}
        quotes = self._handler.get_quotes(symbols)
        return StreamQuotesOutput(status="ok", quotes=quotes).model_dump()

    def close(self) -> dict:
        if self._handler:
            self._handler.close()
            self._handler = None
        return {"status": "closed"}
