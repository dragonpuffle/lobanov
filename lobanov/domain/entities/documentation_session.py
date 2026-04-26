from enum import StrEnum
from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class DocumentationSessionStatus(StrEnum):
    CREATED = "created"
    AUDIO_UPLOADED = "audio_uploaded"
    TRANSCRIBED = "transcribed"
    FACTS_EXTRACTED = "facts_extracted"
    DRAFT_CREATED = "draft_created"
    CONFIRMED = "confirmed"


class DocumentationSession(TimeBaseModel):
    id: UUID
    user_id: UUID
    template_id: UUID
    status: DocumentationSessionStatus
