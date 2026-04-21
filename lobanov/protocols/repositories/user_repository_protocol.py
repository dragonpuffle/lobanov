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

    async def create(self, session: SessionT, user: User) -> User:
        """Create a new user.

        Args:
            session: The database session.
            user: The user entity to create.

        Returns:
            The created user entity.
        """
        ...

    async def get_by_id(self, session: SessionT, user_id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            session: The database session.
            user_id: The UUID of the user.

        Returns:
            The user entity if found, None otherwise.
        """
        ...

    async def get_by_email(self, session: SessionT, email: str) -> User | None:
        """Get a user by email.

        Args:
            session: The database session.
            email: The email address of the user.

        Returns:
            The user entity if found, None otherwise.
        """
        ...

    async def update(self, session: SessionT, user: User) -> User:
        """Update an existing user.

        Args:
            session: The database session.
            user: The user entity with updated fields.

        Returns:
            The updated user entity.
        """
        ...

    async def delete(self, session: SessionT, user_id: UUID) -> bool:
        """Delete a user by ID.

        Args:
            session: The database session.
            user_id: The UUID of the user to delete.

        Returns:
            True if the user was deleted, False otherwise.
        """
        ...

    async def get_all(self, session: SessionT, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users with pagination.

        Args:
            session: The database session.
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of user entities.
        """
        ...
