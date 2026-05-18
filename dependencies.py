from fastapi import Request, Depends
from fastapi.security import OAuth2PasswordBearer
from services.authentication import AuthenticationService
from domains.models import User
from repositories.user_repo import UserRepository
from ps_client import PSClient
from services.user import UserService
from services.message import MessageService
from repositories.message_repo import MessageRepo

def get_db_client(request: Request) -> PSClient:
    return request.app.state.db_client

def get_user_repository(db_client: PSClient = Depends(get_db_client)) -> UserRepository:
    return UserRepository(db_client)

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

def get_message_repository(db_client: PSClient = Depends(get_db_client)) -> MessageRepo:
    return MessageRepo(db_client)

def get_message_service(message_repo: MessageRepo = Depends(get_message_repository)) -> MessageService:
    return MessageService(message_repo)

def get_jwt_secret(request: Request)-> str:
    return request.app.state.jwt_secret

def get_authentication_service(user_repo: UserRepository = Depends(get_user_repository),
                               jwt_secret: str =Depends(get_jwt_secret)) -> AuthenticationService:
    return AuthenticationService(user_repo=user_repo, jwt_secret=jwt_secret)

oauth2_scheme = OAuth2PasswordBearer( tokenUrl="/login" )
async def get_authenticated_user(token: str = Depends(oauth2_scheme),
                                 auth_service: AuthenticationService = Depends(get_authentication_service)) -> User:
    return await auth_service.authenticate_request(token)
