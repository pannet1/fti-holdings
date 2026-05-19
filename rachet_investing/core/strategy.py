from src.constants import logging_func

from traceback import print_exc
from importlib import import_module

logging = logging_func(__name__)


def create_strategies_from_params(params):
    """
    Creates a list of strategies based on the provided symbols_to_trade.
    """
    try:
        strategies = []
        for args in params:
            strategy_name = args["strategy"]
            module_path = f"src.strategies.{strategy_name}"
            strategy_module = import_module(module_path)
            Strategy = getattr(strategy_module, strategy_name.capitalize())
            logging.info(f"creating strategy: {strategy_name}")
            strgy = Strategy(**args)
            strategies.append(strgy)

        return strategies
    except Exception as e:
        logging.error(f"{e} while creating the strategies in StrategyBuilder")
        print_exc()
