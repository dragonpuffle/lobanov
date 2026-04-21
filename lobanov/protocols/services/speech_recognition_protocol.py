from typing import Protocol, List, runtime_checkable

from lobanov.domain.entities.transcript import Transcript


@runtime_checkable
class SpeechRecognitionProtocol(Protocol):
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        """Transcribe an audio file to text using speech recognition.

        Args:
            file_path: The path to the audio file to transcribe.
            language: The language code for transcription (e.g., 'en-US', 'ru-RU').

        Returns:
            The Transcript entity containing the transcribed text and metadata.

        Raises:
            SpeechRecognitionError: If transcription fails due to processing errors or unsupported format.
        """
        ...

    async def get_supported_languages(self) -> List[str]:
        """Get the list of supported languages for speech recognition.

        Args:
            None

        Returns:
            List of language codes supported by the speech recognition service.

        Raises:
            SpeechRecognitionError: If the list cannot be retrieved due to service errors.
        """
        ...
