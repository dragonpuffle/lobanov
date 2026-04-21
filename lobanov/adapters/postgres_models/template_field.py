from datetime import UTC, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.template_field import TemplateField as TemplateFieldEntity
from lobanov.domain.entities.template_field import TemplateFieldType


class TemplateField(Base, IDMixin, TimestampMixin):
    __tablename__ = "template_fields"

    template_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("medical_document_templates.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(255))
    field_type: Mapped[TemplateFieldType] = mapped_column(SQLEnum(TemplateFieldType))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    order: Mapped[int] = mapped_column(Integer)

    def to_domain(self) -> TemplateFieldEntity:
        return TemplateFieldEntity(
            id=self.id,
            template_id=self.template_id,
            name=self.name,
            label=self.label,
            field_type=self.field_type,
            is_required=self.is_required,
            default_value=self.default_value,
            options=self.options,
            order=self.order,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
