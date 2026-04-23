from dataclasses import dataclass
from datetime import timedelta

from lobanov.domain import User
from lobanov.protocols.repositories.user_repository_protocol import UserRepositoryProtocol
from lobanov.protocols.services.jwt_token_protocol import JWTTokenProtocol
from lobanov.protocols.services.password_manager_protocol import PasswordManagerProtocol


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class TokenGenerationError(Exception):
    pass


class LoginUser[SessionT]:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol[SessionT],
        password_manager: PasswordManagerProtocol,
        jwt_token_service: JWTTokenProtocol,
        access_token_expire_minutes: int,
    ):
        self.user_repository = user_repository
        self.password_manager = password_manager
        self.jwt_token_service = jwt_token_service
        self.access_token_expire_minutes = access_token_expire_minutes

    @dataclass
    class LoginResult:
        user: User
        access_token: str
        expires_in: int

    async def execute(self, email: str, password: str) -> LoginResult:
        async with self.user_repository.context() as session:
            user = await self.user_repository.get_by_email(session, email)
            if user is None:
                err_msg = "Invalid email or password"
                raise InvalidCredentialsError(err_msg)

            is_valid = await self.password_manager.verify_password(password, user.hashed_password)
            if not is_valid:
                err_msg = "Invalid email or password"
                raise InvalidCredentialsError(err_msg)

            if not user.is_active:
                error_message = f"User account is disabled: {email}"
                raise InactiveUserError(error_message)

        try:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)
            access_token = await self.jwt_token_service.create_access_token(user.id, expires_delta)
            expires_in = int(expires_delta.total_seconds())
        except Exception as e:
            err_msg = "Failed to generate access token"
            raise TokenGenerationError(err_msg) from e

        return self.LoginResult(user=user, access_token=access_token, expires_in=expires_in)
