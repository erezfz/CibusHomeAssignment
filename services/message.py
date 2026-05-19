import base64
from datetime import datetime
from uuid import UUID

from domains.models import NonEmptyStr, VoteSelection, Message, GetMessagesResponse, MessageState
from exceptions.exceptions import (MessageNotFoundError, MessageDeletionForbiddenError,
                                   MessageVotingForbiddenError, InvalidCursorError)
from repositories.message_repo import MessageRepo, MessageUnitOfWorkContext


class MessageService:
    def __init__(self, message_repo: MessageRepo):
        self.message_repo = message_repo

    async def get_messages(self,next_cursor: str | None , limit: int, author_id: UUID | None) -> GetMessagesResponse:
        """
        Return paginated messages using cursor-based pagination.

        ``next_cursor`` is a base64-encoded ISO timestamp produced by
        :meth:`encode_cursor`. The service fetches ``limit + 1`` rows to
        determine whether a next page exists.
        """
        decoded_cursor = self.decode_cursor(next_cursor) if next_cursor else None
        messages = await self.message_repo.get_messages(next_cursor=decoded_cursor,limit=limit+1, messages_author_id=author_id)
        has_next = len(messages) > limit
        if has_next:
            messages = messages[:limit]
            next_value = self.encode_cursor(messages[-1].created_at)
        else:
            next_value = None
        return GetMessagesResponse(items=messages, next=next_value)


    async def post_message(self, content: NonEmptyStr, user_id: UUID) -> UUID:
        """
        TODO: add in REAME.MD or solve later DB locking ensures correctness
            app-level/distributed locks could optimize contention
        TODO: add 409 code with raise HTTPException(
           status_code=status.HTTP_409_CONFLICT,
            detail="User already posted this message",
        )
        """
        return await self.message_repo.add_message(content, user_id)

    async def delete_message(self, message_id: UUID, user_id: UUID) -> None:
        async def workflow(context: MessageUnitOfWorkContext):
            message: Message | None = await context.get_message_for_update(message_id=message_id)
            if message is None:
                raise MessageNotFoundError()
            if message.author_id != user_id:
                raise MessageDeletionForbiddenError()
            if message.deleted_at is not None:
                return
            await context.mark_message_deleted(message_id=message_id)

        await self.message_repo.execute_transaction(workflow=workflow, )


    async def vote_message(self, message_id: UUID, user_id: UUID, vote: VoteSelection) -> None:
        async def workflow(context: MessageUnitOfWorkContext):
            message_state = await context.get_message_state_for_update(message_id)
            if message_state == MessageState.NOT_FOUND:
                raise MessageNotFoundError()
            if message_state == MessageState.DELETED:
                raise MessageVotingForbiddenError()
            current_vote = await context.get_vote_for_update(message_id=message_id, user_id=user_id)
            delta = vote.internal_value if current_vote is None else (vote.internal_value - current_vote.internal_value)
            await context.upsert_vote(message_id=message_id, user_id=user_id, vote=vote)
            await context.update_vote_count(message_id=message_id, delta=delta)

        await self.message_repo.execute_transaction(workflow=workflow, )


    @staticmethod
    def decode_cursor(value: str):
        """Decode a pagination cursor into ``datetime`` or raise ``InvalidCursorError``."""
        try:
            decoded = base64.urlsafe_b64decode(value.encode()).decode()
            return datetime.fromisoformat(decoded)
        except Exception:
            raise InvalidCursorError()

    @staticmethod
    def encode_cursor(value: datetime):
        """Encode a message timestamp into a stable base64 pagination cursor."""
        raw = value.isoformat()
        return base64.urlsafe_b64encode(raw.encode()).decode()
