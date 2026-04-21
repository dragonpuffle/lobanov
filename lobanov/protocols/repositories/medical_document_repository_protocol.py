from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.medical_document import MedicalDocument


class MedicalDocumentRepositoryProtocol[SessionT](Protocol):
    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("MedicalDocumentRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, session: SessionT, document: MedicalDocument) -> MedicalDocument:
        """Create a new medical document in the repository.

        Args:
            session: The database session.
            document: The MedicalDocument entity to create.

        Returns:
            The created MedicalDocument entity with assigned ID.

        Raises:
            RepositoryError: If the document cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, session: SessionT, document_id: UUID) -> MedicalDocument | None:
        """Retrieve a medical document by its unique identifier.

        Args:
            session: The database session.
            document_id: The UUID of the document to retrieve.

        Returns:
            The MedicalDocument entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_user_id(self, session: SessionT, user_id: UUID, limit: int = 100, offset: int = 0) -> list[MedicalDocument]:
        """Retrieve all medical documents for a specific user with pagination.

        Args:
            session: The database session.
            user_id: The UUID of the user.
            limit: Maximum number of documents to return (default: 100).
            offset: Number of documents to skip (default: 0).

        Returns:
            List of MedicalDocument entities belonging to the user.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session: SessionT, session_id: UUID) -> MedicalDocument | None:
        """Retrieve the medical document associated with a specific documentation session.

        Args:
            session: The database session.
            session_id: The UUID of the documentation session.

        Returns:
            The MedicalDocument entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, session: SessionT, document: MedicalDocument) -> MedicalDocument:
        """Update an existing medical document.

        Args:
            session: The database session.
            document: The MedicalDocument entity with updated fields.

        Returns:
            The updated MedicalDocument entity.

        Raises:
            RepositoryError: If the document cannot be updated due to database errors.
        """
        ...

    async def delete(self, session: SessionT, document_id: UUID) -> bool:
        """Delete a final medical document by its unique identifier.

        Args:
            session: The database session.
            document_id: The UUID of the document to delete.

        Returns:
            True if the document was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...
