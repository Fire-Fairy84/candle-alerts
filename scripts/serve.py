"""Entry point for the Candle REST API.

Starts uvicorn serving the FastAPI application on the port provided by the
environment (Railway injects $PORT automatically).

Usage:
    python scripts/serve.py
"""

import logging
import os

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "candle.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
