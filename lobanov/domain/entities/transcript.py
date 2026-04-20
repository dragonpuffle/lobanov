from datetime import datetime
from uuid import UUID


class Transcript:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        audio_record_id: UUID,
        text: str,
        language: str,
        confidence_score: float,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.audio_record_id = audio_record_id
        self.text = text
        self.language = language
        self.confidence_score = confidence_score
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"Transcript(id={self.id}, session_id={self.session_id}, "
            f"language={self.language}, confidence_score={self.confidence_score})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transcript):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
