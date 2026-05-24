from typing import List, Dict, Any, Optional, Callable
from .Schema import HistoricQuotesConfig

class HistoricQuotesHandler:
    def __init__(self, config: HistoricQuotesConfig, fetch_history: Callable[[str, str, str, str, int], Optional[List[Dict[str, Any]]]]) -> None:
        self.config = config
        self.fetch_history = fetch_history
        self.candles: List[Dict[str, Any]] = []
        self.index = 0
        self._started = False
        self._current_time: str = ""

    def initialize(self) -> None:
        tf_minutes = int(self.config.timeframe.replace('Min', ''))
        fm = self.config.start_date.strftime('%Y-%m-%d')
        to = self.config.end_date.strftime('%Y-%m-%d')
        data = self.fetch_history(
            exch=self.config.exchange,
            tkn=self.config.symbol,
            fm=fm,
            to=to,
            tf=tf_minutes
        )
        if data is None or len(data) == 0:
            raise ValueError("No historical data found")
        self.candles = list(reversed(data))
        self.index = 0
        self._started = True

    def start(self) -> None:
        if not self._started:
            self.initialize()

    def next_close(self) -> float:
        if not self.candles:
            self._current_time = ""
            return 0.0
        if self.index >= len(self.candles):
            self._current_time = str(self.candles[-1].get("time", ""))
            return self.candles[-1]['close']
        candle = self.candles[self.index]
        self.index += 1
        self._current_time = str(candle.get("time", ""))
        return candle['close']

    def get_quote(self) -> Dict[str, Any]:
        if not self.candles:
            return {}
        if self.index >= len(self.candles):
            return self.candles[-1]
        return self.candles[self.index]

    def get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        close = self.next_close()
        result: Dict[str, Any] = {sym: close for sym in symbols}
        result["_time"] = self._current_time
        return result

    def wait_for_quotes(self, symbols: List[str], timeout: float = 10.0) -> Dict[str, Any]:
        return self.get_quotes(symbols)

    def close(self) -> None:
        self._started = False
