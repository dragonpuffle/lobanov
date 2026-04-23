from typing import override

import bcrypt

from lobanov.domain.entities.user import User
from lobanov.protocols.services.password_manager_protocol import PasswordManagerProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class PasswordManagerError(Exception):
    pass


class PasswordManagerService(PasswordManagerProtocol):
    @override
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception as e:
            logger.exception("Password verification failed")
            err_msg = "Failed to verify password"
            raise PasswordManagerError(err_msg) from e

    @override
    async def hash_password(self, plain_password: str) -> str:
        try:
            hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
            return hashed.decode("utf-8")
        except Exception as e:
            logger.exception("Password hashing failed")
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
        except PasswordManagerError:
            raise
        except Exception as e:
            logger.exception("Failed to change password")
            err_msg = "Failed to change password"
            raise PasswordManagerError(err_msg) from e
