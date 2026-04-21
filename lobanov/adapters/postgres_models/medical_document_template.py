from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate as MedicalDocumentTemplateEntity


class MedicalDocumentTemplate(Base, IDMixin, TimestampMixin):
    __tablename__ = "medical_document_templates"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_domain(self) -> MedicalDocumentTemplateEntity:
        return MedicalDocumentTemplateEntity(
            id=self.id,
            name=self.name,
            description=self.description,
            version=self.version,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
