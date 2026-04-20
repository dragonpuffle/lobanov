from datetime import datetime
from typing import Dict
from uuid import UUID


class FinalMedicalDocument:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        draft_id: UUID,
        template_id: UUID,
        field_values: Dict[str, str],
        confirmed_by: UUID,
        confirmed_at: datetime,
        exported_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.draft_id = draft_id
        self.template_id = template_id
        self.field_values = field_values
        self.confirmed_by = confirmed_by
        self.confirmed_at = confirmed_at
        self.exported_at = exported_at

    def __repr__(self) -> str:
        return (
            f"FinalMedicalDocument(id={self.id}, session_id={self.session_id}, "
            f"template_id={self.template_id}, confirmed_by={self.confirmed_by})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FinalMedicalDocument):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
