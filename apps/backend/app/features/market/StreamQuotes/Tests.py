import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from .Handler import StreamQuotesHandler


@pytest.fixture
def mock_broker() -> Any:
    broker = MagicMock()
    broker.broker = MagicMock()
    return broker


@pytest.fixture
def handler(mock_broker: Any) -> StreamQuotesHandler:
    h = StreamQuotesHandler(
        broker_session=mock_broker,
        tokens=["NSE|26000", "BSE|12345"],
        symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
    )
    return h


class TestStreamQuotesHandler:

    def test_start_calls_websocket(self, handler: StreamQuotesHandler, mock_broker: Any) -> None:
        handler.start()
        mock_broker.broker.start_websocket.assert_called_once()

    def test_quote_callback_stores_ltp(self, handler: StreamQuotesHandler) -> None:
        handler.start()
        msg = {"e": "NSE", "tk": "26000", "lp": "2450.50"}
        handler._quote_callback(msg)
        assert handler._ltp["NSE|26000"] == 2450.50

    def test_get_quotes_returns_mapped_values(self, handler: StreamQuotesHandler) -> None:
        handler._ltp["NSE|26000"] = 2450.50
        handler._ltp["BSE|12345"] = 120.75
        quotes = handler.get_quotes(["ACC", "ITBEES"])
        assert quotes["ACC"] == 2450.50
        assert quotes["ITBEES"] == 120.75

    def test_get_quotes_skips_missing_symbols(self, handler: StreamQuotesHandler) -> None:
        handler._ltp["NSE|26000"] = 2450.50
        quotes = handler.get_quotes(["ACC", "UNKNOWN"])
        assert quotes["ACC"] == 2450.50
        assert "UNKNOWN" not in quotes

    def test_get_quotes_empty_when_no_quotes(self, handler: StreamQuotesHandler) -> None:
        quotes = handler.get_quotes(["ACC"])
        assert quotes == {}

    def test_close_calls_websocket_close(self, handler: StreamQuotesHandler, mock_broker: Any) -> None:
        handler.start()
        handler.close()
        mock_broker.broker.close_websocket.assert_called_once()
