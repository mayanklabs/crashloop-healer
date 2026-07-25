import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from app.api import router as api_router
from app.dashboard import router as dashboard_router
from app.database import init_db
from app.watcher import start_watcher

os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_watcher()
    yield


app = FastAPI(title="CrashLoop Healer", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/metrics", make_asgi_app())

app.include_router(api_router, prefix="/api")
app.include_router(dashboard_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3733)
