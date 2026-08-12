from fastapi import Depends, HTTPException, Request, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


def public(func):
    func.__is_public__ = True
    return func


async def enforce_auth(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> User | None:
    route = request.scope.get("route")
    endpoint = getattr(route, "endpoint", None)
    if getattr(endpoint, "__is_public__", False):
        return None

    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    try:
        payload = decode_access_token(token)
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc

    user = await UserRepository(session).get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    request.state.current_user = user
    return user


def get_current_user(request: Request) -> User:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


def require_role(role_name: str):
    async def dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        current = await RoleRepository(session).get_user_with_roles(user.id)
        if current is None or not any(r.name == role_name for r in current.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return dependency


def require_permission(permission_name: str):
    async def dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        current = await RoleRepository(session).get_user_with_roles(user.id)
        has_permission = current is not None and any(
            p.name == permission_name for r in current.roles for p in r.permissions
        )
        if not has_permission:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permission")
        return user

    return dependency
