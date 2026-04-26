from uuid import UUID

from pydantic import BaseModel

from lobanov.domain.entities.medical_document import MedicalDocumentStatus


class FieldValueStatus:
    AUTO_FILLED = "auto_filled"
    USER_EDITED = "user_edited"
    MISSING = "missing"
    DOUBTFUL = "doubtful"
    CONFIRMED = "confirmed"


class FieldValueDTO(BaseModel):
    field_id: UUID
    field_name: str
    field_label: str
    value: str | None
    status: str
    is_required: bool
    confidence: float | None = None
    source_text: str | None = None
    source_start_index: int | None = None
    source_end_index: int | None = None


class GenerateDocumentRequest(BaseModel):
    template_id: UUID


class GenerateDocumentResponse(BaseModel):
    task_id: str
    message: str


class MedicalDocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    template_id: UUID
    transcript_id: UUID
    status: MedicalDocumentStatus
    created_at: str
    updated_at: str


class MedicalDocumentDetailsResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    template_id: UUID
    template_name: str
    transcript_id: UUID
    transcript_text: str
    status: MedicalDocumentStatus
    created_at: str
    updated_at: str
    field_values: list[FieldValueDTO]
    validation_status: dict[str, bool]


class UpdateFieldRequest(BaseModel):
    value: str


class UpdateFieldResponse(BaseModel):
    field_id: UUID
    value: str
    status: str


class ValidateDocumentResponse(BaseModel):
    is_valid: bool
    missing_fields: list[str]
    doubtful_fields: list[str]
    required_fields_count: int
    filled_fields_count: int


class ConfirmDocumentRequest(BaseModel):
    pass


class ConfirmDocumentResponse(BaseModel):
    id: UUID
    status: MedicalDocumentStatus
    message: str


class ExportDocumentRequest(BaseModel):
    format: str = "json"
