# Security Audit — Candle MVP

> 2026-03-30. Revision pre-produccion del proyecto Candle.

---

## Hallazgos que requieren accion inmediata

### 1. CRITICAL — Comparacion de API key vulnerable a timing attack

**Archivo:** `candle/api/auth.py:28`

```python
if api_key != settings.api_key:
```

La comparacion directa con `!=` permite que un atacante mida el tiempo de respuesta para descubrir la key caracter a caracter.

**Fix:**

```python
import secrets

if not secrets.compare_digest(api_key or "", settings.api_key):
    raise HTTPException(...)
```

---

### 2. HIGH — Sin rate limiting en la API

**Archivo:** `candle/api/app.py`

No hay rate limiting en ningun endpoint. Un atacante puede:
- Fuerza bruta contra la API key
- DoS con requests masivos a `/pairs/{id}/candles?limit=500` (computa indicadores on-the-fly)

**Fix:** Instalar `slowapi`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@router.get("/pairs")
@limiter.limit("60/minute")
async def list_pairs(request: Request, ...):
```

---

### 3. HIGH — Frontend proxy pasa query params sin validar (SSRF potencial)

**Archivo:** `frontend/src/app/api/candle/[...path]/route.ts:12`

```typescript
const upstream = `${BASE_URL}/api/v1/${path.join("/")}${url.search}`;
```

`path` y `url.search` se pasan sin filtrar. Un atacante podria inyectar path segments o query params maliciosos.

**Fix:**

```typescript
const ALLOWED_PATHS = ["pairs", "alerts"];
const ALLOWED_PARAMS = ["limit", "since"];

const pathStr = path.join("/");
if (!ALLOWED_PATHS.some((p) => pathStr.startsWith(p))) {
  return NextResponse.json({ detail: "Not found" }, { status: 404 });
}

const filtered = new URLSearchParams();
ALLOWED_PARAMS.forEach((param) => {
  const value = url.searchParams.get(param);
  if (value) filtered.set(param, value);
});

const upstream = `${BASE_URL}/api/v1/${pathStr}?${filtered.toString()}`;
```

---

### 4. HIGH — Credenciales de BD en la URL construida y logueada

**Archivo:** `candle/db/session.py:62`

```python
return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
```

Si se produce un error despues de esta linea, el stack trace mostraria la URL con la password. Ademas, `echo=not settings.is_production` en linea 79 vuelca SQL completo a los logs en desarrollo.

**Fix:**

```python
# No loguear el metodo de construccion con variables de password
logger.info("Database URL resolved from PG* environment variables")

# Asegurar que echo=False en produccion (ya lo hace, pero verificar)
echo=False if settings.is_production else True
```

---

## Hallazgos de severidad media

### 5. MEDIUM — Sin configuracion CORS explicita

**Archivo:** `candle/api/app.py`

No hay CORS middleware. Si alguien expone la API directamente (sin el proxy de Next.js), cualquier origen puede hacer requests.

**Fix:**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)
```

---

### 6. MEDIUM — Sin headers de seguridad HTTP

**Archivo:** `candle/api/app.py`

Faltan headers estandar de seguridad en las respuestas.

**Fix:**

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

### 7. MEDIUM — Sin endpoint de health check

**Archivo:** `candle/api/app.py`

Railway y cualquier monitor necesita un endpoint de salud.

**Fix:**

```python
@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}
```

---

### 8. MEDIUM — Sin audit log de requests

**Archivo:** `candle/api/app.py`

No hay registro de quien accede a que endpoint. No se puede investigar un incidente.

**Fix:** Middleware de logging basico:

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("%s %s %s", request.client.host, request.method, request.url.path)
    response = await call_next(request)
    return response
```

---

### 9. MEDIUM — Frontend .env.local sin proteccion en .gitignore

**Archivo:** `.gitignore`

`.env.local` no esta en `.gitignore`. Actualmente no esta trackeado, pero un `git add .` accidental lo commitearía con la API key de produccion dentro.

**Fix:** Anadir a `.gitignore`:

```
# Frontend secrets
frontend/.env.local
frontend/.env*.local
```

---

## Hallazgos de severidad baja

### 10. LOW — API key en plaintext sin rotacion

La API key es un string fijo sin expiracion, sin versionado, sin hashing. Aceptable para MVP, pero antes de multi-usuario necesita key management real.

### 11. LOW — Exchange API keys sin cifrar en env vars

Las keys de Binance/Kraken/Coinbase estan en texto plano en variables de entorno. Son read-only (verificado en `exchange_factory.py`), pero un leak expondria datos de mercado privados.

### 12. LOW — Telegram bot token sin validacion al arrancar

`candle/alerts/telegram.py` crea el `Bot(token=...)` en cada envio. Si el token esta vacio, silenciosamente no envia. Mejor validar al arrancar.

---

## Lo que esta BIEN

| Area | Estado |
|------|--------|
| SQL injection | Protegido — SQLAlchemy ORM con queries parametrizadas, sin raw SQL |
| Async boundary | Limpio — sin I/O sincrono en funciones async |
| Container non-root | Si — `USER appuser` en Dockerfile |
| Exchange read-only | Verificado — no hay funciones de orden, solo `fetch_ohlcv` |
| .env no commiteado | Correcto — `.env` y `*.env` en `.gitignore` |
| Input validation FastAPI | Presente — `ge=1`, `le=500` en parametros de query |
| Secretos en responses | No se filtran — los endpoints solo devuelven datos de mercado |

---

## Prioridad de implementacion

| # | Severidad | Fix | Esfuerzo |
|---|-----------|-----|----------|
| 1 | CRITICAL | `secrets.compare_digest` en auth.py | 5 min |
| 9 | MEDIUM | Anadir .env.local a .gitignore | 1 min |
| 2 | HIGH | Rate limiting con slowapi | 30 min |
| 3 | HIGH | Whitelist de paths/params en proxy | 15 min |
| 4 | HIGH | Limpiar logs de credenciales DB | 10 min |
| 5 | MEDIUM | CORS middleware | 10 min |
| 6 | MEDIUM | Security headers | 5 min |
| 7 | MEDIUM | Health check endpoint | 5 min |
| 8 | MEDIUM | Request logging | 10 min |
