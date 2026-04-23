from uuid import UUID

from lobanov.domain import DocumentationSessionStatus
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


class DeleteSession[SessionT]:
    def __init__(  # noqa: PLR0913
        self,
        user_repository: UserRepositoryProtocol[SessionT],
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        audio_record_repository: AudioRecordRepositoryProtocol[SessionT],
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        medical_document_repository: MedicalDocumentRepositoryProtocol[SessionT],
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.audio_record_repository = audio_record_repository
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.medical_document_repository = medical_document_repository

    async def execute(
        self,
        session_id: UUID,
        user_id: UUID,
    ) -> None:
        try:
            async with self.user_repository.context() as session:
                await self._validate_user(session, user_id)
                await self._get_and_validate_session(session, session_id, user_id)
                await self._delete_session_data(session, session_id, user_id)
        except (UserNotFoundError, SessionNotFoundError, SessionCannotBeDeletedError, ValueError):
            raise
        except Exception:
            logger.exception("DeleteSession.execute failed")
            raise

    async def _validate_user(self, session, user_id: UUID) -> None:
        user = await self.user_repository.get_by_id(session, user_id)
        if user is None:
            error_message = f"User with id {user_id} not found"
            raise UserNotFoundError(error_message)

        if not user.is_active:
            error_message = f"User with id {user_id} is not active"
            raise ValueError(error_message)

    async def _get_and_validate_session(self, session, session_id: UUID, user_id: UUID) -> None:
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

    async def _delete_session_data(self, session, session_id: UUID, user_id: UUID) -> None:
        await self._delete_medical_document(session, session_id)
        await self._delete_clinical_facts(session, session_id)
        await self._delete_transcript(session, session_id)
        await self._delete_audio_record(session, session_id)
        await self._delete_session(session, session_id, user_id)

    async def _delete_medical_document(self, session, session_id: UUID) -> None:
        medical_document = await self.medical_document_repository.get_by_session_id(session, session_id)
        if medical_document is not None:
            await self.medical_document_repository.delete(session, medical_document.id)
            logger.info("Deleted medical document %s for session %s", medical_document.id, session_id)

    async def _delete_clinical_facts(self, session, session_id: UUID) -> None:
        clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, session_id)
        for fact in clinical_facts:
            await self.clinical_fact_repository.delete(session, fact.id)
        if clinical_facts:
            logger.info("Deleted %d clinical facts for session %s", len(clinical_facts), session_id)

    async def _delete_transcript(self, session, session_id: UUID) -> None:
        transcript = await self.transcript_repository.get_by_session_id(session, session_id)
        if transcript is not None:
            await self.transcript_repository.delete(session, transcript.id)
            logger.info("Deleted transcript %s for session %s", transcript.id, session_id)

    async def _delete_audio_record(self, session, session_id: UUID) -> None:
        audio_record = await self.audio_record_repository.get_by_session_id(session, session_id)
        if audio_record is not None:
            await self.audio_record_repository.delete(session, audio_record.id)
            logger.info("Deleted audio record %s for session %s", audio_record.id, session_id)

    async def _delete_session(self, session, session_id: UUID, user_id: UUID) -> None:
        await self.session_repository.delete(session, session_id)
        logger.info("Deleted session %s for user %s", session_id, user_id)
