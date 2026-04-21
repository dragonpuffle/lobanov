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

    async def create(self, transcript: Transcript) -> Transcript:
        """Create a new transcript in the repository.

        Args:
            transcript: The Transcript entity to create.

        Returns:
            The created Transcript entity with assigned ID.

        Raises:
            RepositoryError: If the transcript cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, transcript_id: UUID) -> Transcript | None:
        """Retrieve a transcript by its unique identifier.

        Args:
            transcript_id: The UUID of the transcript to retrieve.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session_id: UUID) -> Transcript | None:
        """Retrieve the transcript associated with a specific documentation session.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_audio_record_id(self, audio_record_id: UUID) -> Transcript | None:
        """Retrieve the transcript for a specific audio record.

        Args:
            audio_record_id: The UUID of the audio record.

        Returns:
            The Transcript entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def update(self, transcript: Transcript) -> Transcript:
        """Update an existing transcript.

        Args:
            transcript: The Transcript entity with updated fields.

        Returns:
            The updated Transcript entity.

        Raises:
            RepositoryError: If the transcript cannot be updated due to database errors.
        """
        ...

    async def delete(self, transcript_id: UUID) -> bool:
        """Delete a transcript by its unique identifier.

        Args:
            transcript_id: The UUID of the transcript to delete.

        Returns:
            True if the transcript was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...
