from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.clinical_fact import ClinicalFact as ClinicalFactModel
from lobanov.domain.entities.clinical_fact import ClinicalFact
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.clinical_fact_repository_protocol import ClinicalFactRepositoryProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class ClinicalFactRepository(ClinicalFactRepositoryProtocol[AsyncSession]):
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
    async def create(self, session: AsyncSession, clinical_fact: ClinicalFact) -> ClinicalFact:
        session_model = ClinicalFactModel(
            id=clinical_fact.id,
            session_id=clinical_fact.session_id,
            transcript_id=clinical_fact.transcript_id,
            template_field_id=clinical_fact.template_field_id,
            is_updated_by_user=clinical_fact.is_updated_by_user,
            value=clinical_fact.value,
            confidence=clinical_fact.confidence,
            source_text=clinical_fact.source_text,
            source_start_index=clinical_fact.source_start_index,
            source_end_index=clinical_fact.source_end_index,
            created_at=clinical_fact.created_at,
            updated_at=clinical_fact.updated_at,
        )
        session.add(session_model)
        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, fact_id: UUID) -> ClinicalFact | None:
        result = await session.execute(select(ClinicalFactModel).where(ClinicalFactModel.id == fact_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_by_session_id(self, session: AsyncSession, session_id: UUID) -> list[ClinicalFact]:
        result = await session.execute(
            select(ClinicalFactModel)
            .where(ClinicalFactModel.session_id == session_id)
            .order_by(ClinicalFactModel.created_at.desc())
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def get_by_transcript_id(self, session: AsyncSession, transcript_id: UUID) -> list[ClinicalFact]:
        result = await session.execute(
            select(ClinicalFactModel)
            .where(ClinicalFactModel.transcript_id == transcript_id)
            .order_by(ClinicalFactModel.created_at.desc())
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]

    @override
    async def delete(self, session: AsyncSession, fact_id: UUID) -> bool:
        result = await session.execute(select(ClinicalFactModel).where(ClinicalFactModel.id == fact_id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            return False

        await session.delete(session_model)
        return True

    @override
    async def update(self, session: AsyncSession, clinical_fact: ClinicalFact) -> ClinicalFact:
        result = await session.execute(select(ClinicalFactModel).where(ClinicalFactModel.id == clinical_fact.id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            error_message = f"ClinicalFact with id {clinical_fact.id} not found"
            raise ValueError(error_message)

        session_model.session_id = clinical_fact.session_id  # type: ignore[assignment]
        session_model.transcript_id = clinical_fact.transcript_id  # type: ignore[assignment]
        session_model.template_field_id = clinical_fact.template_field_id  # type: ignore[assignment]
        session_model.is_updated_by_user = clinical_fact.is_updated_by_user
        session_model.value = clinical_fact.value
        session_model.confidence = clinical_fact.confidence
        session_model.source_text = clinical_fact.source_text
        session_model.source_start_index = clinical_fact.source_start_index
        session_model.source_end_index = clinical_fact.source_end_index
        session_model.updated_at = clinical_fact.updated_at

        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_template_field_id(
        self, session: AsyncSession, session_id: UUID, template_field_id: UUID
    ) -> list[ClinicalFact]:
        result = await session.execute(
            select(ClinicalFactModel)
            .where(ClinicalFactModel.session_id == session_id)
            .where(ClinicalFactModel.template_field_id == template_field_id)
            .order_by(ClinicalFactModel.confidence.desc())
        )
        session_models = result.scalars().all()
        return [session_model.to_domain() for session_model in session_models]
