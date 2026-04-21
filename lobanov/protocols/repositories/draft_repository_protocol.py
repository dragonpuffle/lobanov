from uuid import UUID
from typing import Protocol, Optional, runtime_checkable

from lobanov.domain.entities.medical_document_draft import MedicalDocumentDraft
from lobanov.domain.entities.draft_field_value import DraftFieldValue


@runtime_checkable
class DraftRepositoryProtocol(Protocol):
    async def create(self, draft: MedicalDocumentDraft) -> MedicalDocumentDraft:
        """Create a new medical document draft in the repository.

        Args:
            draft: The MedicalDocumentDraft entity to create.

        Returns:
            The created MedicalDocumentDraft entity with assigned ID.

        Raises:
            RepositoryError: If the draft cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, draft_id: UUID) -> Optional[MedicalDocumentDraft]:
        """Retrieve a medical document draft by its unique identifier.

        Args:
            draft_id: The UUID of the draft to retrieve.

        Returns:
            The MedicalDocumentDraft entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session_id: UUID) -> Optional[MedicalDocumentDraft]:
        """Retrieve the medical document draft associated with a specific documentation session.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            The MedicalDocumentDraft entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, draft: MedicalDocumentDraft) -> MedicalDocumentDraft:
        """Update an existing medical document draft.

        Args:
            draft: The MedicalDocumentDraft entity with updated fields.

        Returns:
            The updated MedicalDocumentDraft entity.

        Raises:
            RepositoryError: If the draft cannot be updated due to database errors.
        """
        ...

    async def delete(self, draft_id: UUID) -> bool:
        """Delete a medical document draft by its unique identifier.

        Args:
            draft_id: The UUID of the draft to delete.

        Returns:
            True if the draft was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def get_field_values(self, draft_id: UUID) -> dict[str, DraftFieldValue]:
        """Retrieve all field values for a specific draft.

        Args:
            draft_id: The UUID of the draft.

        Returns:
            Dictionary mapping field IDs to their DraftFieldValue entities.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update_field_value(
        self, draft_id: UUID, field_id: UUID, field_value: DraftFieldValue
    ) -> MedicalDocumentDraft:
        """Update a specific field value within a draft.

        Args:
            draft_id: The UUID of the draft containing the field.
            field_id: The UUID of the field to update.
            field_value: The new DraftFieldValue to set.

        Returns:
            The updated MedicalDocumentDraft entity.

        Raises:
            RepositoryError: If the field value cannot be updated due to database errors.
        """
        ...
