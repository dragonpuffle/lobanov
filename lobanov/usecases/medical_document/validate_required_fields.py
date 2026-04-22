from __future__ import annotations

import contextlib
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.template_field import TemplateField
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    TemplateRepositoryProtocol,
)


class MedicalDocumentNotFoundError(Exception):
    pass


class TemplateNotFoundError(Exception):
    pass


class ValidateRequiredFields[sessionT]:
    def __init__(
        self,
        clinical_fact_repository: ClinicalFactRepositoryProtocol,
        template_repository: TemplateRepositoryProtocol,
    ):
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository

    class FieldValueStatus(StrEnum):
        AUTO_FILLED = "auto_filled"
        USER_EDITED = "user_edited"
        MISSING = "missing"
        DOUBTFUL = "doubtful"
        CONFIRMED = "confirmed"

    @dataclass
    class FieldValidationResult:
        field_id: UUID
        field_name: str
        field_label: str
        is_required: bool
        status: ValidateRequiredFields.FieldValueStatus
        value: str | None
        confidence: float | None
        source_fact_ids: list[UUID]

    @dataclass
    class DocumentValidationResult:
        document_id: UUID
        is_valid: bool
        required_fields_count: int
        filled_required_fields_count: int
        field_results: list[ValidateRequiredFields.FieldValidationResult]

    async def execute(
        self,
        prev_session: sessionT | None,
        document_id: UUID,
        template_id: UUID,
        session_id: UUID,
    ) -> DocumentValidationResult:
        async with contextlib.AsyncExitStack() as deferexit:
            session = (
                prev_session or await deferexit.enter_async_context(self.clinical_fact_repository.context())
            )

            template_fields = await self.template_repository.get_fields(session, template_id)
            if not template_fields:
                error_message = f"Template with id {template_id} not found or has no fields"
                raise TemplateNotFoundError(error_message)

            clinical_facts = await self.clinical_fact_repository.get_by_session_id(session, session_id)

            field_results = self._validate_fields(template_fields, clinical_facts)

            required_fields = [f for f in field_results if f.is_required]
            filled_required_fields = [
                f
                for f in required_fields
                if f.status
                in (
                    self.FieldValueStatus.AUTO_FILLED,
                    self.FieldValueStatus.USER_EDITED,
                    self.FieldValueStatus.CONFIRMED,
                )
            ]

            is_valid = len(filled_required_fields) == len(required_fields)

            return self.DocumentValidationResult(
                document_id=document_id,
                is_valid=is_valid,
                required_fields_count=len(required_fields),
                filled_required_fields_count=len(filled_required_fields),
                field_results=field_results,
            )
        raise

    def _validate_fields(
        self,
        template_fields: list[TemplateField],
        clinical_facts: list[ClinicalFact],
    ) -> list[FieldValidationResult]:
        field_results: list[ValidateRequiredFields.FieldValidationResult] = []

        facts_by_template_field_id: dict[UUID, list[ClinicalFact]] = {}
        for fact in clinical_facts:
            if fact.template_field_id not in facts_by_template_field_id:
                facts_by_template_field_id[fact.template_field_id] = []
            facts_by_template_field_id[fact.template_field_id].append(fact)

        for field in template_fields:
            matching_facts = facts_by_template_field_id.get(field.id, [])

            if not matching_facts:
                if field.is_required and field.default_value:
                    status = self.FieldValueStatus.AUTO_FILLED
                    value = field.default_value
                    confidence = 1.0
                    source_fact_ids = []
                elif field.is_required:
                    status = self.FieldValueStatus.MISSING
                    value = None
                    confidence = None
                    source_fact_ids = []
                else:
                    status = self.FieldValueStatus.MISSING
                    value = None
                    confidence = None
                    source_fact_ids = []
            else:
                best_fact = max(matching_facts, key=lambda f: f.confidence)
                value = best_fact.value
                confidence = best_fact.confidence
                source_fact_ids = [fact.id for fact in matching_facts]

                if best_fact.is_updated_by_user:
                    status = self.FieldValueStatus.USER_EDITED
                elif confidence >= 0.8:
                    status = self.FieldValueStatus.AUTO_FILLED
                else:
                    status = self.FieldValueStatus.DOUBTFUL

            field_results.append(
                self.FieldValidationResult(
                    field_id=field.id,
                    field_name=field.name,
                    field_label=field.label,
                    is_required=field.is_required,
                    status=status,
                    value=value,
                    confidence=confidence,
                    source_fact_ids=source_fact_ids,
                )
            )

        return field_results
