# Broker-AI Integration Spec

## Overview

`broker-ai` is the bridge between the ratchet strategy and Finvasia (Shoonya) broker API.

## Finvasia (Shoonya) API

### Authentication
- **Method**: userid + password + TOTP
- **Session**: Daily session token (no persistent enctoken like Zerodha)
- **TOTP**: Time-based one-time password via `pyotp`

### Key Differences from Legacy Brokers

| Aspect | Legacy | Finvasia (new) |
|--------|--------|----------------|
| Auth | API key + secret + token | userid + password + TOTP |
| Token persistence | Token file (daily expiry) | Session token (daily) |
| Instrument lookup | `.instruments()` | `NorenApi.searchscrip()` |
| Order types | `LIMIT`, `MARKET`, `SL`, `SL-M` | Same |
| Product codes | `CNC`, `MIS`, `NRML` | `C`, `M`, `NRML` |
| Exchange codes | `NSE`, `BSE`, `NFO` | Same |
| WebSocket | Vendor Ticker | Shoonya WebSocket |
| Historical data | `.historical_data()` | `NorenApi.get_time_price_series()` |

## broker-ai Interface

### Connection

```python
from broker_ai import FinvasiaBroker

broker = FinvasiaBroker(
    userid="FN12345",
    password="secret",
    totp_secret="JBSWY3DPEHPK3PXP",
    token_path="data/FN12345.txt",
)
authenticated = broker.authenticate()
```

### Quote Methods

```python
# Single LTP
ltp = broker.ltp("NSE|RELIANCE")

# Multiple LTPs
ltps = broker.ltp(["NSE|RELIANCE", "NSE|TCS", "BSE|INFY"])
# Returns: {"RELIANCE": 2450.50, "TCS": 3890.00, "INFY": 1560.25}

# Full quotes (OHLCV + depth)
quotes = broker.get_quotes(["NSE|RELIANCE"])
```

### Order Methods

```python
# Place order
order_id = broker.order_place(
    tradingsymbol="RELIANCE",
    exchange="NSE",
    transaction_type="BUY",      # BUY or SELL
    quantity=33,
    order_type="LIMIT",          # LIMIT, MARKET, SL, SL-M
    product="C",                 # C (CNC), M (MIS), NRML
    variety="regular",
    price=2450.50,               # Required for LIMIT/SL
    trigger_price=None,          # Required for SL/SL-M
)

# Get order status
status = broker.order_status(order_id)

# Get today's trades
trades = broker.trades()

# Get holdings
holdings = broker.holdings()
```

### Historical Data

```python
# Get OHLCV history
data = broker.historical_data(
    instrument_token=12345,
    from_date="2024-01-01",
    to_date="2024-12-31",
    interval="60minute",         # minute, 3minute, 5minute, 15minute, 30minute, 60minute, day, week, month
)
# Returns: list of dicts with date, open, high, low, close, volume
```

### Instrument Resolution

```python
# Get instrument token
token = broker.instrument_symbol("NSE", "RELIANCE")

# Search for instrument
results = broker.search_scrip("NSE", "REL")
```

### WebSocket

```python
# Subscribe to LTP updates
broker.subscribe(["12345", "67890"])

# Unsubscribe
broker.unsubscribe(["12345"])

# Get latest LTPs (populated by WS callback)
ltps = broker.ws_ltp
# Returns: {"12345": 2450.50, "67890": 3890.00}
```

## Adapter Layer (core/helper.py)

The Helper class wraps broker-ai to provide a consistent interface for strategies:

```python
class Helper:
    _api = None

    @classmethod
    def api(cls):
        if cls._api is None:
            cls._api = FinvasiaBroker(...)
            cls._rest = RestApi(cls._api)
            cls._quote = QuoteApi(cls._api)
        return cls._api

class RestApi:
    def __init__(self, session):
        self._api = session

    def trades(self):
        return self._api.trades()

    def history(self, instrument_token):
        return self._api.historical_data(...)

class QuoteApi:
    def __init__(self, ws):
        self._ws = ws

    def get_quotes(self):
        return self._ws.ws_ltp

    def symbol_info(self, exchange, symbol, token=None):
        # Resolve token if not provided, subscribe to WS
        ...
```

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| Authentication failed | Wrong credentials / TOTP | Delete token file, retry |
| Session expired | End of trading day | Auto-reauthenticate next run |
| Rate limit exceeded | Too many API calls | Implement exponential backoff |
| Instrument not found | Wrong symbol/exchange | Validate against factory/symbols.yml |
| Order rejected | Insufficient funds / circuit limits | Log and skip, retry next tick |

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
