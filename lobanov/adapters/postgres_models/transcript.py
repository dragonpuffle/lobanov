from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin


class Transcript(Base, IDMixin, TimestampMixin):
    __tablename__ = "transcripts"

    session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE"))
    audio_record_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("audio_records.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10))
    confidence_score: Mapped[float] = mapped_column(Float)

    session = relationship("DocumentationSession", back_populates="transcript")
    audio_record = relationship("AudioRecord", back_populates="transcripts")
    clinical_facts = relationship("ClinicalFact", back_populates="transcript", cascade="all, delete-orphan")
