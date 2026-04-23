from datetime import UTC, datetime
from uuid import uuid4

from lobanov.domain.entities.user import User
from lobanov.protocols.repositories.user_repository_protocol import UserRepositoryProtocol
from lobanov.protocols.services.password_manager_protocol import PasswordManagerProtocol


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
        if len(password) < 8:
            err_msg = "Password must be at least 8 characters long"
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
