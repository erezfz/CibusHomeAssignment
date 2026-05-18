"""
Unit tests for MessageService.

These tests focus on business logic only and isolate the service from FastAPI and DB.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import Message, MessageResponse, MessageState, VoteSelection
from exceptions.exceptions import (
    InvalidCursorError,
    MessageDeletionForbiddenError,
    MessageNotFoundError,
    MessageVotingForbiddenError,
)
from services.message import MessageService


def _message_response(minutes_offset: int) -> MessageResponse:
    return MessageResponse(
        id=uuid4(),
        author="author_name",
        content=f"content-{minutes_offset}",
        vote_count=0,
        created_at=datetime.now(timezone.utc) + timedelta(minutes=minutes_offset),
    )


@pytest.mark.asyncio
async def test_get_messages_returns_next_when_more_results_exist() -> None:
    """Ensure pagination cursor is returned when repository returns more than requested limit."""
    repo = SimpleNamespace(
        get_messages=AsyncMock(return_value=[_message_response(3), _message_response(2), _message_response(1)])
    )
    service = MessageService(repo)

    result = await service.get_messages(next_cursor=None, limit=2, author_id=None)

    assert len(result.items) == 2
    assert result.next is not None
    repo.get_messages.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_messages_returns_no_next_when_exhausted() -> None:
    """Ensure next cursor is null when returned page does not exceed requested limit."""
    repo = SimpleNamespace(get_messages=AsyncMock(return_value=[_message_response(1)]))
    service = MessageService(repo)

    result = await service.get_messages(next_cursor=None, limit=2, author_id=None)

    assert len(result.items) == 1
    assert result.next is None


@pytest.mark.asyncio
async def test_get_messages_invalid_cursor_raises_domain_error() -> None:
    """Ensure malformed pagination cursor is converted to InvalidCursorError."""
    repo = SimpleNamespace(get_messages=AsyncMock(return_value=[]))
    service = MessageService(repo)

    with pytest.raises(InvalidCursorError):
        await service.get_messages(next_cursor="not-a-valid-cursor", limit=2, author_id=None)


@pytest.mark.asyncio
async def test_delete_message_raises_not_found() -> None:
    """Ensure delete workflow raises MessageNotFoundError when target message is absent."""
    context = SimpleNamespace(
        get_message_for_update=AsyncMock(return_value=None),
        mark_message_deleted=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())

    with pytest.raises(MessageNotFoundError):
        await service.delete_message(message_id=uuid4(), user_id=uuid4())

    context.mark_message_deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_message_raises_forbidden_for_non_owner() -> None:
    """Ensure delete workflow raises forbidden error when requester is not message author."""
    owner_id = uuid4()
    requester_id = uuid4()
    message = Message(id=uuid4(), content="hello", author_id=owner_id, deleted_at=None, vote_count=0)
    context = SimpleNamespace(
        get_message_for_update=AsyncMock(return_value=message),
        mark_message_deleted=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())

    with pytest.raises(MessageDeletionForbiddenError):
        await service.delete_message(message_id=message.id, user_id=requester_id)

    context.mark_message_deleted.assert_not_awaited()


@pytest.mark.asyncio
async def test_vote_message_rejects_deleted_message() -> None:
    """Ensure vote workflow rejects deleted targets and avoids DB updates."""
    context = SimpleNamespace(
        get_message_state_for_update=AsyncMock(return_value=MessageState.DELETED),
        get_vote_for_update=AsyncMock(),
        upsert_vote=AsyncMock(),
        update_vote_count=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())

    with pytest.raises(MessageVotingForbiddenError):
        await service.vote_message(message_id=uuid4(), user_id=uuid4(), vote=VoteSelection.UP)

    context.upsert_vote.assert_not_awaited()
    context.update_vote_count.assert_not_awaited()


@pytest.mark.asyncio
async def test_vote_message_updates_delta_from_previous_vote() -> None:
    """Ensure vote delta is computed correctly when changing an existing vote."""
    message_id = uuid4()
    user_id = uuid4()
    context = SimpleNamespace(
        get_message_state_for_update=AsyncMock(return_value=MessageState.ACTIVE),
        get_vote_for_update=AsyncMock(return_value=VoteSelection.UP),
        upsert_vote=AsyncMock(),
        update_vote_count=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())
    await service.vote_message(message_id=message_id, user_id=user_id, vote=VoteSelection.DOWN)

    context.upsert_vote.assert_awaited_once_with(message_id=message_id, user_id=user_id, vote=VoteSelection.DOWN)
    context.update_vote_count.assert_awaited_once_with(message_id=message_id, delta=-2)
