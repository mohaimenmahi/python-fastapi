from fastapi import FastAPI

from app.config import settings
from app.routers import health

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.mount("/", health.router)

app.get("/")
def hello():
    return { "message": "Hello world" }


