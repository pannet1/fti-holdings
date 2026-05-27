# JournalTrades — Append-Only Trade Journal

## Overview
Append-only journal of completed trades to a CSV file. Records every sell execution for audit and reconciliation. The output directory depends on the `paper` flag from global settings.

## Flow
1. On startup, `settings.yml` is loaded. The `paper` flag (`bool`) is read from `global_settings.paper`.
2. Based on `paper`:
   - `paper = False` → directory is `data/`
   - `paper = True` → directory is `data/paper/`
3. If the target directory does not exist, it is created (`os.makedirs(exist_ok=True)`).
4. After a SELL order is confirmed, `journal_trade(row, base_path)` appends the trade record to `<base_path>/trades.csv`.
5. CSV auto-creates the header row on first write; subsequent appends skip the header.

## Input / Output
| Direction | Name | Type | Description |
|-----------|------|------|-------------|
| Input | `row` | `HoldingsRow` (Pydantic) | Trade record: datetime, exchange, tradingsymbol, side, avg_price, quantity, strategy |
| Input | `paper` | `bool` | Whether paper trading mode is active (injected from settings) |
| Output | `trades.csv` | CSV file | Appended row; file created if missing |

## File Path Resolution
- `paper = False`: `data/trades.csv`
- `paper = True`: `data/paper/trades.csv`
- Path is determined once at feature initialization or passed to `journal_trade` as a parameter.

## Business Logic Constraints
- Append-only: never modify or delete existing rows.
- Header is written only when the file is created.
- Directory is created if absent (including `data/paper/` when `paper=True`).
- The `paper` flag is static for the runtime session; does not change mid-session.

## Error Cases
| Scenario | Behavior |
|----------|----------|
| Directory does not exist | Created automatically before writing |
| File does not exist | Created with header, then row appended |
| File already exists | Row appended; header not repeated |
| `paper` flag missing from settings | Falls back to `False` or raises `KeyError` per system config policy (see `SPEC.md` Config section) |

## Dependencies
- `csv` (stdlib)
- `os` / `pathlib` (stdlib) – for directory creation and path joining
- `pydantic` – for `HoldingsRow` schema

## Integration Notes
- This is an internal background slice (no HTTP endpoint). No `Controller.py` required.
- The `paper` flag is injected from the settings loader (e.g., `LoadSettingsHandler`).
- The feature is called by the trade execution flow after a confirmed sell.

## Code Standards
- PEP 484 type annotations on all function signatures and module-level variables.
- Zero comments in production code.
- Use `logging.getLogger(__name__)` for logging.
- No emojis in any text files.
- Use `uv` package manager only.