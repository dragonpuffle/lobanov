from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin


class ClinicalFact(Base, IDMixin, TimestampMixin):
    __tablename__ = "clinical_facts"

    session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE"))
    transcript_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE"))
    fact_type: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source_text: Mapped[str] = mapped_column(Text)
    source_start_index: Mapped[int] = mapped_column(Integer)
    source_end_index: Mapped[int] = mapped_column(Integer)

    session = relationship("DocumentationSession")
    transcript = relationship("Transcript", back_populates="clinical_facts")
