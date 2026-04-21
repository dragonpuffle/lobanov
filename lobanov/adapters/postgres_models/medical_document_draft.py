from sqlalchemy import Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.medical_document_draft import ValidationStatus


class MedicalDocumentDraft(Base, IDMixin, TimestampMixin):
    __tablename__ = "medical_document_drafts"

    session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE"))
    template_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("medical_document_templates.id"))
    field_values: Mapped[dict] = mapped_column(JSONB)
    validation_status: Mapped[ValidationStatus] = mapped_column(SQLEnum(ValidationStatus), default=ValidationStatus.PENDING)

    session = relationship("DocumentationSession", back_populates="draft")
    template = relationship("MedicalDocumentTemplate", back_populates="drafts")
    final_document = relationship("FinalMedicalDocument", back_populates="draft", uselist=False)
