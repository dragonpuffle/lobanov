from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.medical_document_template import MedicalDocumentTemplate as TemplateModel
from lobanov.adapters.postgres_models.template_field import TemplateField as TemplateFieldModel
from lobanov.domain.entities.medical_document_template import MedicalDocumentTemplate
from lobanov.domain.entities.template_field import TemplateField
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.template_repository_protocol import TemplateRepositoryProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateRepository(TemplateRepositoryProtocol[AsyncSession]):
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
    async def create(self, session: AsyncSession, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        session_model = TemplateModel(
            id=template.id,
            name=template.name,
            description=template.description,
            version=template.version,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )
        session.add(session_model)
        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, template_id: UUID) -> MedicalDocumentTemplate | None:
        result = await session.execute(select(TemplateModel).where(TemplateModel.id == template_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_all(self, session: AsyncSession, limit: int = 100, offset: int = 0) -> list[MedicalDocumentTemplate]:
        result = await session.execute(
            select(TemplateModel).order_by(TemplateModel.created_at.desc()).offset(offset).limit(limit)
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def get_active(
        self, session: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[MedicalDocumentTemplate]:
        result = await session.execute(
            select(TemplateModel)
            .where(TemplateModel.is_active)
            .order_by(TemplateModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def update(self, session: AsyncSession, template: MedicalDocumentTemplate) -> MedicalDocumentTemplate:
        result = await session.execute(select(TemplateModel).where(TemplateModel.id == template.id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            err_msg = f"Medical document template with id {template.id} not found"
            raise ValueError(err_msg)

        session_model.name = template.name
        session_model.description = template.description
        session_model.version = template.version
        session_model.is_active = template.is_active
        session_model.updated_at = template.updated_at

        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def delete(self, session: AsyncSession, template_id: UUID) -> bool:
        result = await session.execute(select(TemplateModel).where(TemplateModel.id == template_id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            return False

        await session.delete(session_model)
        return True

    @override
    async def get_fields(self, session: AsyncSession, template_id: UUID) -> list[TemplateField]:
        result = await session.execute(
            select(TemplateFieldModel)
            .where(TemplateFieldModel.template_id == template_id)
            .order_by(TemplateFieldModel.order.asc())
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]
