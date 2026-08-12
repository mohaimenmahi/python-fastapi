import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.models import Base

test_engine = create_async_engine(settings.test_database_url, future=True)


@pytest.fixture(scope="session", autouse=True)
async def _create_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest.fixture
async def db_session():
    async with test_engine.connect() as connection:
        await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        await session.close()
        await connection.rollback()
