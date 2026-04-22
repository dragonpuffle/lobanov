from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain import ClinicalFact
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.protocols.services import ClinicalExtractionProtocol


class TranscriptNotFoundError(Exception):
    pass


class TemplateNotFoundError(Exception):
    pass


class ClinicalExtractionError(Exception):
    pass


class ExtractClinicalFacts[SessionT]:
    def __init__(
        self,
        transcript_repository: TranscriptRepositoryProtocol[SessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[SessionT],
        template_repository: TemplateRepositoryProtocol[SessionT],
        clinical_extraction_service: ClinicalExtractionProtocol,
    ):
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.clinical_extraction_service = clinical_extraction_service

    async def execute(self, session: SessionT, transcript_id: UUID, template_id: UUID) -> list[ClinicalFact]:
        transcript = await self.transcript_repository.get_by_id(session, transcript_id)
        if transcript is None:
            error_message = f"Transcript with id {transcript_id} not found"
            raise TranscriptNotFoundError(error_message)

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
            error_message = f"Failed to extract clinical facts: {e}"
            raise ClinicalExtractionError(error_message) from e

        now = datetime.now(UTC)
        created_facts = []

        for fact in extracted_facts:
            clinical_fact = ClinicalFact(
                id=uuid4(),
                session_id=transcript.session_id,
                transcript_id=transcript_id,
                template_field_id=fact.template_field_id,
                is_updated_by_user=False,
                value=fact.value,
                confidence=fact.confidence,
                source_text=fact.source_text,
                source_start_index=fact.source_start_index,
                source_end_index=fact.source_end_index,
                created_at=now,
                updated_at=now,
            )

            created_fact = await self.clinical_fact_repository.create(session, clinical_fact)
            created_facts.append(created_fact)

        return created_facts
