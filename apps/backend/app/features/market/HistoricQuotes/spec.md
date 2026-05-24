# HistoricQuotes — Market Feature

## Overview

Provides historic candle data over a configurable time range and timeframe, mimicking the `StreamQuotes` interface so it can be used as a drop-in replacement. The feature loads a series of candles from the broker‑ai historical API and exposes a cursor that advances one candle per call, returning the close price. Default timeframe is `1Min`, default period is one month ending at the current date.

## Input / Output

| Direction | Format | Description |
|-----------|--------|-------------|
| Input | `HistoricQuotesConfig` (Pydantic `BaseModel`) | Configuration: `symbol` (str), `exchange` (str), `timeframe` (str, default `"1Min"`), `start_date` (pendulum date, default `now - 30 days`), `end_date` (pendulum date, default `now`). |
| Output (public methods) | `float` (via `next_close()`) or `dict` (via `get_quote()`) | `next_close()` returns the close price of the current candle and advances the internal index. `get_quote()` returns a dict with keys `"time"`, `"open"`, `"high"`, `"low"`, `"close"` for the current candle without advancing. |

## Business Logic Constraints

- The data is sourced from Finvasia class with the below signature

    ```python
    def historical(self, exch: str, tkn: str, fm: str, to: str, tf: int = 1) -> Optional[List[Dict[str, Any]]]:
        return self.broker.get_time_price_series(exch, tkn, fm, to, tf)
    ```

- The handler instantiates an internal `HistoricQuotes` class that holds the loaded candles and an index pointer.
- `fetch_history` callable is injected as a dependency – the handler never calls the broker API directly.
- On `initialize()` (or `connect()`), the handler calls `fetch_history` to load candle data into the internal list.
- `next_close()` returns the current candle's close and advances the index by one.
- `get_quote()` returns the current candle dict without advancing the index.
- When the index reaches the end of the data, subsequent calls return the last candle's close without advancing.

## Error Cases

| Condition | Error | Behavior |
|-----------|-------|----------|
| `fetch_history` returns None or empty | `ValueError` | Raised during `initialize()` |
| Index past end of data | No error | Return last close repeatedly |
| Missing `exchange` or `symbol` | `ValidationError` | Caught by Pydantic schema |

