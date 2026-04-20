from datetime import datetime
from enum import Enum
from typing import Dict
from uuid import UUID

from lobanov.domain.entities.draft_field_value import DraftFieldValue


class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


class MedicalDocumentDraft:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        template_id: UUID,
        field_values: Dict[str, DraftFieldValue],
        validation_status: ValidationStatus,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.template_id = template_id
        self.field_values = field_values
        self.validation_status = validation_status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"MedicalDocumentDraft(id={self.id}, session_id={self.session_id}, "
            f"template_id={self.template_id}, validation_status={self.validation_status})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MedicalDocumentDraft):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
