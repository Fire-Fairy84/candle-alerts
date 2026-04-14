# Refactor Report — Candle

> Generated 2026-03-30. Based on the current state of the `main` branch.

---

## Quick Wins

1. **Remove unused `get_exchange_by_slug`** in `candle/db/repository.py` — defined but never called anywhere.
2. **Standardize RSI column name** — `jobs.py` uses `df["rsi"]`, `routes/pairs.py` uses `df["rsi_14"]`. Pick one.
3. **Standardize VWAP column name** — `jobs.py` uses `df["vwap"]`, `routes/pairs.py` uses `df["vwap_val"]`. Pick one.
4. **Remove `TelegramError` re-export** in `candle/alerts/telegram.py` — imported with `noqa: F401` but no caller uses it from this module.
5. **Add `/health` endpoint** to `candle/api/app.py` — Railway and monitoring tools expect it.

---

## Suggested Small Refactors

### Refactor 1 — Extract shared indicator computation

**Why:** EMA/RSI/VWAP computation is duplicated in `scheduler/jobs.py` (`_compute_indicators`) and `api/routes/pairs.py` (inline). If the indicator set changes, both must be updated.

**Files:** `candle/scheduler/jobs.py`, `candle/api/routes/pairs.py`

**Risk:** Low

**Change:** Move `_compute_indicators` to a shared location (e.g. `candle/indicators/compute.py`) and import from both places. Unify column names while at it:

```python
# candle/indicators/compute.py
INDICATOR_COLUMNS = {
    "ema_9", "ema_21", "ema_50", "ema_200", "rsi", "vwap",
}

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["ema_9"] = ema(df, 9)
    df["ema_21"] = ema(df, 21)
    df["ema_50"] = ema(df, 50)
    df["ema_200"] = ema(df, 200)
    df["rsi"] = rsi(df)
    df["vwap"] = vwap(df)
    return df
```

Then update `routes/pairs.py` to use `compute_indicators(df)` instead of inline calls, and reference `df["rsi"]` / `df["vwap"]` consistently.

**Why low-risk:** Pure extraction — same logic, just moved. Existing tests cover both paths.

---

### Refactor 2 — Condition registry instead of if/elif chain

**Why:** `_build_rule` in `jobs.py` uses an if/elif chain to map condition type strings to functions. Adding a new condition type requires modifying this function.

**Files:** `candle/scheduler/jobs.py`

**Risk:** Low

**Change:**

```python
from candle.screener.conditions import ema_crossover, rsi_range, price_above_vwap, volume_spike

CONDITION_REGISTRY: dict[str, Callable] = {
    "ema_crossover": ema_crossover,
    "rsi_range": rsi_range,
    "price_above_vwap": price_above_vwap,
    "volume_spike": volume_spike,
}

def _build_rule(db_rule: ScreenerRule) -> Rule:
    condition_fns = []
    for cond in db_rule.conditions:
        ctype = cond["type"]
        fn = CONDITION_REGISTRY.get(ctype)
        if fn is None:
            raise ValueError(f"unknown condition type: {ctype!r}")
        params = {k: v for k, v in cond.items() if k != "type"}
        condition_fns.append(partial(fn, **params))
    return Rule(name=db_rule.name, conditions=condition_fns)
```

**Why low-risk:** Same behavior, just structured differently. `test_jobs.py::TestBuildRule` already covers all paths.

---

### Refactor 3 — Break `screen_job` into smaller functions

**Why:** `screen_job` is 90 lines doing 6 distinct things: load data, build rules, compute indicators, run screener, deduplicate, send alerts. Hard to test in isolation.

**Files:** `candle/scheduler/jobs.py`

**Risk:** Low

**Change:** Extract `_screen_pair(pair, rules, dedup_window)` and `_process_match(match, db_rule, pair, dedup_window)` as separate async functions. `screen_job` becomes an orchestrator:

```python
async def screen_job() -> None:
    pairs, rules = await _load_pairs_and_rules()
    if not rules:
        return
    for pair in pairs:
        await _screen_pair(pair, rules, dedup_window)
```

**Why low-risk:** Pure extraction of existing logic into named functions. Easier to test each piece.

---

### Refactor 4 — Merge `seed.py` and `seed_pairs.py`

**Why:** Two seed scripts with nearly identical patterns. `seed_pairs.py` depends on the exchange created by `seed.py`. Should be one idempotent script.

**Files:** `scripts/seed.py`, `scripts/seed_pairs.py`

**Risk:** Low

**Change:** Add the new pairs to `seed.py` using a loop over a `PAIRS` list. Delete `seed_pairs.py`.

