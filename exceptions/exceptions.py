class AppError(Exception):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail


# --------------------
# Authentication
# --------------------

class AuthenticationError(AppError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    detail = "Invalid authentication credentials"


class InvalidTokenError(AppError):
    status_code = 401
    error_code = "INVALID_TOKEN"
    detail = "Invalid authentication token"


# --------------------
# Users
# --------------------

class UserAlreadyExistsError(AppError):
    status_code = 409
    error_code = "USER_ALREADY_EXISTS"
    detail = "User already exists"


class UserNotFoundError(AppError):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    detail = "User not found"


# --------------------
# Messages
# --------------------

class MessageNotFoundError(AppError):
    status_code = 404
    error_code = "MESSAGE_NOT_FOUND"
    detail = "Message not found"


class MessageAlreadyExistsError(AppError):
    status_code = 409
    error_code = "MESSAGE_ALREADY_EXISTS"
    detail = "User already posted this message"


class MessageDeletionForbiddenError(AppError):
    status_code = 403
    error_code = "MESSAGE_DELETE_FORBIDDEN"
    detail = "Message cannot be deleted by this user"


class MessageVotingForbiddenError(AppError):
    status_code = 403
    error_code = "MESSAGE_VOTING_FORBIDDEN"
    detail = "Message cannot be voted on"


# --------------------
# Cursor pagination
# --------------------

class InvalidCursorError(AppError):
    status_code = 400
    error_code = "INVALID_CURSOR"
    detail = "Invalid pagination cursor"


# --------------------
# Infrastructure
# --------------------

class DatabaseError(Exception):
    def __init__(self, message: str):
        super().__init__(message)