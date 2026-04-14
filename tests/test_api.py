"""Tests for the Candle REST API."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from candle.api.app import create_app
from candle.config import settings


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers(mocker) -> dict[str, str]:
    mocker.patch.object(settings, "api_key", "test-secret")
    return {"X-API-Key": "test-secret"}


@pytest.fixture
def mock_pair() -> MagicMock:
    exchange = MagicMock()
    exchange.id = 1
    exchange.name = "Binance"
    exchange.slug = "binance"

    pair = MagicMock()
    pair.id = 1
    pair.symbol = "BTC/USDT"
    pair.timeframe = "4h"
    pair.active = True
    pair.exchange = exchange
    return pair


class TestAuthentication:
    async def test_missing_key_returns_401(self, app, mocker):
        mocker.patch.object(settings, "api_key", "test-secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs")
        assert response.status_code == 401

    async def test_wrong_key_returns_401(self, app, mocker):
        mocker.patch.object(settings, "api_key", "test-secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    async def test_no_key_configured_allows_all(self, app, mocker):
        mocker.patch.object(settings, "api_key", "")
        mocker.patch("candle.api.routes.pairs.get_active_pairs", new=AsyncMock(return_value=[]))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs")
        assert response.status_code == 200


class TestListPairs:
    async def test_returns_pairs_and_count(self, app, auth_headers, mock_pair, mocker):
        mocker.patch("candle.api.routes.pairs.get_active_pairs", new=AsyncMock(return_value=[mock_pair]))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["pairs"][0]["symbol"] == "BTC/USDT"
        assert body["pairs"][0]["exchange"]["slug"] == "binance"

    async def test_empty_pairs_returns_count_zero(self, app, auth_headers, mocker):
        mocker.patch("candle.api.routes.pairs.get_active_pairs", new=AsyncMock(return_value=[]))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestGetPairCandles:
    async def test_candles_requires_api_key(self, app, mocker):
        """GET /pairs/{id}/candles without X-API-Key → 401."""
        mocker.patch.object(settings, "api_key", "test-secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles")
        assert response.status_code == 401

    async def test_invalid_limit_zero_returns_422(self, app, auth_headers, mocker):
        """limit=0 violates ge=1 → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles?limit=0", headers=auth_headers)
        assert response.status_code == 422

    async def test_invalid_limit_negative_returns_422(self, app, auth_headers, mocker):
        """limit=-1 violates ge=1 → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles?limit=-1", headers=auth_headers)
        assert response.status_code == 422

    async def test_invalid_limit_string_returns_422(self, app, auth_headers, mocker):
        """limit=abc is not an int → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles?limit=abc", headers=auth_headers)
        assert response.status_code == 422

    async def test_limit_over_max_returns_422(self, app, auth_headers, mocker):
        """limit=501 violates le=500 → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles?limit=501", headers=auth_headers)
        assert response.status_code == 422

    async def test_unknown_pair_returns_404(self, app, auth_headers, mocker):
        mocker.patch("candle.api.routes.pairs.get_pair_by_id", new=AsyncMock(return_value=None))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/9999/candles", headers=auth_headers)
        assert response.status_code == 404

    async def test_returns_candles_with_indicators(self, app, auth_headers, mock_pair, mocker):
        import pandas as pd

        df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, i + 1, tzinfo=timezone.utc) for i in range(30)],
            "open":   [float(50000 + i * 10) for i in range(30)],
            "high":   [float(50100 + i * 10) for i in range(30)],
            "low":    [float(49900 + i * 10) for i in range(30)],
            "close":  [float(50050 + i * 10) for i in range(30)],
            "volume": [float(100 + i) for i in range(30)],
        })
        mocker.patch("candle.api.routes.pairs.get_pair_by_id", new=AsyncMock(return_value=mock_pair))
        mocker.patch("candle.api.routes.pairs.get_candles", new=AsyncMock(return_value=df))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 30
        assert "indicators" in body["candles"][0]
        assert "ema_9" in body["candles"][0]["indicators"]

    async def test_indicators_are_null_for_insufficient_data(self, app, auth_headers, mock_pair, mocker):
        """EMA 200 requires 200 rows — with fewer rows it must return null, not error."""
        import pandas as pd

        df = pd.DataFrame({
            "timestamp": [datetime(2024, 1, 1, tzinfo=timezone.utc)],
            "open": [50000.0], "high": [50100.0], "low": [49900.0],
            "close": [50050.0], "volume": [100.0],
        })
        mocker.patch("candle.api.routes.pairs.get_pair_by_id", new=AsyncMock(return_value=mock_pair))
        mocker.patch("candle.api.routes.pairs.get_candles", new=AsyncMock(return_value=df))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/pairs/1/candles", headers=auth_headers)

        assert response.status_code == 200
        indicators = response.json()["candles"][0]["indicators"]
        assert indicators["ema_200"] is None

    async def test_limit_query_param_respected(self, app, auth_headers, mock_pair, mocker):
        import pandas as pd

        mock_get_candles = AsyncMock(return_value=pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        ))
        mocker.patch("candle.api.routes.pairs.get_pair_by_id", new=AsyncMock(return_value=mock_pair))
        mocker.patch("candle.api.routes.pairs.get_candles", new=mock_get_candles)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/v1/pairs/1/candles?limit=42", headers=auth_headers)

        mock_get_candles.assert_called_once()
        _, kwargs = mock_get_candles.call_args
        assert kwargs.get("limit") == 42 or mock_get_candles.call_args[0][2] == 42


class TestListAlerts:
    async def test_returns_alerts_with_flattened_fields(self, app, auth_headers, mock_pair, mocker):
        rule = MagicMock()
        rule.name = "EMA Crossover"

        alert = MagicMock()
        alert.id = 1
        alert.triggered_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        alert.message = "EMA 9 crossed above EMA 21"
        alert.sent = True
        alert.rule = rule
        alert.pair = mock_pair

        mocker.patch("candle.api.routes.alerts.get_recent_alerts", new=AsyncMock(return_value=[alert]))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        item = body["alerts"][0]
        assert item["rule_name"] == "EMA Crossover"
        assert item["symbol"] == "BTC/USDT"
        assert item["exchange_slug"] == "binance"
        assert item["sent"] is True

    async def test_empty_alerts_returns_count_zero(self, app, auth_headers, mocker):
        mocker.patch("candle.api.routes.alerts.get_recent_alerts", new=AsyncMock(return_value=[]))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_empty_alerts_response_shape(self, app, auth_headers, mocker):
        """Empty response must have exactly {alerts: [], count: 0}."""
        mocker.patch("candle.api.routes.alerts.get_recent_alerts", new=AsyncMock(return_value=[]))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts", headers=auth_headers)
        body = response.json()
        assert body == {"alerts": [], "count": 0}

    async def test_alerts_requires_api_key(self, app, mocker):
        """GET /alerts without X-API-Key → 401."""
        mocker.patch.object(settings, "api_key", "test-secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts")
        assert response.status_code == 401

    async def test_alerts_invalid_limit_returns_422(self, app, auth_headers, mocker):
        """limit=-5 violates ge=1 → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts?limit=-5", headers=auth_headers)
        assert response.status_code == 422

    async def test_alerts_limit_over_max_returns_422(self, app, auth_headers, mocker):
        """limit=201 violates le=200 → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/alerts?limit=201", headers=auth_headers)
        assert response.status_code == 422

    async def test_candles_default_limit_is_100(self, app, auth_headers, mock_pair, mocker):
        """When no limit param, the repository is called with limit=100."""
        import pandas as pd

        mock_get_candles = AsyncMock(return_value=pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        ))
        mocker.patch("candle.api.routes.pairs.get_pair_by_id", new=AsyncMock(return_value=mock_pair))
        mocker.patch("candle.api.routes.pairs.get_candles", new=mock_get_candles)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/api/v1/pairs/1/candles", headers=auth_headers)

        mock_get_candles.assert_called_once()
        _, kwargs = mock_get_candles.call_args
        assert kwargs.get("limit") == 100 or mock_get_candles.call_args[0][2] == 100
