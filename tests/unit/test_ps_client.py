"""Unit tests for PSClient lifecycle and pool delegation behavior."""

from unittest.mock import AsyncMock

import pytest

from domains.models import DBConnectionSettings
from ps_client import PSClient
import ps_client as ps_client_module


@pytest.mark.asyncio
async def test_create_builds_pool_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure PSClient.create builds a pool using provided DB settings and wraps it."""
    fake_pool = object()
    create_pool = AsyncMock(return_value=fake_pool)
    monkeypatch.setattr(ps_client_module.asyncpg, "create_pool", create_pool)

    settings = DBConnectionSettings(
        db_url="localhost",
        db_port=5432,
        db_username="user_name",
        db_password="password_value",
        db_name="db_name",
    )

    client = await PSClient.create(settings)

    assert isinstance(client, PSClient)
    create_pool.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_closes_pool_when_present() -> None:
    """Ensure close delegates to underlying pool.close when pool exists."""
    fake_pool = type("Pool", (), {"close": AsyncMock()})()
    client = PSClient(fake_pool)

    await client.close()

    fake_pool.close.assert_awaited_once()


def test_connection_returns_pool_acquire_context() -> None:
    """Ensure connection returns acquire context manager from underlying pool."""
    acquire_context = object()
    fake_pool = type("Pool", (), {"acquire": lambda self: acquire_context})()
    client = PSClient(fake_pool)

    result = client.connection()

    assert result is acquire_context
