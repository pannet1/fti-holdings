import logging

from .Schema import LoadSymbolsSchema
from .Handler import LoadSymbolsHandler

logger = logging.getLogger(__name__)


class LoadSymbolsController:

    def handle(self, request: dict) -> dict:
        schema = LoadSymbolsSchema(**request)
        handler = LoadSymbolsHandler()
        return handler.execute(**schema.model_dump())
