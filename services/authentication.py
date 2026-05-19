import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

from domains.models import NonEmptyStr, User
from exceptions.exceptions import AuthenticationError, InvalidTokenError
from repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

class AuthenticationService:
    def __init__(self, user_repo: UserRepository, jwt_secret: str) -> None:
        self.user_repo = user_repo
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = 'HS256'

    async def login(self, username: NonEmptyStr, password: NonEmptyStr) -> str:
        user = await self.user_repo.get_by_username(username)
        if user is None:
            logger.warning(f"Authentication failed for username={username}") # for PII, usually in audit log
            raise AuthenticationError()
        password_valid: bool = bcrypt.checkpw(password=password.encode(), hashed_password=user.password_hash.encode())
        if password_valid:
            logger.info(f"User authenticated successfully user_id={user.id}") # for PII, usually in audit log
            return self._create_access_token(user=user, jwt_secret=self._jwt_secret, algorithm_name=self._jwt_algorithm)
        else:
            logger.warning(f"Authentication failed for user_id={user.id}") # for PII, usually in audit log
            raise AuthenticationError()


    async def authenticate_request(self, access_token: str) -> User:
        try:
            payload: Dict[str, Any] = jwt.decode(jwt=access_token, key=self._jwt_secret, algorithms=[self._jwt_algorithm])
        except jwt.InvalidTokenError:
            logger.warning("Request authentication failed: invalid JWT token")
            raise InvalidTokenError()
        user_id = payload.get('sub')
        if user_id is None:
            logger.warning("Request authentication failed: missing subject in JWT payload")
            raise InvalidTokenError()
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"Request authentication failed: subject user not found user_id={user_id}")
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
