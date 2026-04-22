from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain import (
    DocumentationSession,
    DocumentationSessionStatus,
    MedicalDocument,
    MedicalDocumentStatus,
)
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TranscriptRepositoryProtocol,
)


class SessionNotFoundError(Exception):
    pass


class InvalidSessionStateError(Exception):
    pass


class TranscriptNotFoundError(Exception):
    pass


class ClinicalFactsNotFoundError(Exception):
    pass


class GenerateMedicalDocument[SessionT]:
    def __init__(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        medical_document_repository: MedicalDocumentRepositoryProtocol[SessionT],
    ):
        self.session_repository = session_repository
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.medical_document_repository = medical_document_repository

    async def execute(self, session_id: UUID, template_id: UUID) -> MedicalDocument:
        async with self.session_repository.context() as session:
            documentation_session = await self.session_repository.get_by_id(session, session_id)
            if documentation_session is None:
                error_message = f"Session with id {session_id} not found"
                raise SessionNotFoundError(error_message)

            if documentation_session.status != DocumentationSessionStatus.TRANSCRIBED:
                error_message = f"Session must be in TRANSCRIBED state, current state: {documentation_session.status}"
                raise InvalidSessionStateError(error_message)

            transcript = await self.transcript_repository.get_by_session_id(session, session_id)
            if transcript is None:
                error_message = f"Transcript for session {session_id} not found"
                raise TranscriptNotFoundError(error_message)

            clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, session_id)
            if not clinical_facts:
                error_message = f"No clinical facts found for session {session_id}"
                raise ClinicalFactsNotFoundError(error_message)

            now = datetime.now(UTC)
            medical_document = MedicalDocument(
                id=uuid4(),
                user_id=documentation_session.user_id,
                session_id=session_id,
                template_id=template_id,
                transcript_id=transcript.id,
                status=MedicalDocumentStatus.PENDING,
                created_at=now,
                updated_at=now,
            )

            created_document = await self.medical_document_repository.create(session, medical_document)

            updated_session = DocumentationSession(
                id=documentation_session.id,
                template_id=documentation_session.template_id,
                user_id=documentation_session.user_id,
                status=DocumentationSessionStatus.DRAFT_CREATED,
                created_at=documentation_session.created_at,
                updated_at=now,
            )

            await self.session_repository.update(session, updated_session)

            return created_document
