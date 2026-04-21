from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Protocol
from uuid import UUID

from lobanov.domain.entities.transcript import Transcript


class TranscriptRepositoryProtocol[SessionT](Protocol):
    @asynccontextmanager
    async def context(self) -> AsyncGenerator[SessionT]:
        raise NotImplementedError("TranscriptRepositoryProtocol.context")
        yield  # pyright: ignore[reportUnreachable]

    async def create(self, session: SessionT, transcript: Transcript) -> Transcript:
        """Create a new transcript in the repository.

        Args:
            session: The database session.
            transcript: The Transcript entity to create.

        Returns:
            The created Transcript entity with assigned ID.

        Raises:
            RepositoryError: If the transcript cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, session: SessionT, transcript_id: UUID) -> Transcript | None:
        """Retrieve a transcript by its unique identifier.

        Args:
            session: The database session.
            transcript_id: The UUID of the transcript to retrieve.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session: SessionT, session_id: UUID) -> Transcript | None:
        """Retrieve the transcript associated with a specific documentation session.

        Args:
            session: The database session.
            session_id: The UUID of the documentation session.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_audio_record_id(self, session: SessionT, audio_record_id: UUID) -> Transcript | None:
        """Retrieve the transcript for a specific audio record.

        Args:
            session: The database session.
            audio_record_id: The UUID of the audio record.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, session: SessionT, transcript: Transcript) -> Transcript:
        """Update an existing transcript.

        Args:
            session: The database session.
            transcript: The Transcript entity with updated fields.

        Returns:
            The updated Transcript entity.

        Raises:
            RepositoryError: If the transcript cannot be updated due to database errors.
        """
        ...

    async def delete(self, session: SessionT, transcript_id: UUID) -> bool:
        """Delete a transcript by its unique identifier.

        Args:
            session: The database session.
            transcript_id: The UUID of the transcript to delete.

        Returns:
            True if the transcript was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...
