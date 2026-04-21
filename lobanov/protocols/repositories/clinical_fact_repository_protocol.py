from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.clinical_fact import ClinicalFact


class ClinicalFactRepositoryProtocol[SessionT](Protocol):
    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("ClinicalFactRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, clinical_fact: ClinicalFact) -> ClinicalFact:
        """Create a new clinical fact in the repository.

        Args:
            clinical_fact: The ClinicalFact entity to create.

        Returns:
            The created ClinicalFact entity with assigned ID.

        Raises:
            RepositoryError: If the clinical fact cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, fact_id: UUID) -> ClinicalFact | None:
        """Retrieve a clinical fact by its unique identifier.

        Args:
            fact_id: The UUID of the clinical fact to retrieve.

        Returns:
            The ClinicalFact entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session_id: UUID) -> list[ClinicalFact]:
        """Retrieve all clinical facts associated with a specific documentation session.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            List of ClinicalFact entities associated with the session.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_transcript_id(self, transcript_id: UUID) -> list[ClinicalFact]:
        """Retrieve all clinical facts extracted from a specific transcript.

        Args:
            transcript_id: The UUID of the transcript.

        Returns:
            List of ClinicalFact entities extracted from the transcript.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def delete(self, fact_id: UUID) -> bool:
        """Delete a clinical fact by its unique identifier.

        Args:
            fact_id: The UUID of the clinical fact to delete.

        Returns:
            True if the clinical fact was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def get_by_fact_type(self, session_id: UUID, fact_type: str) -> list[ClinicalFact]:
        """Retrieve clinical facts of a specific type from a session.

        Args:
            session_id: The UUID of the documentation session.
            fact_type: The type of clinical fact to filter by.

        Returns:
            List of ClinicalFact entities matching the specified type.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...
