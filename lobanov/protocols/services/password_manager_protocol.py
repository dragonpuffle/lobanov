from typing import Protocol, runtime_checkable

from lobanov.domain.entities.user import User


@runtime_checkable
class PasswordManagerProtocol(Protocol):
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hashed password.

        Args:
            plain_password: The plain text password to verify.
            hashed_password: The hashed password to compare against.

        Returns:
            True if the password matches, False otherwise.

        Raises:
            PasswordManagerError: If verification fails due to processing errors.
        """
        ...

    async def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password for secure storage.

        Args:
            plain_password: The plain text password to hash.

        Returns:
            The hashed password as a string.

        Raises:
            PasswordManagerError: If hashing fails due to processing errors.
        """
        ...

    async def change_password(
        self, user: User, old_password: str, new_password: str
    ) -> None:
        """Change a user's password after verifying the old password.

        Args:
            user: The User entity whose password is being changed.
            old_password: The current password for verification.
            new_password: The new password to set.

        Returns:
            None

        Raises:
            PasswordManagerError: If password change fails due to invalid old password or processing errors.
        """
        ...
