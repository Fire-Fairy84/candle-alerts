"""Entry point for the Candle scheduler.

Starts APScheduler with the fetch and screen jobs, then waits for SIGINT or
SIGTERM to shut down gracefully.

Usage:
    python scripts/run.py
"""

import asyncio
import logging
import signal

from candle.logging_config import setup_logging
from candle.scheduler.jobs import build_scheduler

setup_logging()

logger = logging.getLogger(__name__)


async def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Candle scheduler running. Press Ctrl+C to stop.")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await stop_event.wait()
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
