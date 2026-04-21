from uuid import UUID
from typing import Protocol, runtime_checkable

from lobanov.domain.entities.documentation_session import DocumentationSession


@runtime_checkable
class SessionStateValidatorProtocol(Protocol):
    async def can_upload_audio(self, session: DocumentationSession) -> bool:
        """Check if audio can be uploaded to the session based on its current state.

        Args:
            session: The DocumentationSession entity to validate.

        Returns:
            True if audio upload is allowed, False otherwise.

        Raises:
            SessionStateValidatorError: If validation cannot be performed due to processing errors.
        """
        ...

    async def can_transcribe(self, session: DocumentationSession) -> bool:
        """Check if the session can be transcribed based on its current state.

        Args:
            session: The DocumentationSession entity to validate.

        Returns:
            True if transcription is allowed, False otherwise.

        Raises:
            SessionStateValidatorError: If validation cannot be performed due to processing errors.
        """
        ...

    async def can_create_draft(self, session: DocumentationSession) -> bool:
        """Check if a draft can be created for the session based on its current state.

        Args:
            session: The DocumentationSession entity to validate.

        Returns:
            True if draft creation is allowed, False otherwise.

        Raises:
            SessionStateValidatorError: If validation cannot be performed due to processing errors.
        """
        ...

    async def can_confirm(self, session: DocumentationSession) -> bool:
        """Check if the session can be confirmed based on its current state.

        Args:
            session: The DocumentationSession entity to validate.

        Returns:
            True if session confirmation is allowed, False otherwise.

        Raises:
            SessionStateValidatorError: If validation cannot be performed due to processing errors.
        """
        ...
