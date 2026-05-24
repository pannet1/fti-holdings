import logging
import sys

logger = logging.getLogger(__name__)


class HelloWorldHandler:

    def execute(self, **kwargs) -> dict:
        logger.info("HelloWorld.execute called")
        print("hello world", file=sys.stdout, flush=True)
        return {"status": "ok"}
