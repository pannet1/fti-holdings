import logging

from .Schema import HelloWorldSchema
from .Handler import HelloWorldHandler

logger = logging.getLogger(__name__)


class HelloWorldController:

    def handle(self, request: dict) -> dict:
        schema = HelloWorldSchema(**request)
        handler = HelloWorldHandler()
        return handler.execute(**schema.model_dump())
