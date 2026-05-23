import logging

from .Schema import FetchQuotesSchema
from .Handler import FetchQuotesHandler

logger = logging.getLogger(__name__)


class FetchQuotesController:

    def handle(self, request: dict) -> dict:
        schema = FetchQuotesSchema(**request)
        handler = FetchQuotesHandler()
        extra = {k: v for k, v in request.items() if k not in schema.model_dump()}
        return handler.execute(symbols=schema.symbols, **extra)
