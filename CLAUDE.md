# CLAUDE.md — Candle Alerts

> Crypto market screener and alert system.
> Backend-first. Data integrity over features. No premature optimization.

---

## Project overview

Candle is a crypto market screener that fetches OHLCV data from multiple exchanges,
computes technical indicators, evaluates configurable screening conditions, and
delivers alerts via Telegram. Designed as a portfolio project with a clear path
toward a deployable product.

**Current phase:** v1.1 — observability, refactor, frontend improvements
**Completed:** Phase 1 (backend core) + Phase 2 (alerts + scheduling + Railway deploy) + Phase 3 (API + frontend dashboard)

---

## Absolute rules — never break these

- **Never commit secrets.** All credentials live in `.env`. Never hardcode them.
  Never log them, even partially.
- **Never skip error handling on exchange calls.** Exchanges fail constantly.
  Every ccxt call must handle NetworkError, ExchangeError, and RateLimitExceeded.
- **Never modify the database schema directly.** Use Alembic migrations exclusively.
  No raw ALTER TABLE, no editing models without a migration.
- **Never change the project structure** without updating this file first.
- **Never use synchronous I/O inside async functions.** Keep the async boundary clean.

---

## Branching model

- **dev** = development
- **main** = production (Railway)

Do not propose changes directly targeting main.
All changes must go through dev by Pull Request.

---

## Tech stack

### Backend (active)

| Layer              | Technology              | Notes                                   |
| ------------------ | ----------------------- | --------------------------------------- |
| Language           | Python 3.12+            | Type hints on every function            |
| Exchange connector | ccxt 4.x                | Unified API — Binance, Kraken, Coinbase |
| Indicators         | pandas-ta               | Built on pandas DataFrames              |
| ORM                | SQLAlchemy 2.x (async)  | Async session everywhere                |
| Migrations         | Alembic                 | Only way to touch the schema            |
| Scheduler          | APScheduler             | Drives fetch + screen cycles            |
| Alerts             | python-telegram-bot     | Async client, no blocking calls         |
| Config             | pydantic-settings       | Typed config loaded from .env           |
| API                | FastAPI + uvicorn       | REST API with API key auth              |
| Rate limiting      | slowapi                 | Per-IP limits on all endpoints          |
| Testing            | pytest + pytest-asyncio | 74 tests; real DB fixtures              |

### Infrastructure

| Layer     | Technology              |
| --------- | ----------------------- |
| Database  | PostgreSQL 15+          |
| Local dev | Docker + docker-compose |
| Deploy    | Railway (EU West)       |

### Frontend (complete)

| Layer      | Technology                        |
| ---------- | --------------------------------- |
| Framework  | Next.js 14 (App Router)           |
| Styling    | Tailwind CSS + shadcn/ui          |
| Charts     | TradingView Lightweight Charts v5 |
| Data fetch | SWR (auto-refresh every 30 s)     |

---

## Project structure

