import logging
import textwrap
from datetime import datetime
from typing import TypeVar
from uuid import UUID

import asyncpg
from asyncpg import Connection

from domains.models import NonEmptyStr, VoteSelection, Message, MessageResponse, MessageState
from exceptions.exceptions import MessageAlreadyExistsError
from ps_client import PSClient

DBClient = TypeVar('DBClient', bound=PSClient)

USERS_TABLE_NAME = "users"
MESSAGES_TABLE_NAME = "messages"

MAX_PAGE_SIZE = 50
logger = logging.getLogger(__name__)

class MessageRepo:
    def __init__(self, client: DBClient):
        self.client = client

    async def add_message(self, content: NonEmptyStr, user_id: UUID) -> UUID:
        query: str = textwrap.dedent(f"""
        INSERT INTO {MESSAGES_TABLE_NAME} (content, author_id)
        VALUES ($1,$2) RETURNING id
        """)
        async with self.client.connection() as conn:
            try:
                message_id = await conn.fetchval(query, content, user_id)
                logger.info(f"Created message id={message_id} author_id={user_id}")
                return message_id
            except asyncpg.UniqueViolationError:
                logger.warning(f"Message creation conflict for author_id={user_id}")
                raise MessageAlreadyExistsError()


    async def execute_transaction(self, workflow) -> None:
        """
        Run a workflow inside a single DB transaction.

        The workflow is called as ``workflow(context=MessageUnitOfWorkContext(...))``
        so the caller can execute multiple row-level operations atomically.
        """
        async with self.client.connection() as conn:
            async with conn.transaction():
                context = MessageUnitOfWorkContext(connection=conn)
                await workflow(context=context)


    async def get_messages(self, next_cursor: datetime | None, limit: int, messages_author_id: UUID | None)\
            -> list[MessageResponse]:
        limit = min(MAX_PAGE_SIZE, limit) # To safe keep the db, a hard max of messages can be retrieved at one time
        query = textwrap.dedent("""
                                SELECT m.id, u.username AS author, m.content, m.vote_count, m.created_at
                                FROM messages m JOIN users u
                                    ON u.id = m.author_id
                                WHERE m.deleted_at IS NULL 
                            """)
        params = []

        if messages_author_id is not None:
            query += " AND m.author_id = $1 "
            params.append(messages_author_id)

        if next_cursor is not None:
            cursor_param_index = len(params) + 1
            query += f" AND m.created_at < ${cursor_param_index} "
            params.append(next_cursor)

        limit_param_index = len(params) + 1
        query += f" ORDER BY m.created_at DESC, id DESC LIMIT ${limit_param_index} "
        params.append(limit)

        async with self.client.connection() as conn:
            records = await conn.fetch(query, *params)
            return [MessageResponse(
                id=record['id'], content=record['content'], vote_count=record['vote_count'],
                created_at=record['created_at'], author=record['author'])
                for record in records]


class MessageUnitOfWorkContext:
    """Transaction-scoped helpers for message state and voting mutations."""

    def __init__(self, connection: Connection):
        self._conn = connection

    async def get_message_for_update(self, message_id: UUID) -> Message | None:
        query = "SELECT id, content, author_id, deleted_at, vote_count FROM messages WHERE id = $1 FOR UPDATE"
        record = await self._conn.fetchrow(query, message_id)
        if record is None:
            return None
        return Message(id=record['id'], content=record['content'], author_id=record['author_id'],
                       deleted_at=record['deleted_at'], vote_count=record['vote_count'])

    async def mark_message_deleted(self, message_id: UUID) -> None:
        query = "UPDATE messages SET deleted_at = NOW() WHERE id = $1"
        await self._conn.execute(query, message_id)

    async def get_message_state_for_update(self, message_id: UUID) -> MessageState:
        query = "SELECT deleted_at FROM messages WHERE id = $1 FOR UPDATE"
        record = await self._conn.fetchrow(query, message_id)
        if record is None:
            return MessageState.NOT_FOUND
        if record["deleted_at"] is not None:
            return MessageState.DELETED
        return MessageState.ACTIVE

    async def get_vote_for_update(self, *, message_id: UUID, user_id: UUID) -> VoteSelection | None:
        query = "SELECT vote FROM message_votes WHERE message_id = $1 AND user_id = $2 FOR UPDATE"
        result = await self._conn.fetchval(query, message_id, user_id)
        return VoteSelection.from_internal_value(result) if result is not None else None

    async def upsert_vote(self, *, message_id: UUID, user_id: UUID, vote: VoteSelection) -> None:
        query = textwrap.dedent("""
        INSERT INTO message_votes (message_id, user_id,vote) VALUES($1,$2,$3)
         ON CONFLICT (message_id, user_id) DO UPDATE SET vote = EXCLUDED.vote
         """)
        await self._conn.execute(query, message_id, user_id, vote.internal_value)

    async def update_vote_count(self, message_id: UUID, delta: int) -> None:
        query = "UPDATE messages SET vote_count = vote_count + $1 WHERE id = $2"
        await self._conn.execute(query, delta, message_id)
