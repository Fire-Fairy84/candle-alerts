"""Pydantic response schemas for the Candle REST API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExchangeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class TradingPairSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    active: bool
    exchange: ExchangeSchema


class IndicatorsSchema(BaseModel):
    ema_9: float | None
    ema_21: float | None
    ema_50: float | None
    ema_200: float | None
    rsi: float | None
    vwap: float | None


class CandleSchema(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    indicators: IndicatorsSchema


class PairsResponse(BaseModel):
    pairs: list[TradingPairSchema]
    count: int


class CandlesResponse(BaseModel):
    pair_id: int
    symbol: str
    timeframe: str
    candles: list[CandleSchema]
    count: int


class AlertSchema(BaseModel):
    id: int
    triggered_at: datetime
    message: str
    sent: bool
    rule_name: str
    symbol: str
    timeframe: str
    exchange_slug: str


class AlertsResponse(BaseModel):
    alerts: list[AlertSchema]
    count: int
