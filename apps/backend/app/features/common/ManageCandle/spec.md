# ManageCandle — Common Feature

Detects candle boundaries by tracking an incrementing index.

## Usage
A strategy stores `_last_candle_idx`. On each tick, it checks if
`candle_mgr.current_index > _last_candle_idx` — if so, a new candle
has closed and the strategy can evaluate.

## Code Standards
- PEP 484 type annotations on all function signatures
- Zero comments in production code
- Use `logging.getLogger(__name__)` for logging

## Modification

ManageCandle should use Strategy start_time and stop_time for
candle timeframe calculation. This also applies to the stop time
or candle close time whichever happens earlier, rule

### Constraints
* <!-- added by modification -->
