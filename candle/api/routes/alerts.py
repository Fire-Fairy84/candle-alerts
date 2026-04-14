"""Routes for alert history."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from candle.api.limiter import limiter
from candle.api.auth import require_api_key
from candle.api.schemas import AlertSchema, AlertsResponse
from candle.db.repository import get_recent_alerts
from candle.db.session import get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsResponse, dependencies=[Depends(require_api_key)])
@limiter.limit("60/minute")
async def list_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> AlertsResponse:
    """Return the most recent alerts, newest first."""
    alerts = await get_recent_alerts(session, limit=limit)
    schemas = [
        AlertSchema(
            id=alert.id,
            triggered_at=alert.triggered_at,
            message=alert.message,
            sent=alert.sent,
            rule_name=alert.rule.name,
            symbol=alert.pair.symbol,
            timeframe=alert.pair.timeframe,
            exchange_slug=alert.pair.exchange.slug,
        )
        for alert in alerts
    ]
    return AlertsResponse(alerts=schemas, count=len(schemas))
