import pytest
from unittest.mock import Mock
import pendulum
from .Schema import HistoricQuotesConfig
from .Handler import HistoricQuotesHandler

def test_initialize_success():
    config = HistoricQuotesConfig(
        symbol="TEST",
        exchange="NSE",
        tradingsymbol="TEST",
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    mock_fetch_history = Mock()
    mock_fetch_history.return_value = [
        {"time": "2024-01-01 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
        {"time": "2024-01-01 09:16:00", "open": 100, "high": 102, "low": 99, "close": 101}
    ]
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    handler.initialize()
    assert len(handler.candles) == 2
    assert handler.index == 0
    mock_fetch_history.assert_called_once()

def test_initialize_empty_data_raises():
    config = HistoricQuotesConfig(
        symbol="TEST",
        exchange="NSE",
        tradingsymbol="TEST",
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    mock_fetch_history = Mock(return_value=None)
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    with pytest.raises(ValueError):
        handler.initialize()

def test_initialize_empty_list_raises():
    config = HistoricQuotesConfig(
        symbol="TEST",
        exchange="NSE",
        tradingsymbol="TEST",
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    mock_fetch_history = Mock(return_value=[])
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    with pytest.raises(ValueError):
        handler.initialize()

def test_next_close_and_get_quote():
    config = HistoricQuotesConfig(
        symbol="TEST",
        exchange="NSE",
        tradingsymbol="TEST",
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    shoonya_order = [
        {"time": "2024-01-01 09:17:00", "open": 101, "high": 103, "low": 100, "close": 102},
        {"time": "2024-01-01 09:16:00", "open": 100, "high": 102, "low": 99, "close": 101},
        {"time": "2024-01-01 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100}
    ]
    chronological = list(reversed(shoonya_order))
    mock_fetch_history = Mock(return_value=shoonya_order)
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    handler.initialize()
    assert handler.get_quote() == chronological[0]
    assert handler.index == 0
    assert handler.next_close() == 100
    assert handler.index == 1
    assert handler.get_quote() == chronological[1]
    assert handler.index == 1
    assert handler.next_close() == 101
    assert handler.index == 2
    assert handler.next_close() == 102
    assert handler.index == 3
    assert handler.next_close() == 102
    assert handler.index == 3
    assert handler.get_quote() == chronological[2]


def test_get_quotes_returns_tradingsymbol_close():
    config = HistoricQuotesConfig(
        symbol="TOKEN123",
        exchange="NSE",
        tradingsymbol="ITBEES",
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    mock_fetch_history = Mock(return_value=[
        {"time": "2024-01-01 09:15:00", "open": 100, "high": 101, "low": 99, "close": 42},
    ])
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    handler.initialize()
    result = handler.get_quotes(["ITBEES"])
    assert result["ITBEES"] == 42
    assert result["_time"] == "2024-01-01 09:15:00"


def test_close_resets_started_flag():
    config = HistoricQuotesConfig(
        symbol="TOKEN123",
        exchange="NSE",
        tradingsymbol="ITBEES",
        timeframe="1Min",
    )
    mock_fetch_history = Mock(return_value=[
        {"time": "2024-01-01 09:15:00", "open": 100, "high": 101, "low": 99, "close": 42},
    ])
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    handler.initialize()
    assert handler._started
    handler.close()
    assert not handler._started
