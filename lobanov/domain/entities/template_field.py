from uuid import UUID

from lobanov.utils.time_base_model import TimeBaseModel


class TemplateField(TimeBaseModel):
    id: UUID
    template_id: UUID
    name: str
    label: str
    is_required: bool
    default_value: str | None = None
    options: dict | None = None
    order: int
