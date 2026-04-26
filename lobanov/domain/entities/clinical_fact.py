from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class ClinicalFact(TimeBaseModel):
    id: UUID
    session_id: UUID
    transcript_id: UUID
    template_field_id: UUID
    is_updated_by_user: bool
    value: str
    confidence: float
    source_text: str
    source_start_index: int
    source_end_index: int
