from datetime import datetime, timedelta, timezone

from fastapi import Response

from app.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    set_auth_cookies,
    verify_password,
)


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, user_repository, role_repository, refresh_token_repository) -> None:
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.refresh_token_repository = refresh_token_repository

    async def register(self, email: str, password: str):
        existing = await self.user_repository.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError(f"{email} is already registered")

        user = await self.user_repository.create(
            email=email, hashed_password=hash_password(password)
        )
        default_role = await self.role_repository.get_role_by_name("user")
        if default_role is not None:
            await self.role_repository.assign_role(user, default_role)
        return user

    async def login(self, email: str, password: str, response: Response):
        user = await self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        await self._issue_tokens(user.id, response)
        return user

    async def refresh(self, raw_token: str, response: Response) -> None:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.refresh_token_repository.get_by_hash(token_hash)
        if stored is None:
            raise InvalidCredentialsError("Invalid refresh token")

        if stored.revoked_at is not None:
            await self.refresh_token_repository.revoke_all_for_user(stored.user_id)
            raise InvalidCredentialsError("Refresh token reuse detected")

        if stored.expires_at < datetime.now(timezone.utc):
            raise InvalidCredentialsError("Refresh token expired")

        new_token = await self._issue_tokens(stored.user_id, response)
        await self.refresh_token_repository.revoke(stored, replaced_by_id=new_token.id)

    async def logout(self, raw_token: str) -> None:
        token_hash = hash_refresh_token(raw_token)
        stored = await self.refresh_token_repository.get_by_hash(token_hash)
        if stored is not None and stored.revoked_at is None:
            await self.refresh_token_repository.revoke(stored)

    async def _issue_tokens(self, user_id: int, response: Response):
        access_token = create_access_token(user_id)
        raw_refresh, refresh_hash = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        new_token = await self.refresh_token_repository.create(user_id, refresh_hash, expires_at)
        set_auth_cookies(response, access_token, raw_refresh)
        return new_token
