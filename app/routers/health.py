from fastapi import FastAPI

router = FastAPI()

@router.get("/health")
def get_health() -> dict[str, str]:
  return {"status": "ok"}
