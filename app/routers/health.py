from fastapi import APIRouter

from app.core.auth import public

router = APIRouter()


@router.get("/health")
@public
def get_health() -> dict[str, str]:
    return {"status": "ok"}
