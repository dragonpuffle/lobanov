from dataclasses import dataclass
from uuid import UUID

from lobanov.domain import (
    AudioRecord,
    DocumentationSession,
    MedicalDocument,
    Transcript,
)
from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TranscriptRepositoryProtocol,
    UserRepositoryProtocol,
)


class SessionNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class GetSessionDetails[sessionT]:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol[sessionT],
        session_repository: DocumentationSessionRepositoryProtocol[sessionT],
        audio_record_repository: AudioRecordRepositoryProtocol[sessionT],
        transcript_repository: TranscriptRepositoryProtocol[sessionT],
        medical_document_repository: MedicalDocumentRepositoryProtocol[sessionT],
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.audio_record_repository = audio_record_repository
        self.transcript_repository = transcript_repository
        self.medical_document_repository = medical_document_repository

    @dataclass
    class SessionDetails:
        session: DocumentationSession
        audio_record: AudioRecord | None
        transcript: Transcript | None
        medical_document: MedicalDocument | None

    async def execute(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> SessionDetails:
        async with self.user_repository.context() as session:
            user = await self.user_repository.get_by_id(session, user_id)
            if user is None:
                error_message = f"User with id {user_id} not found"
                raise UserNotFoundError(error_message)

            if not user.is_active:
                error_message = f"User with id {user_id} is not active"
                raise ValueError(error_message)

            documentation_session = await self.session_repository.get_by_id(session, session_id)
            if documentation_session is None:
                error_message = f"Session with id {session_id} not found"
                raise SessionNotFoundError(error_message)

            if documentation_session.user_id != user_id:
                error_message = f"Session with id {session_id} does not belong to user with id {user_id}"
                raise ValueError(error_message)

            audio_record = await self.audio_record_repository.get_by_session_id(session, session_id)
            transcript = await self.transcript_repository.get_by_session_id(session, session_id)
            medical_document = await self.medical_document_repository.get_by_session_id(session, session_id)

            return self.SessionDetails(
                session=documentation_session,
                audio_record=audio_record,
                transcript=transcript,
                medical_document=medical_document,
            )
