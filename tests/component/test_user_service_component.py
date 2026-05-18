"""Component tests for UserService with repository boundary mocked."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import User
from exceptions.exceptions import UserAlreadyExistsError
from services.user import UserService


@pytest.mark.asyncio
async def test_create_user_delegates_to_repository_and_returns_user() -> None:
    """Ensure UserService delegates user creation and returns repository result unchanged."""
    expected_user = User(id=uuid4(), username="author_name", password_hash="hash")
    repo = type("Repo", (), {"create_user": AsyncMock(return_value=expected_user)})()
    service = UserService(repo)

    actual = await service.create_user(username="author_name", password="Password123")

    assert actual == expected_user
    repo.create_user.assert_awaited_once_with("author_name", "Password123")


@pytest.mark.asyncio
async def test_create_user_propagates_repository_error() -> None:
    """Ensure UserService does not swallow repository-level domain errors."""
    repo = type("Repo", (), {"create_user": AsyncMock(side_effect=UserAlreadyExistsError())})()
    service = UserService(repo)

    with pytest.raises(UserAlreadyExistsError):
        await service.create_user(username="author_name", password="Password123")
