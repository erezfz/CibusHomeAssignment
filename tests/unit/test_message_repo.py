"""Unit tests for MessageRepo and MessageUnitOfWorkContext internals."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import MessageState, VoteSelection
from exceptions.exceptions import MessageAlreadyExistsError
from repositories import message_repo as message_repo_module
from repositories.message_repo import MAX_PAGE_SIZE, MessageRepo, MessageUnitOfWorkContext


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
async def test_add_message_returns_inserted_id() -> None:
    """Ensure add_message returns UUID from INSERT RETURNING id path."""
    expected_id = uuid4()
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=expected_id)})()
    repo = MessageRepo(_Client(conn))

    created_id = await repo.add_message(content="hello world", user_id=uuid4())

    assert created_id == expected_id
    conn.fetchval.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_message_maps_unique_violation_to_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure duplicate message DB constraint is translated to MessageAlreadyExistsError."""
    class FakeUniqueViolationError(Exception):
        pass

    monkeypatch.setattr(message_repo_module.asyncpg, "UniqueViolationError", FakeUniqueViolationError)
    conn = type("Conn", (), {"fetchval": AsyncMock(side_effect=FakeUniqueViolationError())})()
    repo = MessageRepo(_Client(conn))

    with pytest.raises(MessageAlreadyExistsError):
        await repo.add_message(content="hello world", user_id=uuid4())


@pytest.mark.asyncio
async def test_get_messages_applies_hard_max_page_size() -> None:
    """Ensure repository enforces MAX_PAGE_SIZE even when requested limit is larger."""
    conn = type("Conn", (), {"fetch": AsyncMock(return_value=[])})()
    repo = MessageRepo(_Client(conn))

    await repo.get_messages(next_cursor=None, limit=MAX_PAGE_SIZE + 100, messages_author_id=None)

    limit_arg = conn.fetch.await_args.args[-1]
    assert limit_arg == MAX_PAGE_SIZE


@pytest.mark.asyncio
async def test_get_messages_maps_records_to_message_response() -> None:
    """Ensure fetched DB records are mapped to MessageResponse fields correctly."""
    created_at = datetime.now(timezone.utc)
    row = {
        "id": uuid4(),
        "author": "author_name",
        "content": "hello world",
        "vote_count": 3,
        "created_at": created_at,
    }
    conn = type("Conn", (), {"fetch": AsyncMock(return_value=[row])})()
    repo = MessageRepo(_Client(conn))

    result = await repo.get_messages(next_cursor=None, limit=10, messages_author_id=None)

    assert len(result) == 1
    assert result[0].author == "author_name"
    assert result[0].content == "hello world"
    assert result[0].vote_count == 3
    assert result[0].created_at == created_at


@pytest.mark.asyncio
async def test_get_message_state_for_update_returns_deleted() -> None:
    """Ensure message state resolver returns DELETED when deleted_at is not null."""
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value={"deleted_at": datetime.now(timezone.utc)})})()
    ctx = MessageUnitOfWorkContext(conn)

    state = await ctx.get_message_state_for_update(uuid4())

    assert state == MessageState.DELETED


@pytest.mark.asyncio
async def test_get_vote_for_update_returns_none_when_no_vote() -> None:
    """Ensure missing vote row maps to None."""
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=None)})()
    ctx = MessageUnitOfWorkContext(conn)

    vote = await ctx.get_vote_for_update(message_id=uuid4(), user_id=uuid4())

    assert vote is None


@pytest.mark.asyncio
async def test_get_vote_for_update_maps_internal_value_to_enum() -> None:
    """Ensure numeric vote values are converted to public VoteSelection enum."""
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=-1)})()
    ctx = MessageUnitOfWorkContext(conn)

    vote = await ctx.get_vote_for_update(message_id=uuid4(), user_id=uuid4())

    assert vote == VoteSelection.DOWN
