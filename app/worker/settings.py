import asyncio
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings
from arq.cron import CronJob

from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)


async def heartbeat(ctx: dict[str, Any]) -> None:
    """Keep the foundation worker operational before review jobs are added."""
    async with asyncio.timeout(settings.health_check_timeout_seconds):
        await ctx["redis"].ping()


class WorkerSettings:
    # ARQ requires at least one function or cron job. Review jobs arrive in phase 7.
    cron_jobs: ClassVar[list[CronJob]] = [cron(heartbeat, second=0, run_at_startup=True)]
    redis_settings = RedisSettings.from_dsn(settings.redis_url.get_secret_value())
    job_timeout = 300
    health_check_interval = 30
