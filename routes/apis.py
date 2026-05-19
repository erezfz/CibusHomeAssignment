from typing import Literal, Dict, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Body, Path, Query
from starlette import status

from dependencies import get_user_service, get_message_service, get_authentication_service, get_authenticated_user
from domains.models import UserRegistrationRequest, VoteSelection, LoginResponse, LoginRequest, User, \
    GetMessagesResponse, MessageContentStr
from services.authentication import AuthenticationService
from services.message import MessageService
from services.user import UserService

DEFAULT_PAGE_SIZE = 20

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(data: Annotated[UserRegistrationRequest, Body(...)],
                        service: UserService = Depends(get_user_service)) -> None:
    await service.create_user(username=data.username, password=data.password)

@router.post("/login", response_model=LoginResponse)
async def login_user(request: LoginRequest,
                     service: AuthenticationService = Depends(get_authentication_service)) -> LoginResponse:
    access_token = await service.login(username=request.username, password=request.password)
    return LoginResponse(access_token=access_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(current_user: User = Depends(get_authenticated_user)):
    # Logout in this exercise is implemented as a stateless JWT logout.
    #
    # The server returns 204 No Content and does not revoke the JWT server-side.
    # The client is expected to remove the token locally.
    #
    # Stronger logout semantics could be implemented using approaches such as:
    # - access-token blacklist/revocation tables (per token) - which mean db access for every other request - not scalable
    # - refresh-token architecture which ideally need another end-point /refersh (not asked in the exercise requirements)
    #   so that client can use the refresh token so that the server will send it new access token
    # - Redis-backed distributed token revocation
    #
    # However, these approaches introduce additional complexity and/or
    # require extra stateful lookups during authentication requests.
    #
    # For this exercise, a simpler stateless JWT approach was chosen.
    return

@router.get("/messages", response_model=GetMessagesResponse)
async def get_all_messages(current_user: User = Depends(get_authenticated_user),
                           limit: Annotated[int, Query(ge=1, le=100)] = DEFAULT_PAGE_SIZE,
                           next_result: str | None = None,
                           service: MessageService = Depends(get_message_service)) -> GetMessagesResponse:
    # I assume that the message board is not public - hence - the authentication
    return await service.get_messages(limit=limit, next_cursor=next_result, author_id=None)

@router.post("/messages", status_code=status.HTTP_201_CREATED, response_model=Dict[Literal["message_id"], UUID])
async def post_message(message: Annotated[MessageContentStr, Body(embed=True)],
                       current_user: User = Depends(get_authenticated_user),
                       service: MessageService = Depends(get_message_service)) -> Dict[Literal["message_id"], UUID]:
    return {
        "message_id": await service.post_message(content=message, user_id=current_user.id)
    }


@router.post("/messages/{message_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def vote_message(vote: Annotated[VoteSelection, Body(embed=True)],
                       message_id: Annotated[UUID, Path(...)],
                       current_user: User = Depends(get_authenticated_user),
                       service: MessageService = Depends(get_message_service)):
    await service.vote_message(message_id=message_id, vote=vote, user_id=current_user.id)

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(message_id: Annotated[UUID, Path(...)],
                         current_user: User = Depends(get_authenticated_user),
                         service: MessageService = Depends(get_message_service)):
    await service.delete_message(message_id=message_id, user_id=current_user.id)


@router.get("/user/messages", response_model=GetMessagesResponse)
async def get_current_logged_in_user_messages(
        current_user: User = Depends(get_authenticated_user),
        limit: Annotated[int, Query(ge=1, le=100)] = DEFAULT_PAGE_SIZE,
        next_result: str | None = None,
        service: MessageService = Depends(get_message_service)) -> GetMessagesResponse:
    return await service.get_messages(limit=limit, next_cursor=next_result, author_id=current_user.id)
