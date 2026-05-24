from typing import Dict, Any, Callable, Optional, List
from .Schema import HistoricQuotesConfig
from .Handler import HistoricQuotesHandler

class HistoricQuotesController:
    def __init__(self, raw_config: Dict[str, Any], fetch_history: Callable[[str, str, str, str, int], Optional[List[Dict[str, Any]]]]):
        self.config = HistoricQuotesConfig(**raw_config)
        self.handler = HistoricQuotesHandler(self.config, fetch_history)
        self.handler.initialize()

    def next_close(self) -> float:
        return self.handler.next_close()

    def get_quote(self) -> Dict[str, Any]:
        return self.handler.get_quote()
