from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin


class FinalMedicalDocument(Base, IDMixin):
    __tablename__ = "final_medical_documents"

    session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE"))
    draft_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("medical_document_drafts.id", ondelete="CASCADE"))
    template_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("medical_document_templates.id"))
    field_values: Mapped[dict] = mapped_column(JSONB)
    confirmed_by: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("DocumentationSession", back_populates="final_document")
    draft = relationship("MedicalDocumentDraft", back_populates="final_document")
    template = relationship("MedicalDocumentTemplate", back_populates="final_documents")
    user = relationship("User")
