from datetime import UTC, datetime
from uuid import uuid4

from lobanov.domain.entities.user import User
from lobanov.protocols.repositories.user_repository_protocol import UserRepositoryProtocol
from lobanov.protocols.services.password_manager_protocol import PasswordManagerProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)

MIN_PASSWORD_LENGTH = 8


class UserAlreadyExistsError(Exception):
    pass


class InvalidEmailError(Exception):
    pass


class WeakPasswordError(Exception):
    pass


class RegisterUser[SessionT]:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol[SessionT],
        password_manager: PasswordManagerProtocol,
    ):
        self.user_repository = user_repository
        self.password_manager = password_manager

    async def execute(self, email: str, password: str, full_name: str) -> User:
        try:
            if len(password) < MIN_PASSWORD_LENGTH:
                err_msg = f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
                raise WeakPasswordError(err_msg)

            async with self.user_repository.context() as session:
                existing_user = await self.user_repository.get_by_email(session, email)
                if existing_user is not None:
                    error_message = f"User with email {email} already exists"
                    raise UserAlreadyExistsError(error_message)

                hashed_password = await self.password_manager.hash_password(password)

                now = datetime.now(UTC)
                user = User(
                    id=uuid4(),
                    email=email,
                    hashed_password=hashed_password,
                    full_name=full_name,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )

                return await self.user_repository.create(session, user)
        except (UserAlreadyExistsError, WeakPasswordError):
            raise
        except Exception:
            logger.exception("RegisterUser.execute failed")
            raise
