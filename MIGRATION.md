# Migration Plan: fti-holdings → ratchet-holdings

## Context

The existing `fti-holdings` codebase uses:
- **Broker**: Zerodha Kite (via `kiteext`, `kiteconnect`)
- **Bridge**: `omspy-brokers` (Bypass wrapper)
- **Time**: Mixed `time.sleep()` and `pendulum`
- **Logging**: `toolkit.logger.Logger` + `print()`
- **Config**: YAML + CSV files in same directory

The new `ratchet-holdings` will use:
- **Broker**: Finvasia Shoonya (via `broker-ai`)
- **Bridge**: `broker-ai` (direct adapter)
- **Time**: `pendulum` exclusively
- **Logging**: `AsyncLogger` with queue-based non-blocking I/O
- **Config**: Separated `factory/` templates and `data/` runtime files

## Migration Phases

### Phase 1: Infrastructure (broker-ai adapter)
- [ ] Replace `omspy_brokers.bypass.Bypass` with `broker-ai` Finvasia adapter
- [ ] Update authentication flow (Finvasia uses userid+password+TOTP, no enctoken)
- [ ] Implement `broker-ai` interface parity: `ltp()`, `order_place()`, `historical_data()`
- [ ] Update `core/helper.py` login functions

### Phase 2: Core refactoring
- [ ] Remove all `time.sleep()` calls — use `pendulum` + proper async/event loop
- [ ] Replace `print()` with `logging.getLogger(__name__)` throughout
- [ ] Move hardcoded paths (`dir_path = "../../../"`) to config-driven resolution
- [ ] Implement proper rate limiting (token bucket, not sleep)

### Phase 3: Strategy migration
- [ ] Port `strategy1.py` signal logic into `strategies/ratchet.py`
- [ ] Port `fti_holdings/main.py` signal logic (MA12/MA380 crossovers)
- [ ] Unify two signal approaches: simple fibo (strategy1) vs. MA-based (main.py)
- [ ] Implement two-book CSV state management (holdings.csv + swing.csv)

### Phase 4: Data layer
- [ ] Replace single `tradebook.csv` with dual-book architecture
- [ ] Implement position sync: compare local CSV with broker holdings
- [ ] Add drift detection and reconciliation
- [ ] Implement proper CSV locking for concurrent writes

### Phase 5: Service management
- [ ] Create systemd user service template in `factory/`
- [ ] Implement `data/run.txt` state tracking
- [ ] Add graceful shutdown on SIGTERM/SIGINT
- [ ] Create `scripts/local_*` and `scripts/remote_*`

## Breaking Changes

| Old | New | Impact |
|-----|-----|--------|
| `omspy-brokers` | `broker-ai` | All broker calls must be updated |
| `tradebook.csv` | `holdings.csv` + `swing.csv` | Trade history migration needed |
| `time.sleep()` | `pendulum` + event loop | Timing behavior changes |
| `print()` | `logging.getLogger()` | Output format changes |
| Zerodha enctoken | Finvasia session | Auth flow completely different |
| Single signal file | Strategy plugin system | Signal logic restructured |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| broker-ai API mismatch | Medium | High | Test all broker calls before migration |
| Position drift during migration | Medium | High | Sync local CSV with broker before first run |
| Signal logic regression | Low | Medium | Backtest both old and new signals side-by-side |
| Finvasia rate limits | Low | Medium | Implement proper rate limiting from day 1 |

## Rollback Plan

1. Keep `fti-holdings` code intact in separate branch
2. Maintain Zerodha credentials until Finvasia is verified
3. First run in paper-trading mode (no real orders)
4. Compare paper results with expected behavior for 5 trading days
