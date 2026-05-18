from pydantic import BaseModel, StringConstraints, Field
from typing import Annotated
from dataclasses import dataclass
from uuid import UUID
from enum import Enum
from datetime import datetime


class MessageState(str, Enum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    NOT_FOUND = "NOT_FOUND"

class VoteSelection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"

    @property
    def internal_value(self) -> int:
        return {
            VoteSelection.UP: 1,
            VoteSelection.DOWN: -1,
        }[self]

    @classmethod
    def from_internal_value(cls, value: int) -> "VoteSelection":
        mapping = {1: cls.UP,-1: cls.DOWN,}
        try:
            return mapping[value]
        except KeyError:
            raise ValueError(f"Invalid vote selection: {value}")

NonEmptyStr = Annotated[str, StringConstraints(min_length=5, strip_whitespace=True, )]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=50, strip_whitespace=True)]
MessageContentStr = Annotated[str, StringConstraints(min_length=3, max_length=1000)]

class DBConnectionSettings(BaseModel):
    db_url: str
    db_port: int
    db_username: str
    db_password: str
    db_name: str

class UserRegistrationRequest(BaseModel):
    username: NonEmptyStr = Field(max_length=50)
    password: PasswordStr

class LoginRequest(BaseModel):
    username: NonEmptyStr
    password: PasswordStr

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    id: UUID
    author: NonEmptyStr
    content: MessageContentStr
    vote_count: int
    created_at: datetime

class GetMessagesResponse(BaseModel):
    items: list[MessageResponse]
    next: str | None

@dataclass(slots=True)
class User:
    id: UUID
    username: NonEmptyStr
    password_hash: str

@dataclass(slots=True)
class Message:
    id: UUID
    content: MessageContentStr
    author_id: UUID
    deleted_at: datetime | None
    vote_count: int







