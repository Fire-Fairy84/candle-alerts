"""Routes for trading pairs and their candles."""

import math  # used by _nan_to_none

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from candle.api.limiter import limiter
from candle.api.auth import require_api_key
from candle.api.schemas import (
    CandleSchema,
    CandlesResponse,
    IndicatorsSchema,
    PairsResponse,
    TradingPairSchema,
)
from candle.db.repository import get_active_pairs, get_candles, get_pair_by_id
from candle.db.session import get_session
from candle.indicators.compute import compute_indicators

router = APIRouter(prefix="/pairs", tags=["pairs"])


def _nan_to_none(value: float) -> float | None:
    return None if math.isnan(value) else value


@router.get("", response_model=PairsResponse, dependencies=[Depends(require_api_key)])
@limiter.limit("60/minute")
async def list_pairs(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> PairsResponse:
    """Return all active trading pairs with their exchange."""
    pairs = await get_active_pairs(session)
    return PairsResponse(
        pairs=[TradingPairSchema.model_validate(p) for p in pairs],
        count=len(pairs),
    )


@router.get(
    "/{pair_id}/candles",
    response_model=CandlesResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def get_pair_candles(
    request: Request,
    pair_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> CandlesResponse:
    """Return candles for a trading pair with indicators computed on the fly.

    Indicators are NaN for the first rows where there is insufficient history
    (e.g. EMA 200 needs at least 200 candles). These are returned as null.
    """
    pair = await get_pair_by_id(session, pair_id)
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pair not found")

    df = await get_candles(session, pair_id, limit=limit)

    candles: list[CandleSchema] = []
    if not df.empty:
        compute_indicators(df)

        for row in df.itertuples(index=False):
            candles.append(
                CandleSchema(
                    timestamp=row.timestamp,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                    indicators=IndicatorsSchema(
                        ema_9=_nan_to_none(row.ema_9),
                        ema_21=_nan_to_none(row.ema_21),
                        ema_50=_nan_to_none(row.ema_50),
                        ema_200=_nan_to_none(row.ema_200),
                        rsi=_nan_to_none(row.rsi),
                        vwap=_nan_to_none(row.vwap),
                    ),
                )
            )

    return CandlesResponse(
        pair_id=pair_id,
        symbol=pair.symbol,
        timeframe=pair.timeframe,
        candles=candles,
        count=len(candles),
    )
