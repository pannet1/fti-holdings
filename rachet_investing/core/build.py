from src.constants import logging_func

from toolkit.kokoo import is_time_past

logging = logging_func(__name__)


class Builder:
    def __init__(self, trade_settings: dict, user_settings: dict, quote, rest):
        self._data = user_settings
        self._meta = trade_settings
        meta = {"quote": quote, "rest": rest}
        self._meta.update(meta)

    def merge_settings_and_symbols(self, symbol_factory):
        """
        Retrieves tokens for all trading symbols.
        """
        try:

            # explode k = NIFTY, v = {settings}
            for k, settings in self._data.items():

                if k not in symbol_factory:
                    self._data[k] = settings
                    continue
                # find a matching symbol based on the user settings trade key
                # example settings["NIFTY"]
                assert isinstance(symbol_factory, dict), "symbol_factory is not a dict"
                assert symbol_factory.get(k), f"symbol {k} not found in symbol_factory"

                symbol_item = symbol_factory[k]
                assert isinstance(symbol_item, dict), "symbol_item is not a dict"

                # avoid duplication of base key
                symbol_item["base"] = k

                # use base key as default for symbol
                symbol_item["symbol"] = settings.get("symbol", k)

                # if token not found in case of mcx future expiry
                token = symbol_item.get("token", None)

                # MCX only
                if not token:
                    symbol_item["index"] = k + settings["future_expiry"]
                    symbol_item["exchange"] = settings["option_exchange"]
                    underlying_future = self._meta["quote"].symbol_info(
                        symbol_item["exchange"], symbol_item["index"]
                    )
                    assert isinstance(
                        underlying_future, dict
                    ), "underlying_future is not a dict"
                    symbol_item["token"] = underlying_future["key"].split("|")[1]

                # overwrite symbol item on settings
                self._data[k] = settings | symbol_item
            return self
        except Exception as e:
            logging.error(f"{e} while merging symbol and settings")

    def can_build(self):
        if is_time_past(self._meta["start_time"]):
            return True
        return False

    def find_expiry(self):
        print("not implemented yet")
        return self

def find_atm_fm_ltp():
    print("find atm fm ltp")

def stuff_atm(data, meta):
    print("stuff atm")
    return data

def stuff_tradingsymbols(data, meta):
    merge = {}
    for v in data.values():
        merge = v | meta
        merge["quote"].symbol_info(merge["exchange"], merge["tradingsymbol"], merge["instrument_token"])
    lst = [merge]
    return lst

if __name__ == "__main__":
    try:
        from pprint import pprint
        from src.constants import (
            logging_func,
            TradeSet,
            get_symbol_fm_factory,
        )

        from src.sdk.helper import Helper

        Helper.api()
        quote = Helper._quote
        rest = Helper._rest
        while True:
            O_TRADESET = TradeSet().read()
            if not O_TRADESET or not any(O_TRADESET):
                break
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

            data = stuff_atm(builder._data, builder._meta)
            print("**************************************************")
            pprint(data)
            lst_of_params = stuff_tradingsymbols(data, builder._meta)
            pprint(lst_of_params)

    except Exception as e:
        print(e)
