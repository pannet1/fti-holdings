import logging

from .Schema import RatchetStrategyRunSchema
from .Handler import RatchetStrategyRunHandler

logger = logging.getLogger(__name__)


class RatchetStrategyRunController:

    def handle(self, request: dict) -> dict:
        schema = RatchetStrategyRunSchema(**request)
        handler = RatchetStrategyRunHandler()
        return handler.execute(
            start=schema.start,
            stop=schema.stop,
            strategies=[s.model_dump() for s in schema.strategies],
        )
