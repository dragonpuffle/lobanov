from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain import ClinicalFact, DocumentationSession, DocumentationSessionStatus
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    DocumentationSessionRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.protocols.services import ClinicalExtractionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


def _source_indices_in_transcript(transcript_text: str, source_text: str) -> tuple[int, int]:
    if not source_text or not transcript_text:
        return 0, 0
    i = transcript_text.find(source_text)
    if i != -1:
        return i, i + len(source_text)
    t_lower = transcript_text.lower()
    s_lower = source_text.lower()
    j = t_lower.find(s_lower)
    if j != -1:
        return j, j + len(source_text)
    return 0, 0


class TranscriptNotFoundError(Exception):
    pass


class TemplateNotFoundError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class ClinicalExtractionError(Exception):
    pass


class ExtractClinicalFacts[SessionT]:
    def __init__(
        self,
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        template_repository: TemplateRepositoryProtocol[SessionT],
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        clinical_extraction_service: ClinicalExtractionProtocol,
    ):
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.session_repository = session_repository
        self.clinical_extraction_service = clinical_extraction_service

    async def execute(self, session: SessionT, transcript_id: UUID) -> list[ClinicalFact]:
        transcript = await self.transcript_repository.get_by_id(session, transcript_id)
        if transcript is None:
            error_message = f"Transcript with id {transcript_id} not found"
            raise TranscriptNotFoundError(error_message)

        documentation_session = await self.session_repository.get_by_id(session, transcript.session_id)
        if documentation_session is None:
            error_message = f"Session with id {transcript.session_id} not found"
            raise SessionNotFoundError(error_message)

        template_id = documentation_session.template_id

        template = await self.template_repository.get_by_id(session, template_id)
        if template is None:
            error_message = f"Template with id {template_id} not found"
            raise TemplateNotFoundError(error_message)

        template_fields = await self.template_repository.get_fields(session, template_id)
        if not template_fields:
            return []

        try:
            extracted_facts = await self.clinical_extraction_service.extract_clinical_facts(
                transcript.text, template_fields
            )
        except Exception as e:
            logger.exception("Clinical fact extraction failed in use case")
            error_message = f"Failed to extract clinical facts: {e}"
            raise ClinicalExtractionError(error_message) from e

        now = datetime.now(UTC)
        created_facts = []

        for fact in extracted_facts:
            start_idx, end_idx = _source_indices_in_transcript(transcript.text, fact.source_text)
            clinical_fact = ClinicalFact(
                id=uuid4(),
                session_id=transcript.session_id,
                transcript_id=transcript_id,
                template_field_id=fact.template_field_id,
                is_updated_by_user=False,
                value=fact.value,
                confidence=fact.confidence,
                source_text=fact.source_text,
                source_start_index=start_idx,
                source_end_index=end_idx,
                created_at=now,
                updated_at=now,
            )

            created_fact = await self.clinical_fact_repository.create(session, clinical_fact)
            created_facts.append(created_fact)

        updated_session = DocumentationSession(
            id=documentation_session.id,
            user_id=documentation_session.user_id,
            template_id=documentation_session.template_id,
            status=DocumentationSessionStatus.FACTS_EXTRACTED,
            created_at=documentation_session.created_at,
            updated_at=now,
        )
        await self.session_repository.update(session, updated_session)

        return created_facts
