from uuid import UUID

from pydantic import BaseModel


class AudioUploadResponse(BaseModel):
    id: UUID
    session_id: UUID
    file_name: str
    file_size: int
    duration: float
    format: str
    uploaded_at: str


class AudioInfoResponse(BaseModel):
    id: UUID
    session_id: UUID
    file_name: str
    file_size: int
    duration: float
    format: str
    uploaded_at: str
