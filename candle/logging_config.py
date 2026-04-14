"""Structured JSON logging configuration for the Candle application.

Call setup_logging() once at process startup from each entrypoint (scheduler,
API server). All existing logger.info/warning/error calls automatically emit
JSON with any extra= kwargs promoted to top-level fields.

Railway captures stdout and makes JSON fields searchable in Log Explorer.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger to emit JSON to stdout.

    Clears any existing handlers to avoid duplicate output when called
    during tests or hot-reload scenarios.

    Args:
        level: Logging level for the root logger. Defaults to INFO.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Suppress noisy third-party loggers that clutter Railway logs.
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
