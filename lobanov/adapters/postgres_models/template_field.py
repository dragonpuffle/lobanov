from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin
from lobanov.domain.enums.field_value_type import FieldValueType


class TemplateField(Base, IDMixin):
    __tablename__ = "template_fields"

    template_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("medical_document_templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(255))
    field_type: Mapped[FieldValueType] = mapped_column(SQLEnum(FieldValueType))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_regex: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order: Mapped[int] = mapped_column(Integer)

    template = relationship("MedicalDocumentTemplate", back_populates="fields")
