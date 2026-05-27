from .NorenApi import NorenApi
import time
import concurrent.futures
import pendulum
from traceback import print_exc
from typing import Any, Dict, List, Optional, Tuple

api: Optional["ShoonyaApiPy"] = None


def convert_time_string(dct: Dict[str, Any], key: str, fmt: str) -> Dict[str, Any]:
    """Convert a datetime key in *dct* from its current format to *fmt*.

    If *key* is missing or ``None``, the current IST time is used.
    """
    if key not in dct or dct[key] is None:
        ts = pendulum.now(tz="Asia/Kolkata").format(fmt)
        dct[key] = str(pendulum.from_format(ts, fmt=fmt, tz="Asia/Kolkata"))
        return dct

    try:
        ts = dct.pop(key)
        dct[key] = str(pendulum.from_format(ts, fmt=fmt, tz="Asia/Kolkata"))
    except Exception as e:
        print(f"{e} while converting time to string for {key=} and {fmt=}")
        ts = pendulum.now(tz="Asia/Kolkata").format(fmt)
        dct[key] = str(pendulum.from_format(ts, fmt=fmt, tz="Asia/Kolkata"))
    finally:
        return dct


def filter_dictionary_by_keys(elephant: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Return a new dict containing only the keys listed in *keys*."""
    if not any(elephant):
        return elephant

    filtered: Dict[str, Any] = {}
    for item in keys:
        filtered[item] = elephant.get(item, None)
    return filtered


def get_order_type(order_type: str) -> str:
    """Convert a canonical order type to the Noren API equivalent."""
    order_types: Dict[str, str] = {
        "LIMIT": "LMT",
        "MARKET": "MKT",
        "SL": "SL-LMT",
        "SLL": "SL-LMT",
        "SL-L": "SL-LMT",
        "SLM": "SL-MKT",
        "SL-M": "SL-MKT",
    }
    return order_types.get(order_type.upper(), order_type)


def get_product(product_type: str) -> str:
    """Convert a canonical product type to the Noren API equivalent."""
    product_types: Dict[str, str] = {"MIS": "I", "CNC": "C", "NRML": "M", "BRACKET": "B", "COVER": "H"}
    return product_types.get(product_type.upper(), product_type)


def make_order_modify_args(**kwargs: Any) -> Dict[str, Any]:
    """Build the argument dict for :meth:`NorenApi.modify_order`.

    Expected keyword arguments:
        orderno, tradingsymbol, exchange, newprice_type, newprice, newquantity,
        newtrigger_price (optional).
    """
    order_args: Dict[str, Any] = dict(
        orderno=kwargs.pop("orderno"),
        tradingsymbol=convert_symbol(
            kwargs.pop("tradingsymbol", None), kwargs["exchange"]
        ),
        exchange=kwargs.pop("exchange"),
        newprice_type=get_order_type(kwargs.pop("newprice_type")),
        newprice=(lambda x: x if x >= 0 else 0.05)(kwargs.pop("newprice", 0)),
        newquantity=kwargs.pop("newquantity"),
    )
    if kwargs.get("newtrigger_price", None):
        order_args["newtrigger_price"] = kwargs.pop("newtrigger_price")
    print(f"remaining dictionary items: {kwargs}")
    return order_args


def make_order_place_args(**kwargs: Any) -> Dict[str, Any]:
    """Build the argument dict for :meth:`NorenApi.place_order`.

    Expected keyword arguments:
        buy_or_sell, product_type, tradingsymbol, exchange, discloseqty,
        price_type, retention, quantity, remarks,
        trigger_price (optional), price (optional).
    """
    order_args: Dict[str, Any] = dict(
        buy_or_sell=kwargs.pop("buy_or_sell")[0].upper(),
        product_type=get_product(kwargs.pop("product_type", "I")),
        tradingsymbol=convert_symbol(
            kwargs.pop("tradingsymbol", None), kwargs["exchange"]
        ),
        discloseqty=kwargs.pop("discloseqty", kwargs["quantity"]),
        price_type=get_order_type(kwargs.pop("price_type")),
        retention=kwargs.pop("retention", "DAY"),
        quantity=kwargs["quantity"],
        exchange=kwargs["exchange"],
        remarks=kwargs.pop("remarks", "broker_ai"),
    )
    if kwargs.get("trigger_price", None):
        order_args["trigger_price"] = kwargs.pop("trigger_price")
    if kwargs.get("price", None):
        order_args["price"] = kwargs.pop("price")
    print(f"remaing dict {kwargs}")
    return order_args


def post_trade_hook(*tradebook: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Post-process the trade-book response: filter, cast types, format timestamps."""
    try:
        trade_list: List[Dict[str, Any]] = []
        keys: List[str] = [
            "exchange",
            "symbol",
            "order_id",
            "quantity",
            "side",
            "product",
            "price_type",
            "fill_shares",
            "average_price",
            "exchange_order_id",
            "tag",
            "validity",
            "price_precison",
            "tick_size",
            "fill_timestamp",
            "fill_quantity",
            "fill_price",
            "source",
            "broker_timestamp",
        ]
        if tradebook and any(tradebook):
            tradebook = [filter_dictionary_by_keys(trade, keys) for trade in tradebook]
            int_cols: List[str] = ["flqty", "qty", "fillshares"]
            float_cols: List[str] = ["prc", "flprc"]
            for trade in tradebook:
                try:
                    for int_col in int_cols:
                        trade[int_col] = int(trade.get(int_col, 0))
                    for float_col in float_cols:
                        trade[float_col] = float(trade.get(float_col, 0))
                    now: str = pendulum.now(tz="Asia/Kolkata").format("DD-MM-YYYY HH:mm:ss")
                    ts: str = trade.get("norentm", now)
                    trade_list.append(trade)
                except Exception as e:
                    print(f"{e} while iter stockbroker trades")
                    print_exc()
        return trade_list
    except Exception as e:
        print(f"{e} while processing broker_ai tradebook")
        print_exc()
        return []


def post_order_hook(*orderbook: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Post-process the order-book response: filter, cast types, format timestamps."""
    try:
        keys: List[str] = [
            "symbol",
            "quantity",
            "side",
            "validity",
            "price",
            "trigger_price",
            "average_price",
            "filled_quantity",
            "order_id",
            "exchange",
            "exchange_order_id",
            "disclosed_quantity",
            "broker_timestamp",
            "exchange_timestamp",
            "status",
            "product",
            "order_type",
        ]
        orderbook = [filter_dictionary_by_keys(order, keys) for order in orderbook]
        float_cols: List[str] = ["average_price", "price", "trigger_price"]
        int_cols: List[str] = ["filled_quantity", "quantity"]
        order_list: List[Dict[str, Any]] = []
        for order in orderbook:
            for int_col in int_cols:
                order[int_col] = (
                    lambda x: int(x) if isinstance(x, str) and x.isdigit() else 0
                )(order.get(int_col, 0))
            for float_col in float_cols:
                order[float_col] = (
                    lambda x: float(x) if isinstance(x, str) and x.isdigit() else 0.0
                )(order.get(float_col, 0.0))

            order = convert_time_string(
                order, "exchange_timestamp", "DD-MM-YYYY HH:mm:ss"
            )
            order_list.append(order)
        return order_list
    except Exception as e:
        print(f"{e} while processing broker_ai orderbook")
        print_exc()
        return []


def convert_symbol(symbol: Optional[str], exchange: str = "NSE") -> str:
    """Append ``-EQ`` suffix for NSE equity symbols when missing."""
    if exchange == "NSE":
        if not symbol:
            return ""
        if symbol.endswith("-EQ") or symbol.endswith("-eq"):
            return symbol.upper()
        else:
            return f"{symbol}-EQ"
    return symbol or ""


class Order:
    """Represents a single order for basket placement via :meth:`ShoonyaApiPy.place_basket`."""

    def __init__(
        self,
        buy_or_sell: Optional[str] = None,
        product_type: Optional[str] = None,
        exchange: Optional[str] = None,
        tradingsymbol: Optional[str] = None,
        price_type: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        discloseqty: int = 0,
        retention: str = "DAY",
        remarks: str = "tag",
        order_id: Optional[str] = None,
    ):
        self.buy_or_sell: Optional[str] = buy_or_sell
        self.product_type: Optional[str] = product_type
        self.exchange: Optional[str] = exchange
        self.tradingsymbol: Optional[str] = tradingsymbol
        self.quantity: Optional[int] = quantity
        self.discloseqty: int = discloseqty
        self.price_type: Optional[str] = price_type
        self.price: Optional[float] = price
        self.trigger_price: Optional[float] = trigger_price
        self.retention: str = retention
        self.remarks: str = remarks
        self.order_id: Optional[str] = None


def get_time(time_string: str) -> float:
    """Convert a ``DD-MM-YYYY HH:mm:ss`` string to a Unix timestamp."""
    data = time.strptime(time_string, "%d-%m-%Y %H:%M:%S")
    return time.mktime(data)


class ShoonyaApiPy(NorenApi):
    """Shoonya-specific Noren API wrapper with basket-order support."""

    def __init__(
        self,
        host: str = "https://api.shoonya.com/NorenWClientAPI/",
        websocket: str = "wss://api.shoonya.com/NorenWSAPI/",
    ):
        super().__init__(host=host, websocket=websocket)
        global api
        api = self

    def place_basket(self, orders: List[Order]) -> List[Any]:
        """Place multiple orders concurrently using a thread pool.

        Args:
            orders: List of :class:`Order` instances.

        Returns:
            List of results from each :meth:`place_order` call.
        """
        resp_err: int = 0
        resp_ok: int = 0
        result: List[Any] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_order: Dict[concurrent.futures.Future, Order] = {
                executor.submit(self.place_order, order): order for order in orders
            }
            for future in concurrent.futures.as_completed(future_to_order):
                try:
                    result.append(future.result())
                except Exception as exc:
                    print(exc)
                    resp_err = resp_err + 1
                else:
                    resp_ok = resp_ok + 1
        return result

    def placeOrder(self, order: Order) -> Any:
        """Place a single order from an :class:`Order` instance.

        Delegates to :meth:`NorenApi.place_order` with unpacked fields.
        """
        ret = NorenApi.place_order(
            self,
            buy_or_sell=order.buy_or_sell,
            product_type=order.product_type,
            exchange=order.exchange,
            tradingsymbol=order.tradingsymbol,
            quantity=order.quantity,
            discloseqty=order.discloseqty,
            price_type=order.price_type,
            price=order.price,
            trigger_price=order.trigger_price,
            retention=order.retention,
            remarks=order.remarks,
        )
        return ret
