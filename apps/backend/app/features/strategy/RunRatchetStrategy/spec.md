# RunRatchetStrategy — Ratchet Two-Book Investing

## Concept

The Ratchet strategy manages equity positions across **two independent books**:

1. **Holdings Book (Vault)** — Core long-term accumulation
2. **Swing Book (Trade)** — Tactical entries for mean-reversion profits

The strategy name comes from the **ratchet mechanism**: the base unit `x` only increases (ratchets up) when swing trades close at profit, never decreases.

**Same‑day round‑trip constraint**: a sell and a buy must never occur on the same trading day. The engine processes one action per day; if both triggers fire, the sell has priority (profit exit) and the buy is suppressed until the next day.

## Fibonacci Position Sizing

```
FIBO_SEQ = [1, 2, 3, 5, 8, 13, 21, 34, 55]
```

Position sizes are multiples of the base unit `x`:
- Buy quantity = `x * fibo_multiplier`
- Default `x = 33` shares
- `x` increases by `RATCHET_FACTOR (1.07)` on each profitable swing exit

## Signal Generation

### Technical Indicators
- **MA12**: 12-period moving average (fast signal)
- **MA380**: 380-period moving average (trend filter)
- **Timeframe**: 60-minute candles (from historical data)

### BUY Conditions
| Scenario | Trigger | Quantity |
|----------|---------|----------|
| Re-entry after sell | open < MA12 AND close > MA12 AND price dropped below fibo% AND above MA380 | 1 share |
| First dip (qty=1) | open < MA12 AND close > MA12 AND price < -5% AND above MA380 | 2 shares |
| Fibo buy (1 < qty < 13) | open < MA12 AND close > MA12 AND price < -martingale% AND above MA380 | Next fibo |
| Below MA380 recovery | open < MA12 AND close > MA12 AND price < -martingale% AND below MA380 | Next fibo |
| *Suppressed if a sell has already executed today* | | |

### SELL Conditions
| Scenario | Trigger | Quantity |
|----------|---------|----------|
| Profit above MA380 | open > MA12 AND close < MA12 AND price > fibo% AND below MA380 | Reverse fibo |
| Cross below MA380 | open < MA380 AND close > MA380 AND price > 1% | Reverse fibo |
| Extended rally | open > MA12 AND close < MA12 AND price > martingale% AND above MA380 | Full quantity |

**Priority**: if both a buy and a sell condition are met in the same tick, the sell executes and the buy is skipped. The engine logs the suppressed buy.

## Two-Book State Machine

### Holdings Book
```
Fields: date, price, qty, wap (weighted avg price), count
Operations:
  - BUY: qty += new_qty, wap = recalculate WAP
  - NEVER sells directly (swing book handles exits)
  - Receives swing positions on PIVOT events
```

### Swing Book
```
Fields: date, price, qty, wap, count (fibo step index)
Operations:
  - BUY: qty += new_qty, wap = recalculate WAP, count = next_fibo_index
  - SELL: qty = 0, wap = 0, count = 0 (full exit on profit)
  - PIVOT: move all swing qty to holdings, reset swing
```

### State Transitions

**Same‑day rule applies**: after a sell, no further buys are allowed for the rest of the trading day. After a buy, a sell is still allowed only if the price moves into profit *within the same day* (though a buy followed by a sell in the same day is also a round‑trip; the rule forbids both directions in the same day). Thus if a buy occurs, any subsequent sell trigger is suppressed until the next day.

```
                    DOWNTREND (<= -5%)
                    ┌─────────────────────┐
                    │                     │
              ┌─────▼─────┐         ┌─────┴─────┐
              │ Fibo-1?   │         │ Fibo-N?   │
              └─────┬─────┘         └─────┬─────┘
                    │                     │
                    ▼                     ▼
            ┌───────────────┐     ┌───────────────┐
            │ HOLDINGS BUY  │     │ SWING STACK   │
            │ (add to vault)│     │ (add to trade)│
            └───────────────┘     └───────────────┘
                                         │
                    UPTREND (>= +5%)     │
                    ┌────────────────────┘
                    │
              ┌─────▼─────┐
              │ Profit?   │─────YES────► SWING SELL (ratchet x up)
              │ (>= 5%)   │            (suppresses any buy today)
              └─────┬─────┘
                    │ NO
                    ▼
              ┌───────────┐
              │ PIVOT     │──► Move swing→holdings + buy more
              │ (weak)    │
              └───────────┘
```

## Invariants

1. **Base unit `x` never decreases** — only increases on profitable swing exits
2. **Holdings book never sells** — only accumulates; exits happen via swing book
3. **Swing book resets to zero** on full profit exit or pivot
4. **Fibo sequence is bounded** — max multiplier is 55 (last in sequence)
5. **Price change threshold is symmetric** — ±5% for buy/sell triggers
6. **MA380 is the trend filter** — above = bullish bias, below = bearish bias
7. **No same‑day round‑trip** — at most one direction (buy OR sell) per trading day. If both fire, sell wins.

## Configuration Parameters

```yaml
# Per-strategy YAML (data/*.yml)
strategy: ratchet
base: NIFTY
symbol: NIFTYBEES
exchange: NSE
quantity: 33              # Base unit x
start_time: "09:30"
stop_time: "15:00"
fibo_seq: [1, 2, 3, 5, 8, 13, 21, 34, 55]
downtrend_thresh: -0.05   # -5%
uptrend_thresh: 0.05      # +5%
ratchet_factor: 1.07      # 7% increase
sell_profit_thresh:
## Modification Request

we should not buy on the same day we sold

## Modification Request

we should not buy on the same day we sold
