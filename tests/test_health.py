import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(Settings(_env_file=None, environment="test"))
    with TestClient(app) as test_client:
        session = AsyncMock()
        context = AsyncMock()
        context.__aenter__.return_value = session
        app.state.session_factory = MagicMock(return_value=context)
        app.state.redis = AsyncMock()
        yield test_client


def test_liveness_without_dependencies(client: TestClient) -> None:
    client.app.state.session_factory.side_effect = RuntimeError("database unavailable")
    client.app.state.redis.ping.side_effect = RuntimeError("redis unavailable")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_healthy(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"postgres": True, "redis": True}}


@pytest.mark.parametrize("dependency", ["postgres", "redis", "both"])
def test_readiness_unavailable(client: TestClient, dependency: str) -> None:
    secret = "secret-connection-string"
    if dependency in ("postgres", "both"):
        client.app.state.session_factory.side_effect = RuntimeError(secret)
    if dependency in ("redis", "both"):
        client.app.state.redis.ping.side_effect = RuntimeError(secret)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"postgres": dependency == "redis", "redis": dependency == "postgres"},
    }
    assert secret not in response.text


def test_readiness_timeout(client: TestClient) -> None:
    async def slow_ping() -> None:
        await asyncio.sleep(10)

    client.app.state.settings.health_check_timeout_seconds = 0.01
    client.app.state.redis.ping.side_effect = slow_ping
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"] == {"postgres": True, "redis": False}


def test_request_ids(client: TestClient) -> None:
    first = client.get("/healthz")
    second = client.get("/healthz")
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert (
        client.get("/healthz", headers={"x-request-id": "test-123"}).headers["x-request-id"]
        == "test-123"
    )
    assert (
        client.get("/healthz", headers={"x-request-id": "bad value"}).headers["x-request-id"]
        != "bad value"
    )


def test_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/healthz" in schema["paths"]
    assert "503" in schema["paths"]["/readyz"]["get"]["responses"]
