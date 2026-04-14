# Security Fixes Applied — 2026-03-30

Fixes aplicados en respuesta a la auditoria de seguridad (`docs/security-audit.md`).

---

## Fix 1 — CRITICAL: Timing attack en API key comparison

**Archivo:** `candle/api/auth.py`

**Antes:**
```python
if api_key != settings.api_key:
```

**Despues:**
```python
import secrets
if not secrets.compare_digest(api_key or "", settings.api_key):
```

**Por que:** La comparacion directa de strings con `!=` cortocircuita en el primer caracter diferente. Un atacante puede medir el tiempo de respuesta para descubrir la key caracter a caracter. `secrets.compare_digest()` toma tiempo constante independientemente de donde diverjan los strings.

**Aprendizaje:** Nunca comparar secretos con `==` o `!=`. Siempre usar `secrets.compare_digest()` o `hmac.compare_digest()`.

---

## Fix 2 — HIGH: Rate limiting en la API

**Archivos:** `candle/api/limiter.py` (nuevo), `candle/api/app.py`, `candle/api/routes/pairs.py`, `candle/api/routes/alerts.py`, `pyproject.toml`

**Cambio:** Se instalo `slowapi` y se aplican limites por IP:

| Endpoint | Limite |
|----------|--------|
| GET /api/v1/pairs | 60 req/min |
| GET /api/v1/pairs/{id}/candles | 30 req/min |
| GET /api/v1/alerts | 60 req/min |

El endpoint de candles tiene limite mas bajo porque computa indicadores on-the-fly (CPU-bound).

**Problema encontrado:** Importar `limiter` desde `app.py` en las routes creaba un import circular (`app.py` importa routes, routes importan `app.py`). Solucion: extraer el `Limiter` a su propio modulo `candle/api/limiter.py`.

**Aprendizaje:** Objetos compartidos entre `app.py` y las routes deben vivir en un modulo independiente para evitar ciclos de import. Es un patron comun en FastAPI.

---

## Fix 3 — HIGH: SSRF/Open redirect en frontend proxy

**Archivo:** `frontend/src/app/api/candle/[...path]/route.ts`

**Antes:**
```typescript
const upstream = `${BASE_URL}/api/v1/${path.join("/")}${url.search}`;
```

**Despues:**
```typescript
const ALLOWED_PATH_PREFIXES = ["pairs", "alerts"];
const ALLOWED_PARAMS = ["limit", "since"];

// Reject unknown paths
if (!ALLOWED_PATH_PREFIXES.some((p) => pathStr.startsWith(p))) {
  return NextResponse.json({ detail: "Not found" }, { status: 404 });
}

// Only forward whitelisted params
const filtered = new URLSearchParams();
ALLOWED_PARAMS.forEach((param) => { ... });
```

**Por que:** Sin validacion, un atacante podia inyectar paths arbitrarios (`../../admin`) o query params maliciosos que el proxy reenviaba al backend con la API key del servidor.

**Aprendizaje:** Un proxy que reenvía requests con credenciales server-side es un vector SSRF clasico. Siempre hacer whitelist de paths y parametros permitidos.

---

## Fix 4 — HIGH: Credenciales de BD en logs

**Archivo:** `candle/db/session.py`

**Antes:**
```python
logger.info("Database URL built from PGHOST/PGUSER/PGPASSWORD/PGDATABASE")
```

**Despues:**
```python
logger.info("Database URL resolved (source: PG* env vars, host=%s)", host)
```

Los logs ahora solo indican el metodo de resolucion y el host (no sensible), sin mencionar password ni la URL completa.

**Aprendizaje:** Nunca loguear URLs de conexion que contengan credenciales. Si un stack trace expone la URL construida en memoria, la password queda en los logs del sistema.

---

## Fix 5 — Quick win: .gitignore para .env.local

**Archivo:** `.gitignore`

Se anadieron:
```
.env.local
.env*.local
frontend/.env.local
frontend/.env*.local
```

Previene que un `git add .` accidental commitee la API key de produccion.

---

## Estado de la auditoria

| # | Severidad | Fix | Estado |
|---|-----------|-----|--------|
| 1 | CRITICAL | Timing attack | Aplicado |
| 2 | HIGH | Rate limiting | Aplicado |
| 3 | HIGH | Proxy SSRF | Aplicado |
| 4 | HIGH | Logs de BD | Aplicado |
| 5 | MEDIUM | .gitignore | Aplicado |
| 6 | MEDIUM | CORS middleware | Pendiente |
| 7 | MEDIUM | Security headers | Pendiente |
| 8 | MEDIUM | Health check | Pendiente |
| 9 | MEDIUM | Audit log | Pendiente |

---

## Tests

74 tests pasan tras los cambios. Los tests de autenticacion existentes validan que `secrets.compare_digest` se comporta igual que la comparacion directa para los casos happy path y error.
