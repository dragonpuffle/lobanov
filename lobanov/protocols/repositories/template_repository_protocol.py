from uuid import UUID
from typing import Protocol, List, Optional, runtime_checkable

from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate
from lobanov.domain.entities.template_field import TemplateField


@runtime_checkable
class TemplateRepositoryProtocol(Protocol):
    async def create(self, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        """Create a new medical document template in the repository.

        Args:
            template: The MedicalDocumentTemplate entity to create.

        Returns:
            The created MedicalDocumentTemplate entity with assigned ID.

        Raises:
            RepositoryError: If the template cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, template_id: UUID) -> Optional[MedicalDocumentTemplate]:
        """Retrieve a medical document template by its unique identifier.

        Args:
            template_id: The UUID of the template to retrieve.

        Returns:
            The MedicalDocumentTemplate entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[MedicalDocumentTemplate]:
        """Retrieve all medical document templates with pagination.

        Args:
            limit: Maximum number of templates to return (default: 100).
            offset: Number of templates to skip (default: 0).

        Returns:
            List of MedicalDocumentTemplate entities.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_active(self, limit: int = 100, offset: int = 0) -> List[MedicalDocumentTemplate]:
        """Retrieve all active medical document templates with pagination.

        Args:
            limit: Maximum number of templates to return (default: 100).
            offset: Number of templates to skip (default: 0).

        Returns:
            List of active MedicalDocumentTemplate entities.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        """Update an existing medical document template.

        Args:
            template: The MedicalDocumentTemplate entity with updated fields.

        Returns:
            The updated MedicalDocumentTemplate entity.

        Raises:
            RepositoryError: If the template cannot be updated due to database errors.
        """
        ...

    async def delete(self, template_id: UUID) -> bool:
        """Delete a medical document template by its unique identifier.

        Args:
            template_id: The UUID of the template to delete.

        Returns:
            True if the template was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def get_fields(self, template_id: UUID) -> List[TemplateField]:
        """Retrieve all fields defined in a specific template.

        Args:
            template_id: The UUID of the template.

        Returns:
            List of TemplateField entities defined in the template.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...
