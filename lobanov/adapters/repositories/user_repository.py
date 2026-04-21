from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import override
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.adapters.postgres_models.user import User as UserModel
from lobanov.domain.entities.user import User
from lobanov.infra.postgres import AsyncSessionFactory
from lobanov.protocols.repositories.user_repository_protocol import UserRepositoryProtocol


class UserRepository(UserRepositoryProtocol[AsyncSession]):
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
    async def create(self, session: AsyncSession, user: User) -> User:
        user_model = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        session.add(user_model)
        await session.flush()
        await session.refresh(user_model)
        return user_model.to_domain()

    @override
    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user_model = result.scalar_one_or_none()
        return user_model.to_domain() if user_model else None

    @override
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(UserModel).where(UserModel.email == email))
        user_model = result.scalar_one_or_none()
        return user_model.to_domain() if user_model else None

    @override
    async def update(self, session: AsyncSession, user: User) -> User:
        result = await session.execute(select(UserModel).where(UserModel.id == user.id))
        user_model = result.scalar_one_or_none()
        if user_model is None:
            err_msg = f"User with id {user.id} not found"
            raise ValueError(err_msg)

        user_model.email = user.email
        user_model.hashed_password = user.hashed_password
        user_model.full_name = user.full_name
        user_model.is_active = user.is_active
        user_model.updated_at = user.updated_at

        await session.flush()
        await session.refresh(user_model)
        return user_model.to_domain()

    @override
    async def delete(self, session: AsyncSession, user_id: UUID) -> bool:
        result = await session.execute(select(UserModel).where(UserModel.id == user_id))
        user_model = result.scalar_one_or_none()
        if user_model is None:
            return False

        await session.delete(user_model)
        return True

    @override
    async def get_all(self, session: AsyncSession, limit: int = 100, offset: int = 0) -> list[User]:
        result = await session.execute(select(UserModel).offset(offset).limit(limit))
        user_models = result.scalars().all()
        return [user_model.to_domain() for user_model in user_models]
