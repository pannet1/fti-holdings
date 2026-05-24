# StreamQuotes — Market Feature

## Overview

Establishes a persistent WebSocket connection to the Finvasia broker via `broker_ai.finvasia.wsocket.Wsocket`, subscribes to a list of trading symbol tokens, and streams live touchline (LTP) data. Other features poll for latest quotes via `get_quotes()` or `wait_for_quotes()`.

## Input / Output

| Direction | Format | Description |
|-----------|--------|-------------|
| Input | `broker_session`, `tokens: List[str]`, `symbol_map: Dict[str, str]` | Authenticated broker session, exchange token list, mapping of human-readable symbols to WS keys |
| Output | `Dict[str, float]` | Symbol → last traded price queried via `get_quotes(symbols)` |

## Business Logic Constraints

- Only one WebSocket connection per broker session (idempotent `start()`)
- LTP is stored in a thread-safe dict protected by `Lock()`
- `get_quotes()` returns only symbols that have received at least one tick
- `wait_for_quotes()` blocks up to `timeout` seconds until all requested symbols have data
- Callbacks (`on_connect`, `on_ticks`, `on_close`, `on_error`) are assigned before `connect()`

## Error Cases

| Condition | Error | Message |
|-----------|-------|---------|
| Connection fails before timeout | Partial or empty dict from `wait_for_quotes()` | No error raised; caller checks completeness |
| WebSocket disconnects mid-session | `_on_close` sets `_socket_opened = False` | Logged as warning; LTP cache preserved |

## Dependencies

- `broker_ai.finvasia.wsocket.Wsocket`
- Authenticated broker session (from AuthenticateBroker)

## Code Standards

All code must use type annotations per PEP 484.
