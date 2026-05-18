"""Component tests for MessageService with repository boundary mocked."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import Message, MessageResponse, MessageState, VoteSelection
from exceptions.exceptions import MessageNotFoundError, MessageVotingForbiddenError
from services.message import MessageService


def _message_response() -> MessageResponse:
    return MessageResponse(
        id=uuid4(),
        author="author_name",
        content="hello world",
        vote_count=0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_messages_calls_repo_with_limit_plus_one() -> None:
    """Ensure service asks repository for limit+1 records to compute pagination next cursor."""
    repo = SimpleNamespace(get_messages=AsyncMock(return_value=[_message_response()]))
    service = MessageService(repo)

    await service.get_messages(next_cursor=None, limit=2, author_id=None)

    repo.get_messages.assert_awaited_once()
    assert repo.get_messages.await_args.kwargs["limit"] == 3


@pytest.mark.asyncio
async def test_delete_message_marks_existing_message_deleted() -> None:
    """Ensure delete workflow marks message as deleted when owner deletes active message."""
    user_id = uuid4()
    message = Message(id=uuid4(), content="hello", author_id=user_id, deleted_at=None, vote_count=0)
    context = SimpleNamespace(
        get_message_for_update=AsyncMock(return_value=message),
        mark_message_deleted=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())
    await service.delete_message(message_id=message.id, user_id=user_id)

    context.mark_message_deleted.assert_awaited_once_with(message_id=message.id)


@pytest.mark.asyncio
async def test_delete_message_raises_not_found_for_missing_message() -> None:
    """Ensure missing message during delete path raises MessageNotFoundError."""
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


@pytest.mark.asyncio
async def test_vote_message_active_state_updates_vote_and_counter() -> None:
    """Ensure vote workflow updates vote row and vote_count delta when message is active."""
    message_id = uuid4()
    user_id = uuid4()
    context = SimpleNamespace(
        get_message_state_for_update=AsyncMock(return_value=MessageState.ACTIVE),
        get_vote_for_update=AsyncMock(return_value=None),
        upsert_vote=AsyncMock(),
        update_vote_count=AsyncMock(),
    )

    class Repo:
        async def execute_transaction(self, workflow):
            await workflow(context)

    service = MessageService(Repo())
    await service.vote_message(message_id=message_id, user_id=user_id, vote=VoteSelection.UP)

    context.upsert_vote.assert_awaited_once_with(message_id=message_id, user_id=user_id, vote=VoteSelection.UP)
    context.update_vote_count.assert_awaited_once_with(message_id=message_id, delta=1)


@pytest.mark.asyncio
async def test_vote_message_deleted_state_raises_forbidden() -> None:
    """Ensure votes on deleted messages are rejected with MessageVotingForbiddenError."""
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
