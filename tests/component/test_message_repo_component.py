"""Component tests for MessageRepo and MessageUnitOfWorkContext using fake DB boundaries."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import MessageState, VoteSelection
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
async def test_add_message_returns_created_message_id() -> None:
    """Ensure add_message returns UUID from INSERT RETURNING id."""
    expected_id = uuid4()
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=expected_id)})()
    repo = MessageRepo(_Client(conn))

    created_id = await repo.add_message(content="hello world", user_id=uuid4())

    assert created_id == expected_id
    conn.fetchval.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_messages_enforces_hard_max_page_size() -> None:
    """Ensure repository enforces MAX_PAGE_SIZE regardless of larger requested limit."""
    conn = type("Conn", (), {"fetch": AsyncMock(return_value=[])})()
    repo = MessageRepo(_Client(conn))

    await repo.get_messages(next_cursor=None, limit=MAX_PAGE_SIZE + 100, messages_author_id=None)

    # Last SQL parameter is LIMIT value sent to DB driver.
    limit_arg = conn.fetch.await_args.args[-1]
    assert limit_arg == MAX_PAGE_SIZE


@pytest.mark.asyncio
async def test_get_message_state_for_update_returns_not_found() -> None:
    """Ensure state resolution returns NOT_FOUND when row is missing."""
    conn = type("Conn", (), {"fetchrow": AsyncMock(return_value=None)})()
    ctx = MessageUnitOfWorkContext(conn)

    state = await ctx.get_message_state_for_update(uuid4())

    assert state == MessageState.NOT_FOUND


@pytest.mark.asyncio
async def test_get_vote_for_update_maps_internal_vote_to_enum() -> None:
    """Ensure numeric DB vote value maps into VoteSelection enum."""
    conn = type("Conn", (), {"fetchval": AsyncMock(return_value=1)})()
    ctx = MessageUnitOfWorkContext(conn)

    vote = await ctx.get_vote_for_update(message_id=uuid4(), user_id=uuid4())

    assert vote == VoteSelection.UP


@pytest.mark.asyncio
async def test_update_vote_count_executes_expected_sql() -> None:
    """Ensure vote_count update sends expected delta and message id to DB."""
    conn = type("Conn", (), {"execute": AsyncMock(return_value="UPDATE 1")})()
    ctx = MessageUnitOfWorkContext(conn)
    message_id = uuid4()

    await ctx.update_vote_count(message_id=message_id, delta=-2)

    conn.execute.assert_awaited_once()
    assert conn.execute.await_args.args[1] == -2
    assert conn.execute.await_args.args[2] == message_id
