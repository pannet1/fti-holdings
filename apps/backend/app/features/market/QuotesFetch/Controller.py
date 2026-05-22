import logging

from .Schema import QuotesFetchSchema
from .Handler import QuotesFetchHandler

logger = logging.getLogger(__name__)


class QuotesFetchController:

    def handle(self, request: dict) -> dict:
        schema = QuotesFetchSchema(**request)
        handler = QuotesFetchHandler()
        extra = {k: v for k, v in request.items() if k not in schema.model_dump()}
        return handler.execute(symbols=schema.symbols, **extra)
