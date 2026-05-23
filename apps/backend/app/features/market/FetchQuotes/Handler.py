import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class FetchQuotesHandler:

    def execute(self, symbols: List[str], broker_session: Any = None) -> dict:
        if not symbols:
            return {"status": "empty", "quotes": {}}

        if broker_session is None:
            raise ValueError("Authenticated broker session required. Run AuthenticateBroker first.")

        quotes = {}
        for symbol in symbols:
            try:
                parts = symbol.split("|")
                exch, tkn = parts[0], parts[1]
                result = broker_session.get_quotes(exch, tkn)
                quotes[symbol] = result
            except Exception as e:
                logger.error(f"Failed to fetch quote for {symbol}: {e}")
                quotes[symbol] = None

        return {"status": "ok", "quotes": quotes}
