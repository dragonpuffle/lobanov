from enum import StrEnum
from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class TemplateFieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    TEXTAREA = "textarea"


class TemplateField(TimeBaseModel):
    id: UUID
    template_id: UUID
    name: str
    label: str
    field_type: TemplateFieldType
    is_required: bool
    default_value: str | None = None
    options: dict | None = None
    order: int
