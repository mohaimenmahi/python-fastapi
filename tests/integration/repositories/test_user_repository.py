from app.repositories.user_repository import UserRepository


async def test_create_and_get_by_email(db_session):
    repo = UserRepository(db_session)
    created = await repo.create(email="a@example.com", hashed_password="hashed")

    fetched = await repo.get_by_email("a@example.com")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "a@example.com"


async def test_get_by_email_missing_returns_none(db_session):
    repo = UserRepository(db_session)

    result = await repo.get_by_email("missing@example.com")

    assert result is None
