from datetime import datetime, timedelta, timezone

from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


async def test_create_get_revoke_and_revoke_all(db_session):
    users = UserRepository(db_session)
    tokens = RefreshTokenRepository(db_session)
    user = await users.create(email="c@example.com", hashed_password="hashed")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    created = await tokens.create(user.id, "hash-1", expires_at)
    fetched = await tokens.get_by_hash("hash-1")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.revoked_at is None

    await tokens.revoke(fetched)
    refetched = await tokens.get_by_hash("hash-1")
    assert refetched.revoked_at is not None

    second = await tokens.create(user.id, "hash-2", expires_at)
    await tokens.revoke_all_for_user(user.id)
    refetched_second = await tokens.get_by_hash("hash-2")
    assert refetched_second.revoked_at is not None
