import os

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from app.config import Settings
from app.main import create_app


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 with PostgreSQL and Redis running",
)
def test_migrations_and_live_readiness() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    with TestClient(create_app(Settings())) as client:
        assert client.get("/readyz").status_code == 200
