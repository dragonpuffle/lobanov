from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.clinical_fact import ClinicalFact as ClinicalFactEntity


class ClinicalFact(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinical_facts"

    session_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE")
    )
    transcript_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE")
    )
    template_field_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("template_fields.id", ondelete="CASCADE")
    )
    is_updated_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source_text: Mapped[str] = mapped_column(Text)
    source_start_index: Mapped[int] = mapped_column(Integer)
    source_end_index: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        Index("ix_clinical_facts_session_id", "session_id"),
        Index("ix_clinical_facts_transcript_id", "transcript_id"),
        Index("ix_clinical_facts_template_field_id", "template_field_id"),
    )

    def to_domain(self) -> ClinicalFactEntity:
        return ClinicalFactEntity(
            id=self.id,
            session_id=self.session_id,
            transcript_id=self.transcript_id,
            template_field_id=self.template_field_id,
            is_updated_by_user=self.is_updated_by_user,
            value=self.value,
            confidence=self.confidence,
            source_text=self.source_text,
            source_start_index=self.source_start_index,
            source_end_index=self.source_end_index,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
