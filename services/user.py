import logging

from domains.models import User
from repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_user(self, username: str, password: str) -> User:
        user = await self.user_repo.create_user(username, password)
        logger.info(f"User creation request completed user_id={user.id} username={user.username}")
        return user
