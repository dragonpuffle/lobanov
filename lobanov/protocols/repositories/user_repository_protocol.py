from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.user import User


class UserRepositoryProtocol[SessionT](Protocol):
    """Protocol for user repository operations."""

    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("UserRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: The user entity to create.

        Returns:
            The created user entity.
        """
        ...

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The UUID of the user.

        Returns:
            The user entity if found, None otherwise.
        """
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email.

        Args:
            email: The email address of the user.

        Returns:
            The user entity if found, None otherwise.
        """
        ...

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: The user entity with updated fields.

        Returns:
            The updated user entity.
        """
        ...

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID.

        Args:
            user_id: The UUID of the user to delete.

        Returns:
            True if the user was deleted, False otherwise.
        """
        ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users with pagination.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of user entities.
        """
        ...
