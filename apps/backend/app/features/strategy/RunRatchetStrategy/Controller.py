import logging

from .Schema import RunRatchetStrategySchema
from .Handler import RunRatchetStrategyHandler

logger = logging.getLogger(__name__)


class RunRatchetStrategyController:

    def handle(self, request: dict) -> dict:
        schema = RunRatchetStrategySchema(**request)
        handler = RunRatchetStrategyHandler()
        return handler.execute(config=schema.model_dump())
