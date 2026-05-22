import logging

from .Schema import SymbolsLoadSchema
from .Handler import SymbolsLoadHandler

logger = logging.getLogger(__name__)


class SymbolsLoadController:

    def handle(self, request: dict) -> dict:
        schema = SymbolsLoadSchema(**request)
        handler = SymbolsLoadHandler()
        return handler.execute(**schema.model_dump())
