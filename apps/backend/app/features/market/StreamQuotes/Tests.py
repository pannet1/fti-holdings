import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from .Handler import StreamQuotesHandler


@pytest.fixture
def mock_broker() -> Any:
    broker = MagicMock()
    broker.broker = MagicMock()
    return broker


class TestStreamQuotesHandler:

    @patch("app.features.market.StreamQuotes.Handler.Wsocket")
    def test_start_wires_callbacks_and_connects(
        self, mock_ws: Any, mock_broker: Any
    ) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler.start()
        ws_instance = mock_ws.return_value
        assert ws_instance.on_connect == handler._on_open
        assert ws_instance.on_ticks == handler._on_ticks
        assert ws_instance.on_close == handler._on_close
        assert ws_instance.on_error == handler._on_error
        ws_instance.connect.assert_called_once()

    @patch("app.features.market.StreamQuotes.Handler.Wsocket")
    def test_on_open_subscribes_tokens(self, mock_ws: Any, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler.start()
        handler._on_open()
        handler._ws.subscribe.assert_called_once_with(
            ["NSE|26000", "BSE|12345"]
        )
        assert handler._socket_opened is True

    @patch("app.features.market.StreamQuotes.Handler.Wsocket")
    def test_on_ticks_stores_ltp(self, mock_ws: Any, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler.start()
        ltp = {"NSE|26000": 2450.50, "BSE|12345": 120.75}
        handler._on_ticks(ltp)
        assert handler._ltp["NSE|26000"] == 2450.50
        assert handler._ltp["BSE|12345"] == 120.75

    def test_get_quotes_returns_mapped_values(self, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler._ltp["NSE|26000"] = 2450.50
        handler._ltp["BSE|12345"] = 120.75
        quotes = handler.get_quotes(["ACC", "ITBEES"])
        assert quotes["ACC"] == 2450.50
        assert quotes["ITBEES"] == 120.75

    def test_get_quotes_skips_missing_symbols(self, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler._ltp["NSE|26000"] = 2450.50
        quotes = handler.get_quotes(["ACC", "UNKNOWN"])
        assert quotes["ACC"] == 2450.50
        assert "UNKNOWN" not in quotes

    def test_get_quotes_empty_when_no_quotes(self, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        quotes = handler.get_quotes(["ACC"])
        assert "ACC" not in quotes
        assert "_time" in quotes

    @patch("app.features.market.StreamQuotes.Handler.Wsocket")
    def test_close_disconnects_wsocket(self, mock_ws: Any, mock_broker: Any) -> None:
        handler = StreamQuotesHandler(
            broker_session=mock_broker,
            tokens=["NSE|26000", "BSE|12345"],
            symbol_map={"ACC": "NSE|26000", "ITBEES": "BSE|12345"},
        )
        handler.start()
        handler.close()
        handler._ws.disconnect.assert_called_once()
        assert handler._started is False
