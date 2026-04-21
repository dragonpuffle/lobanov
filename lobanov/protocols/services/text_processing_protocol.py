from typing import Protocol, runtime_checkable


@runtime_checkable
class TextProcessingProtocol(Protocol):
    async def preprocess_text(self, text: str) -> str:
        """Preprocess text for further processing or analysis.

        Args:
            text: The input text to preprocess.

        Returns:
            The preprocessed text with basic formatting and cleanup applied.

        Raises:
            TextProcessingError: If preprocessing fails due to processing errors.
        """
        ...

    async def clean_text(self, text: str) -> str:
        """Clean text by removing unnecessary characters and formatting.

        Args:
            text: The input text to clean.

        Returns:
            The cleaned text with unnecessary characters and formatting removed.

        Raises:
            TextProcessingError: If cleaning fails due to processing errors.
        """
        ...

    async def normalize_text(self, text: str) -> str:
        """Normalize text to a standard format for consistent processing.

        Args:
            text: The input text to normalize.

        Returns:
            The normalized text in a standard format.

        Raises:
            TextProcessingError: If normalization fails due to processing errors.
        """
        ...