```
candle/
├── CLAUDE.md                    # This file — always read before doing anything
├── README.md
├── serve.py                     # Process entrypoint — scheduler or API mode
├── .env                         # Never commit
├── .env.example                 # Committed — all keys with placeholder values
├── docker-compose.yml           # PostgreSQL for local dev
├── pyproject.toml               # Single source of truth for deps and tooling
├── alembic.ini
│
├── candle/                      # Main Python package
│   ├── __init__.py
│   ├── config.py                # Single Settings instance via pydantic-settings
│   │
│   ├── data/                    # Fetching layer — talks to exchanges
│   │   ├── fetcher.py           # ccxt wrapper — fetch_ohlcv per exchange/pair
│   │   ├── normalizer.py        # Raw ccxt output → clean DataFrame
│   │   ├── exchange_factory.py  # Builds read-only exchange instances from config
│   │   └── bit2me.py            # Custom Bit2Me connector (not in ccxt)
│   │
│   ├── indicators/              # Pure functions. Input: DataFrame. Output: Series
│   │   ├── trend.py             # EMA, SMA, MACD
│   │   ├── momentum.py          # RSI, Stochastic
│   │   └── volume.py            # VWAP, OBV
│   │
│   ├── screener/                # Evaluation engine
│   │   ├── conditions.py        # Condition primitives (crossover, threshold, etc.)
│   │   ├── rules.py             # Rule dataclass — composes conditions with AND logic
│   │   └── engine.py            # Runs rules, builds alert messages with indicator values
│   │
│   ├── alerts/                  # Notification layer
│   │   └── telegram.py          # Formats and sends alert messages
│   │
│   ├── db/                      # Database layer
│   │   ├── models.py            # SQLAlchemy ORM models — data containers only
│   │   ├── session.py           # Async engine + session factory
│   │   └── repository.py        # All DB queries go here — no raw SQL elsewhere
│   │
│   ├── api/                     # REST API
│   │   ├── app.py               # FastAPI factory — routers, rate limiter, lifespan
│   │   ├── auth.py              # X-API-Key dependency (secrets.compare_digest)
│   │   ├── limiter.py           # Shared slowapi Limiter instance
│   │   ├── schemas.py           # Pydantic response models
│   │   └── routes/
│   │       ├── pairs.py         # GET /pairs, GET /pairs/{id}/candles
│   │       └── alerts.py        # GET /alerts
│   │
│   └── scheduler/               # Task orchestration
│       └── jobs.py              # APScheduler job definitions (fetch + screen cycles)
│
├── frontend/                    # Next.js 14 dashboard
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Dashboard — pair cards with live price/RSI
│       │   ├── api/candle/      # Server-side proxy with path/param whitelist
│       │   ├── alerts/          # Alert history table
│       │   └── pairs/[id]/      # Pair detail with candlestick chart
│       ├── components/
│       │   ├── chart/           # TradingView Lightweight Charts wrapper
│       │   ├── pairs/           # PairCard, PairsList
│       │   └── alerts/          # AlertsTable with category badges
│       └── lib/hooks/           # SWR hooks: usePairs, useCandles, useAlerts
│
├── migrations/                  # Alembic migration files
│   └── versions/
│
├── scripts/
│   ├── seed.py                  # Seeds exchanges and initial trading pairs
│   └── seed_pairs.py            # Adds pairs idempotently (get-or-create)
│
├── docs/
│   ├── technical/               # Backend code review, security audit
│   └── user-guide/              # End-user documentation
│
└── tests/
    ├── conftest.py              # Shared fixtures (test DB, mock exchange, etc.)
    ├── test_fetcher.py
    ├── test_indicators.py
    ├── test_screener.py
    ├── test_alerts.py
    └── test_api.py
```

---

## Database models (Phase 1)

```
User          id, email, hashed_password, telegram_chat_id, language, created_at
Exchange      id, name, slug (binance | kraken | coinbase)
TradingPair   id, exchange_id, symbol (BTC/USDT), timeframe (4h | 1d), active
Candle        id, pair_id, timestamp, open, high, low, close, volume
ScreenerRule  id, user_id, name, description, conditions (JSON), active
Alert         id, rule_id, pair_id, user_id, triggered_at, message, sent
```

- `User` is the owner of rules and alerts. Seed admin user (id=1) backfilled for existing rows.
- `Exchange`, `TradingPair`, `Candle` are global — market data is shared across users.
- `ScreenerRule` and `Alert` are per-user — alerts route to `user.telegram_chat_id`.

All timestamps are **UTC**. No exceptions.

---

## Supported exchanges

| Exchange | Slug       | Connector | Notes                                          |
| -------- | ---------- | --------- | ---------------------------------------------- |
| Binance  | `binance`  | ccxt      | Primary — deepest liquidity, USDT pairs        |
| Kraken   | `kraken`   | ccxt      | EU-friendly, reliable API                      |
| Coinbase | `coinbase` | ccxt      | US pairs, good for BTC/ETH                     |
| Bit2Me   | `bit2me`   | custom    | EUR/USDC pairs, 2 req/s limit, max 288 candles |

