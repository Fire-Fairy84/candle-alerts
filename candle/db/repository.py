"""Repository — all database queries for the Candle application.

No SQLAlchemy queries exist outside this module. Business logic must not live here;
repositories only translate between domain objects and database rows.
"""

from datetime import datetime

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from candle.db.models import Alert, Candle, ScreenerRule, TradingPair, User


async def get_active_pairs(session: AsyncSession) -> list[TradingPair]:
    """Return all active TradingPairs with their exchanges eagerly loaded.

    Args:
        session: Active async database session.

    Returns:
        List of active TradingPair instances, each with .exchange populated.
    """
    result = await session.execute(
        select(TradingPair)
        .where(TradingPair.active.is_(True))
        .options(joinedload(TradingPair.exchange))
    )
    return list(result.scalars().all())


async def save_candles(
    session: AsyncSession,
    pair_id: int,
    df: pd.DataFrame,
) -> int:
    """Upsert OHLCV candles from a DataFrame into the database.

    Uses INSERT ... ON CONFLICT (pair_id, timestamp) DO NOTHING so that
    re-fetching the same candles is always safe.

    Args:
        session: Active async database session.
        pair_id: ID of the TradingPair these candles belong to.
        df: Normalized DataFrame with columns [timestamp, open, high, low, close, volume].

    Returns:
        Number of new rows inserted (0 if all already existed).
    """
    if df.empty:
        return 0

    rows = [
        {
            "pair_id": pair_id,
            "timestamp": row.timestamp,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        }
        for row in df.itertuples(index=False)
    ]

    stmt = pg_insert(Candle).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["pair_id", "timestamp"])
    result = await session.execute(stmt)
    return result.rowcount


async def get_candles(
    session: AsyncSession,
    pair_id: int,
    limit: int = 500,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Fetch candles for a pair from the database as a DataFrame.

    Args:
        session: Active async database session.
        pair_id: ID of the TradingPair to fetch candles for.
        limit: Maximum number of candles to return. Defaults to 500.
        since: If provided, only return candles at or after this UTC datetime.

    Returns:
        DataFrame with columns [timestamp, open, high, low, close, volume],
        sorted ascending by timestamp. Empty DataFrame if no rows found.
    """
    query = (
        select(
            Candle.timestamp,
            Candle.open,
            Candle.high,
            Candle.low,
            Candle.close,
            Candle.volume,
        )
        .where(Candle.pair_id == pair_id)
        .order_by(Candle.timestamp.desc())
        .limit(limit)
    )

    if since is not None:
        query = query.where(Candle.timestamp >= since)

    result = await session.execute(query)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df.sort_values("timestamp").reset_index(drop=True)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Return a User by primary key, or None if not found.

    Args:
        session: Active async database session.
        user_id: Primary key of the User.

    Returns:
        The User instance, or None.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def save_alert(
    session: AsyncSession,
    rule_id: int,
    pair_id: int,
    user_id: int,
    triggered_at: datetime,
    message: str,
) -> Alert:
    """Persist a new Alert record and return it.

    Args:
        session: Active async database session.
        rule_id: ID of the ScreenerRule that triggered.
        pair_id: ID of the TradingPair that triggered the rule.
        user_id: ID of the User who owns the rule.
        triggered_at: UTC datetime when the rule fired.
        message: Human-readable alert description.

    Returns:
        The newly created Alert instance (unsent).
    """
    alert = Alert(
        rule_id=rule_id,
        pair_id=pair_id,
        user_id=user_id,
        triggered_at=triggered_at,
        message=message,
        sent=False,
    )
    session.add(alert)
    await session.flush()  # populate alert.id without committing the outer transaction
    return alert


async def get_active_rules(session: AsyncSession) -> list[ScreenerRule]:
    """Return all active ScreenerRule records with their owner eagerly loaded.

    Args:
        session: Active async database session.

    Returns:
        List of active ScreenerRule instances, each with .user populated.
    """
    result = await session.execute(
        select(ScreenerRule)
        .where(ScreenerRule.active.is_(True))
        .options(joinedload(ScreenerRule.user))
    )
    return list(result.scalars().all())


async def get_recent_alert(
    session: AsyncSession,
    rule_id: int,
    pair_id: int,
    since: datetime,
) -> Alert | None:
    """Return the most recent alert for a rule/pair combination, if any exists since `since`.

    Used for deduplication: before firing a new alert, check whether the same
    rule already triggered on the same pair within the deduplication window.

    Args:
        session: Active async database session.
        rule_id: ID of the ScreenerRule to check.
        pair_id: ID of the TradingPair to check.
        since: Only consider alerts triggered at or after this UTC datetime.

    Returns:
        The most recent matching Alert, or None if no alert exists in the window.
    """
    result = await session.execute(
        select(Alert)
        .where(
            Alert.rule_id == rule_id,
            Alert.pair_id == pair_id,
            Alert.triggered_at >= since,
        )
        .order_by(Alert.triggered_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_pair_by_id(
    session: AsyncSession,
    pair_id: int,
) -> TradingPair | None:
    """Return a TradingPair by primary key with its exchange eagerly loaded, or None.

    Args:
        session: Active async database session.
        pair_id: Primary key of the TradingPair.

    Returns:
        The TradingPair instance with .exchange populated, or None if not found.
    """
    result = await session.execute(
        select(TradingPair)
        .where(TradingPair.id == pair_id)
        .options(joinedload(TradingPair.exchange))
    )
    return result.scalar_one_or_none()


async def get_recent_alerts(
    session: AsyncSession,
    limit: int = 50,
) -> list[Alert]:
    """Return the most recent Alert records, newest first, with rule and pair loaded.

    Args:
        session: Active async database session.
        limit: Maximum number of alerts to return. Defaults to 50.

    Returns:
        List of Alert instances with .rule and .pair.exchange populated.
    """
    result = await session.execute(
        select(Alert)
        .options(
            joinedload(Alert.rule),
            joinedload(Alert.pair).joinedload(TradingPair.exchange),
        )
        .order_by(Alert.triggered_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_alert_sent(session: AsyncSession, alert_id: int) -> None:
    """Mark an alert as sent after successful Telegram delivery.

    Args:
        session: Active async database session.
        alert_id: ID of the Alert to mark as sent.
    """
    await session.execute(
        update(Alert).where(Alert.id == alert_id).values(sent=True)
    )
