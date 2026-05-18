"""Unit tests for UserRepository internals and DB interaction mapping."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from exceptions.exceptions import UserAlreadyExistsError
from repositories import user_repo as user_repo_module
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


def _record():
    return {"id": uuid4(), "username": "author_name", "password_hash": "hashed_password"}


@pytest.mark.asyncio
async def test_is_user_exists_returns_fetchval_result() -> None:
    """Ensure existence check returns boolean result from connection.fetchval."""
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=True)})()
    repo = UserRepository(_Client(conn))

    result = await repo.is_user_exists("author_name")

    assert result is True
    conn.fetchval.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_returns_mapped_domain_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure create_user maps INSERT RETURNING record into User domain instance."""
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value=_record())})()
    repo = UserRepository(_Client(conn))
    monkeypatch.setattr(UserRepository, "_hash_password", staticmethod(lambda _: "hashed_password"))

    created = await repo.create_user(username="author_name", password="Password123")

    assert created.username == "author_name"
    assert created.password_hash == "hashed_password"
    assert created.id is not None


@pytest.mark.asyncio
async def test_create_user_maps_unique_violation_to_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure DB unique constraint errors are translated to UserAlreadyExistsError."""
    class FakeUniqueViolationError(Exception):
        pass

    monkeypatch.setattr(user_repo_module.asyncpg, "UniqueViolationError", FakeUniqueViolationError)
    conn = type("Conn", (), {"fetchrow": AsyncMock(side_effect=FakeUniqueViolationError())})()
    repo = UserRepository(_Client(conn))
    monkeypatch.setattr(UserRepository, "_hash_password", staticmethod(lambda _: "hashed_password"))

    with pytest.raises(UserAlreadyExistsError):
        await repo.create_user(username="author_name", password="Password123")


@pytest.mark.asyncio
async def test_get_by_username_returns_none_when_not_found() -> None:
    """Ensure get_by_username returns None when no database row exists."""
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value=None)})()
    repo = UserRepository(_Client(conn))

    result = await repo.get_by_username("ghost_user")

    assert result is None


def test_hash_password_generates_non_plaintext_hash() -> None:
    """Ensure hashing utility does not return raw password text."""
    raw = "Password123"
    hashed = UserRepository._hash_password(raw)

    assert isinstance(hashed, str)
    assert hashed != raw
    assert len(hashed) > 20
