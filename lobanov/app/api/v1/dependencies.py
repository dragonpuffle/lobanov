from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.domain.entities.user import User
from lobanov.infra.config import GlobalConfig
from lobanov.protocols.repositories.user_repository_protocol import UserRepositoryProtocol

security = HTTPBearer()


class AuthenticationError(Exception):
    pass


class InvalidTokenError(AuthenticationError):
    pass


class UserNotFoundError(AuthenticationError):
    pass


class InactiveUserError(AuthenticationError):
    pass


class UserAlreadyExistsError(AuthenticationError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class WeakPasswordError(AuthenticationError):
    pass


@inject
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_repository: FromDishka[UserRepositoryProtocol[AsyncSession]],
    config: FromDishka[GlobalConfig],
) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, config.jwt.secret_key, algorithms=[config.jwt.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError("Invalid token: missing user ID")
    except JWTError as e:
        error_message = f"Invalid token: {e!s}"
        raise InvalidTokenError(error_message) from e

    async with user_repository.context() as session:
        user = await user_repository.get_by_id(session, UUID(user_id))
    if user is None:
        error_message = f"User not found: {user_id}"
        raise UserNotFoundError(error_message)

    if not user.is_active:
        error_message = f"User is inactive: {user_id}"
        raise InactiveUserError(error_message)

    return user


def authentication_exception_handler(_, exc: AuthenticationError):
    if isinstance(exc, UserAlreadyExistsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InvalidCredentialsError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if isinstance(exc, WeakPasswordError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if isinstance(exc, UserNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(exc, InactiveUserError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Authentication error",
    ) from exc
