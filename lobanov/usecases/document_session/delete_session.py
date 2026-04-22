from uuid import UUID

from lobanov.domain import DocumentationSession, DocumentationSessionStatus
from lobanov.protocols.repositories import (
    AudioRecordRepositoryProtocol,
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TranscriptRepositoryProtocol,
    UserRepositoryProtocol,
)
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SessionNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class SessionCannotBeDeletedError(Exception):
    pass


class DeleteSession:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        session_repository: DocumentationSessionRepositoryProtocol,
        audio_record_repository: AudioRecordRepositoryProtocol,
        transcript_repository: TranscriptRepositoryProtocol,
        clinical_fact_repository: ClinicalFactRepositoryProtocol,
        medical_document_repository: MedicalDocumentRepositoryProtocol,
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.audio_record_repository = audio_record_repository
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.medical_document_repository = medical_document_repository

    async def execute(
        self,
        session: sessionT,
        session_id: UUID,
        user_id: UUID,
    ) -> None:
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

        if documentation_session.status == DocumentationSessionStatus.CONFIRMED:
            error_message = f"Session with id {session_id} is confirmed and cannot be deleted"
            raise SessionCannotBeDeletedError(error_message)

        audio_record = await self.audio_record_repository.get_by_session_id(session, session_id)
        if audio_record is not None:
            await self.audio_record_repository.delete(session, audio_record.id)
            logger.info(f"Deleted audio record {audio_record.id} for session {session_id}")

        transcript = await self.transcript_repository.get_by_session_id(session, session_id)
        if transcript is not None:
            await self.transcript_repository.delete(session, transcript.id)
            logger.info(f"Deleted transcript {transcript.id} for session {session_id}")

        clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, session_id)
        for fact in clinical_facts:
            await self.clinical_fact_repository.delete(session, fact.id)
        if clinical_facts:
            logger.info(f"Deleted {len(clinical_facts)} clinical facts for session {session_id}")

        medical_document = await self.medical_document_repository.get_by_session_id(session, session_id)
        if medical_document is not None:
            await self.medical_document_repository.delete(session, medical_document.id)
            logger.info(f"Deleted medical document {medical_document.id} for session {session_id}")

        await self.session_repository.delete(session, session_id)
        logger.info(f"Deleted session {session_id} for user {user_id}")
