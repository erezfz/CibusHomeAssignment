"""Component tests for AuthenticationService with repository boundary mocked."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import bcrypt
import jwt
import pytest

from domains.models import User
from exceptions.exceptions import AuthenticationError, InvalidTokenError
from services.authentication import AuthenticationService


JWT_SECRET = "component-test-secret-key-at-least-32-bytes"


def _hashed_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.mark.asyncio
async def test_login_uses_repository_user_and_generates_jwt() -> None:
    """Ensure login verifies password and returns JWT with expected claims."""
    user = User(id=uuid4(), username="author_name", password_hash=_hashed_password("Password123"))
    repo = type("Repo", (), {"get_by_username": AsyncMock(return_value=user)})()
    service = AuthenticationService(repo, jwt_secret=JWT_SECRET)

    token = await service.login(username="author_name", password="Password123")
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

    assert payload["sub"] == str(user.id)
    assert payload["username"] == user.username


@pytest.mark.asyncio
async def test_login_with_wrong_password_raises_authentication_error() -> None:
    """Ensure invalid password is converted to AuthenticationError."""
    user = User(id=uuid4(), username="author_name", password_hash=_hashed_password("Password123"))
    repo = type("Repo", (), {"get_by_username": AsyncMock(return_value=user)})()
    service = AuthenticationService(repo, jwt_secret=JWT_SECRET)

    with pytest.raises(AuthenticationError):
        await service.login(username="author_name", password="WrongPassword123")


@pytest.mark.asyncio
async def test_authenticate_request_requires_existing_user() -> None:
    """Ensure token with unknown subject is rejected as InvalidTokenError."""
    unknown_user_id = uuid4()
    token = jwt.encode(
        {"sub": str(unknown_user_id), "username": "author_name", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        JWT_SECRET,
        algorithm="HS256",
    )
    repo = type("Repo", (), {"get_by_id": AsyncMock(return_value=None)})()
    service = AuthenticationService(repo, jwt_secret=JWT_SECRET)

    with pytest.raises(InvalidTokenError):
        await service.authenticate_request(token)
