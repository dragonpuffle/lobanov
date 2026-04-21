from io import BytesIO
from typing import Protocol
from uuid import UUID


class FileStorageProtocol(Protocol):
    async def save_audio(self, file: BytesIO, filename: str, session_id: UUID) -> str:
        """Save an audio file to storage.

        Args:
            file: The audio file content as BytesIO.
            filename: The name to assign to the saved file.
            session_id: The UUID of the documentation session the file belongs to.

        Returns:
            The path where the file was saved.

        Raises:
            FileStorageError: If the file cannot be saved due to storage errors.
        """
        ...

    async def get_audio_url(self, file_path: str) -> str:
        """Get the URL for accessing an audio file.

        Args:
            file_path: The path of the audio file.

        Returns:
            The URL for accessing the audio file.

        Raises:
            FileStorageError: If the URL cannot be generated due to storage errors.
        """
        ...

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage.

        Args:
            file_path: The path of the file to delete.

        Returns:
            True if the file was successfully deleted, False otherwise.

        Raises:
            FileStorageError: If the file cannot be deleted due to storage errors.
        """
        ...

    async def save_document(self, content: str, filename: str, session_id: UUID) -> str:
        """Save a document to storage.

        Args:
            content: The document content as a string.
            filename: The name to assign to the saved file.
            session_id: The UUID of the documentation session the document belongs to.

        Returns:
            The path where the document was saved.

        Raises:
            FileStorageError: If the document cannot be saved due to storage errors.
        """
        ...
