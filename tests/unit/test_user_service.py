"""Unit tests for UserService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domains.models import User
from services.user import UserService


@pytest.mark.asyncio
async def test_create_user_delegates_to_repository() -> None:
    """Ensure UserService forwards create_user call to repository with same arguments."""
    expected = User(id=uuid4(), username="author_name", password_hash="hash")
    repo = type("Repo", (), {"create_user": AsyncMock(return_value=expected)})()
    service = UserService(repo)

    result = await service.create_user(username="author_name", password="Password123")

    assert result == expected
    repo.create_user.assert_awaited_once_with("author_name", "Password123")
