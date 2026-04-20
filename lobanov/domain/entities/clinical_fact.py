from datetime import datetime
from uuid import UUID


class ClinicalFact:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        transcript_id: UUID,
        fact_type: str,
        value: str,
        confidence: float,
        source_text: str,
        source_start_index: int,
        source_end_index: int,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.session_id = session_id
        self.transcript_id = transcript_id
        self.fact_type = fact_type
        self.value = value
        self.confidence = confidence
        self.source_text = source_text
        self.source_start_index = source_start_index
        self.source_end_index = source_end_index
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"ClinicalFact(id={self.id}, session_id={self.session_id}, "
            f"fact_type={self.fact_type}, value={self.value}, "
            f"confidence={self.confidence})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClinicalFact):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
