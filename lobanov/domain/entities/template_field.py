from enum import Enum
from typing import List
from uuid import UUID


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    TEXTAREA = "textarea"


class TemplateField:
    def __init__(
        self,
        id: UUID,
        template_id: UUID,
        name: str,
        label: str,
        field_type: FieldType,
        is_required: bool,
        order: int,
        default_value: str | None = None,
        options: List[str] | None = None,
        validation_regex: str | None = None,
    ) -> None:
        self.id = id
        self.template_id = template_id
        self.name = name
        self.label = label
        self.field_type = field_type
        self.is_required = is_required
        self.order = order
        self.default_value = default_value
        self.options = options or []
        self.validation_regex = validation_regex

    def __repr__(self) -> str:
        return (
            f"TemplateField(id={self.id}, template_id={self.template_id}, "
            f"name={self.name}, field_type={self.field_type}, "
            f"is_required={self.is_required}, order={self.order})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TemplateField):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
