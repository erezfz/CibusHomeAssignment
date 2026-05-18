from repositories.user_repo import UserRepository
from domains.models import User
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_user(self, username: str, password: str) -> User:
         return await self.user_repo.create_user(username, password)


