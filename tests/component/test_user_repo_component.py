"""Component tests for UserRepository using fake DB client/connection."""

from collections.abc import Mapping
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from repositories.user_repo import UserRepository


class _Acquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Client:
    def __init__(self, conn):
        self._conn = conn

    def connection(self):
        return _Acquire(self._conn)


@pytest.mark.asyncio
async def test_is_user_exists_uses_boolean_fetchval() -> None:
    """Ensure is_user_exists delegates SQL existence check and returns bool as-is."""
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=True)})()
    repo = UserRepository(_Client(conn))

    result = await repo.is_user_exists("author_name")

    assert result is True
    conn.fetchval.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_username_returns_none_when_record_missing() -> None:
    """Ensure missing DB row is mapped to None for get_by_username."""
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value=None)})()
    repo = UserRepository(_Client(conn))

    result = await repo.get_by_username("author_name")

    assert result is None


@pytest.mark.asyncio
async def test_create_user_maps_returned_record_to_domain_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure create_user maps INSERT RETURNING row into User domain object."""
    record: Mapping[str, object] = {
        "id": uuid4(),
        "username": "author_name",
        "password_hash": "hashed_password",
    }
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value=record)})()
    repo = UserRepository(_Client(conn))
    monkeypatch.setattr(UserRepository, "_hash_password", staticmethod(lambda _: "hashed_password"))

    created = await repo.create_user(username="author_name", password="Password123")

    assert str(created.id) == str(record["id"])
    assert created.username == "author_name"
    assert created.password_hash == "hashed_password"
