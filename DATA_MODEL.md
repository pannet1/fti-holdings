# Data Model

## Configuration Files

### factory/symbols.yml

Symbol configuration template. Copied to runtime as needed.

```yaml
NIFTYBEES:
  token: "12345"
  exchange: "NSE"
  tradingsymbol: "NIFTYBEES"
  instrument_token: 12345

RELIANCE:
  token: "67890"
  exchange: "NSE"
  tradingsymbol: "RELIANCE"
  instrument_token: 67890
```

### data/settings.yml

Global runtime settings.

```yaml
broker: finvasia
log_level: DEBUG
log_show: true
start: "09:15"
stop: "15:30"
```

### data/*.yml (Per-Strategy)

Individual strategy configurations. Filename determines strategy name.

```yaml
trade:
  strategy: ratchet
  base: NIFTY
  symbol: NIFTYBEES
  exchange: NSE
  quantity: 33
  start_time: "09:30"
  stop_time: "15:00"
```

### data/bypass.yaml

Finvasia credentials (never committed to git).

```yaml
bypass:
  userid: "FN12345"
  password: "secret"
  totp: "JBSWY3DPEHPK3PXP"
```

## State Files

### data/holdings.csv

Holdings book (Vault) — core long-term positions.

| Column | Type | Description |
|--------|------|-------------|
| date | str | Last trade date (YYYY-MM-DD) |
| price | float | Last trade price |
| qty | int | Total quantity held |
| wap | float | Weighted average price |
| count | int | Total shares accumulated |

```csv
date,price,qty,wap,count
2024-01-15,2450.50,99,2430.25,99
```

### data/swing.csv

Swing book (Trade) — tactical positions.

| Column | Type | Description |
|--------|------|-------------|
| date | str | Last trade date (YYYY-MM-DD) |
| price | float | Last trade price |
| qty | int | Current swing quantity |
| wap | float | Weighted average price of swing |
| count | int | Current fibo step index |

```csv
date,price,qty,wap,count
2024-01-15,2450.50,66,2440.00,2
```

### data/run.txt

Strategy execution tracker. One strategy filename per line.

```
ratchet_nifty.yml
ratchet_bank.yml
```

Reset daily or when all strategies have been executed.

### data/log.txt

Application log (rotating, 10MB max, 5 backups).

```
2024-01-15 09:30:00,123 - INFO - **rachet_investing.strategies.ratchet** - MainThread - HOLDINGS BUY: 33 @ 2450.50
2024-01-15 09:30:01,456 - DEBUG - **rachet_investing.core.engine** - MainThread - tick complete
```

### data/<userid>.txt

Finvasia session token (auto-managed, daily expiry).

## Legacy Files (fti_holdings/)

### tradebook.csv

Flat trade history (deprecated, replaced by two-book architecture).

| Column | Type | Description |
|--------|------|-------------|
| symbol | str | Trading symbol |
| trade_date | str | Trade date (YYYY-MM-DD) |
| exchange | str | NSE or BSE |
| trade_type | str | buy or sell |
| quantity | int | Trade quantity |
| price | float | Trade price |

```csv
symbol,trade_date,exchange,trade_type,quantity,price
GABRIEL,2022-10-07,NSE,buy,1,156.5
HINDALCO,2022-12-20,BSE,buy,1,449.8
```

### symbols.csv

Watchlist with disable flag (deprecated, replaced by factory/symbols.yml).

| Column | Type | Description |
|--------|------|-------------|
| symbol | str | Trading symbol |
| token | str | Instrument token (optional) |
| disabled | str | 'x' to disable |

## Data Flow Diagram

```
┌─────────────────┐
│ factory/        │
│  symbols.yml    │────┐
│  settings.yml   │    │
└─────────────────┘    │
                       ▼
┌─────────────────┐  ┌──────────────┐
│ data/*.yml      │─►│   Builder    │
│ (strategy cfg)  │  │ (merge)      │
└─────────────────┘  └──────┬───────┘
                            │
                            ▼
┌─────────────────┐  ┌──────────────┐     ┌──────────────┐
│ data/holdings.csv│◄─│   Ratchet    │────►│ broker-ai    │
│ data/swing.csv   │  │  (strategy)  │     │ (Finvasia)   │
└─────────────────┘  └──────────────┘     └──────────────┘
       ▲                      │
       │                      ▼
┌─────────────────┐  ┌──────────────┐
│ data/run.txt    │◄─│   Engine     │
│ (state tracker) │  │  (tick loop) │
└─────────────────┘  └──────────────┘
```
