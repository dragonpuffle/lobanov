from datetime import datetime
from uuid import UUID


class MedicalDocumentTemplate:
    def __init__(
        self,
        id: UUID,
        name: str,
        description: str,
        version: str,
        is_active: bool = True,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.version = version
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"MedicalDocumentTemplate(id={self.id}, name={self.name}, "
            f"version={self.version}, is_active={self.is_active})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MedicalDocumentTemplate):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
