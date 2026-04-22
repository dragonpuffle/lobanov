from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.medical_document import MedicalDocument
from lobanov.domain.entities.template_field import TemplateField
from lobanov.domain.entities.transcript import Transcript
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TemplateRepositoryProtocol,
    TranscriptRepositoryProtocol,
)
from lobanov.usecases.medical_document.validate_required_fields import ValidateRequiredFields

if TYPE_CHECKING:
    from uuid import UUID


HIGH_CONFIDENCE_THRESHOLD = 0.8
LOW_CONFIDENCE_THRESHOLD = 0.5


class MedicalDocumentNotFoundError(Exception):
    pass


class TranscriptNotFoundError(Exception):
    pass


class ReviewMedicalDocument[sessionT]:
    def __init__(
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[sessionT],
        transcript_repository: TranscriptRepositoryProtocol[sessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[sessionT],
        template_repository: TemplateRepositoryProtocol[sessionT],
        validate_required_fields: ValidateRequiredFields[sessionT],
    ):
        self.medical_document_repository = medical_document_repository
        self.transcript_repository = transcript_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.validate_required_fields = validate_required_fields

    @dataclass
    class SourceTextReference:
        text: str
        start_index: int
        end_index: int
        fact_id: UUID

    @dataclass
    class FieldValueWithSource:
        field_id: UUID
        field_name: str
        field_label: str
        is_required: bool
        value: str | None
        status: ValidateRequiredFields.FieldValueStatus
        confidence: float | None
        source_references: list[ReviewMedicalDocument.SourceTextReference]

    @dataclass
    class DocumentReviewResult:
        document: MedicalDocument
        transcript: Transcript
        field_values: list[ReviewMedicalDocument.FieldValueWithSource]
        validation_result: ValidateRequiredFields.DocumentValidationResult
        is_ready_for_confirmation: bool

    async def execute(self, document_id: UUID) -> DocumentReviewResult:
        async with self.medical_document_repository.context() as session:
            document = await self.medical_document_repository.get_by_id(session, document_id)
            if document is None:
                error_message = f"Medical document with id {document_id} not found"
                raise MedicalDocumentNotFoundError(error_message)

            transcript = await self.transcript_repository.get_by_id(session, document.transcript_id)
            if transcript is None:
                error_message = f"Transcript with id {document.transcript_id} not found"
                raise TranscriptNotFoundError(error_message)

            clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, document.session_id)
            template_fields = await self.template_repository.get_fields(session, document.template_id)

            field_values = self._build_field_values(template_fields, clinical_facts)

            validation_result = await self.validate_required_fields.execute(
                prev_session=session,
                document_id=document_id,
                template_id=document.template_id,
                session_id=document.session_id,
            )

            is_ready_for_confirmation = self._check_ready_for_confirmation(field_values)

            return self.DocumentReviewResult(
                document=document,
                transcript=transcript,
                field_values=field_values,
                validation_result=validation_result,
                is_ready_for_confirmation=is_ready_for_confirmation,
            )

    def _build_field_values(
        self,
        template_fields: list[TemplateField],
        clinical_facts: list[ClinicalFact],
    ) -> list[FieldValueWithSource]:
        field_values = []

        facts_by_template_field_id = {}
        for fact in clinical_facts:
            if fact.template_field_id not in facts_by_template_field_id:
                facts_by_template_field_id[fact.template_field_id] = []
            facts_by_template_field_id[fact.template_field_id].append(fact)

        for field in template_fields:
            matching_facts = facts_by_template_field_id.get(field.id, [])

            if not matching_facts:
                if field.is_required and field.default_value:
                    value = field.default_value
                    status = ValidateRequiredFields.FieldValueStatus.AUTO_FILLED
                    confidence = 1.0
                    source_references = []
                else:
                    value = None
                    status = ValidateRequiredFields.FieldValueStatus.MISSING
                    confidence = None
                    source_references = []
            else:
                best_fact = max(matching_facts, key=lambda f: f.confidence)
                value = best_fact.value
                confidence = best_fact.confidence

                if best_fact.is_updated_by_user:
                    status = ValidateRequiredFields.FieldValueStatus.USER_EDITED
                elif confidence >= HIGH_CONFIDENCE_THRESHOLD:
                    status = ValidateRequiredFields.FieldValueStatus.AUTO_FILLED
                else:
                    status = ValidateRequiredFields.FieldValueStatus.DOUBTFUL

                source_references = [
                    self.SourceTextReference(
                        text=fact.source_text,
                        start_index=fact.source_start_index,
                        end_index=fact.source_end_index,
                        fact_id=fact.id,
                    )
                    for fact in matching_facts
                ]

            field_values.append(
                self.FieldValueWithSource(
                    field_id=field.id,
                    field_name=field.name,
                    field_label=field.label,
                    is_required=field.is_required,
                    value=value,
                    status=status,
                    confidence=confidence,
                    source_references=source_references,
                )
            )

        return field_values

    def _check_ready_for_confirmation(self, field_values: list[FieldValueWithSource]) -> bool:
        required_fields = [fv for fv in field_values if fv.is_required]

        for field_value in required_fields:
            if field_value.status == ValidateRequiredFields.FieldValueStatus.MISSING:
                return False
            if (
                field_value.status == ValidateRequiredFields.FieldValueStatus.DOUBTFUL
                and field_value.confidence is not None
                and field_value.confidence < LOW_CONFIDENCE_THRESHOLD
            ):
                return False

        return True
