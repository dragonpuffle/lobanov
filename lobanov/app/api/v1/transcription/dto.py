from uuid import UUID

from pydantic import BaseModel

from lobanov.domain.entities.transcript import TranscriptLanguage


class TranscribeRequest(BaseModel):
    language: TranscriptLanguage = TranscriptLanguage.RU


class TranscribeResponse(BaseModel):
    task_id: str
    message: str


class TranscriptResponse(BaseModel):
    id: UUID
    session_id: UUID
    audio_record_id: UUID
    text: str
    language: TranscriptLanguage
    confidence_score: float
    created_at: str
