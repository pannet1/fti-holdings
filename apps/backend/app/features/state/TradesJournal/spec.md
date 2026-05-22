# TradesJournal

## Purpose
Append-only journal of completed trades to `data/trades.csv`. Records every sell execution for audit and reconciliation.

## Flow
1. After a SELL order is confirmed, `journal_trade(row)` appends the trade record
2. CSV auto-creates header on first write (no manual setup needed)
3. File is append-only — never modifies or deletes rows

## CSV Schema
```
datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy
```

## Edge Cases
| Scenario | Behavior |
|----------|----------|
| File does not exist | Create file with header, then append row |
| File already exists | Append row without writing header again |

## Dependencies
- `csv` (stdlib)
- `pydantic` for HoldingsRow schema

## Code Standards
- PEP 484 type annotations on all function signatures and module-level variables
- Zero comments in production code
- Use `logging.getLogger(__name__)` for logging
- No emojis in any text files
- Use `uv` package manager only
