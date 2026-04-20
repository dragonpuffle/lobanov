from enum import Enum
from typing import List
from uuid import UUID


class FieldValueStatus(str, Enum):
    AUTO_FILLED = "auto_filled"
    USER_EDITED = "user_edited"
    MISSING = "missing"
    DOUBTFUL = "doubtful"
    CONFIRMED = "confirmed"


class DraftFieldValue:
    def __init__(
        self,
        field_id: UUID,
        value: str | None,
        status: FieldValueStatus,
        source_fact_ids: List[UUID] | None = None,
        confidence: float | None = None,
    ) -> None:
        self.field_id = field_id
        self.value = value
        self.status = status
        self.source_fact_ids = source_fact_ids or []
        self.confidence = confidence

    def __repr__(self) -> str:
        return (
            f"DraftFieldValue(field_id={self.field_id}, value={self.value}, "
            f"status={self.status}, confidence={self.confidence})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DraftFieldValue):
            return NotImplemented
        return self.field_id == other.field_id

    def __hash__(self) -> int:
        return hash(self.field_id)
