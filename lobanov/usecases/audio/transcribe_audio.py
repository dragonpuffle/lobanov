from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain import DocumentationSession, DocumentationSessionStatus, Transcript, TranscriptLanguage
from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.protocols.services import SpeechRecognitionProtocol


class SessionNotFoundError(Exception):
    pass


class InvalidSessionStateError(Exception):
    pass


class AudioRecordNotFoundError(Exception):
    pass


class TranscriptionError(Exception):
    pass


class TranscribeAudio[SessionT]:
    def __init__(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        audio_record_repository: AudioRecordRepositoryProtocol[SessionT],
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        stt_service: SpeechRecognitionProtocol,
    ):
        self.session_repository = session_repository
        self.audio_record_repository = audio_record_repository
        self.transcript_repository = transcript_repository
        self.stt_service = stt_service

    async def execute(self, session_id: UUID, language: str = "ru") -> Transcript:
        async with self.session_repository.context() as session:
            documentation_session = await self.session_repository.get_by_id(session, session_id)
            if documentation_session is None:
                error_message = f"Session with id {session_id} not found"
                raise SessionNotFoundError(error_message)

            if documentation_session.status != DocumentationSessionStatus.AUDIO_UPLOADED:
                error_message = (
                    f"Session must be in AUDIO_UPLOADED state, current state: {documentation_session.status}"
                )
                raise InvalidSessionStateError(error_message)

            audio_record = await self.audio_record_repository.get_by_session_id(session, session_id)
            if audio_record is None:
                error_message = f"Audio record for session {session_id} not found"
                raise AudioRecordNotFoundError(error_message)

            try:
                transcript = await self.stt_service.transcribe_audio(audio_record.file_path, language)
            except Exception as e:
                error_message = f"Failed to transcribe audio: {e}"
                raise TranscriptionError(error_message) from e

            now = datetime.now(UTC)
            new_transcript = Transcript(
                id=uuid4(),
                session_id=session_id,
                audio_record_id=audio_record.id,
                text=transcript.text,
                language=TranscriptLanguage.RU,
                confidence_score=transcript.confidence_score,
                created_at=now,
                updated_at=now,
            )

            created_transcript = await self.transcript_repository.create(session, new_transcript)

            updated_session = DocumentationSession(
                id=documentation_session.id,
                template_id=documentation_session.template_id,
                user_id=documentation_session.user_id,
                status=DocumentationSessionStatus.TRANSCRIBED,
                created_at=documentation_session.created_at,
                updated_at=now,
            )

            await self.session_repository.update(session, updated_session)

            return created_transcript
