from fastapi import APIRouter, Depends, FastAPI

from app.config import settings
from app.core.auth import enforce_auth
from app.routers import auth, health

app = FastAPI(title=settings.app_name, debug=settings.debug)

api_router = APIRouter(dependencies=[Depends(enforce_auth)])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

app.include_router(api_router)
