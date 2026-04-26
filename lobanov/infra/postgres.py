from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class PostgresConfig(BaseModel):
    host: str = Field(description="Хост")
    port: int = Field(description="Порт")
    username: str = Field(description="Имя пользователя")
    password: str = Field(description="Пароль пользователя")
    database: str = Field(description="Имя базы данных")

    pool_size: int = Field(
        default=10, description="Максимальное количество соединений в пуле в режиме нормальной работы"
    )

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class AsyncSessionFactory(async_sessionmaker[AsyncSession]): ...


async def provide_async_engine(config: PostgresConfig) -> AsyncGenerator[AsyncEngine]:
    kw: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "pool_size": config.pool_size,
    }

    engine = create_async_engine(config.url, **kw)
    try:
        yield engine
    finally:
        await engine.dispose()


async def provide_async_session_factory(engine: AsyncEngine) -> AsyncSessionFactory:
    return AsyncSessionFactory(engine, class_=AsyncSession, expire_on_commit=False)
