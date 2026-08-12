import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.dependencies import get_db_session
from app.models import Base
from app.models.role import Permission, Role
from main import app

test_engine = create_async_engine(settings.test_database_url, future=True)


@pytest.fixture(scope="session", autouse=True)
async def _create_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        user_role = Role(name="user")
        admin_role = Role(name="admin")
        write_perm = Permission(name="items:write")
        delete_perm = Permission(name="items:delete")
        admin_role.permissions.extend([write_perm, delete_perm])
        session.add_all([user_role, admin_role, write_perm, delete_perm])
        await session.commit()

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


@pytest.fixture
async def client(db_session):
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(client):
    await client.post(
        "/auth/register", json={"email": "user@example.com", "password": "Passw0rd!"}
    )
    await client.post("/auth/login", json={"email": "user@example.com", "password": "Passw0rd!"})
    return client


@pytest.fixture
async def admin_client(client, db_session):
    from sqlalchemy import select

    from app.models.role import Role
    from app.models.user import User

    await client.post(
        "/auth/register", json={"email": "admin@example.com", "password": "Passw0rd!"}
    )
    user = (
        await db_session.execute(select(User).where(User.email == "admin@example.com"))
    ).scalar_one()
    admin_role = (await db_session.execute(select(Role).where(Role.name == "admin"))).scalar_one()
    user.roles.append(admin_role)
    await db_session.commit()

    await client.post("/auth/login", json={"email": "admin@example.com", "password": "Passw0rd!"})
    return client
