from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate
from lobanov.domain.entities.template_field import TemplateField


class TemplateRepositoryProtocol[SessionT](Protocol):
    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("TemplateRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, session: SessionT, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        """Create a new medical document template in the repository.

        Args:
            session: The database session.
            template: The MedicalDocumentTemplate entity to create.

        Returns:
            The created MedicalDocumentTemplate entity with assigned ID.

        Raises:
            RepositoryError: If the template cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, session: SessionT, template_id: UUID) -> MedicalDocumentTemplate | None:
        """Retrieve a medical document template by its unique identifier.

        Args:
            session: The database session.
            template_id: The UUID of the template to retrieve.

        Returns:
            The MedicalDocumentTemplate entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_all(self, session: SessionT, limit: int = 100, offset: int = 0) -> list[MedicalDocumentTemplate]:
        """Retrieve all medical document templates with pagination.

        Args:
            session: The database session.
            limit: Maximum number of templates to return (default: 100).
            offset: Number of templates to skip (default: 0).

        Returns:
            List of MedicalDocumentTemplate entities.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_active(self, session: SessionT, limit: int = 100, offset: int = 0) -> list[MedicalDocumentTemplate]:
        """Retrieve all active medical document templates with pagination.

        Args:
            session: The database session.
            limit: Maximum number of templates to return (default: 100).
            offset: Number of templates to skip (default: 0).

        Returns:
            List of active MedicalDocumentTemplate entities.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, session: SessionT, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        """Update an existing medical document template.

        Args:
            session: The database session.
            template: The MedicalDocumentTemplate entity with updated fields.

        Returns:
            The updated MedicalDocumentTemplate entity.

        Raises:
            RepositoryError: If the template cannot be updated due to database errors.
        """
        ...

    async def delete(self, session: SessionT, template_id: UUID) -> bool:
        """Delete a medical document template by its unique identifier.

        Args:
            session: The database session.
            template_id: The UUID of the template to delete.

        Returns:
            True if the template was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def get_fields(self, session: SessionT, template_id: UUID) -> list[TemplateField]:
        """Retrieve all fields defined in a specific template.

        Args:
            session: The database session.
            template_id: The UUID of the template.

        Returns:
            List of TemplateField entities defined in the template.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...
