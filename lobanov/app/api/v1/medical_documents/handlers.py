from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.app.api.v1.dependencies import get_current_user
from lobanov.app.api.v1.medical_documents.dto import (
    ConfirmDocumentResponse,
    ExportDocumentRequest,
    ExportDocumentResponse,
    FieldValueDTO,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    MedicalDocumentDetailsResponse,
    UpdateFieldRequest,
    UpdateFieldResponse,
    ValidateDocumentResponse,
)
from lobanov.domain.entities.user import User
from lobanov.protocols.repositories import MedicalDocumentRepositoryProtocol, TemplateRepositoryProtocol
from lobanov.usecases.medical_document import (
    ConfirmDocument,
    GenerateMedicalDocument,
    ReviewMedicalDocument,
    SaveDocument,
    UpdateDocumentField,
    ValidateRequiredFields,
)

router = APIRouter(prefix="/sessions/{session_id}/document", tags=["medical_documents"])


class MedicalDocumentHandlerError(Exception):
    pass


class SessionNotFoundError(MedicalDocumentHandlerError):
    pass


class MedicalDocumentNotFoundError(MedicalDocumentHandlerError):
    pass


class InvalidSessionStateError(MedicalDocumentHandlerError):
    pass


class InvalidDocumentStateError(MedicalDocumentHandlerError):
    pass


class TemplateNotFoundError(MedicalDocumentHandlerError):
    pass


class RequiredFieldsNotFilledError(MedicalDocumentHandlerError):
    pass


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_document(
    session_id: str,
    request: GenerateDocumentRequest,
    generate_document_use_case: GenerateMedicalDocument[AsyncSession],
) -> GenerateDocumentResponse:
    try:
        session_uuid = UUID(session_id)

        document = await generate_document_use_case.execute(
            session_id=session_uuid,
            template_id=request.template_id,
        )

        return GenerateDocumentResponse(
            task_id=str(document.id),
            message="Document generated successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            if "session" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
            if "transcript" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
            if "clinical facts" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
        if "state" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate document",
        ) from e


@router.get("")
async def get_document(
    session_id: str,
    medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    template_repository: TemplateRepositoryProtocol[AsyncSession],
    review_document_use_case: ReviewMedicalDocument[AsyncSession],
) -> MedicalDocumentDetailsResponse:
    try:
        session_uuid = UUID(session_id)

        async with medical_document_repository.context() as session:
            document = await medical_document_repository.get_by_session_id(session, session_uuid)

            if document is None:
                error_message = f"Document not found for session {session_id}"
                raise MedicalDocumentNotFoundError(error_message)

            template = await template_repository.get_by_id(session, document.template_id)
            if template is None:
                error_message = f"Template not found for document {document.id}"
                raise TemplateNotFoundError(error_message)

            review_result = await review_document_use_case.execute(document.id)

            field_values = [
                FieldValueDTO(
                    field_id=fv.field_id,
                    field_name=fv.field_name,
                    field_label=fv.field_label,
                    value=fv.value,
                    status=fv.status.value,
                    is_required=fv.is_required,
                    confidence=fv.confidence,
                    source_text=fv.source_references[0].text if fv.source_references else None,
                    source_start_index=fv.source_references[0].start_index if fv.source_references else None,
                    source_end_index=fv.source_references[0].end_index if fv.source_references else None,
                )
                for fv in review_result.field_values
            ]

            validation_status = {
                fr.field_name: fr.status.value in ("auto_filled", "user_edited", "confirmed")
                for fr in review_result.validation_result.field_results
            }

            return MedicalDocumentDetailsResponse(
                id=document.id,
                user_id=document.user_id,
                session_id=document.session_id,
                template_id=document.template_id,
                template_name=template.name,
                transcript_id=document.transcript_id,
                transcript_text=review_result.transcript.text,
                status=document.status,
                created_at=document.created_at.isoformat(),
                updated_at=document.updated_at.isoformat(),
                field_values=field_values,
                validation_status=validation_status,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except (MedicalDocumentNotFoundError, TemplateNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document",
        ) from e


@router.put("/fields/{field_id}")
async def update_field(
    session_id: str,
    field_id: str,
    request: UpdateFieldRequest,
    _: Annotated[User, Depends(get_current_user)],
    medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    update_field_use_case: UpdateDocumentField[AsyncSession],
) -> UpdateFieldResponse:
    try:
        session_uuid = UUID(session_id)
        field_uuid = UUID(field_id)

        async with medical_document_repository.context() as session:
            document = await medical_document_repository.get_by_session_id(session, session_uuid)

            if document is None:
                error_message = f"Document not found for session {session_id}"
                raise MedicalDocumentNotFoundError(error_message)

            validation_result = await update_field_use_case.execute(
                document_id=document.id,
                field_id=field_uuid,
                new_value=request.value,
            )

            field_result = next(
                (fr for fr in validation_result.field_results if fr.field_id == field_uuid),
                None,
            )

            if field_result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Field {field_id} not found in validation results",
                )

            return UpdateFieldResponse(
                field_id=field_uuid,
                value=request.value,
                status=field_result.status,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ID: {e!s}",
        ) from e
    except MedicalDocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        if "state" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update field",
        ) from e