```python
PAIRS = [
    ("BTC/USDT", "4h"),
    ("ETH/USDT", "4h"),
    ("SOL/USDT", "4h"),
    ("BNB/USDT", "4h"),
    ("BTC/USDT", "1d"),
    ("ETH/USDT", "1d"),
]
```

**Why low-risk:** Both scripts use the same get-or-create pattern. Already idempotent.

---

### Refactor 5 — Move `_nan_to_none` to a utils module

**Why:** `_nan_to_none` is defined inline in `api/routes/pairs.py`. It's a generic utility that could be needed in other routes or serialization contexts.

**Files:** `candle/api/routes/pairs.py` → new `candle/utils.py`

**Risk:** Low

**Change:** Create `candle/utils.py` with:

```python
import math

def nan_to_none(value: float) -> float | None:
    return None if math.isnan(value) else value
```

**Why low-risk:** One function, one caller. Trivial move.

---

### Refactor 6 — Consolidate message templates with emoji mapping

**Why:** Alert message templates live in `candle/screener/engine.py` and emoji mapping lives in `candle/alerts/telegram.py`. Both use the same rule name keys and must be updated together when adding rules.

**Files:** `candle/screener/engine.py`, `candle/alerts/telegram.py`

**Risk:** Low

**Change:** Create a single `RULE_METADATA` dict in a shared location (e.g. `candle/screener/metadata.py`):

```python
RULE_METADATA: dict[str, RuleMeta] = {
    "RSI Oversold": RuleMeta(
        emoji="\U0001f4c9",
        template="RSI at {rsi:.1f} — entering oversold territory...",
        category="momentum",
    ),
    ...
}
```

Both engine and telegram import from this one source. Frontend category badges could also be derived from the `category` field via the API.

**Why low-risk:** Data consolidation, no logic change.

---

### Refactor 7 — Add `get_session` cleanup to FastAPI lifespan

**Why:** The `lifespan` context manager in `candle/api/app.py` logs startup/shutdown but doesn't dispose the database engine. Connections may leak on shutdown.

**Files:** `candle/api/app.py`, `candle/db/session.py`

**Risk:** Low

**Change:** Add engine disposal in the lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Candle API starting up")
    yield
    from candle.db.session import engine
    await engine.dispose()
    logger.info("Candle API shut down")
```

**Why low-risk:** Only runs at shutdown. No impact on running requests.

---

## Cleanup Opportunities After Deployment Fixes

1. **`candle/db/session.py` — lazy DB URL resolution.** The `_resolve_db_url()` function tries multiple environment variable names (`CANDLE_DB_URL`, `DATABASE_URL`, `DATABASE_PRIVATE_URL`, `DATABASE_PUBLIC_URL`). This was added during Railway deploy debugging. Now that the deploy is stable with `DATABASE_URL`, the fallback chain can be simplified to just `CANDLE_DB_URL` and `DATABASE_URL`.

2. **`railway.toml` — minimal config.** The `startCommand` was removed during debugging to allow per-service override in Railway dashboard. This is fine, but the file should document why it's missing (a comment would help future contributors).

3. **`docs/railway-deployment-report.md` — deleted but unstaged.** The file was deleted locally but the deletion hasn't been committed. Either commit the deletion or restore the file.

---

## Refactors I Would NOT Do Yet

| Refactor | Why wait |
|----------|----------|
| Replace `settings = Settings()` singleton with dependency injection | Touches every module. Do it when introducing a DI framework or multi-tenancy. |
| Split `jobs.py` into separate files per job | Only 2 jobs exist. Wait until there are 4+. |
| Move condition validation from pure functions to boundary layer | The current validation (KeyError, ValueError) is explicit and well-tested. Removing it adds fragility for minimal gain. |
| Add Pydantic validators to API schemas (enum for exchange slugs, etc.) | Low priority until multi-exchange or public API. |
| Replace `AsyncSessionFactory` naming with `get_async_session` | Would touch every file that uses it. Do it in a dedicated rename PR. |
| Abstract exchange credentials into a registry pattern | Only 3 exchanges supported. Premature until 5+. |

---

## Priority Order

If implementing incrementally, this order maximizes value with minimal risk:

1. Quick wins (15 minutes total)
2. Refactor 1 — shared indicator computation (eliminates the most impactful duplication)
3. Refactor 4 — merge seed scripts (simplest cleanup)
4. Refactor 2 — condition registry (prepares for adding new rule types)
5. Refactor 3 — break screen_job (improves testability)
6. Refactor 6 — consolidate rule metadata (single source of truth)
7. Refactor 5 — utils module (trivial)
8. Refactor 7 — lifespan cleanup (good practice)
