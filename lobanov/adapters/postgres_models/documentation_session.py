from sqlalchemy import Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.enums.session_status import SessionStatus


class DocumentationSession(Base, IDMixin, TimestampMixin):
    __tablename__ = "documentation_sessions"

    user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.CREATED)

    user = relationship("User", back_populates="sessions")
    audio_record = relationship("AudioRecord", back_populates="session", cascade="all, delete-orphan", uselist=False)
    transcript = relationship("Transcript", back_populates="session", cascade="all, delete-orphan", uselist=False)
    draft = relationship("MedicalDocumentDraft", back_populates="session", cascade="all, delete-orphan", uselist=False)
    final_document = relationship("FinalMedicalDocument", back_populates="session", cascade="all, delete-orphan", uselist=False)
