import pytest
from unittest.mock import Mock

from .Handler import QuotesFetchHandler


class TestQuotesFetchHandler:

    def test_empty_symbols(self):
        handler = QuotesFetchHandler()
        result = handler.execute(symbols=[])
        assert result["status"] == "empty"

    def test_raises_without_session(self):
        handler = QuotesFetchHandler()
        with pytest.raises(ValueError, match="Authenticated broker session required"):
            handler.execute(symbols=["NSE|26000"])

    def test_returns_quotes_with_session(self):
        mock_session = Mock()
        mock_session.get_quotes.return_value = {"lp": "2450.50"}
        handler = QuotesFetchHandler()
        result = handler.execute(symbols=["NSE|26000"], broker_session=mock_session)
        assert result["status"] == "ok"
        assert result["quotes"]["NSE|26000"]["lp"] == "2450.50"

    def test_handles_symbol_failure_gracefully(self):
        mock_session = Mock()
        mock_session.get_quotes.side_effect = Exception("API error")
        handler = QuotesFetchHandler()
        result = handler.execute(symbols=["NSE|26000"], broker_session=mock_session)
        assert result["quotes"]["NSE|26000"] is None
