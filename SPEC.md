# SPEC: Ratchet Holdings — Finvasia + broker-ai

## Overview

Automated equity trading system implementing the **Ratchet investing strategy** — a two-book architecture (Holdings/Vault + Swing/Trade) with Fibonacci-based position sizing and moving-average crossover signals.

**Deprecated predecessor**: `fti-holdings` (Zerodha/Kite + omspy-brokers)  
**New stack**: Finvasia (Shoonya) broker + `broker-ai` bridge

## Architecture

```
┌──────────────────────────────────────────────┐
│                  main.py                      │
│  (entry point, Engine orchestration)          │
├────────────┬──────────────┬──────────────────┤
│  Builder   │   Engine     │   Helper         │
│  (config   │   (tick      │   (login, REST,  │
│   merge)   │    loop)     │    WebSocket)    │
├────────────┴──────────────┴──────────────────┤
│              broker-ai bridge                │
│  (Finvasia NorenApi adapter layer)           │
├──────────────────────────────────────────────┤
│          Finvasia (Shoonya) API              │
└──────────────────────────────────────────────┘
         │                        │
    ┌────┴────┐            ┌──────┴──────┐
    │Strategy │            │  Providers  │
    │(Ratchet)│            │(AsyncLogger)│
    └─────────┘            └─────────────┘
```

## Core Components

### 1. Builder (`core/build.py`)
- Merges user trade settings with symbol factory data
- Resolves instrument tokens via broker-ai
- Finds expiry dates for derivatives (future scope)
- Validates build readiness via `can_build()`

### 2. Engine (`core/engine.py`)
- Time-gated execution loop (start/stop from `settings.yml`)
- Dispatches `tick()` to all registered strategies
- Receives trades, quotes, positions from REST/WS APIs
- Removes completed/expired strategies automatically

### 3. Strategy — Ratchet (`strategies/ratchet.py`)
Two-book architecture:

| Book | Purpose | Reset Condition |
|------|---------|-----------------|
| **Holdings** (Vault) | Core long-term position | Never auto-reset |
| **Swing** (Trade) | Tactical entries/exits | Profit target hit or pivot |

**Invariants**:
- `FIBO_SEQ = [1, 2, 3, 5, 8, 13, 21, 34, 55]`
- `DOWNTREND_THRESH = -5%` → triggers buy
- `UPTREND_THRESH = +5%` → triggers sell/pivot
- `RATCHET_FACTOR = 1.07` → scales base unit `x` on profit
- `SELL_PROFIT_THRESH = 1.05` → 5% profit on swing to sell

**Signal logic** (from `fti_holdings/main.py` `generate_signals`):
- BUY: open < MA12 AND close > MA12 AND price conditions met
- SELL: open > MA12 AND close < MA12 AND price conditions met
- MA380 used as trend filter (above = bullish, below = bearish)

### 4. Helper (`core/helper.py`)
- `Helper.api()` — singleton broker session initialization
- `RestApi` — historical data, trades, baseline prices
- `QuoteApi` — WebSocket LTP subscription, symbol info
- Login flow: reads config YAML, authenticates via broker-ai

### 5. Providers
- `AsyncLogger` — queue-based non-blocking logging with RotatingFileHandler

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, reads settings, builds strategies, runs engine |
| `core/build.py` | Builder class — merges settings + symbols |
| `core/engine.py` | Engine class — tick loop, strategy dispatch |
| `core/strategy.py` | Dynamic strategy loader via importlib |
| `core/constants.py` | Paths, TradeSet singleton, symbol factory loader, logging init |
| `core/helper.py` | Broker login, REST wrapper, Quote/WS wrapper |
| `strategies/ratchet.py` | Ratchet strategy implementation |
| `providers/async_logger.py` | Async logging infrastructure |
| `data/settings.yml` | Runtime config (start/stop times, log level) |
| `data/*.yml` | Per-strategy trade settings |
| `data/holdings.csv` | Holdings book state |
| `data/swing.csv` | Swing book state |
| `data/run.txt` | Run state tracker (which strategies executed today) |
| `factory/symbols.yml` | Symbol configuration template |
| `factory/state_template.csv` | State file template |

