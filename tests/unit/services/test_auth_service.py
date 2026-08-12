import pytest
from fastapi import Response

from app.core.security import hash_refresh_token
from app.services.auth_service import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError
from tests.unit.services.fakes import FakeRefreshTokenRepository, FakeRole, FakeRoleRepository, FakeUserRepository


def make_service(default_role_name="user"):
    return AuthService(
        FakeUserRepository(),
        FakeRoleRepository(default_role=FakeRole(id=1, name=default_role_name)),
        FakeRefreshTokenRepository(),
    )


async def test_register_creates_user_and_assigns_default_role():
    service = make_service()

    user = await service.register("a@example.com", "s3cret!")

    assert user.email == "a@example.com"
    assert [r.name for r in user.roles] == ["user"]


async def test_register_duplicate_email_raises():
    service = make_service()
    await service.register("a@example.com", "s3cret!")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register("a@example.com", "other")


async def test_login_sets_cookies_on_success():
    service = make_service()
    await service.register("a@example.com", "s3cret!")
    response = Response()

    await service.login("a@example.com", "s3cret!", response)

    assert _extract_cookie_value(response, "access_token")


async def test_login_wrong_password_raises():
    service = make_service()
    await service.register("a@example.com", "s3cret!")

    with pytest.raises(InvalidCredentialsError):
        await service.login("a@example.com", "wrong", Response())


async def test_refresh_rotates_token():
    service = make_service()
    user = await service.register("a@example.com", "s3cret!")
    login_response = Response()
    await service.login("a@example.com", "s3cret!", login_response)
    raw_refresh = _extract_cookie_value(login_response, "refresh_token")

    refresh_response = Response()
    await service.refresh(raw_refresh, refresh_response)

    assert _extract_cookie_value(refresh_response, "access_token")
    new_refresh = _extract_cookie_value(refresh_response, "refresh_token")
    assert new_refresh != raw_refresh

    old = service.refresh_token_repository._tokens[hash_refresh_token(raw_refresh)]
    new = service.refresh_token_repository._tokens[hash_refresh_token(new_refresh)]
    assert old.revoked_at is not None
    assert old.replaced_by_id == new.id


async def test_refresh_reuse_of_revoked_token_revokes_all_and_raises():
    service = make_service()
    await service.register("a@example.com", "s3cret!")
    login_response = Response()
    await service.login("a@example.com", "s3cret!", login_response)
    raw_refresh = _extract_cookie_value(login_response, "refresh_token")

    await service.refresh(raw_refresh, Response())  # first use rotates it

    with pytest.raises(InvalidCredentialsError):
        await service.refresh(raw_refresh, Response())  # reuse of the now-revoked token

    tokens = list(service.refresh_token_repository._tokens.values())
    assert len(tokens) == 2
    assert all(t.revoked_at is not None for t in tokens)


def _extract_cookie_value(response: Response, cookie_name: str) -> str:
    from http.cookies import SimpleCookie

    for header_value in response.raw_headers:
        if header_value[0].decode().lower() == "set-cookie":
            cookie = SimpleCookie()
            cookie.load(header_value[1].decode())
            if cookie_name in cookie:
                return cookie[cookie_name].value
    raise AssertionError(f"{cookie_name} cookie not set")
