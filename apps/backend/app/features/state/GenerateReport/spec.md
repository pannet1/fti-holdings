# GenerateReport — Backtest Performance Report

## Overview
Reads a trades CSV (live or paper), groups sequential BUYs into cycles terminated by a SELL, and computes per-cycle P&L plus a summary. The output is a printable report string. The CSV path depends on the `paper` flag, matching the convention used by `JournalTrades` and `TrackHoldings`.

## Flow
1. `generate_report(data_dir, paper)` is called with a base directory and paper flag.
2. If `paper = True`, the CSV is read from `<data_dir>/paper/trades.csv`.
3. If `paper = False`, the CSV is read from `<data_dir>/trades.csv`.
4. If the file does not exist, return an error message.
5. Rows are read sequentially. BUYs accumulate into a stack. A SELL terminates the current cycle.
6. For each cycle, compute: total buy quantity, weighted average buy price, sell price, P&L (₹), P&L (%).
7. Output a formatted report string with per-cycle breakdown and summary totals.

## Input / Output
| Direction | Name | Type | Description |
|-----------|------|------|-------------|
| Input | `data_dir` | `str` | Base directory for CSV files |
| Input | `paper` | `bool` | Whether to read from `data/paper/` |
| Output | `str` | Report | Human-readable P&L breakdown |

## Business Logic Constraints
- A cycle starts with one or more BUYs and ends with one SELL.
- If a SELL quantity exceeds accumulated BUY quantity, treat as an error.
- If the file has rows after the last SELL (open position), report it separately.
- 100% win rate is normal for a strategy that only sells at a profit.

## Error Cases
| Scenario | Behavior |
|----------|----------|
| File does not exist | Returns `"No trades file found at <path>"` |
| SELL quantity exceeds BUY stack | Returns `"Trade data error: SELL qty exceeds buys at row N"` |
| Empty file | Returns `"Trades file is empty"` |
| Malformed CSV | Lets `csv.DictReader` raise — caller handles |

## Dependencies
- `csv` (stdlib) – CSV reading
- `pathlib` (stdlib) – path handling
- `pydantic` – for report schemas

## Integration Notes
- No HTTP endpoint. Called as a utility from other features or CLI.
- The `paper` flag is injected from settings loader (same as JournalTrades).
