import logging
from typing import Any, List

from .Rachet import Rachet

logger = logging.getLogger(__name__)


class RatchetStrategyRunHandler:

    def execute(self, config: dict, broker_session: Any = None) -> dict:
        if broker_session is None:
            raise ValueError("Authenticated broker session required")

        strategy = Rachet(**config)
        logger.info(f"Loaded strategy {strategy.strategy} for {strategy._tradingsymbol}")

        return {"status": "ok", "strategy": strategy.strategy, "tradingsymbol": strategy._tradingsymbol}

    def load_strategies(self, configs: List[dict]) -> list:
        instances = []
        for cfg in configs:
            try:
                instance = Rachet(**cfg)
                instances.append(instance)
                logger.info(f"Loaded strategy: {cfg.get('strategy')}")
            except Exception as e:
                logger.error(f"Failed to load strategy {cfg.get('strategy')}: {e}")
        return instances
