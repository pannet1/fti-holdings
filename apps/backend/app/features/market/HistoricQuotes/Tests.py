import pytest
from unittest.mock import Mock
import pendulum
from .Schema import HistoricQuotesConfig
from .Handler import HistoricQuotesHandler

def test_initialize_success():
    config = HistoricQuotesConfig(
        symbol="TEST",
        exchange="NSE",
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
        timeframe="1Min",
        start_date=pendulum.yesterday().date(),
        end_date=pendulum.today().date()
    )
    candles = [
        {"time": "2024-01-01 09:15:00", "open": 100, "high": 101, "low": 99, "close": 100},
        {"time": "2024-01-01 09:16:00", "open": 100, "high": 102, "low": 99, "close": 101},
        {"time": "2024-01-01 09:17:00", "open": 101, "high": 103, "low": 100, "close": 102}
    ]
    mock_fetch_history = Mock(return_value=candles)
    handler = HistoricQuotesHandler(config, mock_fetch_history)
    handler.initialize()
    assert handler.get_quote() == candles[0]
    assert handler.index == 0
    assert handler.next_close() == 100
    assert handler.index == 1
    assert handler.get_quote() == candles[1]
    assert handler.index == 1
    assert handler.next_close() == 101
    assert handler.index == 2
    assert handler.next_close() == 102
    assert handler.index == 3
    assert handler.next_close() == 102
    assert handler.index == 3
    assert handler.get_quote() == candles[2]
