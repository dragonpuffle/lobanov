from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.documentation_session import DocumentationSession as SessionModel
from lobanov.domain.entities.documentation_session import DocumentationSession, DocumentationSessionStatus
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.documentation_session_repository_protocol import (
    DocumentationSessionRepositoryProtocol,
)


class DocumentationSessionRepository(DocumentationSessionRepositoryProtocol[AsyncSession]):
    def __init__(self, session_factory: AsyncSessionFactory) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    @override
    async def context(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @override
    async def create(self, session: AsyncSession, documentation_session: DocumentationSession) -> DocumentationSession:
        session_model = SessionModel(
            id=documentation_session.id,
            user_id=documentation_session.user_id,
            status=documentation_session.status,
            created_at=documentation_session.created_at,
            updated_at=documentation_session.updated_at,
        )
        session.add(session_model)
        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, session_id: UUID) -> DocumentationSession | None:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_by_user_id(
        self, session: AsyncSession, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[DocumentationSession]:
        result = await session.execute(
            select(SessionModel)
            .where(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def update(self, session: AsyncSession, documentation_session: DocumentationSession) -> DocumentationSession:
        result = await session.execute(select(SessionModel).where(SessionModel.id == documentation_session.id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            err_msg = f"Documentation session with id {documentation_session.id} not found"
            raise ValueError(err_msg)

        session_model.status = documentation_session.status
        session_model.updated_at = documentation_session.updated_at

        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def delete(self, session: AsyncSession, session_id: UUID) -> bool:
        result = await session.execute(select(SessionModel).where(SessionModel.id == session_id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            return False

        await session.delete(session_model)
        return True

    @override
    async def get_active_sessions(
        self, session: AsyncSession, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[DocumentationSession]:
        result = await session.execute(
            select(SessionModel)
            .where(SessionModel.user_id == user_id)
            .where(SessionModel.status != DocumentationSessionStatus.CONFIRMED)
            .order_by(SessionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]
