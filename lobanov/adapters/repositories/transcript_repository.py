from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.transcript import Transcript as TranscriptModel
from lobanov.domain.entities.transcript import Transcript
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.transcript_repository_protocol import TranscriptRepositoryProtocol


class TranscriptRepository(TranscriptRepositoryProtocol[AsyncSession]):
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
    async def create(self, session: AsyncSession, transcript: Transcript) -> Transcript:
        session_model = TranscriptModel(
            id=transcript.id,
            session_id=transcript.session_id,
            audio_record_id=transcript.audio_record_id,
            text=transcript.text,
            language=transcript.language,
            confidence_score=transcript.confidence_score,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )
        session.add(session_model)
        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, transcript_id: UUID) -> Transcript | None:
        result = await session.execute(select(TranscriptModel).where(TranscriptModel.id == transcript_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_by_session_id(self, session: AsyncSession, session_id: UUID) -> Transcript | None:
        result = await session.execute(select(TranscriptModel).where(TranscriptModel.session_id == session_id))
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def get_by_audio_record_id(self, session: AsyncSession, audio_record_id: UUID) -> Transcript | None:
        result = await session.execute(
            select(TranscriptModel).where(TranscriptModel.audio_record_id == audio_record_id)
        )
        session_model = result.scalar_one_or_none()
        return session_model.to_domain() if session_model else None

    @override
    async def update(self, session: AsyncSession, transcript: Transcript) -> Transcript:
        result = await session.execute(select(TranscriptModel).where(TranscriptModel.id == transcript.id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            err_msg = f"Transcript with id {transcript.id} not found"
            raise ValueError(err_msg)

        session_model.text = transcript.text
        session_model.language = transcript.language
        session_model.confidence_score = transcript.confidence_score
        session_model.updated_at = transcript.updated_at

        await session.flush()
        await session.refresh(session_model)
        return session_model.to_domain()

    @override
    async def delete(self, session: AsyncSession, transcript_id: UUID) -> bool:
        result = await session.execute(select(TranscriptModel).where(TranscriptModel.id == transcript_id))
        session_model = result.scalar_one_or_none()
        if session_model is None:
            return False

        await session.delete(session_model)
        return True
