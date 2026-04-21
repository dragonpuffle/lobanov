from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.documentation_session import DocumentationSession


class DocumentationSessionRepositoryProtocol[SessionT](Protocol):
    """Protocol for documentation session repository operations."""

    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("DocumentationSessionRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, session: DocumentationSession) -> DocumentationSession:
        """Create a new documentation session.

        Args:
            session: The documentation session entity to create.

        Returns:
            The created documentation session entity.
        """
        ...

    async def get_by_id(self, session_id: UUID) -> DocumentationSession | None:
        """Get a documentation session by ID.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            The documentation session entity if found, None otherwise.
        """
        ...

    async def get_by_user_id(self, user_id: UUID, limit: int = 100, offset: int = 0) -> list[DocumentationSession]:
        """Get all documentation sessions for a user with pagination.

        Args:
            user_id: The UUID of the user.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of documentation session entities.
        """
        ...

    async def update(self, session: DocumentationSession) -> DocumentationSession:
        """Update an existing documentation session.

        Args:
            session: The documentation session entity with updated fields.

        Returns:
            The updated documentation session entity.
        """
        ...

    async def delete(self, session_id: UUID) -> bool:
        """Delete a documentation session by ID.

        Args:
            session_id: The UUID of the documentation session to delete.

        Returns:
            True if the session was deleted, False otherwise.
        """
        ...

    async def get_active_sessions(self, user_id: UUID, limit: int = 100, offset: int = 0) -> list[DocumentationSession]:
        """Get active documentation sessions for a user (not confirmed).

        Args:
            user_id: The UUID of the user.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of active documentation session entities.
        """
        ...
