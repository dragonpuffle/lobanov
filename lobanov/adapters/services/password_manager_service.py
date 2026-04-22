from typing import override

from passlib.context import CryptContext

from lobanov.domain.entities.user import User
from lobanov.protocols.services.password_manager_protocol import PasswordManagerProtocol


class PasswordManagerError(Exception):
    pass


class PasswordManagerService(PasswordManagerProtocol):
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @override
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            err_msg = "Failed to verify password"
            raise PasswordManagerError(err_msg) from e

    @override
    async def hash_password(self, plain_password: str) -> str:
        try:
            return self.pwd_context.hash(plain_password)
        except Exception as e:
            err_msg = "Failed to hash password"
            raise PasswordManagerError(err_msg) from e

    @override
    async def change_password(self, user: User, old_password: str, new_password: str) -> None:
        is_valid = await self.verify_password(old_password, user.hashed_password)
        if not is_valid:
            err_msg = "Old password is incorrect"
            raise PasswordManagerError(err_msg)
        try:
            user.hashed_password = await self.hash_password(new_password)
        except Exception as e:
            err_msg = "Failed to change password"
            raise PasswordManagerError(err_msg) from e
