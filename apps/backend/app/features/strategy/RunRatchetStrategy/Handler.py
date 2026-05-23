import logging
from typing import Any, List, Optional

from .Ratchet import Rachet

logger = logging.getLogger(__name__)


class RunRatchetStrategyHandler:

    def execute(self, config: dict) -> dict:
        strategy = Rachet(**config)
        logger.info(f"Loaded strategy {strategy.strategy} for {strategy._tradingsymbol}")

        return {
            "status": "ok",
            "strategy": strategy.strategy,
            "tradingsymbol": strategy._tradingsymbol,
        }

    def execute_tick(self, strategy: Rachet, quotes: dict) -> Optional[dict]:
        trades: Any = None
        positions: Any = None
        signal = strategy.run(trades=trades, quotes=quotes, positions=positions)
        if signal is not None:
            logger.info(f"Signal: {signal['action']} {signal['tradingsymbol']} @ {signal['price']}")
        return signal

    def load_strategies(self, configs: List[dict], config_key: str = "strategy") -> list:
        instances = []
        for cfg in configs:
            try:
                instance = Rachet(**cfg)
                instances.append(instance)
                logger.info(f"Loaded strategy: {cfg.get(config_key)}")
            except Exception as e:
                logger.error(f"Failed to load strategy {cfg.get(config_key)}: {e}")
        return instances
