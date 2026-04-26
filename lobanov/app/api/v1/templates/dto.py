from uuid import UUID

from pydantic import BaseModel


class TemplateFieldDTO(BaseModel):
    id: UUID
    name: str
    label: str
    is_required: bool
    default_value: str | None = None
    options: dict | None = None
    order: int


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    description: str
    version: str
    is_active: bool
    created_at: str
    updated_at: str


class TemplateDetailsResponse(BaseModel):
    id: UUID
    name: str
    description: str
    version: str
    is_active: bool
    created_at: str
    updated_at: str
    fields: list[TemplateFieldDTO]


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int
