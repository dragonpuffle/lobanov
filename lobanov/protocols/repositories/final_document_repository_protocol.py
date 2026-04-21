from uuid import UUID
from typing import Protocol, List, Optional, runtime_checkable

from lobanov.domain.entities.final_medical_document import FinalMedicalDocument


@runtime_checkable
class FinalDocumentRepositoryProtocol(Protocol):
    async def create(self, document: FinalMedicalDocument) -> FinalMedicalDocument:
        """Create a new final medical document in the repository.

        Args:
            document: The FinalMedicalDocument entity to create.

        Returns:
            The created FinalMedicalDocument entity with assigned ID.

        Raises:
            RepositoryError: If the document cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, document_id: UUID) -> Optional[FinalMedicalDocument]:
        """Retrieve a final medical document by its unique identifier.

        Args:
            document_id: The UUID of the document to retrieve.

        Returns:
            The FinalMedicalDocument entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_user_id(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[FinalMedicalDocument]:
        """Retrieve all final medical documents for a specific user with pagination.

        Args:
            user_id: The UUID of the user.
            limit: Maximum number of documents to return (default: 100).
            offset: Number of documents to skip (default: 0).

        Returns:
            List of FinalMedicalDocument entities belonging to the user.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session_id: UUID) -> Optional[FinalMedicalDocument]:
        """Retrieve the final medical document associated with a specific documentation session.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            The FinalMedicalDocument entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, document: FinalMedicalDocument) -> FinalMedicalDocument:
        """Update an existing final medical document.

        Args:
            document: The FinalMedicalDocument entity with updated fields.

        Returns:
            The updated FinalMedicalDocument entity.

        Raises:
            RepositoryError: If the document cannot be updated due to database errors.
        """
        ...

    async def delete(self, document_id: UUID) -> bool:
        """Delete a final medical document by its unique identifier.

        Args:
            document_id: The UUID of the document to delete.

        Returns:
            True if the document was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def export(self, document_id: UUID, format: str) -> bytes:
        """Export a final medical document in the specified format.

        Args:
            document_id: The UUID of the document to export.
            format: The export format (e.g., 'pdf', 'docx', 'json').

        Returns:
            The exported document as bytes.

        Raises:
            RepositoryError: If the document cannot be exported due to database or processing errors.
            ValueError: If the specified format is not supported.
        """
        ...
