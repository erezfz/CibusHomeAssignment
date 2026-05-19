import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from typing import Any, Dict
from repositories.user_repo import UserRepository
from domains.models import NonEmptyStr, User
from exceptions.exceptions import AuthenticationError, InvalidTokenError

class AuthenticationService:
    def __init__(self, user_repo: UserRepository, jwt_secret: str) -> None:
        self.user_repo = user_repo
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = 'HS256'

    async def login(self, username: NonEmptyStr, password: NonEmptyStr) -> str:
        user = await self.user_repo.get_by_username(username)
        if user is None:
            raise AuthenticationError()
        password_valid: bool = bcrypt.checkpw(password=password.encode(), hashed_password=user.password_hash.encode())
        if password_valid:
            return self._create_access_token(user=user, jwt_secret=self._jwt_secret, algorithm_name=self._jwt_algorithm)
        else:
            raise AuthenticationError()


    async def authenticate_request(self, access_token: str) -> User:
        try:
            payload: Dict[str, Any] = jwt.decode(jwt=access_token, key=self._jwt_secret, algorithms=[self._jwt_algorithm])
        except jwt.InvalidTokenError:
            raise InvalidTokenError()
        user_id = payload.get('sub')
        if user_id is None:
            raise InvalidTokenError()
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise InvalidTokenError()
        return user

    @staticmethod
    def _create_access_token(user: User, jwt_secret: str, algorithm_name: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        payload = {
            'sub': str(user.id),
            'username': user.username,
            "exp": expires_at,
        }
        return jwt.encode(payload=payload, key=jwt_secret, algorithm=algorithm_name)
