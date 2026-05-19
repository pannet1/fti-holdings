# Project Status: Ratchet Holdings

## Current State

The `fti-holdings` repository contains two codebases:

### 1. `fti_holdings/` (Legacy — Zerodha/Kite)
- **Status**: Deprecated, reference only
- **Broker**: Zerodha via `omspy-brokers`
- **Files**:
  - `main.py` — MA12/MA380 signal generation with fibo sizing
  - `strategy1.py` — Simpler fibo-based buy/sell logic
  - `login_get_kite.py` — Zerodha authentication
  - `df_utils.py` — Holdings calculation from tradebook
  - `redis_client.py` — Redis-based LTP cache (unused)
  - `scrape.py` — Kite chart scraping (unused)
  - `industry.py` — Industry analysis script (unused)
  - `constants.py` — Path constants
  - `data/` — Per-symbol CSV files (199 files)
  - `symbols.csv` — Watchlist (10 symbols)
  - `tradebook.csv` — Trade history
  - `ind_niftysmallcap250list.csv` — Nifty Smallcap 250 universe

### 2. `rachet_investing/` (New Architecture — In Progress)
- **Status**: Partially implemented, needs broker-ai integration
- **Broker**: Intended for Finvasia via `broker-ai`
- **Files**:
  - `main.py` — Entry point with Engine orchestration
  - `core/build.py` — Builder pattern for config merging
  - `core/engine.py` — Tick loop with strategy dispatch
  - `core/strategy.py` — Dynamic strategy loader
  - `core/constants.py` — Paths, TradeSet, logging init
  - `core/helper.py` — Broker login, REST, Quote wrappers
  - `strategies/ratchet.py` — Two-book Ratchet strategy
  - `providers/async_logger.py` — Queue-based async logging

## What Works

- [x] Engine tick loop with start/stop time gating
- [x] Builder pattern for merging settings + symbols
- [x] Dynamic strategy loading via importlib
- [x] Two-book state management (holdings.csv + swing.csv)
- [x] Fibonacci position sizing logic
- [x] Async logging infrastructure
- [x] TradeSet run-state tracking

## What Needs Work

### High Priority
- [ ] **broker-ai integration** — Replace all `stock_brokers` imports
- [ ] **Finvasia authentication** — TOTP-based login flow
- [ ] **Signal generation** — Port MA12/MA380 logic from fti_holdings/main.py
- [ ] **Order placement** — Implement via broker-ai with error handling
- [ ] **Position sync** — Compare local CSV with broker holdings

### Medium Priority
- [ ] **Rate limiting** — Replace `time.sleep()` with proper throttling
- [ ] **Logging cleanup** — Remove all `print()` calls
- [ ] **Path resolution** — Config-driven paths instead of hardcoded `../../../`
- [ ] **systemd service** — Create user service template
- [ ] **pyproject.toml** — Replace requirements.txt

### Low Priority
- [ ] **Options support** — ATM strike resolution (`stuff_atm`)
- [ ] **Expiry handling** — Future/options expiry detection (`find_expiry`)
- [ ] **Backtesting** — Historical signal replay
- [ ] **Dashboard** — Real-time position monitoring
- [ ] **Alerts** — Telegram/email notifications on trades

## Dependencies to Resolve

| Package | Current | Target | Notes |
|---------|---------|--------|-------|
| Broker bridge | `omspy-brokers` | `broker-ai` | Core replacement |
| Broker API | `kiteconnect` | Finvasia NorenApi | Via broker-ai |
| Toolkit | `git+toolkit` | `git+toolkit` | Keep shared utils |
| Time | `pendulum` + `time` | `pendulum` only | Remove `time` usage |
| Validation | `pydantic==1.9.0` | `pydantic>=2.0` | Upgrade if possible |

## Next Steps

1. Create `pyproject.toml` with correct dependencies
2. Implement broker-ai adapter in `core/helper.py`
3. Port signal generation from `fti_holdings/main.py`
4. Implement order placement with error recovery
5. Add position sync on startup
6. Create systemd service template
7. Write unit tests for strategy logic
8. Test with paper trading account
