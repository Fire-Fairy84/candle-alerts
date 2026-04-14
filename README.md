# Candle

**Crypto market screener and alert system.**

Fetches OHLCV data from multiple exchanges on a schedule, computes technical indicators, evaluates configurable screening rules, and delivers alerts via Telegram. Includes a REST API and a Next.js dashboard.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Tests](https://img.shields.io/badge/tests-155%20passing-brightgreen)
![Deploy](https://img.shields.io/badge/deploy-Railway-blueviolet)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Why this project exists

Most crypto alert tools are black boxes: you configure a rule in a UI and hope it fires correctly. Candle's screening rules are explicit Python functions with real test fixtures — every condition is readable, testable, and version-controlled. The entire stack runs on infrastructure you control, with no dependency on third-party SaaS beyond the exchange APIs themselves.

---

## What it does

- **Fetches candle data** from Binance, Kraken, Coinbase, and Bit2Me every N minutes
- **Computes indicators** on each fetch cycle: EMA (9/21/50/200), RSI, VWAP
- **Screens for conditions**: EMA crossovers, RSI ranges, price vs VWAP, volume spikes
- **Deduplicates alerts**: the same rule won't fire twice for the same pair within a configurable window
- **Delivers alerts to Telegram** with rich messages that include real indicator values
- **Exposes a REST API** for pairs, candles (with indicators), and alert history
- **Dashboard** showing live price, change %, RSI per pair, and a candlestick chart with indicator overlays

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Scheduler (APScheduler)              │
│                                                             │
│   fetch_job (60 min)          screen_job (60 min)           │
│        │                             │                      │
│        ▼                             ▼                      │
│   Exchange APIs              Screener Engine                │
│  (ccxt — read only)          conditions.py / rules.py       │
│        │                             │                      │
│        ▼                             ▼                      │
│   Normalizer             ┌── RuleMatch ──┐                  │
│  (DataFrame)             │               │                  │
│        │              Alerts DB     Telegram Bot            │
│        ▼              (dedup)       (async send)            │
│   Candles DB                                                │
└─────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    FastAPI (REST)    │
                    │  /pairs             │
                    │  /pairs/{id}/candles│
                    │  /alerts            │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Next.js Dashboard  │
                    │  (SWR + TradingView │
                    │   Lightweight Charts│
                    └─────────────────────┘
```

Data flows in one direction: exchange → DB → screener → alert. The API and frontend are read-only consumers. No layer knows about the layer above it.

---

## How it works

**End-to-end example: EMA crossover on BTC/USDT 4h**

1. `fetch_job` runs at 20:00 UTC. It calls `ccxt.binance.fetch_ohlcv("BTC/USDT", "4h")`, normalizes the response into a DataFrame, and upserts the latest candle into `candles`.

2. `screen_job` runs immediately after. For every active pair, it loads the last N candles from the DB, computes EMA 9 and EMA 21, and evaluates the `EMA Crossover 9/21` rule: the previous candle had EMA 9 below EMA 21, the current candle has EMA 9 above.

3. The engine returns a `RuleMatch`. Before firing, it checks the `alerts` table — if the same rule fired on the same pair within the last 4 hours, it's skipped.

4. A new `Alert` row is persisted. The Telegram sender formats the message with the current close price, EMA values, and RSI, and calls `bot.send_message()`.

5. The alert arrives in Telegram within seconds of the 20:00 candle closing. No polling, no webhook — the scheduler drives everything.

---

## Tech stack

| Layer              | Technology                  | Notes                                          |
|--------------------|-----------------------------|------------------------------------------------|
| Language           | Python 3.12+                | Type hints on every function signature         |
| Exchange connector | ccxt 4.x                    | Unified API across Binance, Kraken, Coinbase   |
| Indicators         | pandas-ta                   | Pure functions on pandas DataFrames            |
| ORM                | SQLAlchemy 2.x (async)      | Async sessions throughout; no sync I/O         |
| Migrations         | Alembic                     | Schema changes via migrations only             |
| Scheduler          | APScheduler                 | Interval jobs for fetch and screen cycles      |
| Alerts             | python-telegram-bot         | Async client                                   |
| Config             | pydantic-settings           | Typed, validated config from `.env`            |
| API framework      | FastAPI + uvicorn           | Rate-limited, API key auth                     |
| Rate limiting      | slowapi                     | Per-IP limits; 30–60 req/min by endpoint       |
| Database           | PostgreSQL 15+              | All timestamps UTC                             |
| Frontend framework | Next.js 14 (App Router)     | Server components + API proxy route            |
| Styling            | Tailwind CSS + shadcn/ui    |                                                |
| Charts             | TradingView Lightweight Charts v5 | Candlestick + EMA/RSI overlays           |
| Data fetching      | SWR                         | Auto-refresh every 30 s                        |
| Deploy             | Railway                     | Separate services for scheduler and API        |
| Local dev          | Docker + docker-compose     | PostgreSQL only; app runs outside container    |
| Testing            | pytest + pytest-asyncio     | 74 tests; real DB fixtures, no mocks for DB    |

---

## Getting started

**Requirements:** Docker, Python 3.12+, Node 18+

```bash
# 1. Clone and install
git clone https://github.com/Fire-Fairy84/candle.git && cd candle
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Start PostgreSQL
docker-compose up -d postgres

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, API_KEY

# 4. Apply migrations and seed data
alembic upgrade head
python -m scripts.seed

# 5. Run scheduler (fetches + screens every 60 min)
python serve.py
```

Frontend (separate terminal):

```bash
cd frontend
npm install
cp .env.example .env.local   # set CANDLE_API_URL and CANDLE_API_KEY
npm run dev
```

Open `http://localhost:3000`.

---

## Configuration

All configuration is loaded from `.env` via pydantic-settings. Copy `.env.example` to get started.

| Variable                  | Required | Default | Description                                         |
|---------------------------|----------|---------|-----------------------------------------------------|
| `DATABASE_URL`            | Yes      | —       | PostgreSQL asyncpg URL                              |
| `API_KEY`                 | Yes (prod) | —     | Shared secret for `X-API-Key` header. Empty = auth disabled (local dev only) |
| `TELEGRAM_BOT_TOKEN`      | Yes      | —       | Bot token from @BotFather                           |
| `TELEGRAM_CHAT_ID`        | Yes      | —       | Target chat or user ID                              |
| `FETCH_INTERVAL_MINUTES`  | No       | `60`    | How often to pull new candles from exchanges        |
| `SCREEN_INTERVAL_MINUTES` | No       | `60`    | How often to run the screener                       |
| `ALERT_DEDUP_HOURS`       | No       | `4`     | Suppress re-alerts for the same rule+pair within N hours |
| `DEFAULT_TIMEFRAME`       | No       | `4h`    | Fallback timeframe when not specified               |
| `BINANCE_API_KEY`         | No       | —       | Optional — public OHLCV data works without keys     |
| `BINANCE_API_SECRET`      | No       | —       |                                                     |
| `KRAKEN_API_KEY`          | No       | —       |                                                     |
| `KRAKEN_API_SECRET`       | No       | —       |                                                     |

Exchange API keys are read-only. The application never places orders.

---

## API reference

All endpoints require `X-API-Key: <your-key>` header in production. Omit the header in local dev when `API_KEY` is unset.

Interactive docs available at `/docs` (Swagger UI) when the API is running.

### `GET /api/v1/pairs`

Returns all active trading pairs with their exchange.

Rate limit: 60 req/min per IP.

```bash
curl http://localhost:8000/api/v1/pairs \
  -H "X-API-Key: your-key"
```

```json
{
  "pairs": [
    {
      "id": 1,
      "symbol": "BTC/USDT",
      "timeframe": "4h",
      "active": true,
      "exchange": { "id": 1, "name": "Binance", "slug": "binance" }
    }
  ],
  "count": 1
}
```

---

### `GET /api/v1/pairs/{pair_id}/candles`

Returns candles for a pair with indicators computed on the fly. Indicators are `null` for leading rows where there is insufficient history (e.g. EMA 200 needs 200 candles).

Rate limit: 30 req/min per IP (CPU-bound indicator computation).

**Query params:**

| Param   | Type | Default | Range   |
|---------|------|---------|---------|
| `limit` | int  | `100`   | 1–500   |

```bash
curl "http://localhost:8000/api/v1/pairs/1/candles?limit=3" \
  -H "X-API-Key: your-key"
```

```json
{
  "pair_id": 1,
  "symbol": "BTC/USDT",
  "timeframe": "4h",
  "count": 3,
  "candles": [
    {
      "timestamp": "2026-03-29T20:00:00Z",
      "open": 82341.5,
      "high": 83100.0,
      "low": 82100.0,
      "close": 82900.0,
      "volume": 1245.8,
      "indicators": {
        "ema_9": 82750.3,
        "ema_21": 82100.1,
        "ema_50": 80500.0,
        "ema_200": null,
        "rsi": 58.4,
        "vwap": 82600.0
      }
    }
  ]
}
```

---

### `GET /api/v1/alerts`

Returns the most recent alerts, newest first.

Rate limit: 60 req/min per IP.

**Query params:**

| Param   | Type | Default | Range   |
|---------|------|---------|---------|
| `limit` | int  | `50`    | 1–200   |

```bash
curl "http://localhost:8000/api/v1/alerts?limit=2" \
  -H "X-API-Key: your-key"
```

```json
{
  "alerts": [
    {
      "id": 42,
      "triggered_at": "2026-03-30T14:00:00Z",
      "message": "RSI at 28.3 — entering oversold territory. Watch for a potential bounce.",
      "sent": true,
      "rule_name": "RSI Oversold",
      "symbol": "ETH/USDT",
      "timeframe": "4h",
      "exchange_slug": "binance"
    }
  ],
  "count": 1
}
```

---

### Errors

All error responses use this shape:

```json
{ "detail": "human-readable description" }
```

| Status | Cause                                                              |
|--------|--------------------------------------------------------------------|
| `401`  | `X-API-Key` header missing or does not match the configured key   |
| `422`  | Invalid query parameter (e.g. `limit=0`, `limit=abc`, `limit=501`) |
| `429`  | Rate limit exceeded for this IP on this endpoint                  |
| `500`  | Unhandled server error — check logs                               |

Example 401 response:

```json
{ "detail": "Invalid or missing API key" }
```

Example 422 response:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be greater than or equal to 1",
      "input": "0"
    }
  ]
}
```

---

## Security

A full audit is documented in [`docs/security-audit.md`](docs/security-audit.md). Controls currently in place:

- **Timing-safe API key comparison** — `secrets.compare_digest()` prevents timing attacks on the auth header
- **Rate limiting** — per-IP limits on all endpoints via slowapi (30–60 req/min)
- **Non-root Docker container** — `USER appuser` in the Dockerfile
- **Read-only exchange keys** — ccxt instances are initialized without trading permissions; the codebase has no order-placement functions
- **Secrets never logged** — DB connection URLs are sanitized before any log output; no credentials appear in stack traces
- **Proxy input validation** — the Next.js API proxy whitelists allowed path prefixes and query parameters before forwarding requests to the backend

---

## Project structure (by responsibility)

```
candle/
├── candle/                      # Main Python package
│   ├── config.py                # Owns all configuration — single Settings instance,
│   │                            #   validated at startup; the only place env vars are read
│   ├── data/                    # Responsible for exchange I/O only
│   │   ├── fetcher.py           # Asks ccxt for OHLCV data; handles NetworkError,
│   │   │                        #   ExchangeError, RateLimitExceeded on every call
│   │   ├── normalizer.py        # Converts raw ccxt lists to a typed DataFrame;
│   │   │                        #   knows nothing about the DB or indicators
│   │   └── exchange_factory.py  # Constructs read-only ccxt instances from config;
│   │                            #   no trading permissions, no API keys required
│   ├── indicators/              # Pure computation — no I/O, no DB, no logging
│   │   ├── trend.py             # EMA, SMA, MACD — same input always returns same output
│   │   ├── momentum.py          # RSI, Stochastic
│   │   └── volume.py            # VWAP, OBV
│   ├── screener/                # Responsible for deciding whether conditions are met
│   │   ├── conditions.py        # Atomic condition primitives — each returns a bool
│   │   ├── rules.py             # Rule dataclass — composes conditions with AND logic;
│   │   │                        #   adding a rule is adding a Rule() instance here
│   │   └── engine.py            # Iterates rules over DataFrames; builds the human-readable
│   │                            #   alert message using real indicator values
│   ├── alerts/                  # Responsible for notification delivery only
│   │   └── telegram.py          # Formats messages with emoji + context;
│   │                            #   never called directly from the screener
│   ├── db/                      # Responsible for persistence
│   │   ├── models.py            # ORM models — data containers only, no business logic
│   │   ├── session.py           # Async engine factory; sanitizes credentials from logs
│   │   └── repository.py        # Every DB query lives here — no SQLAlchemy outside
│   │                            #   this module, no raw SQL anywhere in the codebase
│   ├── api/                     # Responsible for the HTTP interface
│   │   ├── app.py               # FastAPI factory — wires routers, rate limiter, lifespan
│   │   ├── auth.py              # X-API-Key validation using secrets.compare_digest;
│   │   │                        #   auth is skipped when API_KEY is unset (local dev)
│   │   ├── limiter.py           # Shared Limiter instance — extracted to avoid circular
│   │   │                        #   imports between app.py and route modules
│   │   ├── schemas.py           # Pydantic response models — the contract for API consumers
│   │   └── routes/
│   │       ├── pairs.py         # /pairs and /pairs/{id}/candles — computes indicators
│   │       │                    #   on the fly; rate-limited at 60 and 30 req/min
│   │       └── alerts.py        # /alerts — read-only alert history; 60 req/min
│   └── scheduler/
│       └── jobs.py              # Owns the fetch → screen → alert cycle timing;
│                                #   the only place APScheduler is configured
│
├── frontend/                    # Next.js 14 dashboard
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Dashboard — pair grid with live price, change %, RSI
│       │   ├── api/candle/      # Server-side proxy — validates paths and params before
│       │   │                    #   forwarding to the backend with the server API key
│       │   ├── alerts/          # Alert history with category badges and relative timestamps
│       │   └── pairs/[id]/      # Pair detail — candlestick chart with EMA overlays
│       ├── components/
│       │   ├── chart/           # TradingView Lightweight Charts v5 wrapper;
│       │   │                    #   handles mount race condition and cleanup
│       │   ├── pairs/           # PairCard (live data via SWR), PairsList
│       │   └── alerts/          # AlertsTable — rule category color coding
│       └── lib/hooks/           # SWR data hooks — usePairs, useCandles, useAlerts;
│                                #   all poll every 30 s
│
├── migrations/                  # Alembic migration history — the only way to change schema
├── tests/                       # 74 tests across indicators, screener, API, alerts
│   └── fixtures/                # Real OHLCV CSVs downloaded once; stable, never regenerated
├── scripts/
│   ├── seed.py                  # One-time setup: creates exchanges and initial pairs
│   └── seed_pairs.py            # Idempotent: adds new pairs without duplicating existing
├── docs/
│   ├── refactor-report.md       # Prioritized backend refactor opportunities
│   └── security-audit.md        # Pre-production security review with 18 findings
├── serve.py                     # Process entrypoint — selects scheduler or API mode
├── docker-compose.yml           # PostgreSQL for local dev; app runs outside the container
└── pyproject.toml               # Deps, build config, pytest settings — single source of truth
```

---

## Database schema

```
User          id, email, hashed_password, telegram_chat_id, language, created_at
Exchange      id, name, slug
TradingPair   id, exchange_id, symbol, timeframe, active
Candle        id, pair_id, timestamp, open, high, low, close, volume
ScreenerRule  id, user_id, name, description, conditions (JSON), active
Alert         id, rule_id, pair_id, user_id, triggered_at, message, sent
```

`Exchange`, `TradingPair`, and `Candle` are global — market data is shared. `ScreenerRule` and `Alert` are per-user: each rule belongs to a user and alerts route to that user's Telegram chat. All timestamps are UTC. Schema changes go through Alembic migrations exclusively — no `ALTER TABLE` directly.

---

## Roadmap

### v1.0 — complete

- [x] OHLCV fetcher for Binance, Kraken, Coinbase (read-only)
- [x] EMA, RSI, VWAP indicators with real-data fixtures
- [x] Composable screener rules with AND logic
- [x] Telegram alerts with deduplication
- [x] APScheduler fetch + screen cycles
- [x] Railway deploy (EU West)
- [x] REST API with rate limiting and API key auth
- [x] Next.js dashboard with candlestick chart and alert history
- [x] Security hardened: timing-safe auth, proxy input validation, sanitized logs

### v1.1 — planned

- [ ] Deploy frontend to Railway
- [ ] CORS and security headers middleware
- [ ] Health check endpoint
- [ ] OR logic for screener conditions
- [ ] Webhook support as an alternative to Telegram
- [ ] Per-rule alert thresholds configurable via API

---

## License

MIT
