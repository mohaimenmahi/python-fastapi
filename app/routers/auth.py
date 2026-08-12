from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import get_current_user, public
from app.core.dependencies import get_auth_service
from app.core.security import clear_auth_cookies
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService, EmailAlreadyRegisteredError, InvalidCredentialsError

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@public
async def register(payload: UserCreate, service: AuthService = Depends(get_auth_service)) -> User:
    try:
        return await service.register(payload.email, payload.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/login")
@public
async def login(
    payload: LoginRequest, response: Response, service: AuthService = Depends(get_auth_service)
) -> dict[str, str]:
    try:
        await service.login(payload.email, payload.password, response)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return {"detail": "logged in"}


@router.post("/refresh")
@public
async def refresh(
    request: Request, response: Response, service: AuthService = Depends(get_auth_service)
) -> dict[str, str]:
    token = request.cookies.get("refresh_token")
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        await service.refresh(token, response)
    except InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return {"detail": "refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    token = request.cookies.get("refresh_token")
    if token:
        await service.logout(token)
    clear_auth_cookies(response)
    return {"detail": "logged out"}
