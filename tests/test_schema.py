from io import StringIO

from alembic.config import Config
from sqlalchemy import UniqueConstraint

from alembic import command
from app.db.base import Base
from app.db.models import Repository, ReviewRun


def test_all_foreign_keys_are_indexed() -> None:
    for table in Base.metadata.tables.values():
        indexed = {tuple(c.name for c in index.columns) for index in table.indexes}
        for foreign_key in table.foreign_keys:
            assert (foreign_key.parent.name,) in indexed


def test_idempotency_and_repository_uniqueness() -> None:
    for model, column in ((Repository, "github_repo_id"), (ReviewRun, "trigger_delivery_id")):
        assert any(
            isinstance(constraint, UniqueConstraint) and column in constraint.columns
            for constraint in model.__table__.constraints
        )


def test_migration_renders_postgres_upgrade_and_downgrade() -> None:
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    for table in Base.metadata.tables:
        assert f"CREATE TABLE {table}" in sql
    assert "JSONB" in sql
    assert "CREATE TYPE review_status" in sql
    output.seek(0)
    output.truncate()
    command.downgrade(config, "0001:base", sql=True)
    assert "DROP TABLE repositories" in output.getvalue()
    assert "DROP TYPE review_status" in output.getvalue()
