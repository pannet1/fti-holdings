# FetchQuotes — Market Quote Fetcher Spec

## Overview

Fetches live quotes for given symbols through an authenticated broker session.

## Flow

1. Accept list of symbols in `EXCHANGE|TOKEN` format
2. Accept authenticated broker session
3. Call `broker_session.get_quotes(exch, token)` for each symbol
4. Return dict of symbol→quote results

## Error Handling

- Empty symbols list returns early with no error
- Missing broker session raises ValueError
- Individual symbol failures return None for that symbol

## Dependencies

- Authenticated broker session (from AuthenticateBroker)

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
