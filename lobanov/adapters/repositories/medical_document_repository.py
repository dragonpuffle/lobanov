from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.medical_document import MedicalDocument as MedicalDocumentModel
from lobanov.domain.entities.medical_document import MedicalDocument
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.medical_document_repository_protocol import MedicalDocumentRepositoryProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class MedicalDocumentRepository(MedicalDocumentRepositoryProtocol[AsyncSession]):
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
                logger.exception("Transaction failed; rolling back")
                await session.rollback()
                raise

    @override
    async def create(self, session: AsyncSession, document: MedicalDocument) -> MedicalDocument:
        session_model = MedicalDocumentModel(
            id=document.id,
            user_id=document.user_id,
            session_id=document.session_id,
            template_id=document.template_id,
            transcript_id=document.transcript_id,
            status=document.status,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        session.add(session_model)
        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, document_id: UUID) -> MedicalDocument | None:
        result = await session.execute(select(MedicalDocumentModel).where(MedicalDocumentModel.id == document_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_by_user_id(
        self, session: AsyncSession, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[MedicalDocument]:
        result = await session.execute(
            select(MedicalDocumentModel)
            .where(MedicalDocumentModel.user_id == user_id)
            .order_by(MedicalDocumentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def get_by_session_id(self, session: AsyncSession, session_id: UUID) -> MedicalDocument | None:
        result = await session.execute(
            select(MedicalDocumentModel).where(MedicalDocumentModel.session_id == session_id)
        )
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def update(self, session: AsyncSession, document: MedicalDocument) -> MedicalDocument:
        result = await session.execute(select(MedicalDocumentModel).where(MedicalDocumentModel.id == document.id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            err_msg = f"Medical document with id {document.id} not found"
            raise ValueError(err_msg)

        session_model.status = document.status
        session_model.updated_at = document.updated_at

        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def delete(self, session: AsyncSession, document_id: UUID) -> bool:
        result = await session.execute(select(MedicalDocumentModel).where(MedicalDocumentModel.id == document_id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            return False

        await session.delete(session_model)
        return True