@router.get("/validate")
async def validate_document(
    session_id: str,
    _: Annotated[User, Depends(get_current_user)],
    medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    validate_required_fields_use_case: ValidateRequiredFields[AsyncSession],
) -> ValidateDocumentResponse:
    try:
        session_uuid = UUID(session_id)

        async with medical_document_repository.context() as session:
            document = await medical_document_repository.get_by_session_id(session, session_uuid)

            if document is None:
                error_message = f"Document not found for session {session_id}"
                raise MedicalDocumentNotFoundError(error_message)

            validation_result = await validate_required_fields_use_case.execute(
                prev_session=session,
                document_id=document.id,
                template_id=document.template_id,
                session_id=session_uuid,
            )

            missing_fields = [
                fr.field_name
                for fr in validation_result.field_results
                if fr.is_required and fr.status.value == "missing"
            ]

            doubtful_fields = [fr.field_name for fr in validation_result.field_results if fr.status.value == "doubtful"]

            return ValidateDocumentResponse(
                is_valid=validation_result.is_valid,
                missing_fields=missing_fields,
                doubtful_fields=doubtful_fields,
                required_fields_count=validation_result.required_fields_count,
                filled_fields_count=validation_result.filled_required_fields_count,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except MedicalDocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate document",
        ) from e


@router.post("/confirm")
async def confirm_document(
    session_id: str,
    _: Annotated[User, Depends(get_current_user)],
    medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    confirm_document_use_case: ConfirmDocument[AsyncSession],
) -> ConfirmDocumentResponse:
    try:
        session_uuid = UUID(session_id)

        async with medical_document_repository.context() as session:
            document = await medical_document_repository.get_by_session_id(session, session_uuid)

            if document is None:
                error_message = f"Document not found for session {session_id}"
                raise MedicalDocumentNotFoundError(error_message)

            confirmed_document = await confirm_document_use_case.execute(document.id)

            return ConfirmDocumentResponse(
                id=confirmed_document.id,
                status=confirmed_document.status,
                message="Document confirmed successfully",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except MedicalDocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        if "state" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        if "required fields" in error_msg or "missing" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm document",
        ) from e


@router.post("/export")
async def export_document(
    session_id: str,
    request: ExportDocumentRequest,
    _: Annotated[User, Depends(get_current_user)],
    medical_document_repository: MedicalDocumentRepositoryProtocol[AsyncSession],
    save_document_use_case: SaveDocument[AsyncSession],
) -> ExportDocumentResponse:
    try:
        session_uuid = UUID(session_id)

        async with medical_document_repository.context() as session:
            document = await medical_document_repository.get_by_session_id(session, session_uuid)

            if document is None:
                error_message = f"Document not found for session {session_id}"
                raise MedicalDocumentNotFoundError(error_message)

            file_path = await save_document_use_case.execute(
                document_id=document.id,
                output_format=request.format,
            )

            return ExportDocumentResponse(
                task_id=str(document.id),
                message=f"Document exported successfully to {file_path}",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session ID: {e!s}",
        ) from e
    except MedicalDocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        if "state" in error_msg or "status" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        if "unsupported format" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export document",
        ) from e
