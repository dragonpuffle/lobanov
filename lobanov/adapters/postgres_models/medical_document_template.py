from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin


class MedicalDocumentTemplate(Base, IDMixin, TimestampMixin):
    __tablename__ = "medical_document_templates"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    fields = relationship("TemplateField", back_populates="template", cascade="all, delete-orphan")
    drafts = relationship("MedicalDocumentDraft", back_populates="template")
    final_documents = relationship("FinalMedicalDocument", back_populates="template")
