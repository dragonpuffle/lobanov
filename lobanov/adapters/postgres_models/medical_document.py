from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.medical_document import MedicalDocument as MedicalDocumentEntity
from lobanov.domain.entities.medical_document import MedicalDocumentStatus


class MedicalDocument(Base, IDMixin, TimestampMixin):
    __tablename__ = "medical_documents"

    user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    session_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE")
    )
    template_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("medical_document_templates.id"))
    transcript_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE")
    )
    status: Mapped[MedicalDocumentStatus] = mapped_column(
        SQLEnum(MedicalDocumentStatus), default=MedicalDocumentStatus.PENDING
    )

    __table_args__ = (
        Index("ix_medical_documents_user_id", "user_id"),
        Index("ix_medical_documents_session_id", "session_id"),
        Index("ix_medical_documents_transcript_id", "transcript_id"),
    )

    def to_domain(self) -> MedicalDocumentEntity:
        return MedicalDocumentEntity(
            id=self.id,
            user_id=self.user_id,
            session_id=self.session_id,
            template_id=self.template_id,
            transcript_id=self.transcript_id,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
