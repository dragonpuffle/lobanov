from uuid import UUID

from pydantic import BaseModel

from lobanov.domain.entities.documentation_session import DocumentationSessionStatus


class CreateSessionRequest(BaseModel):
    pass


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: DocumentationSessionStatus
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int


class SessionDetailsResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: DocumentationSessionStatus
    created_at: str
    updated_at: str
    has_audio: bool = False
    has_transcript: bool = False
    has_document: bool = False
