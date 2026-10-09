from unittest.mock import AsyncMock

from arq.worker import create_worker

from app.worker.settings import WorkerSettings, heartbeat


async def test_worker_settings_construct_without_connecting() -> None:
    worker = create_worker(WorkerSettings, handle_signals=False)
    assert "cron:heartbeat" in worker.functions


async def test_heartbeat_checks_redis() -> None:
    redis = AsyncMock()
    await heartbeat({"redis": redis})
    redis.ping.assert_awaited_once()
