# src/main.py
import logging
from src.constants import (
    S_SETG,
    TradeSet,
    yml_to_obj,
    get_symbol_fm_factory,
    logging_func
)

from src.sdk.helper import Helper
from src.core.build import Builder, stuff_atm, stuff_tradingsymbols
from src.core.strategy import create_strategies_from_params
from src.core.engine import Engine

from traceback import print_exc


logging = logging_func(__name__)

def read_builders(quote, rest):

    logging.debug("reading user trade settings")
    O_TRADESET = TradeSet().find_one()
    if not O_TRADESET or not any(O_TRADESET):
        return None

    trade_settings = O_TRADESET.pop("trade")
    builder = (
        Builder(
            trade_settings=trade_settings,
            user_settings=O_TRADESET,
            quote=quote,
            rest=rest,
        )
        .merge_settings_and_symbols(symbol_factory=get_symbol_fm_factory())
        .find_expiry()
    )
    return builder


def main():
    try:
        # read common start time and stop time
        O_SETG = yml_to_obj(S_SETG)
        engine = Engine(O_SETG["start"], O_SETG["stop"])
        
        Helper.api()
        rest = Helper._rest
        quote = Helper._quote
        builder = read_builders(quote=quote, rest=rest)

        if builder and builder.can_build():
            data = stuff_atm(builder._data, builder._meta)
            print(data, builder._meta)
            lst_of_params = stuff_tradingsymbols(data, builder._meta)
            print(lst_of_params)
            strategies = create_strategies_from_params(lst_of_params)
            print(strategies)
            engine.add_strategy(strategies)
            engine.tick(rest, quote)

    except KeyboardInterrupt:
        __import__("sys").exit()
    except Exception as e:
        logging.error(f"main: {e}")
        print_exc()


if __name__ == "__main__":
    main()