Exchange instances are **read-only**. API keys are optional for public OHLCV data.
Bit2Me uses a custom connector (`candle/data/bit2me.py`) since it is not supported by ccxt.
If keys are provided, they must only have read permissions.

---

## Supported timeframes

`1h` · `4h` · `1d`

Start with `4h` for swing screening. Anything below `1h` is out of scope for Phase 1.

---

## Screener conditions (Phase 1 primitives)

- `ema_crossover(fast, slow)` — fast EMA crosses above slow EMA
- `rsi_range(min, max)` — RSI within a given range
- `price_above_vwap()` — close above VWAP
- `volume_spike(multiplier)` — volume N× the rolling average

Conditions are composable with AND logic. OR logic comes in Phase 2.

---

## Environment variables

```bash
# .env.example

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/candle

# API
API_KEY=                         # Shared secret for X-API-Key header. Empty = auth disabled (local dev only)

# Exchanges (all optional for public OHLCV data)
BINANCE_API_KEY=
BINANCE_API_SECRET=
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
COINBASE_API_KEY=
COINBASE_API_SECRET=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=                    # market alerts — delivered to traders
TELEGRAM_ADMIN_CHAT_ID=              # operator alerts — job failures, heartbeats (can equal TELEGRAM_CHAT_ID in dev)

# Scheduler
FETCH_INTERVAL_MINUTES=60
SCREEN_INTERVAL_MINUTES=60
DEFAULT_TIMEFRAME=4h
ALERT_DEDUP_HOURS=4              # Suppress re-alerts for the same rule+pair within N hours
```

---

## Language conventions

- All code in English: variable names, function names, class names, comments
- All docstrings in English
- All log messages in English
- Commit messages in English following Conventional Commits:
  `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`
- README and internal technical docs in English
- CLAUDE.md can be updated in Spanish by the developer

## Coding conventions

- **Type hints on every function signature.** No bare `dict` — use TypedDict or Pydantic models.
- **Async by default** in data, db, and alerts layers. Sync only for pure indicator
  functions (CPU-bound, no I/O).
- **No business logic in models.** Models are data containers. Logic lives in
  repositories or services.
- **Repository pattern for all DB access.** No SQLAlchemy queries outside `db/repository.py`.
- **Indicators are pure functions.** Same input always produces same output. No side
  effects. No DB calls. No logging inside indicator functions.
- **One responsibility per module.** `fetcher.py` fetches. `normalizer.py` normalizes.
  They do not know about each other.
- **Fail loudly in development, fail gracefully in production.** Use environment-aware
  error handling via the config.

---

## What NOT to do — common mistakes to avoid

- Do not use `requests` or any sync HTTP library. Use ccxt's async client.
- Do not store raw ccxt responses in the database. Always normalize first.
- Do not compute indicators inside the fetcher. Keep layers strictly separate.
- Do not hardcode symbols or timeframes anywhere. They come from the DB or config.
- Do not send a Telegram message directly from the screener. Go through the alerts layer.
- Do not create a new DB session per query. Use the session factory from `db/session.py`.

---

## Development workflow

```bash
# Start local DB
docker-compose up -d postgres

# Apply migrations
alembic upgrade head

# Run tests
pytest

# Run scheduler (fetches + screens on interval)
python serve.py

# Run API server (development)
python serve.py --api
```

---

## Phase checklist

### Phase 1 — Backend core

- [x] Project scaffolding + pyproject.toml
- [x] Docker-compose with PostgreSQL
- [x] Config via pydantic-settings
- [x] ccxt exchange factory
- [x] OHLCV fetcher for Binance / Kraken / Coinbase
- [x] DataFrame normalizer
- [x] EMA, RSI, VWAP indicators
- [x] Alembic models + initial migration
- [x] Repository layer (save candles, read candles)
- [x] Screener engine with 2 working rules
- [x] pytest suite for indicators and screener

### Phase 2 — Alerts + scheduling

- [x] Telegram bot setup
- [x] Alert formatter and sender
- [x] APScheduler jobs wired to fetcher + screener
- [x] Alert persistence in DB
- [x] Deduplication (no re-alert for same condition within N hours)
- [x] Railway deploy (EU West, Dockerfile, alembic release command)

