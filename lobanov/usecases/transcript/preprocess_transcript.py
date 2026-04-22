from datetime import UTC, datetime
from uuid import UUID

from lobanov.domain import Transcript
from lobanov.protocols.repositories import TranscriptRepositoryProtocol
from lobanov.protocols.services import TextProcessingProtocol


class TranscriptNotFoundError(Exception):
    pass


class TextPreprocessingError(Exception):
    pass


class PreprocessTranscript[sessionT]:
    def __init__(
        self,
        transcript_repository: TranscriptRepositoryProtocol[sessionT],
        text_processing_service: TextProcessingProtocol,
    ):
        self.transcript_repository = transcript_repository
        self.text_processing_service = text_processing_service

    async def execute(self, session: sessionT, transcript_id: UUID) -> Transcript:
        transcript = await self.transcript_repository.get_by_id(session, transcript_id)
        if transcript is None:
            error_message = f"Transcript with id {transcript_id} not found"
            raise TranscriptNotFoundError(error_message)

        try:
            cleaned_text = await self.text_processing_service.preprocess_text(transcript.text)
        except Exception as e:
            error_message = f"Failed to preprocess transcript: {e}"
            raise TextPreprocessingError(error_message) from e

        now = datetime.now(UTC)
        updated_transcript = Transcript(
            id=transcript.id,
            session_id=transcript.session_id,
            audio_record_id=transcript.audio_record_id,
            text=cleaned_text,
            language=transcript.language,
            confidence_score=transcript.confidence_score,
            created_at=transcript.created_at,
            updated_at=now,
        )

        return await self.transcript_repository.update(session, updated_transcript)
