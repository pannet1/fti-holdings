# LoadSettings — Configuration Spec

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

Global configuration (broker is derived from auth.yaml's top-level key):

```yaml
log_level: DEBUG          # DEBUG, INFO, WARNING, ERROR
log_show: true            # also log to stdout
start: "09:15"            # market start (HH:MM)
stop: "15:30"             # market stop (HH:MM)
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

### data/auth.yaml

Finvasia credentials (never committed to git).

```yaml
finvasia:
  user_id: "FN12345"
  password: "secret"
  totp_secret: "JBSWY3DPEHPK3PXP"
  vendor_code: ""
  app_key: ""
  api_secret: ""
  imei: ""
  oauth_url: ""
```

## State Files

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
2024-01-15 09:30:00,123 - INFO - **app.strategies.ratchet** - MainThread - HOLDINGS BUY: 33 @ 2450.50
2024-01-15 09:30:01,456 - DEBUG - **app.core.engine** - MainThread - tick complete
```

### data/<userid>.txt

Finvasia session token (auto-managed, daily expiry).

## Bootstrapping (Handler Behavior)

The `LoadSettingsHandler` follows a three-phase bootstrapping sequence:

### Phase 1: Bootstrap Check
1. Verify `data/` directory exists; create it if missing.
2. Check for `data/settings.yml` and `data/auth.yaml`.

3. If missing:
   - Copy `factory/settings.yml` → `data/settings.yml`
   - Copy `factory/auth.yaml` → `data/auth.yaml`
   - Raise `RuntimeError` telling the user to fill in the copied templates.

### Phase 2: Parse Broker
1. Read `data/auth.yaml` with `yaml.safe_load()`.
2. Take the top-level key (e.g. `finvasia`) as the broker identifier.
3. On empty file, raise `ValueError`.

### Phase 3: Parse Global Settings
1. Read `data/settings.yml` with `yaml.safe_load()`.
2. Validate into `GlobalSettings` Pydantic model (log_level, log_show, start, stop).
3. On `ValidationError`, log and re-raise.

### Phase 4: Parse Strategy Files
1. Scan `data/*.yml` excluding `settings.yml`, `auth.yaml`, `auth.yml`.
2. Each strategy YAML may have a top-level wrapper key (e.g. `trade:`); unwrap it.
3. Validate each into `StrategySettings` Pydantic model.
4. Return aggregated dict with `global` + `strategies` keys.

### Error Handling
| Scenario | Behavior |
|----------|----------|
| Missing config files | Copy templates from `factory/`, raise `RuntimeError` |
| Invalid YAML syntax | `yaml.safe_load` raises — propagate to caller |
| Schema mismatch | `ValidationError` from Pydantic — logged and re-raised |
| Empty data/ dir | Return empty `strategies` list (no crash) |

## Data Flow

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

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).

## Modification Request

the factory path and data path are changed. please ensure that settings are loaded correctly

## Modification Request

i want to add another key to the factory/settings yaml file.

backtest: 0

if backtest: 1 is set in the data/settings yaml file, the bot will run in backtest mode.
