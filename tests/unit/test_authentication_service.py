"""
Unit tests for AuthenticationService.

These tests verify token creation/validation and credential checks in isolation.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import bcrypt
import jwt
import pytest

from domains.models import User
from exceptions.exceptions import AuthenticationError, InvalidTokenError
from services.authentication import AuthenticationService


JWT_SECRET = "test-secret-key-at-least-32-bytes-long"


def _user(username: str, plain_password: str) -> User:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return User(id=uuid4(), username=username, password_hash=hashed)


@pytest.mark.asyncio
async def test_login_success_returns_access_token() -> None:
    """Ensure successful login returns JWT containing user subject and username claims."""
    user = _user("user_a", "Password123")
    repo = SimpleNamespace(get_by_username=AsyncMock(return_value=user))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)

    token = await service.login(username="user_a", password="Password123")
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

    assert payload["sub"] == str(user.id)
    assert payload["username"] == user.username
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_invalid_password_raises_authentication_error() -> None:
    """Ensure invalid password is rejected with AuthenticationError."""
    user = _user("user_a", "Password123")
    repo = SimpleNamespace(get_by_username=AsyncMock(return_value=user))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)

    with pytest.raises(AuthenticationError):
        await service.login(username="user_a", password="WrongPassword123")


@pytest.mark.asyncio
async def test_login_missing_user_raises_authentication_error() -> None:
    """Ensure unknown user login attempts are rejected with AuthenticationError."""
    repo = SimpleNamespace(get_by_username=AsyncMock(return_value=None))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)

    with pytest.raises(AuthenticationError):
        await service.login(username="ghost_user", password="Password123")


@pytest.mark.asyncio
async def test_authenticate_request_invalid_token_raises_invalid_token() -> None:
    """Ensure malformed token string is rejected as InvalidTokenError."""
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)

    with pytest.raises(InvalidTokenError):
        await service.authenticate_request(access_token="this.is.not.valid")


@pytest.mark.asyncio
async def test_authenticate_request_token_without_sub_raises_invalid_token() -> None:
    """Ensure tokens missing required subject claim are rejected."""
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)
    token = jwt.encode({"username": "user_a"}, JWT_SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        await service.authenticate_request(access_token=token)


@pytest.mark.asyncio
async def test_authenticate_request_unknown_user_raises_invalid_token() -> None:
    """Ensure token for non-existent user is rejected as InvalidTokenError."""
    user_id = uuid4()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "username": "user_a",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    service = AuthenticationService(user_repo=repo, jwt_secret=JWT_SECRET)

    with pytest.raises(InvalidTokenError):
        await service.authenticate_request(access_token=token)
