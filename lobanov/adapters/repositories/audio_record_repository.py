from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.audio_record import AudioRecord as AudioRecordModel
from lobanov.domain.entities.audio_record import AudioRecord
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.audio_record_repository_protocol import AudioRecordRepositoryProtocol


class AudioRecordRepository(AudioRecordRepositoryProtocol[AsyncSession]):
    def __init__(self, session_factory: AsyncSessionFactory) -> None:
        self._session_factory = session_factory

    @override
    @asynccontextmanager
    async def context(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @override
    async def create(self, session: AsyncSession, audio_record: AudioRecord) -> AudioRecord:
        audio_record_model = AudioRecordModel(
            id=audio_record.id,
            session_id=audio_record.session_id,
            file_path=audio_record.file_path,
            file_name=audio_record.file_name,
            file_size=audio_record.file_size,
            duration=audio_record.duration,
            format=audio_record.format,
            created_at=audio_record.created_at,
            updated_at=audio_record.updated_at,
        )
        session.add(audio_record_model)
        await session.flush()
        await session.refresh(audio_record_model)
        return audio_record_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, audio_record_id: UUID) -> AudioRecord | None:
        result = await session.execute(select(AudioRecordModel).where(AudioRecordModel.id == audio_record_id))
        audio_record_model = result.scalar_one_or_none()
        return audio_record_model.to_domain() if audio_record_model else None

    @override
    async def get_by_session_id(self, session: AsyncSession, session_id: UUID) -> AudioRecord | None:
        result = await session.execute(select(AudioRecordModel).where(AudioRecordModel.session_id == session_id))
        audio_record_model = result.scalar_one_or_none()
        return audio_record_model.to_domain() if audio_record_model else None

    @override
    async def delete(self, session: AsyncSession, audio_record_id: UUID) -> bool:
        result = await session.execute(select(AudioRecordModel).where(AudioRecordModel.id == audio_record_id))
        audio_record_model = result.scalar_one_or_none()
        if audio_record_model is None:
            return False

        await session.delete(audio_record_model)
        return True

    @override
    async def get_file_path(self, session: AsyncSession, audio_record_id: UUID) -> str | None:
        result = await session.execute(select(AudioRecordModel.file_path).where(AudioRecordModel.id == audio_record_id))
        return result.scalar_one_or_none()
