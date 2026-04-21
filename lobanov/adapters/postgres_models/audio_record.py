import datetime

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin


class AudioRecord(Base, IDMixin):
    __tablename__ = "audio_records"

    session_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documentation_sessions.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    format: Mapped[str] = mapped_column(String(50))
    uploaded_at: Mapped[datetime.datetime] = mapped_column(server_default=datetime.datetime.utcnow)

    session = relationship("DocumentationSession", back_populates="audio_record")
    transcripts = relationship("Transcript", back_populates="audio_record", cascade="all, delete-orphan")
