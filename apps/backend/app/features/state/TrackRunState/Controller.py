import logging

from .Schema import TrackRunStateSchema
from .Handler import TrackRunStateHandler

logger = logging.getLogger(__name__)


class TrackRunStateController:

    def handle(self, request: dict) -> dict:
        schema = TrackRunStateSchema(**request)
        handler = TrackRunStateHandler(data_dir=schema.data_dir, run_file=schema.run_file)
        return handler.execute()
