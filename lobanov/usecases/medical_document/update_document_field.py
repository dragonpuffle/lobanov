from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.domain.entities.medical_document import MedicalDocument
from lobanov.protocols.repositories import (
    ClinicalFactRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
    TemplateRepositoryProtocol,
)
from lobanov.usecases.medical_document.validate_required_fields import ValidateRequiredFields


class MedicalDocumentNotFoundError(Exception):
    pass


class TemplateFieldNotFoundError(Exception):
    pass


class InvalidDocumentStateError(Exception):
    pass


class UpdateDocumentField[sessionT]:
    def __init__(
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[sessionT],
        clinical_fact_repository: ClinicalFactRepositoryProtocol[sessionT],
        template_repository: TemplateRepositoryProtocol[sessionT],
        validate_required_fields: ValidateRequiredFields[sessionT],
    ):
        self.medical_document_repository = medical_document_repository
        self.clinical_fact_repository = clinical_fact_repository
        self.template_repository = template_repository
        self.validate_required_fields = validate_required_fields

    async def execute(
        self,
        document_id: UUID,
        field_id: UUID,
        new_value: str,
    ) -> ValidateRequiredFields.DocumentValidationResult:
        async with self.medical_document_repository.context() as session:
            document = await self.medical_document_repository.get_by_id(session, document_id)
            if document is None:
                error_message = f"Medical document with id {document_id} not found"
                raise MedicalDocumentNotFoundError(error_message)

            if document.status.value != "pending":
                error_message = f"Cannot update field in document with status {document.status}"
                raise InvalidDocumentStateError(error_message)

            template_fields = await self.template_repository.get_fields(session, document.template_id)
            field = next((f for f in template_fields if f.id == field_id), None)
            if field is None:
                error_message = f"Field with id {field_id} not found in template"
                raise TemplateFieldNotFoundError(error_message)

            existing_facts = await self.clinical_fact_repository.get_by_template_field_id(
                session, document.session_id, field.id
            )

            if existing_facts:
                for fact in existing_facts:
                    updated_fact = ClinicalFact(
                        id=fact.id,
                        session_id=fact.session_id,
                        transcript_id=fact.transcript_id,
                        template_field_id=fact.template_field_id,
                        is_updated_by_user=True,
                        value=new_value,
                        confidence=1.0,
                        source_text=fact.source_text,
                        source_start_index=fact.source_start_index,
                        source_end_index=fact.source_end_index,
                        created_at=fact.created_at,
                        updated_at=datetime.now(UTC),
                    )
                    await self.clinical_fact_repository.update(session, updated_fact)
            else:
                transcript_id = document.transcript_id
                new_fact = ClinicalFact(
                    id=uuid4(),
                    session_id=document.session_id,
                    transcript_id=transcript_id,
                    template_field_id=field.id,
                    is_updated_by_user=True,
                    value=new_value,
                    confidence=1.0,
                    source_text="",
                    source_start_index=0,
                    source_end_index=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                await self.clinical_fact_repository.create(session, new_fact)

            updated_document = MedicalDocument(
                id=document.id,
                user_id=document.user_id,
                session_id=document.session_id,
                template_id=document.template_id,
                transcript_id=document.transcript_id,
                status=document.status,
                created_at=document.created_at,
                updated_at=datetime.now(UTC),
            )
            await self.medical_document_repository.update(session, updated_document)

            validation_result = await self.validate_required_fields.execute(
                prev_session=session,
                document_id=document_id,
                template_id=document.template_id,
                session_id=document.session_id,
            )

            return validation_result
