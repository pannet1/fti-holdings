# FTI Holdings — Ratchet Trading Strategy

## Overview
A ratchet-style position sizing strategy for BSE ETFs (ITBEES, MOTHERSON).

## Holdings
Each buy order's quantity is the base unit times a multiplier.

Multiplier ladder: [1, 2, 3, 5, 8, 13, 21, 33, 55]
Base unit = quantity of the first buy

## Buy Rules
### On Start (no open holdings)
- Determine win_qty and loss_qty from trade history
- If no prior trade exists, both default to the configured quantity
- On run: if winning (price up) use win_qty, if losing (price down) use loss_qty

### During Trading (open holdings exist)
The multiplier moves based on market price vs last trade price:
- Price rises 5% -> lower multiplier
- Price falls 5% -> higher multiplier

## Example
Base unit: 33, ladder: [1, 2, 3, 5, 8...], starting price: 100

Step 1: Buy 33 @ 100 (multiplier 1)
Step 2: Price drops to 95. Buy 66 (multiplier 2)
Step 3: Price drops to 90.25. Buy 99 (multiplier 3)
Step 4: Price rises to 94.76. Buy 66 (multiplier 2)

## Trade Records
Open holdings and completed trades are recorded to track state
across restarts.
