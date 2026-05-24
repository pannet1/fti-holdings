# SPEC.md — Technical Architecture Blueprint

## Stack
- **Runtime**: Python 3.10, uv monorepo
- **Framework**: FastAPI (no Django, no Flask)
- **ORM / DB**: SQLite via aiosqlite (raw SQL, no SQLAlchemy)
- **Validation**: Pydantic v2 for all input/output schemas
- **Time**: pendulum only (never datetime, time, calendar)
- **Async**: asyncio event loop; all I/O is async
- **Logging**: `logging.getLogger(__name__)` with `AsyncLogger` from `toolkit.logger`

## Directory Layout
```
repo-root/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── features/     # Vertical slices (see below)
│   │   │   ├── main.py       # App entry point
│   │   │   └── shared/       # Cross-feature utilities
│   │   ├── factory/          # Template config files (defaults, not secrets)
│   │   └── tests/            # Integration tests
│   └── frontend/             # Qwik app (separate concerns)
├── packages/
│   └── shared/               # Pydantic schemas shared between apps
├── data/                     # Runtime runtime data (gitignored, secrets)
├── .agents/                  # Orchestrator + runner + personas (AI harness)
├── AGENTS.md                 # Agentic workflow constitution
├── SPEC.md                   # THIS FILE — architectural blueprint
└── pyproject.toml            # uv workspace root
```

## Vertical Slice Architecture (4 Files Per Feature)
Every feature lives at `apps/backend/app/features/<domain>/<ActionName>/` with exactly these files:

| File | Responsibility |
|------|---------------|
| `Schema.py` | Pydantic v2 model for input validation. No logic. |
| `Handler.py` | Pure business logic. No I/O, no framework imports. Dependencies are parameters. |
| `Controller.py` | Thin shell: parse input from Schema, call Handler, format output. No business logic. |
| `Tests.py` | Unit tests for Handler. Happy path + empty state + error edges. |

**Rules**:
- Handler never imports FastAPI, never reads files, never calls external APIs
- Controller never contains business logic (if-else on domain state)
- Schema uses Pydantic v2 `BaseModel` only (no `dataclasses`, no `TypedDict`)
- No `__init__.py` beyond the empty marker
- **Internal data/background slices** that are never called via HTTP (e.g. `JournalTrades`, `TrackHoldings`) may omit `Controller.py`. This is the only exception to the 4-file rule. Such slices must be explicitly documented in their `spec.md` as non-HTTP utilities.

## Feature Discovery & Registration
- `main.py` auto-discovers features by scanning `features/` at startup
- Each feature directory with `Controller.py` is registered as a route
- No manual route registration in `main.py`

## Error Handling
- Controllers catch `ValidationError` from Pydantic and return 422
- Handlers raise custom exceptions defined in `shared/errors.py`
- Unhandled exceptions propagate to FastAPI's default exception handler (500)
- No try/except in Controllers for business logic failures

## WebSocket Protocol
- Quotes stream via `broker_ai.finvasia.wsocket.Wsocket`
- Touchline updates are pushed to subscribed strategies as dicts
- Strategy callbacks receive `(touchline: dict) -> None`
- One websocket connection per broker session; multiplexed to all strategies

## Config & Secrets — Source of Truth

**`data/` is THE authoritative runtime config directory. `factory/` is a template library only, never read at runtime.**

- Template configs in `apps/backend/factory/*.yml` — committed, no secrets. These are reference copies for scaffolding new environments. Never modified at runtime.
- Runtime config in `data/*.yml` — gitignored, contains secrets. This is the only directory read by `LoadSettingsHandler` at startup.
- `settings.yml` has two sections: `global_settings` and `strategies`. The `factory/` template and `data/` runtime copy must be kept in sync manually — `data/` is the source of truth.
- `data/auth.yaml` holds broker credentials (never committed). No auth template exists in `factory/`.

**Rule**: If a key exists in `factory/settings.yml` but not in `data/settings.yml`, the app crashes at startup with a `KeyError`. The runtime never falls back to factory defaults.

## Broker Integration
- **broker-ai** library in separate Git repo; fixes done upstream, pulled via uv.lock
- Auth flow: `AuthenticateBrokerHandler` → Finvasia API → access/refresh tokens
- Websocket: `broker_ai.finvasia.wsocket.Wsocket` (wraps ShoonyaApiPy)
- Auth is forced fresh every run (`access_token=None`)

## Candle / Time Frame
- `candle` is a global int setting in `settings.yml` (e.g. `240` = 4 hours)
- No hardcoded defaults; `O_SETG["candle"]` required at runtime
- Injected into strategy config by `build_strategies()` in `main.py`

## Strategy System
- Each strategy is a class with `on_tick(touchline: dict)` callback
- Registered by name in `settings.yml` under `strategies` key
- Loaded dynamically via `importlib` in strategy/run ratchet feature
- A strategy file is identified by containing a `"strategy"` key in its YAML
- Non-strategy `.yml` files in the strategies dir are skipped with a warning

## Agentic Workflow (AI Harness)
- **Orchestrator** (`.agents/orchestrator.py`): decomposes human request, dispatches
- **Runner** (`.agents/runner.py`): persona + spec → Zen API → write code → pytest
- **Personas**: stored in `.agents/personas/` (backend_agent.md, qa_agent.md)
- **Spec flow**: human prompt → Orchestrator → Zen API → spec.md → Runner → code
- **Evaluation**: Runner runs pytest after codegen; auto-QA loop up to 3 attempts
- **Model selection**: `.agents/model_config.json` persists chosen Zen model; fallback chain on 401
- Never call `opencode` CLI; always use Zen API directly via HTTPS
- `SPEC.md` is the technical blueprint — ingested by all agents. Business terms live in `docs/SOW.md`.

## Code Standards (Enforced by CI)
- Type annotations (PEP 484) on every function signature and module-level variable
- Zero comments in source code
- No `print()` — use `logging.getLogger(__name__)`
- No emojis in text files
- `pytest` for all tests; coverage gate on new features
- `uv` only — no pip, no poetry, no conda, no `requirements.txt` (except `uv export` for deploy)
