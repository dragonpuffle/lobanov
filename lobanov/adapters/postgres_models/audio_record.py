from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.audio_record import AudioRecord as AudioRecordEntity


class AudioRecord(Base, IDMixin, TimestampMixin):
    __tablename__ = "audio_records"

    session_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE")
    )
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    format: Mapped[str] = mapped_column(String(50))

    __table_args__ = (Index("ix_audio_records_session_id", "session_id"),)

    def to_domain(self) -> AudioRecordEntity:
        return AudioRecordEntity(
            id=self.id,
            session_id=self.session_id,
            file_path=self.file_path,
            file_name=self.file_name,
            file_size=self.file_size,
            duration=self.duration,
            format=self.format,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
