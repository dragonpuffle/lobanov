from datetime import UTC, datetime
from uuid import UUID

from lobanov.domain import (
    DocumentationSession,
    DocumentationSessionStatus,
    MedicalDocument,
    MedicalDocumentStatus,
)
from lobanov.protocols.repositories import (
    DocumentationSessionRepositoryProtocol,
    MedicalDocumentRepositoryProtocol,
)
from lobanov.usecases.medical_document.validate_required_fields import (
    ValidateRequiredFields,
)


class MedicalDocumentNotFoundError(Exception):
    pass


class InvalidDocumentStateError(Exception):
    pass


class RequiredFieldsNotFilledError(Exception):
    pass


class ConfirmDocument[SessionT]:
    def __init__(
        self,
        medical_document_repository: MedicalDocumentRepositoryProtocol[SessionT],
        session_repository: DocumentationSessionRepositoryProtocol[SessionT],
        validate_required_fields: ValidateRequiredFields[SessionT],
    ):
        self.medical_document_repository = medical_document_repository
        self.session_repository = session_repository
        self.validate_required_fields = validate_required_fields

    async def execute(self, document_id: UUID) -> MedicalDocument:
        async with self.medical_document_repository.context() as session:
            document = await self.medical_document_repository.get_by_id(session, document_id)
            if document is None:
                error_message = f"Medical document with id {document_id} not found"
                raise MedicalDocumentNotFoundError(error_message)

            if document.status != MedicalDocumentStatus.PENDING:
                error_message = f"Document is already in {document.status} status and cannot be confirmed"
                raise InvalidDocumentStateError(error_message)

            validation_result = await self.validate_required_fields.execute(
                prev_session=session,
                document_id=document_id,
                template_id=document.template_id,
                session_id=document.session_id,
            )

            if not validation_result.is_valid:
                missing_fields = [
                    fr.field_name
                    for fr in validation_result.field_results
                    if fr.is_required and fr.status.value == "missing"
                ]
                error_message = f"Cannot confirm document: required fields are missing: {', '.join(missing_fields)}"
                raise RequiredFieldsNotFilledError(error_message)

            now = datetime.now(UTC)

            updated_document = MedicalDocument(
                id=document.id,
                user_id=document.user_id,
                session_id=document.session_id,
                template_id=document.template_id,
                transcript_id=document.transcript_id,
                status=MedicalDocumentStatus.CONFIRMED,
                created_at=document.created_at,
                updated_at=now,
            )

            confirmed_document = await self.medical_document_repository.update(session, updated_document)

            documentation_session = await self.session_repository.get_by_id(session, document.session_id)
            if documentation_session is not None:
                updated_session = DocumentationSession(
                    id=documentation_session.id,
                    user_id=documentation_session.user_id,
                    status=DocumentationSessionStatus.CONFIRMED,
                    created_at=documentation_session.created_at,
                    updated_at=now,
                )
                await self.session_repository.update(session, updated_session)

            return confirmed_document
