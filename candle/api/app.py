"""FastAPI application factory for the Candle REST API."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from candle.api.limiter import limiter
from candle.api.routes.alerts import router as alerts_router
from candle.api.routes.pairs import router as pairs_router
from candle.db.session import dispose_engine
from candle.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Candle API starting up")
    yield
    await dispose_engine()
    logger.info("Candle API shutting down")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns:
        A configured FastAPI instance with all routers registered under /api/v1.
    """
    setup_logging()
    app = FastAPI(
        title="Candle API",
        description="Crypto market screener — pairs, candles, and alert history",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        client = request.client.host if request.client else "unknown"
        logger.info(
            "api request",
            extra={
                "service": "api",
                "client": client,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            },
        )
        return response

    app.include_router(pairs_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")

    @app.get("/health", tags=["health"], include_in_schema=False)
    async def health() -> JSONResponse:
        """Health check for Railway and external monitors."""
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