### Phase 3 — API + frontend

- [x] FastAPI router for pairs, candles, alerts
- [x] Authentication (API key, simple)
- [x] Next.js project scaffolding
- [x] Price chart with indicators overlay
- [x] Alert history view
- [x] Dashboard with live price, change %, RSI per pair
- [x] Rich alert messages with real indicator values
- [x] Deploy frontend to Railway

---

## v1.1 Roadmap

### Observabilidad

- [x] Structured logging (JSON) en backend para Railway Log Explorer
- [x] Alertas de scheduler caído — send_error_alert en fetch_job y screen_job

### Multi-user (seam)

- [x] User model con email, telegram_chat_id, language
- [x] user_id FK en ScreenerRule y Alert — reglas y alertas son por usuario
- [x] screen_job enruta alertas al telegram_chat_id del dueño de la regla
- [x] send_alert acepta chat_id explícito; fallback a TELEGRAM_CHAT_ID para modo single-user
- [ ] JWT auth + registro — diferido hasta tener un segundo usuario real
- [ ] Frontend login/signup — diferido
- [ ] Suscripciones de pares por usuario (tabla user_pairs) — diferido

### Refactor

- [x] Quick wins del `docs/refactor-report.md`: dead code eliminado, column names unificados, TelegramError re-export, seed scripts mergeados
- [x] Health check endpoint `GET /health`
- [x] Shared indicator computation (`candle/indicators/compute.py`)
- [x] Condition registry en `_build_rule`
- [x] Engine dispose en lifespan de FastAPI
- [x] Session URL resolution simplificada
- [x] Security headers middleware (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- [x] Request audit log middleware (client IP, method, path, status code)
- [ ] CORS middleware — diferido hasta tener clientes externos

### Frontend

- [ ] Mejorar diseño general del dashboard — layout, tipografía, dark mode consistente
- [ ] Página de configuración: gestionar pares activos (activar/desactivar) y reglas del screener (activar/desactivar, editar umbrales)

### Alertas Telegram enriquecidas

- [x] Mensajes estructurados: precio, RSI, VWAP, volumen, exchange, timestamp UTC

### Tests

- [ ] Tests E2E con Playwright — flujo completo: dashboard carga pares, pinchar par abre gráfico, tabla de alertas muestra entradas

---

## MCP servers in use

| MCP        | Purpose                                           |
| ---------- | ------------------------------------------------- |
| filesystem | Claude navigates and edits project files          |
| github     | PRs, commits, issue tracking from conversation    |
| postgresql | Claude queries the live dev DB during development |

---

## Testing rules

- Indicators must have at least 2 tests each: one happy path, one edge case
- Never call real exchange APIs in tests — use fixtures in `tests/fixtures/`
- Never use random data — fixtures must contain known signals with known outputs
- A fixture is a real OHLCV response downloaded once with ccxt and saved as CSV or JSON
- Integration tests use a separate test database (`DATABASE_URL_TEST` in `.env`)
- Repository tests run against a real PostgreSQL test instance, not SQLite
- Mock the Telegram client — verify it was called with the correct message, never send real messages in tests
- A test that only checks "no exception raised" is not a test

### Fixture strategy

```
tests/fixtures/
├── btc_4h_100.csv          # 100 real BTC/USDT 4h candles for indicator tests
├── btc_4h_crossover.csv    # Candles containing a known EMA crossover signal
├── btc_4h_overbought.csv   # Candles where RSI exceeds 70
└── raw_ccxt_binance.json   # Raw ccxt response saved once, used in normalizer tests
```

Generate fixtures once with a helper script (`scripts/generate_fixtures.py`).
Never regenerate them automatically — fixtures must be stable and committed to git.

---

## Open questions

- Authentication strategy if moving toward multi-user SaaS (current: single shared API key)
- Whether to use Supabase instead of raw PostgreSQL for easier auth
- Pricing model if monetizing

---

_Last updated: 2026-04-14 — removed all Polymarket code; repository now focused exclusively on alerting system_
