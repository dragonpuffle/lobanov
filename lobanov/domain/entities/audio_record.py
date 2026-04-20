from datetime import datetime
from uuid import UUID


class AudioRecord:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        file_path: str,
        file_name: str,
        file_size: int,
        duration: float,
        format: str,
        uploaded_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.file_path = file_path
        self.file_name = file_name
        self.file_size = file_size
        self.duration = duration
        self.format = format
        self.uploaded_at = uploaded_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"AudioRecord(id={self.id}, session_id={self.session_id}, "
            f"file_name={self.file_name}, format={self.format}, "
            f"duration={self.duration}s)"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AudioRecord):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
