from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from lobanov.adapters.postgres_models.base import Base, IDMixin, TimestampMixin
from lobanov.domain.entities.documentation_session import DocumentationSessionStatus


class DocumentationSession(Base, IDMixin, TimestampMixin):
    __tablename__ = "documentation_sessions"

    user_id: Mapped[PG_UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[DocumentationSessionStatus] = mapped_column(
        SQLEnum(DocumentationSessionStatus), default=DocumentationSessionStatus.CREATED
    )

    __table_args__ = (Index("ix_documentation_sessions_user_id", "user_id"),)
