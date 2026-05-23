# ManageOrder — CNC Delivery Order Placement Spec

## Overview

Places delivery (CNC) orders through an authenticated broker session for a given trading symbol, exchange, and side.

## Flow

1. Accept order params: tradingsymbol, exchange, transaction_type (BUY/SELL), quantity, price
2. Accept authenticated broker session
3. Call `broker_session.order_place(tradingsymbol, exchange, transaction_type, quantity, order_type="LIMIT", product="C", price=price)`
4. Return order confirmation with order_id

## Error Handling

- Empty required fields raise ValueError
- Missing broker session raises ValueError
- Broker API failure returns error status

## Dependencies

- Authenticated broker session (from AuthenticateBroker)

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
