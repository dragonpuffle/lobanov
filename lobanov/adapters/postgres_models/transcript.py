from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.transcript import Transcript as TranscriptEntity
from lobanov.domain.entities.transcript import TranscriptLanguage


class Transcript(Base, IDMixin, TimestampMixin):
    __tablename__ = "transcripts"

    session_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE")
    )
    audio_record_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("audio_records.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[TranscriptLanguage] = mapped_column(SQLEnum(TranscriptLanguage), default=TranscriptLanguage.RU)
    confidence_score: Mapped[float] = mapped_column(Float)

    def to_domain(self) -> TranscriptEntity:
        return TranscriptEntity(
            id=self.id,
            session_id=self.session_id,
            audio_record_id=self.audio_record_id,
            text=self.text,
            language=self.language,
            confidence_score=self.confidence_score,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
