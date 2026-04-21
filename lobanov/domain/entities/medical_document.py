from enum import StrEnum
from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class MedicalDocumentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"


class MedicalDocument(TimeBaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    template_id: UUID
    transcript_id: UUID
    status: MedicalDocumentStatus