## API Routes (broker-ai Bridge)

The `broker-ai` library replaces `omspy-brokers`/`stock-brokers`. Expected interface:

| Method | Description | Replaces |
|--------|-------------|----------|
| `authenticate()` | Login to Finvasia, handle TOTP | `Bypass.authenticate()` |
| `ltp(symbols)` | Get last traded prices | `broker.ltp()` |
| `order_place(...)` | Place limit/market orders | `broker.order_place()` |
| `historical_data(...)` | Fetch OHLCV history | `broker.kite.historical_data()` |
| `instrument_symbol(exchange, symbol)` | Resolve token | `broker.kite.instrument_symbol()` |
| `trades()` | Get today's trades | `rest.trades()` |
| `get_quotes()` | Get subscribed quotes | `quote.get_quotes()` |
| `subscribe(tokens)` | Subscribe to WebSocket | `ws.subscribe()` |

## Finvasia (Shoonya) Specifics

- API library: `NorenApi` from Finvasia
- Authentication: userid + password + TOTP (no API key/secret like Zerodha)
- Product types: `CNC` (delivery), `MIS` (intraday), `NRML` (futures)
- Exchange codes: `NSE`, `BSE`, `NFO`, `MCX`, `CDS`
- Token format: integer instrument tokens
- WebSocket: direct subscription, no encryption token needed

## Data Flow

```
1. main() reads settings.yml → start/stop times
2. Helper.api() → authenticates with Finvasia via broker-ai
3. TradeSet.find_one() → loads strategy YAML from data/
4. Builder merges settings + factory/symbols.yml
5. stuff_atm() → resolves ATM strikes (for options, future scope)
6. stuff_tradingsymbols() → builds strategy params
7. create_strategies_from_params() → imports Ratchet class
8. Engine.tick() → loops: trades + quotes → strategy.run()
9. Ratchet.run() → evaluates price change → buy/sell/hold
10. Orders placed via broker-ai → tradebook updated
```

## Known Issues (from fti-holdings)

1. **Token expiry**: Zerodha enctoken expires daily; Finvasia session management differs
2. **Hardcoded paths**: `dir_path = "../../../"` in constants — needs config-based resolution
3. **CSV race conditions**: Multiple strategies writing to same tradebook.csv
4. **No error recovery**: `sys.exit(1)` on login failure, no retry logic
5. **Sleep-based rate limiting**: `sleep(1)` and `sleep(5)` — should use proper rate limiter
6. **Mixed broker imports**: `omspy_brokers.bypass` + `omspy.brokers.zerodha` — needs single broker-ai abstraction
7. **No position sync**: Local tradebook can drift from broker holdings
8. **Signal generation blocks**: Historical data fetches block the main loop
9. **No systemd integration**: Uses `run.sh` instead of proper service management

## Dependencies

| Package | Purpose |
|---------|---------|
| `broker-ai` | Finvasia broker bridge (replaces omspy-brokers) |
| `pandas` | Data manipulation, CSV I/O |
| `pendulum` | Date/time handling (project standard) |
| `pyyaml` | Settings file parsing |
| `pydantic` | Settings validation |
| `toolkit` | Shared utilities (Logger, Fileutils, kokoo) |

## Project Structure

```
rachet-holdings/
├── main.py
├── core/
│   ├── __init__.py
│   ├── build.py
│   ├── constants.py
│   ├── engine.py
│   ├── helper.py
│   └── strategy.py
├── strategies/
│   ├── __init__.py
│   └── ratchet.py
├── providers/
│   ├── __init__.py
│   └── async_logger.py
├── factory/
│   ├── symbols.yml
│   └── state_template.csv
├── data/
│   ├── settings.yml
│   ├── holdings.csv
│   ├── swing.csv
│   ├── log.txt
│   └── run.txt
├── tests/
├── scripts/
├── pyproject.toml
└── .gitignore
```
