from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin


class AudioRecord(Base, IDMixin):
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
