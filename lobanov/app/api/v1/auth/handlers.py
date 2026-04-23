from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.auth.dto import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from lobanov.usecases.auth import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginUser,
    RegisterUser,
    TokenGenerationError,
    UserAlreadyExistsError,
    WeakPasswordError,
)
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"], route_class=DishkaRoute)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    register_use_case: FromDishka[RegisterUser[AsyncSession]],
) -> AuthResponse:
    try:
        user = await register_use_case.execute(
            email=str(request.email),
            password=request.password,
            full_name=request.full_name,
        )
        return AuthResponse(
            user=UserResponse.from_entity(user),
            token=TokenResponse(
                access_token="",
                expires_in=0,
            ),
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except WeakPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed") from e


@router.post("/login")
async def login(
    request: LoginRequest,
    login_use_case: FromDishka[LoginUser[AsyncSession]],
) -> AuthResponse:
    try:
        result = await login_use_case.execute(
            email=str(request.email),
            password=request.password,
        )
        return AuthResponse(
            user=UserResponse.from_entity(result.user),
            token=TokenResponse(
                access_token=result.access_token,
                expires_in=result.expires_in,
            ),
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except InactiveUserError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except TokenGenerationError as e:
        logger.exception("Token generation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token generation failed") from e
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed") from e
