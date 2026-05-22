import logging

from .Schema import RunStateTrackSchema
from .Handler import RunStateTrackHandler

logger = logging.getLogger(__name__)


class RunStateTrackController:

    def handle(self, request: dict) -> dict:
        schema = RunStateTrackSchema(**request)
        handler = RunStateTrackHandler(data_dir=schema.data_dir, run_file=schema.run_file)
        return handler.execute()
