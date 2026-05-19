import asyncpg
from asyncpg import Pool

from domains.models import DBConnectionSettings
from exceptions.exceptions import DatabaseError


class PSClient:
    """Thin wrapper around an asyncpg connection pool."""

    def __init__(self, pool: Pool):
        self._pool: Pool = pool

    @classmethod
    async def create(cls, settings: DBConnectionSettings):
        """Create a pool-backed client using DB settings from application config."""
        pool: Pool = await asyncpg.create_pool(
            dsn=f"postgresql://{settings.db_username}:{settings.db_password}@{settings.db_url}:{settings.db_port}/{settings.db_name}")
        return cls(pool)

    async def close(self):
        if self._pool is not None:
            await self._pool.close()

    def connection(self):
        """
        Return a pool acquire context manager for request-scoped DB work.

        Raises:
            DatabaseError: when pool was not initialized.
        """
        if self._pool is not None:
            return self._pool.acquire()
        raise DatabaseError("Database pool is not initialized")
