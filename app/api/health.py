import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "ready", "not_ready"]
    checks: dict[str, bool] | None = None


@router.get("/healthz", response_model=HealthResponse, response_model_exclude_none=True)
async def healthz() -> HealthResponse:
    """Process liveness; does not depend on external services."""
    return HealthResponse(status="ok")


async def check_database(request: Request) -> None:
    async with request.app.state.session_factory() as session:
        await session.execute(text("SELECT 1"))


async def check_redis(request: Request) -> None:
    await request.app.state.redis.ping()


async def probe(check: Callable[[Request], Awaitable[None]], request: Request) -> bool:
    try:
        async with asyncio.timeout(request.app.state.settings.health_check_timeout_seconds):
            await check(request)
        return True
    except Exception:
        return False


@router.get("/readyz", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def readyz(request: Request, response: Response) -> HealthResponse:
    """Readiness checks PostgreSQL and Redis within a bounded timeout."""
    database, redis = await asyncio.gather(
        probe(check_database, request), probe(check_redis, request)
    )
    ready = database and redis
    response.status_code = 200 if ready else 503
    return HealthResponse(
        status="ready" if ready else "not_ready", checks={"postgres": database, "redis": redis}
    )
