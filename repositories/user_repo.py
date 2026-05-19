import logging
from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

import asyncpg
import bcrypt

from domains.models import User, NonEmptyStr
from exceptions.exceptions import UserAlreadyExistsError
from ps_client import PSClient

DBClient = TypeVar('DBClient', bound=PSClient)

TABLE_NAME = "users"
logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, client: DBClient):
        self.client = client

    async def is_user_exists(self, username: NonEmptyStr) -> bool:
        async with self.client.connection() as conn:
            query = f"SELECT EXISTS (SELECT id FROM {TABLE_NAME} WHERE username = $1)"
            return await conn.fetchval(query, username)

    async def create_user(self, username: NonEmptyStr, password: NonEmptyStr) -> User:
        async with self.client.connection() as conn:
            hash_password = self._hash_password(password)
            query = f"INSERT INTO {TABLE_NAME} (username, password_hash) VALUES ($1, $2) RETURNING id, username, password_hash"
            try:
                record = await conn.fetchrow(query, username, hash_password)
                user = self._map_record_to_user(record)
                logger.info(f"Created user id={user.id} username={user.username}")
                return user
            except asyncpg.UniqueViolationError:
                logger.warning(f"User creation conflict for username={username}")
                raise UserAlreadyExistsError()


    async def get_by_username(self, username: NonEmptyStr) -> User | None:
        query = f"SELECT id, username, password_hash FROM {TABLE_NAME} WHERE username = $1"
        return await self._get_one(query, username)

    async def get_by_id(self, id: UUID) -> User | None:
        query = f"SELECT id, username, password_hash FROM {TABLE_NAME} WHERE id = $1"
        return await self._get_one(query, id)

    async def _get_one(self, query: str, *args) -> User | None:
        async with self.client.connection() as conn:
            record = await conn.fetchrow(query, *args)
            return self._map_record_to_user(record) if record is not None else None

    @staticmethod
    def _hash_password(password: NonEmptyStr) -> NonEmptyStr:
        salt: bytes = bcrypt.gensalt()
        hashed_password: bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def _map_record_to_user(record: Mapping[str, Any]) -> User:
        return User(username=record['username'], password_hash=record['password_hash'], id=record['id'])
