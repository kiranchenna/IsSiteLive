import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import scheduler
from app.config import settings
from app.db import init_db
from app.routers import accounts, alert_channels, runs, sites


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="IsSiteLive", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sites.router)
app.include_router(accounts.router)
app.include_router(alert_channels.router)
app.include_router(runs.router)

os.makedirs(settings.screenshots_dir, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=settings.screenshots_dir), name="screenshots")


@app.get("/api/health")
def health():
    return {"status": "ok"}
