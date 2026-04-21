from enum import StrEnum
from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class TranscriptLanguage(StrEnum):
    RU = "ru"


class Transcript(TimeBaseModel):
    id: UUID
    session_id: UUID
    audio_record_id: UUID
    text: str
    language: TranscriptLanguage
    confidence_score: float
