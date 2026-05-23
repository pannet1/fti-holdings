import logging

from .Schema import AuthenticateBrokerSchema
from .Handler import AuthenticateBrokerHandler

logger = logging.getLogger(__name__)


class AuthenticateBrokerController:

    def handle(self, request: dict) -> dict:
        schema = AuthenticateBrokerSchema(**request)
        handler = AuthenticateBrokerHandler()
        return handler.execute(**schema.model_dump())
