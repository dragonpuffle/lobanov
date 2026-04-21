from uuid import UUID
from typing import Protocol, Optional, runtime_checkable

from lobanov.domain.entities.audio_record import AudioRecord


@runtime_checkable
class AudioRecordRepositoryProtocol(Protocol):
    async def create(self, audio_record: AudioRecord) -> AudioRecord:
        """Create a new audio record in the repository.

        Args:
            audio_record: The AudioRecord entity to create.

        Returns:
            The created AudioRecord entity with assigned ID.

        Raises:
            RepositoryError: If the audio record cannot be created due to database errors.
        """
        ...

    async def get_by_id(self, audio_record_id: UUID) -> Optional[AudioRecord]:
        """Retrieve an audio record by its unique identifier.

        Args:
            audio_record_id: The UUID of the audio record to retrieve.

        Returns:
            The AudioRecord entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def get_by_session_id(self, session_id: UUID) -> Optional[AudioRecord]:
        """Retrieve an audio record associated with a specific documentation session.

        Args:
            session_id: The UUID of the documentation session.

        Returns:
            The AudioRecord entity if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...

    async def delete(self, audio_record_id: UUID) -> bool:
        """Delete an audio record by its unique identifier.

        Args:
            audio_record_id: The UUID of the audio record to delete.

        Returns:
            True if the audio record was successfully deleted, False otherwise.

        Raises:
            RepositoryError: If there is a database error during deletion.
        """
        ...

    async def get_file_path(self, audio_record_id: UUID) -> Optional[str]:
        """Retrieve the file path of an audio record.

        Args:
            audio_record_id: The UUID of the audio record.

        Returns:
            The file path as a string if found, None otherwise.

        Raises:
            RepositoryError: If there is a database error during retrieval.
        """
        ...
