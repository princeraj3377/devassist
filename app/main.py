from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.health import router as health_router
from app.config import Settings, get_settings
from app.core.logging import RequestIDMiddleware, configure_logging
from app.db.session import create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(config.log_level)
        factory = create_session_factory(config)
        redis = Redis.from_url(
            config.redis_url.get_secret_value(),
            socket_connect_timeout=config.health_check_timeout_seconds,
            socket_timeout=config.health_check_timeout_seconds,
            decode_responses=True,
        )
        app.state.session_factory = factory
        app.state.redis = redis
        try:
            yield
        finally:
            try:
                await redis.aclose()
            finally:
                engine = factory.kw["bind"]
                assert isinstance(engine, AsyncEngine)
                await engine.dispose()

    app = FastAPI(title="DevAssist", version="0.1.0", lifespan=lifespan)
    app.state.settings = config
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    return app
