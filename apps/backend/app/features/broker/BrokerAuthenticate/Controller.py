import logging

from .Schema import BrokerAuthenticateSchema
from .Handler import BrokerAuthenticateHandler

logger = logging.getLogger(__name__)


class BrokerAuthenticateController:

    def handle(self, request: dict) -> dict:
        schema = BrokerAuthenticateSchema(**request)
        handler = BrokerAuthenticateHandler()
        return handler.execute(**schema.model_dump())
