import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import retention, scheduler
from app.config import settings
from app.db import init_db, reconcile_interrupted_runs
from app.recorder import manager as recorder_manager
from app.routers import accounts, alert_channels, recordings, runs, sites


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    reconcile_interrupted_runs()
    scheduler.start()
    recorder_manager.start_sweeper()
    retention.start_sweeper()
    yield
    retention.stop_sweeper()
    recorder_manager.stop_sweeper()
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
app.include_router(recordings.router)

os.makedirs(settings.screenshots_dir, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory=settings.screenshots_dir), name="screenshots")


@app.get("/api/health")
def health():
    return {"status": "ok"}
