from datetime import datetime
from enum import Enum
from uuid import UUID


class SessionStatus(str, Enum):
    CREATED = "created"
    AUDIO_UPLOADED = "audio_uploaded"
    TRANSCRIBED = "transcribed"
    DRAFT_CREATED = "draft_created"
    CONFIRMED = "confirmed"


class DocumentationSession:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        status: SessionStatus,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"DocumentationSession(id={self.id}, user_id={self.user_id}, "
            f"status={self.status})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DocumentationSession):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
