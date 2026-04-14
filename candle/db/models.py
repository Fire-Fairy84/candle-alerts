"""SQLAlchemy ORM models for the Candle application.

All timestamps are UTC. No business logic lives here — models are data containers.
Schema changes must go through Alembic migrations; never ALTER TABLE directly.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


class User(Base):
    """An operator or subscriber who owns screener rules and receives alerts."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    rules: Mapped[list["ScreenerRule"]] = relationship(back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user")


class Exchange(Base):
    """A supported cryptocurrency exchange."""

    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    pairs: Mapped[list["TradingPair"]] = relationship(back_populates="exchange")


class TradingPair(Base):
    """A trading pair on a specific exchange, with a fixed timeframe."""

    __tablename__ = "trading_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exchange: Mapped[Exchange] = relationship(back_populates="pairs")
    candles: Mapped[list["Candle"]] = relationship(back_populates="pair")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="pair")


class Candle(Base):
    """A single OHLCV candle for a trading pair."""

    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pair_id: Mapped[int] = mapped_column(ForeignKey("trading_pairs.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    pair: Mapped[TradingPair] = relationship(back_populates="candles")


class ScreenerRule(Base):
    """A configurable screener rule stored in the database."""

    __tablename__ = "screener_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dedup_hours: Mapped[int] = mapped_column(Integer, default=4, nullable=False)

    user: Mapped[User] = relationship(back_populates="rules")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="rule")


class Alert(Base):
    """An alert triggered by a screener rule on a trading pair."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("screener_rules.id"), nullable=False)
    pair_id: Mapped[int] = mapped_column(ForeignKey("trading_pairs.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rule: Mapped[ScreenerRule] = relationship(back_populates="alerts")
    pair: Mapped[TradingPair] = relationship(back_populates="alerts")
    user: Mapped[User] = relationship(back_populates="alerts")
