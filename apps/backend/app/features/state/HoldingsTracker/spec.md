# HoldingsTracker

## Purpose
Read and manage live holdings from `data/holdings.csv`. Provides CRUD operations for holdings records consumed by strategies (e.g., Ratchet).

## Flow
1. Consumer calls `read_by_symbol(tradingsymbol)` to get current holdings for a symbol
2. `add_holding(row)` appends a new trade row to the CSV
3. `remove_holder(tradingsymbol, quantity)` deducts quantity from matching rows
4. CSV auto-creates header on first write

## CSV Schema
```
datetime,exchange,tradingsymbol,side,avg_price,quantity,strategy
```

## Edge Cases
| Scenario | Behavior |
|----------|----------|
| CSV file missing | Return empty list |
| Empty file (header only) | Return empty list |
| Symbol not found | Return empty list |
| Remove more than held | Remove all matching rows, keep remainder in remaining |
| Remove nonexistent symbol | No-op |

## Dependencies
- `csv` (stdlib)
- `pydantic` for HoldingsRow schema

## Code Standards
- PEP 484 type annotations on all function signatures and module-level variables
- Zero comments in production code
- Use `logging.getLogger(__name__)` for logging
- No emojis in any text files
- Use `uv` package manager only
